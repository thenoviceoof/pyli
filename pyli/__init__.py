import ast
from pyli.refs import find_free_references
from pyli.preamble import set_intro_variables

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
    # TODO

    # Add variables passed in from the CLI.
    set_intro_variables(tree, variables)

    # Add imports for the rest of the free variables.
    # TODO

    # Compile and execute the code.
    bytecode = compile(
        tree,
        '<generated code>',  # filename
        'exec'               # Multiple statements.
    )
    exec(bytecode)
