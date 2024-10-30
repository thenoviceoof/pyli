import ast

def set_intro_variables(tree: ast.AST, variables: dict) -> None:
    assert isinstance(tree, ast.Module)
    for name, value in variables.items():
        new_node = ast.Assign(targets=[ast.Name(id=name, ctx=ast.Store())],
                              value=ast.Constant(value=value))
        # Order doesn't really matter, otherwise we wouldn't use a dict.
        tree.body.insert(new_node, 0)
    ast.fix_missing_locations(tree)
