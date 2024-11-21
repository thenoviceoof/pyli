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


def var_base_intersection(
    vars_path: set[tuple[str, ...]], vars_base: set[str]
) -> set[str]:
    """
    Check whether any variable paths share a common base reference.
    This handles cases like `stdin.write` or `contents.split`.
    """
    return vars_base & {v[0] for v in vars_path}


def var_base_difference(
    vars_path: set[tuple[str, ...]], vars_base: set[str]
) -> set[tuple[str, ...]]:
    """
    Check whether any variable paths share a common base reference.
    This handles cases like `stdin.write` or `contents.split`.
    """
    return {v for v in vars_path if v[0] not in vars_base}
