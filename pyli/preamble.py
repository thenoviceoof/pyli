import ast
from collections.abc import Sequence

def create_import(import_path: Sequence[str]) -> ast.Import:
    return ast.Import(names=[ast.alias(name='.'.join(import_path))])

def create_imports(tree: ast.AST, free_variables: set[tuple[str]]) -> None:
    assert isinstance(tree, ast.Module)
    for free_var in free_variables:
        # Build up a try-import chain from most specific to least.
        current_import: ast.stmt = create_import(free_var[:1])
        for i in range(2, len(free_var)+1):
            current_import = ast.Try(
                body=[create_import(free_var[:i])],
                handlers=[ast.ExceptHandler(
                    type=ast.Name(id='ImportError', ctx=ast.Load()),
                    body=[current_import],
                )],
                orelse=[],
                finalbody=[])
        # This should continually copy line 0 to each new import.
        ast.copy_location(current_import, tree.body[0])
        # It is possible to keep pushing the rest of the body down,
        # but for some reason this easily ends up with impossible line
        # ranges (start larger than end).
        tree.body.insert(0, current_import)
