import ast
from pyli.refs import find_free_references
from pyli.preamble import set_intro_variables
from pyli.spec import handle_special_variables

def main(code: str,
         debug: bool = False,
         pprint_opt: bool = False,
         variables: dict = {}) -> None:
    # Set logging verbosity.
    # TODO

    # Parse the code.
    tree = ast.parse(code)
    if debug:
        print(ast.dump(tree, indent=4))

    # Find the free variables.
    free_vars = find_free_references(tree)
    if debug:
        print(free_vars)

    # Handle any special variables and output on a case-by-case basis.
    free_vars = handle_special_variables(tree, free_vars)

    # Add variables passed in from the CLI.
    set_intro_variables(tree, variables)

    # Add imports for the rest of the free variables.
    # TODO

    # Compile and execute the code.
    ast.fix_missing_locations(tree)
    bytecode = compile(
        tree,
        '<generated code>',  # filename
        'exec'               # Multiple statements.
    )
    exec(bytecode)
