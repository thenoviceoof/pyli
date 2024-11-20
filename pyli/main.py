#  Copyright (c) <2014> <thenoviceoof>
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.

import ast
from pyli.refs import find_free_references
from pyli.preamble import create_imports
from pyli.spec import handle_special_variables
from pyli.util import var_base_difference, var_base_intersection
import logging
import sys

LOG = logging.getLogger(__name__)


def main(
    code: str,
    debug: int = logging.ERROR,
    pprint_opt: bool = False,
    variables: dict = {},
) -> None:
    # Set logging verbosity.
    logging.basicConfig(level=debug)

    # Parse the code.
    tree = ast.parse(code)
    LOG.debug("Initial parse tree...")
    LOG.debug(ast.dump(tree, indent=4))

    # Find the free variables.
    free_vars = find_free_references(tree)
    LOG.debug("Free variables found: {}".format(free_vars))
    if pprint_opt:
        free_vars.add(("pprint",))

    if debug != logging.ERROR and var_base_intersection(free_vars, {"stderr"}):
        LOG.error("Conflictng use of debug logging and writing to stderr.")
        sys.exit(2)

    # Handle any special variables and output on a case-by-case basis.
    free_vars = handle_special_variables(tree, free_vars, pprint_opt)
    # We will pass in command line variables via exec.
    free_vars = var_base_difference(free_vars, {k for k in variables.keys()})

    # Add imports for the rest of the free variables.
    create_imports(tree, free_vars)

    # Compile and execute the code.
    ast.fix_missing_locations(tree)
    LOG.debug("Final parse tree...")
    LOG.debug(ast.dump(tree, indent=4))
    LOG.info("Compiling and executing code...")
    bytecode = compile(
        tree,
        "<generated code>",  # "filename", used in tracebacks
        "exec",  # Mode, multiple statements (instead of expr)
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
        context,  # Globals
        # If not locals dict is given, globals=locals.
    )
