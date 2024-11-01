import ast

PREFIX = 'PYLI_RESERVED_'

SPEC_PER_LINE = set(('l', 'li', 'line'))
SPEC_LINE_GEN = set(('ls', 'lis', 'lines'))

def handle_special_variables(tree: ast.AST, free_variables: set[str]) -> set[str]:
    if free_variables & SPEC_PER_LINE:
        # Create a stdin line generator.
        stdin_nodes = create_stdin_reader()
        tmp_line_name = PREFIX + 'line'
        aliasing = [set_variable_to_name(v, tmp_line_name)
                    for v in free_variables & SPEC_PER_LINE]
        # Wrap the last statement with print(...).
        tree.body[-1] = wrap_statement_with_print(tree.body[-1])
        # Execute the code per line.
        for_node = ast.For(
            target = ast.Name(id=tmp_line_name, ctx=ast.Store()),
            iter = ast.Name(id=PREFIX + 'lines', ctx=ast.Load()),
            body = aliasing + tree.body,
            orelse = []
        )
        tree.body = stdin_nodes + [for_node]
        return free_variables - SPEC_PER_LINE + set(('sys',))
    elif free_variables & SPEC_LINE_GEN:
        # Create a stdin line generator.
        stdin_nodes = create_stdin_reader()
        aliasing = [set_variable_to_name(v, PREFIX + 'lines')
                    for v in free_variables & SPEC_LINE_GEN]
        # Wrap the last statement with print(...).
        tree.body[-1] = wrap_statement_with_print(tree.body[-1])
        tree.body = stdin_nodes + aliasing + tree.body
        return free_variables - SPEC_LINE_GEN + set(('sys',))
    else:
        # No special behavior required, just make sure to print the last statement.
        tree.body[-1] = wrap_statement_with_print(tree.body[-1])
        return free_variables

def set_variable_to_name(target_name: str, source_name: str) -> ast.AST:
    return ast.Assign(targets=[ast.Name(id=target_name, ctx=ast.Store())],
                      value=ast.Name(id=source_name, ctx=ast.Load()))

def wrap_statement_with_print(node: ast.AST) -> ast.AST:
    if isinstance(node, ast.Expr):
        # Check if the expression is already wrapped in a print statement.
        if (isinstance(node.value, ast.Call) and
            isinstance(node.value.func, ast.Name) and
            node.value.func.id == 'print'):
            return node
        # If our given node is an Expr (statement-expression), unwrap
        # it before putting it into a print(...).
        # See https://stackoverflow.com/a/32429203
        print_expr = ast.Expr(ast.Call(func=ast.Name(id='print', ctx=ast.Load()),
                                   args=[node.value], keywords=[]))
        ast.copy_location(print_expr, node)
        return print_expr
    else:
        raise ValueError('Unhandled node type.')
        
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
