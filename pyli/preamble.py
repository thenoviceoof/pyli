import ast

def set_intro_variables(tree: ast.AST, variables: dict) -> None:
    assert isinstance(tree, ast.Module)
    for name, value in variables.items():
        new_node = ast.Assign(targets=[ast.Name(id=name, ctx=ast.Store())],
                              value=ast.Constant(value=value))
        # Order doesn't really matter, otherwise we wouldn't use a dict.
        tree.body.insert(0, new_node)
    ast.fix_missing_locations(tree)

def create_imports(tree: ast.AST, free_variables: set[str]) -> None:
    assert isinstance(tree, ast.Module)
    first_node = tree.body[0]
    for free_var in free_variables:
        import_stmt = ast.Import(names=[ast.alias(name=free_var)])
        ast.copy_location(import_stmt, first_node)
        tree.body.insert(0, import_stmt)
