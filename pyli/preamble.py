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
import logging
from collections.abc import Sequence

LOG = logging.getLogger(__name__)


def create_imports(tree: ast.AST, free_variables: set[tuple[str, ...]]) -> None:
    LOG.info("Creating imports...")
    assert isinstance(tree, ast.Module)
    for free_var in free_variables:
        LOG.debug("Creating import chain for {}".format(".".join(free_var)))
        # Build up a try-import chain from most specific to least.
        current_import: ast.stmt = create_import(free_var[:1])
        for i in range(2, len(free_var) + 1):
            current_import = ast.Try(
                body=[create_import(free_var[:i])],
                handlers=[
                    ast.ExceptHandler(
                        type=ast.Name(id="ImportError", ctx=ast.Load()),
                        body=[current_import],
                    )
                ],
                orelse=[],
                finalbody=[],
            )
        # This should continually copy line 0 to each new import.
        ast.copy_location(current_import, tree.body[0])
        # It is possible to keep pushing the rest of the body down,
        # but for some reason this easily ends up with impossible line
        # ranges (start larger than end).
        tree.body.insert(0, current_import)


def create_import(import_path: Sequence[str]) -> ast.Import:
    return ast.Import(names=[ast.alias(name=".".join(import_path))])
