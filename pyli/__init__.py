import ast
from pyli.refs import find_free_references
from pyli.preamble import create_imports
from pyli.spec import handle_special_variables

def main(code: str,
         debug: bool = False,
         pprint_opt: bool = False,
         variables: dict = {}) -> None:
    # Set logging verbosity.
    # TODO: switch to logging.

    # Parse the code.
    tree = ast.parse(code)
    if debug:
        print(ast.dump(tree, indent=4))

    # Find the free variables.
    free_vars = find_free_references(tree)
    if debug:
        print(free_vars)
    if pprint_opt:
        free_vars.add(('pprint',))

    # Handle any special variables and output on a case-by-case basis.
    free_vars = handle_special_variables(tree, free_vars, pprint_opt)
    # We will pass in command line variables via exec.
    # TODO: use var_base_difference.
    free_vars -= {(k,) for k in variables.keys()}

    # Add imports for the rest of the free variables.
    create_imports(tree, free_vars)

    # Compile and execute the code.
    ast.fix_missing_locations(tree)
    bytecode = compile(
        tree,
        '<generated code>',  # filename
        'exec'               # Multiple statements.
    )
    # Create a clean context, since test cases might leak the default
    # arg dict across runs.
    context = dict(**variables)
    # Since we're executing inside of main(), any imports are actually
    # locals. Providing a globals dict prevents leaking any dev
    # environment leaks, and is used as a locals, meaning that any
    # "local" imports end up in the "globals" namespace.
    # See https://stackoverflow.com/a/12505166
    exec(
        bytecode,
        context # Globals
        # If not locals dict is given, globals=locals.
    )
