import ast

PREFIX = 'PYLI_RESERVED_'

SPEC_PER_LINE = set(('l', 'li', 'line'))
SPEC_LINE_GEN = set(('ls', 'lis', 'lines'))
SPEC_CONTENTS = set(('cs', 'conts', 'contents'))

def handle_special_variables(tree: ast.AST,
                             free_variables: set[str],
                             pprint: bool) -> set[str]:
    if free_variables & SPEC_PER_LINE:
        # Create a stdin line generator.
        stdin_nodes = create_stdin_reader()
        tmp_line_name = PREFIX + 'line'
        aliasing = [set_variable_to_name(v, tmp_line_name)
                    for v in free_variables & SPEC_PER_LINE]
        wrap_last_statement_with_print(tree.body, pprint)
        ast.increment_lineno(tree, stdin_nodes[-1].lineno)
        # Execute the code per line.
        for_node = ast.For(
            target = ast.Name(id=tmp_line_name, ctx=ast.Store()),
            iter = ast.Name(id=PREFIX + 'lines', ctx=ast.Load()),
            body = aliasing + tree.body,
            orelse = []
        )
        tree.body = stdin_nodes + [for_node]
        return (free_variables - SPEC_PER_LINE) | set(('sys',))
    elif free_variables & SPEC_LINE_GEN:
        # Create a stdin line generator.
        stdin_nodes = create_stdin_reader()
        aliasing = [set_variable_to_name(v, PREFIX + 'lines')
                    for v in free_variables & SPEC_LINE_GEN]
        # Wrap the last statement with print(...).
        wrap_last_statement_with_print(tree.body, pprint)
        ast.increment_lineno(tree, stdin_nodes[-1].lineno + len(aliasing))
        tree.body = stdin_nodes + aliasing + tree.body
        return (free_variables - SPEC_LINE_GEN) | set(('sys',))
    elif free_variables & SPEC_CONTENTS:
        # Create a stdin line generator.
        stdin_node = ast.Assign(
            targets=[ast.Name(id=PREFIX+'contents', ctx=ast.Store())],
            value=ast.Call(func=ast_attr(('sys', 'stdin', 'read'), load=True),
                           args=[], keywords=[]))
        aliasing = [set_variable_to_name(v, PREFIX + 'contents')
                    for v in free_variables & SPEC_CONTENTS]
        # Wrap the last statement with print(...).
        wrap_last_statement_with_print(tree.body, pprint)
        ast.increment_lineno(tree, 1 + len(aliasing))
        tree.body = [stdin_node] + aliasing + tree.body
        return (free_variables - SPEC_CONTENTS) | set(('sys',))
    else:
        # No special behavior required, just make sure to print the last statement.
        wrap_last_statement_with_print(tree.body, pprint)
        return free_variables

def set_variable_to_name(target_name: str, source_name: str) -> ast.AST:
    return ast.Assign(targets=[ast.Name(id=target_name, ctx=ast.Store())],
                      value=ast.Name(id=source_name, ctx=ast.Load()))

def ast_attr(parts: list[str], load: bool = False) -> ast.AST:
    '''Produce an AST representing a dot access chain.'''
    if len(parts) == 1:
        return ast.Name(id=parts[0], ctx=ast.Load() if load else ast.Store())
    else:
        return ast.Attribute(value=ast_attr(parts[:-1], load),
                             attr=parts[-1],
                             ctx=ast.Load() if load else ast.Store())

def create_print_ast(node: ast.AST, pprint: bool, location_node: ast.AST) -> list[ast.AST]:
    '''Wraps a given AST node into a print pattern; don't print None.'''
    # Assign the result of the node to a variable, since the node could have side effects.
    tmp_var_name = PREFIX + 'tmp_print_holder'
    assign_node = ast.Assign(targets=[ast.Name(id=tmp_var_name, ctx=ast.Store())],
                             value=node)
    print_expr = (
        ast.Call(func=ast.Attribute(value=ast.Name(id='pprint', ctx=ast.Load()),
                                    attr='pprint', ctx=ast.Load()),
                 args=[ast.Name(id=tmp_var_name, ctx=ast.Load())], keywords=[])
        if pprint else
        ast.Call(func=ast.Name(id='print', ctx=ast.Load()),
                 args=[ast.Name(id=tmp_var_name, ctx=ast.Load())], keywords=[])
    )
    none_check = ast.If(test=ast.Compare(left=ast.Name(id=tmp_var_name, ctx=ast.Load()),
                                         ops=[ast.IsNot()],
                                         comparators=[ast.Constant(value=None)]),
                        body=[ast.Expr(value=print_expr)],
                        orelse=[])
    ast.copy_location(assign_node, location_node)
    ast.copy_location(none_check, location_node)
    return [assign_node, none_check]

def wrap_last_statement_with_print(stmts: ast.AST, pprint: bool) -> None:
    '''Given an AST body, wrap the "last" statement in a call to print(...).'''
    last_node = stmts[-1]
    if isinstance(last_node, ast.Expr):
        # Check if the expression is already wrapped in a print statement.
        if is_ast_print(last_node.value):
            return
        # If our given node is an Expr (statement-expression), unwrap
        # it before putting it into a print(...).
        # See https://stackoverflow.com/a/32429203
        print_stmts = create_print_ast(last_node.value, pprint, last_node)
        stmts.pop()
        stmts.extend(print_stmts)
    elif (isinstance(last_node, ast.Assign) or
          isinstance(last_node, ast.AnnAssign) or
          isinstance(last_node, ast.AugAssign)):
        # - Why don't we just transform `x = 1` into `print(1)`?
        #   `x.a = 1` could potentially do weird things, by overriding __setattr__.
        #   Therefore, we only print the last reference.
        # - If there are multiple targets, we are parsing something like
        #   `a = b = 1`, and only need the first reference.
        # - If there is destructuring, we will get a ast.Tuple object to print.
        target = None
        if isinstance(last_node.targets[0], ast.Name):
            target = ast.Name(id=last_node.targets[0].id, ctx=ast.Load())
        elif isinstance(last_node.targets[0], ast.Tuple):
            target = ast.Tuple(elts=[ast.Name(id=var.id, ctx=ast.Load())
                                     for var in last_node.targets[0].elts],
                               ctx=ast.Load())
        else:
            raise AssertionError('Unhandled assignment type: {}'.format(last_node.targets[0]))
        print_stmts = create_print_ast(target, pprint, last_node)
        stmts.extend(print_stmts)
    elif isinstance(last_node, ast.If):
        # That is disgusting, elif is represented extra If nodes.
        # Either way, we need to print the last statement of each
        # branch, and since we recurse we should get every branch
        # automatically.
        wrap_last_statement_with_print(last_node.body, pprint)
        if len(last_node.orelse):
            wrap_last_statement_with_print(last_node.orelse, pprint)
    elif (isinstance(last_node, ast.For) or
          isinstance(last_node, ast.While)):
        if last_node.orelse:
            wrap_last_statement_with_print(last_node.orelse, pprint)
        else:
            wrap_last_statement_with_print(last_node.body, pprint)
    elif isinstance(last_node, ast.Try):
        if last_node.finalbody:
            wrap_last_statement_with_print(last_node.finalbody, pprint)
            # Finally always executes, so it is the definitive last statement.
            return
        if last_node.orelse:
            # Else executes if no exceptions are handled.
            wrap_last_statement_with_print(last_node.orelse, pprint)
        else:
            wrap_last_statement_with_print(last_node.body, pprint)
        # I think you could argue that we should not be printing
        # exception handlers, but the user is doing custom work they
        # might want printed.
        for handler in last_node.handlers:
            assert isinstance(handler, ast.ExceptHandler)
            wrap_last_statement_with_print(handler.body, pprint)
    elif isinstance(last_node, ast.With):
        wrap_last_statement_with_print(last_node.body, pprint)
    # TODO: handle `match`.
    else:
        # There are many statements that shouldn't be printed, like
        # Raise or Assert, enough that I will not bother explicitly
        # listing them out.
        # In days of yore, we used to print function/class
        # definitions, but upon reflection who would want to see that?
        pass

def is_ast_print(node: ast.AST) -> bool:
    '''Check if the given node represents a print(...) call.'''
    return (isinstance(node, ast.Call) and
            isinstance(node.func, ast.Name) and
            node.func.id == 'print')
        
def create_stdin_reader() -> list[ast.AST]:
    code = '''
def {fn}():
    while True:
        li = sys.stdin.readline()
        if not li:
            break
        yield li.rstrip('\\n')
{gen} = {fn}()
    '''.format(fn = PREFIX + 'line_generator', gen = PREFIX + 'lines')
    tmp_tree = ast.parse(code)
    return tmp_tree.body
