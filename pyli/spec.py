import ast

PREFIX = 'PYLI_RESERVED_'

SPEC_PER_LINE = set(('l', 'li', 'line'))
SPEC_LINE_GEN = set(('ls', 'lis', 'lines'))

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
        tree.body = stdin_nodes + aliasing + tree.body
        return (free_variables - SPEC_LINE_GEN) | set(('sys',))
    else:
        # No special behavior required, just make sure to print the last statement.
        wrap_last_statement_with_print(tree.body, pprint)
        return free_variables

def set_variable_to_name(target_name: str, source_name: str) -> ast.AST:
    return ast.Assign(targets=[ast.Name(id=target_name, ctx=ast.Store())],
                      value=ast.Name(id=source_name, ctx=ast.Load()))

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
        print_expr = (
            ast.Expr(ast.Call(func=ast.Attribute(value=ast.Name(id='pprint', ctx=ast.Load()),
                                                 attr='pprint', ctx=ast.Load()),
                              args=[last_node.value], keywords=[]))
            if pprint else
            ast.Expr(ast.Call(func=ast.Name(id='print', ctx=ast.Load()),
                              args=[last_node.value], keywords=[])))
        ast.copy_location(print_expr, last_node)
        stmts[-1] = print_expr
    elif (isinstance(last_node, ast.Assign) or
          isinstance(last_node, ast.AnnAssign) or
          isinstance(last_node, ast.AugAssign)):
        # Why don't we just transform `x = 1` into `print(1)`?
        # `x.a = 1` could potentially do weird things, by overriding __setattr__.
        # Therefore, we only print the last reference.
        #
        # If there are multiple targets, we are parsing something like
        # `a = b = 1`, and only need the first reference.
        #
        # If there is destructuring, we will get a ast.Tuple object to print.
        target = None
        if isinstance(last_node.targets[0], ast.Name):
            target = ast.Name(id=last_node.targets[0].id, ctx=ast.Load())
        elif isinstance(last_node.targets[0], ast.Tuple):
            target = ast.Tuple(elts=[ast.Name(id=var.id, ctx=ast.Load())
                                     for var in last_node.targets[0].elts],
                               ctx=ast.Load())
        else:
            raise AssertionError('Unhandled assignment type: {}'.format(last_node.targets[0]))
        print_expr = ast.Expr(ast.Call(func=ast.Name(id='print', ctx=ast.Load()),
                                       args=[target], keywords=[]))
        ast.copy_location(print_expr, last_node)
        stmts.append(print_expr)
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
        # TODO: unclear what exactly should happen here.
        pass
    elif isinstance(last_node, ast.Try):
        # TODO: don't edit the try block if the there's a finally or else.
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
        # definitions, but upon reflection no one wants to see that.
        raise ValueError('Unhandled last statement node type: {}.'.format(last_node))

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
