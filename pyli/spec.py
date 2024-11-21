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
import sys
from collections.abc import Sequence
from pyli.util import var_base_intersection, var_base_difference

LOG = logging.getLogger(__name__)

PREFIX = "PYLI_RESERVED_"

SPEC_PER_LINE = {"l", "li", "line"}
SPEC_LINE_GEN = {"ls", "lis", "lines"}
SPEC_CONTENTS = {"cs", "conts", "contents"}
SPEC_PER_PART = {"p", "part"}
SPEC_PARTS_GEN = {"ps", "parts"}
SPEC_STD = {"stdin", "stdout", "stderr"}


def handle_special_variables(
    tree: ast.Module, free_variables: set[tuple[str, ...]], pprint: bool
) -> set[tuple[str, ...]]:
    LOG.info("Handling special variables...")
    if var_base_intersection(free_variables, SPEC_PER_LINE):
        LOG.debug("Per-line variables detected")
        # Create a stdin line generator.
        stdin_nodes = create_stdin_reader_lines()
        tmp_line_name = PREFIX + "line"
        aliasing = [
            set_variable_to_name(v, tmp_line_name)
            for v in var_base_intersection(free_variables, SPEC_PER_LINE)
        ]
        wrap_last_statement_with_print(tree.body, pprint)
        ast.increment_lineno(tree, stdin_nodes[-1].lineno)
        # Execute the code per line.
        for_node = ast.For(
            target=ast.Name(id=tmp_line_name, ctx=ast.Store()),
            iter=ast.Name(id=PREFIX + "lines", ctx=ast.Load()),
            body=aliasing + tree.body,
            orelse=[],
        )
        tree.body = stdin_nodes + [for_node]
        return var_base_difference(free_variables, SPEC_PER_LINE) | {("sys",)}
    elif var_base_intersection(free_variables, SPEC_LINE_GEN):
        LOG.debug("Line generator variables detected")
        # Create a stdin line generator.
        stdin_nodes = create_stdin_reader_lines()
        aliasing = [
            set_variable_to_name(v, PREFIX + "lines")
            for v in var_base_intersection(free_variables, SPEC_LINE_GEN)
        ]
        # Wrap the last statement with print(...).
        wrap_last_statement_with_print(tree.body, pprint)
        ast.increment_lineno(tree, stdin_nodes[-1].lineno + len(aliasing))
        tree.body = stdin_nodes + aliasing + tree.body
        return var_base_difference(free_variables, SPEC_LINE_GEN) | {("sys",)}
    elif var_base_intersection(free_variables, SPEC_CONTENTS):
        LOG.debug("Contents variables detected")
        # Create a stdin line generator.
        stdin_node = ast.Assign(
            targets=[ast.Name(id=PREFIX + "contents", ctx=ast.Store())],
            value=ast.Call(
                func=ast_attr(("sys", "stdin", "read")), args=[], keywords=[]
            ),
        )
        aliasing = [
            set_variable_to_name(v, PREFIX + "contents")
            for v in var_base_intersection(free_variables, SPEC_CONTENTS)
        ]
        # Wrap the last statement with print(...).
        wrap_last_statement_with_print(tree.body, pprint)
        ast.increment_lineno(tree, 1 + len(aliasing))
        tree.body = [stdin_node] + aliasing + tree.body
        return var_base_difference(free_variables, SPEC_CONTENTS) | {("sys",)}
    elif var_base_intersection(free_variables, SPEC_PER_PART):
        LOG.debug("Space-delimited parts variables detected")
        # Create a stdin space-delimited parts generator.
        stdin_nodes = create_stdin_reader_parts()
        # Wrap the last statement with print(...).
        wrap_last_statement_with_print(tree.body, pprint)
        aliasing = [
            set_variable_to_name(v, PREFIX + "part")
            for v in var_base_intersection(free_variables, SPEC_PER_PART)
        ]
        ast.increment_lineno(tree, 1 + stdin_nodes[-1].lineno + len(aliasing))
        for_node = ast.For(
            target=ast.Name(id=PREFIX + "part", ctx=ast.Store()),
            iter=ast.Name(id=PREFIX + "parts", ctx=ast.Load()),
            body=aliasing + tree.body,
            orelse=[],
        )
        tree.body = stdin_nodes + [for_node]
        return var_base_difference(free_variables, SPEC_PER_PART) | {("sys",)}
    elif var_base_intersection(free_variables, SPEC_PARTS_GEN):
        LOG.debug("Space-delimited line generator detected")
        # Create a stdin space-delimited parts generator.
        stdin_nodes = create_stdin_reader_parts()
        # Wrap the last statement with print(...).
        wrap_last_statement_with_print(tree.body, pprint)
        aliasing = [
            set_variable_to_name(v, PREFIX + "parts")
            for v in var_base_intersection(free_variables, SPEC_PARTS_GEN)
        ]
        ast.increment_lineno(tree, stdin_nodes[-1].lineno + len(aliasing))
        tree.body = stdin_nodes + aliasing + tree.body
        return var_base_difference(free_variables, SPEC_PARTS_GEN) | {("sys",)}
    elif var_base_intersection(free_variables, SPEC_STD):
        LOG.debug("std* reference detected")
        aliasing = []
        if var_base_intersection(free_variables, {"stdin"}):
            aliasing.append(set_variable_to_node("stdin", ast_attr(["sys", "stdin"])))
        if var_base_intersection(free_variables, {"stdout"}):
            aliasing.append(set_variable_to_node("stdout", ast_attr(["sys", "stdout"])))
        if var_base_intersection(free_variables, {"stderr"}):
            aliasing.append(set_variable_to_node("stderr", ast_attr(["sys", "stderr"])))
        for alias in aliasing:
            ast.copy_location(alias, tree.body[0])
        # If you're using stdout, you probably want only specific things going to stdout.
        if not var_base_intersection(free_variables, {"stdout"}):
            wrap_last_statement_with_print(tree.body, pprint)
        ast.increment_lineno(tree, 1 + len(aliasing))
        tree.body = aliasing + tree.body
        return var_base_difference(free_variables, SPEC_STD) | {("sys",)}
    else:
        # No special behavior required, just make sure to print the last statement.
        LOG.debug("No special variable behavior detected")
        wrap_last_statement_with_print(tree.body, pprint)
        return free_variables


def set_variable_to_node(target_name: str, source_node: ast.expr) -> ast.Assign:
    return ast.Assign(
        targets=[ast.Name(id=target_name, ctx=ast.Store())], value=source_node
    )


def set_variable_to_name(target_name: str, source_name: str) -> ast.Assign:
    return set_variable_to_node(target_name, ast.Name(id=source_name, ctx=ast.Load()))


def ast_attr(parts: Sequence[str], load: bool = True) -> ast.expr:
    """Produce an AST representing a dot access chain."""
    if len(parts) == 1:
        return ast.Name(id=parts[0], ctx=ast.Load() if load else ast.Store())
    else:
        return ast.Attribute(
            value=ast_attr(parts[:-1], load),
            attr=parts[-1],
            ctx=ast.Load() if load else ast.Store(),
        )


def create_print_ast(
    node: ast.expr, pprint: bool, location_node: ast.AST
) -> list[ast.stmt]:
    """Wraps a given AST node into a print pattern; don't print None."""
    # Assign the result of the node to a variable, since the node could have side effects.
    tmp_var_name = PREFIX + "tmp_print_holder"
    assign_node = ast.Assign(
        targets=[ast.Name(id=tmp_var_name, ctx=ast.Store())], value=node
    )
    print_expr = (
        ast.Call(
            func=ast.Attribute(
                value=ast.Name(id="pprint", ctx=ast.Load()),
                attr="pprint",
                ctx=ast.Load(),
            ),
            args=[ast.Name(id=tmp_var_name, ctx=ast.Load())],
            keywords=[],
        )
        if pprint
        else ast.Call(
            func=ast.Name(id="print", ctx=ast.Load()),
            args=[ast.Name(id=tmp_var_name, ctx=ast.Load())],
            keywords=[],
        )
    )
    none_check = ast.If(
        test=ast.Compare(
            left=ast.Name(id=tmp_var_name, ctx=ast.Load()),
            ops=[ast.IsNot()],
            comparators=[ast.Constant(value=None)],
        ),
        body=[ast.Expr(value=print_expr)],
        orelse=[],
    )
    ast.copy_location(assign_node, location_node)
    ast.copy_location(none_check, location_node)
    return [assign_node, none_check]


def wrap_last_statement_with_print(stmts: list[ast.stmt], pprint: bool) -> None:
    """Given an AST body, wrap the "last" statement in a call to print(...)."""
    last_node = stmts[-1]
    if isinstance(last_node, ast.Expr):
        # Check if the expression is already wrapped in a print statement.
        if is_ast_print(last_node.value):
            return
        # If our given node is an Expr (statement-expression), unwrap
        # it before putting it into a print(...).
        # See https://stackoverflow.com/a/32429203
        print_stmts = create_print_ast(last_node.value, pprint, last_node)
        stmts.pop()
        stmts.extend(print_stmts)
    elif (
        isinstance(last_node, ast.Assign)
        or isinstance(last_node, ast.AnnAssign)
        or isinstance(last_node, ast.AugAssign)
    ):
        # If there's no actual assignment, then there's nothing to print.
        if not hasattr(last_node, "value"):
            return
        # - Why don't we just transform `x = 1` into `print(1)`?
        #   `x.a = 1` could potentially do weird things, by overriding __setattr__.
        #   Additionally, the rhs might be non-idempotent.
        #   Therefore, we only print the last reference.
        # - If there are multiple targets, we are parsing something like
        #   `a = b = 1`, and only need the first reference.
        # - If there is destructuring, we will get a ast.Tuple object to print.
        target = None
        if isinstance(last_node, ast.Assign):
            target = last_node.targets[0]
        else:
            target = last_node.target
        target = set_assignment_target_context(target, ast.Load())
        print_stmts = create_print_ast(target, pprint, last_node)
        stmts.extend(print_stmts)
    elif isinstance(last_node, ast.If):
        # That is disgusting, elif is represented extra If nodes.
        # Either way, we need to print the last statement of each
        # branch, and since we recurse we should get every branch
        # automatically.
        wrap_last_statement_with_print(last_node.body, pprint)
        if len(last_node.orelse):
            wrap_last_statement_with_print(last_node.orelse, pprint)
    elif isinstance(last_node, ast.For) or isinstance(last_node, ast.While):
        if last_node.orelse:
            wrap_last_statement_with_print(last_node.orelse, pprint)
        else:
            wrap_last_statement_with_print(last_node.body, pprint)
    elif isinstance(last_node, ast.Try):
        if last_node.finalbody:
            wrap_last_statement_with_print(last_node.finalbody, pprint)
            # Finally always executes, so it is the definitive last statement.
            return
        if last_node.orelse:
            # Else executes if no exceptions are handled.
            wrap_last_statement_with_print(last_node.orelse, pprint)
        else:
            wrap_last_statement_with_print(last_node.body, pprint)
        # I think you could argue that we should not be printing
        # exception handlers, but the user is doing custom work they
        # might want printed.
        for handler in last_node.handlers:
            assert isinstance(handler, ast.ExceptHandler)
            wrap_last_statement_with_print(handler.body, pprint)
    elif isinstance(last_node, ast.With):
        wrap_last_statement_with_print(last_node.body, pprint)
    elif sys.version_info >= (3, 10, 0) and isinstance(last_node, ast.Match):
        for case in last_node.cases:
            assert isinstance(case, ast.match_case)
            wrap_last_statement_with_print(case.body, pprint)
    else:
        # There are many statements that shouldn't be printed, like
        # Raise or Assert, enough that I will not bother explicitly
        # listing them out.
        # In days of yore, we used to print function/class
        # definitions, but upon reflection who would want to see that?
        pass


def is_ast_print(node: ast.AST) -> bool:
    """Check if the given node represents a print(...) call."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "print"
    )


def create_stdin_reader_lines() -> list[ast.stmt]:
    code = """
def {fn}():
    while True:
        li = sys.stdin.readline()
        if not li:
            break
        yield li.rstrip('\\n')
{gen} = {fn}()
    """.format(
        fn=PREFIX + "line_generator", gen=PREFIX + "lines"
    )
    tmp_tree = ast.parse(code)
    return tmp_tree.body


def create_stdin_reader_parts() -> list[ast.stmt]:
    code = """
def {fn}():
    while True:
        li = sys.stdin.readline()
        if not li:
            break
        yield li.rstrip('\\n').split(' ')
{gen} = {fn}()
    """.format(
        fn=PREFIX + "parts_generator", gen=PREFIX + "parts"
    )
    tmp_tree = ast.parse(code)
    return tmp_tree.body


def set_assignment_target_context(
    target: ast.expr, context: ast.expr_context
) -> ast.expr:
    """Iterate through an assignment target and switch between
    load/store context.
    """
    # Thankfully, there is a limited number of ast nodes involved in assignment.
    if isinstance(target, ast.Attribute):
        return ast.Attribute(
            set_assignment_target_context(target.value, context), target.attr, context
        )
    elif isinstance(target, ast.Subscript):
        return ast.Subscript(
            set_assignment_target_context(target.value, context),
            set_assignment_target_context(target.slice, context),
            context,
        )
    elif isinstance(target, ast.Starred):
        return ast.Starred(
            set_assignment_target_context(target.value, context), context
        )
    elif isinstance(target, ast.Name):
        return ast.Name(target.id, context)
    elif isinstance(target, ast.List):
        return ast.List(
            [set_assignment_target_context(elt, context) for elt in target.elts],
            context,
        )
    elif isinstance(target, ast.Tuple):
        return ast.Tuple(
            [set_assignment_target_context(elt, context) for elt in target.elts],
            context,
        )
    elif isinstance(target, ast.Constant):
        return target
    else:
        raise ValueError(
            "Unexpected node type found in assignment context: {}".format(target)
        )
