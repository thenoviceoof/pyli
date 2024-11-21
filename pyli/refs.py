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
import builtins
import logging
import sys
from collections.abc import Sequence
from pyli.util import var_base_difference

LOG = logging.getLogger(__name__)

# There are 2 possible approaches to doing reference handling. Consider this example:
# `math.sqrt(2); math = 10`
# Should we insert `import math`, or not?
#   1. `math` is technically unbound at the time of first usage, and
#      this is valid python, so we should import the module. The
#      downside is that this becomes more complicated; what about
#      variables that are only set in one branch of an if-else
#      statement? Afterwards the variables could be treated as bound
#      or unbound, depending on runtime behavior. We could try to
#      import anyways, but this seems kind of messy.
#   2. Why the hell are we encouraging these shenanigans?  In English
#      we have 26 lowercase one-letter variable names, what do you
#      mean you want to re-use variables? The more likely cause of
#      these scenarios is probably incorrect input, and there's not
#      much we can do about that. Instead of trying to make
#      complicated rules, we can just opt for simpler rules, for a
#      simple tool.
#
# All that to say, if there is any binding anywhere, pyli will treat
# that variable as bound.
# Exceptions:
#  - list comprehension bindings are deliberately not accounted for
#    anywhere. List comprehensions are a nice shorthand, and we want
#    to be able to overload, say, `l`.

BUILTIN_NAMES = set(name for name in dir(builtins) if not name.startswith("_"))


def find_free_references(node: ast.AST) -> set[tuple[str, ...]]:
    """Recurse through an AST and find all the unbound references, without the builtins"""
    LOG.info("Looking for variables...")
    # Python keywords are consumed by parsing the ast, so there's no
    # need to worry about those.
    bound_vars, refs = find_references(node)
    LOG.debug("Found bound variables: {}".format(bound_vars))
    LOG.debug("Found references (including builtins): {}".format(refs))
    return var_base_difference(var_base_difference(refs, BUILTIN_NAMES), bound_vars)


def find_references(node: ast.AST) -> tuple[set[str], set[tuple[str, ...]]]:
    """Recurse through an AST and find all the bound variables and references."""
    # Start by recursing past everything that doesn't deal directly with variables.
    # Nodes are ordered as in
    # https://docs.python.org/3/library/ast.html, except if there's
    # some special processing necessary.
    if isinstance(node, ast.Module):
        return find_multiple_node_references(node.body)
    elif isinstance(node, ast.FormattedValue):
        return find_references(node.value)
    elif isinstance(node, ast.JoinedStr):
        return find_multiple_node_references(node.values)
    elif (
        isinstance(node, ast.List)
        or isinstance(node, ast.Tuple)
        or isinstance(node, ast.Set)
    ):
        return find_multiple_node_references(node.elts)
    elif isinstance(node, ast.Dict):
        # Possible to unpack a dictionary into a literal, which has a None key.
        # Example: `{'a': 1, **existing_dict}`
        return find_multiple_node_references(
            [key for key in node.keys if key is not None] + node.values
        )
    elif isinstance(node, ast.Expr):
        return find_references(node.value)
    elif isinstance(node, ast.UnaryOp):
        return find_references(node.operand)
    elif isinstance(node, ast.BinOp):
        return find_multiple_node_references([node.left, node.right])
    elif isinstance(node, ast.BoolOp):
        return find_multiple_node_references(node.values)
    elif isinstance(node, ast.Compare):
        # Interestingly, this is not a BoolOp.
        return find_multiple_node_references([node.left] + node.comparators)
    elif isinstance(node, ast.Call):
        return find_multiple_node_references(
            [node.func] + list(node.args) + [keyword.value for keyword in node.keywords]
        )
    elif isinstance(node, ast.Starred):
        return find_references(node.value)
    elif isinstance(node, ast.IfExp):
        return find_multiple_node_references([node.test, node.body, node.orelse])
    elif isinstance(node, ast.Attribute):
        # Check if this is a simple a.b.c reference. This does some
        # duplicate work with long attribute chains, but it is trivial
        # in the context of a CLI call.
        unwrap: ast.expr = node
        names = []
        while isinstance(unwrap, ast.Attribute):
            names.append(unwrap.attr)
            unwrap = unwrap.value
        if isinstance(unwrap, ast.Name):
            names.append(unwrap.id)
            return set(), {tuple(reversed(names))}
        # It is not really possible to do unusual references with the
        # `attr`; the ast of `a.b(...)` looks like Call(Attribute(...,
        # attr='b'), args=...). It is not possible to do `a.(b+c)`,
        # and `(a+b).b.c` should be automatically handled.
        return find_references(node.value)
    elif isinstance(node, ast.Subscript):
        return find_multiple_node_references([node.value, node.slice])
    elif isinstance(node, ast.Slice):
        nodes = []
        if node.lower:
            nodes.append(node.lower)
        if node.upper:
            nodes.append(node.upper)
        if node.step:
            nodes.append(node.step)
        return find_multiple_node_references(nodes)
    elif isinstance(node, ast.Raise):
        nodes = []
        if node.exc:
            nodes.append(node.exc)
        if node.cause:
            nodes.append(node.cause)
        return find_multiple_node_references(nodes)
    elif isinstance(node, ast.Delete):
        # We don't want to disallow `del`, since __delattr__ might do
        # something significant.
        return find_multiple_node_references(node.targets)
    elif isinstance(node, ast.If) or isinstance(node, ast.While):
        check_nodes = [node.test] + node.body + node.orelse
        return find_multiple_node_references(check_nodes)
    elif isinstance(node, ast.Try) or (
        sys.version_info >= (3, 11, 0) and isinstance(node, ast.TryStar)  # type: ignore
    ):
        try_nodes = node.body + node.handlers + node.orelse + node.finalbody
        return find_multiple_node_references(try_nodes)
    elif (
        isinstance(node, ast.Return)
        or isinstance(node, ast.Yield)
        or isinstance(node, ast.YieldFrom)
    ):
        if node.value:
            return find_references(node.value)
        else:
            return set(), set()
    elif isinstance(node, ast.Await):
        return find_references(node.value)
    # Handle syntax that temporarily binds values.
    elif (
        isinstance(node, ast.ListComp)
        or isinstance(node, ast.SetComp)
        or isinstance(node, ast.GeneratorExp)
        or isinstance(node, ast.DictComp)
    ):
        local_binds = set()
        bound_vars = set()
        refs = set()
        # Earlier generators can be used in later generators.
        for gen in node.generators:
            target_binds, target_refs = find_assignment_lhs_references([gen.target])
            local_binds.update(target_binds)
            # Inline assignments cannot be used in iterables, so we
            # don't have to worry about a more permanent bind
            # overwriting the temporary one.
            iter_binds, iter_refs = find_references(gen.iter)
            assert len(iter_binds) == 0
            if_binds, if_refs = find_multiple_node_references(gen.ifs)
            bound_vars.update(if_binds)
            refs.update(
                var_base_difference(target_refs | iter_refs | if_refs, local_binds)
            )
        elt_binds, elt_refs = (
            find_multiple_node_references([node.key, node.value])
            if isinstance(node, ast.DictComp)
            else find_references(node.elt)
        )
        bound_vars.update(elt_binds)
        refs.update(var_base_difference(elt_refs, local_binds))
        return bound_vars, refs
    elif isinstance(node, ast.ExceptHandler):
        bound_vars, refs = find_multiple_node_references(node.body)
        if node.name is not None:
            refs = var_base_difference(refs, {node.name})
        return bound_vars, refs
    elif isinstance(node, ast.With) or isinstance(node, ast.AsyncWith):
        binds, refs = find_multiple_node_references(node.body)
        # Assignment via with persists beyond the block.
        for item in node.items:
            assert isinstance(item, ast.withitem)
            if item.optional_vars:
                as_binds, as_refs = find_assignment_lhs_references([item.optional_vars])
                binds.update(as_binds)
                refs.update(as_refs)
            ctx_binds, ctx_refs = find_references(item.context_expr)
            binds.update(ctx_binds)
            refs.update(ctx_refs)
        return binds, refs
    elif sys.version_info >= (3, 10, 0) and isinstance(node, ast.Match):  # type: ignore
        # Extracted components are persistent.
        match_nodes = [node.subject] + node.cases
        return find_multiple_node_references(match_nodes)
    elif sys.version_info >= (3, 10, 0) and isinstance(node, ast.match_case):
        case_binds, case_refs = find_match_case_references(node.pattern)
        match_case_nodes: list[ast.AST] = []
        if node.guard:
            match_case_nodes.append(node.guard)
        match_case_nodes.extend(node.body)
        binds, refs = find_multiple_node_references(match_case_nodes)
        return binds | case_binds, refs | case_refs
    # Handle actual binds.
    elif (
        isinstance(node, ast.Assign)
        or isinstance(node, ast.AnnAssign)
        or isinstance(node, ast.AugAssign)
    ):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        else:
            targets = [node.target]
        bound_vars, lhs_refs = find_assignment_lhs_references(targets)
        # Type annotated assignments can omit an actual assignment.
        # We could treat this var as free, or raise an error, but
        # instead of trying to guess the user's intent we just let
        # them deal with the runtime consequences of whatever they're
        # up to.
        if hasattr(node, "value") and node.value:
            rhs_bound_vars, rhs_refs = find_references(node.value)
            return bound_vars | rhs_bound_vars, lhs_refs | rhs_refs
        else:
            return bound_vars, lhs_refs
    elif isinstance(node, ast.NamedExpr):
        # Example syntax: (x := 4) (walrus operator).  Walrus
        # disallowed with attributes, subscripts, or tuple unpacking
        # (as of 3.11.2), but treat it as a general assignment LHS,
        # just in case.
        lhs_bound_vars, lhs_refs = find_assignment_lhs_references([node.target])
        rhs_bound_vars, rhs_refs = find_references(node.value)
        return lhs_bound_vars | rhs_bound_vars, lhs_refs | rhs_refs
    elif isinstance(node, ast.Name):
        # If we see a Name, and it isn't otherwise bound, it must be free.
        return (set(), {(node.id,)})
    elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
        return find_multiple_node_references(node.names)
    elif isinstance(node, ast.alias):
        if node.asname:
            return {node.asname}, set()
        else:
            # This can lead to weird behavior: `import xml` will mask
            # any reference to xml.etree.ElementTree and prevent it
            # from being auto-imported.  Trying to work around this
            # seems absurdly fiddly for a weird corner case, so I'm
            # not going to do anything special about this.
            # Note that the parser automatically handles relative
            # imports so we don't need to do anything with munging
            # away the leading period.
            return {node.name.split(".")[0]}, set()
    elif isinstance(node, ast.For) or isinstance(node, ast.AsyncFor):
        # Unlike generators, `for` bindings stick around afterwards,
        # so definitely don't try to filter them out.
        # You can do things like `for math.x in range(2):`, so re-use
        # normal assignment logic.
        target_bindings, target_refs = find_assignment_lhs_references([node.target])
        for_nodes = [node.iter] + node.body + node.orelse
        body_bindings, body_refs = find_multiple_node_references(for_nodes)
        return target_bindings | body_bindings, target_refs | body_refs
    elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
        fn_nodes = [node.args] + node.body + node.decorator_list
        bound_vars, refs = find_multiple_node_references(fn_nodes)
        return bound_vars | {node.name}, refs
    elif isinstance(node, ast.Lambda):
        return find_multiple_node_references([node.args, node.body])
    elif isinstance(node, ast.arguments):
        arg_nodes = (
            node.posonlyargs
            + node.args
            + node.kwonlyargs
            + [node.vararg]
            + [node.kwarg]
            + node.kw_defaults
            + node.defaults
        )
        return find_multiple_node_references([n for n in arg_nodes if n])
    elif isinstance(node, ast.arg):
        return {node.arg}, set()
    elif isinstance(node, ast.keyword):
        binds, refs = find_references(node.value)
        return binds | ({node.arg} if node.arg else set()), refs
    elif isinstance(node, ast.ClassDef):
        # Keywords are not actually used anywhere (not real bindings), but the values can have refs.
        class_nodes = node.bases + node.keywords + node.body + node.decorator_list
        bindings, refs = find_multiple_node_references(class_nodes)
        return {node.name} | bindings, refs
    # Explicitly don't do anything.
    elif (
        isinstance(node, ast.Constant)
        or isinstance(node, ast.Pass)
        or (sys.version_info >= (3, 12, 0) and isinstance(node, ast.TypeAlias))  # type: ignore
        or isinstance(node, ast.Break)
        or isinstance(node, ast.Continue)
        or
        # The referred variables aren't actually assigned this way.
        isinstance(node, ast.Global)
        or isinstance(node, ast.Nonlocal)
    ):
        return set(), set()
    # Fallback case.
    else:
        LOG.warning("Skipping reference checking for {}".format(node))
        return (set(), set())


def find_multiple_node_references(
    nodes: Sequence[ast.AST],
) -> tuple[set[str], set[tuple[str, ...]]]:
    """Helper function to gather all reference types from a list of nodes."""
    bound_vars = set()
    refs = set()
    for node in nodes:
        node_bound_vars, node_refs = find_references(node)
        bound_vars.update(node_bound_vars)
        refs.update(node_refs)
    return bound_vars, refs


def find_assignment_lhs_references(
    targets: Sequence[ast.expr],
) -> tuple[set[str], set[tuple[str, ...]]]:
    """Only a subset of ast nodes are allowed on the LHS of an
    assignment, and names are bindings instead of free variables.
    """
    bound_vars = set()
    lhs_refs = set()
    for t in targets:
        if isinstance(t, ast.Name):
            bound_vars.add(t.id)
        elif isinstance(t, ast.Tuple) or isinstance(t, ast.List):
            tmp_binds, tmp_refs = find_assignment_lhs_references(t.elts)
            bound_vars.update(tmp_binds)
            lhs_refs.update(tmp_refs)
        else:
            # Anything that is not a plain name is actually a reference.
            # Think `module.flag = 1`.
            tmp_bound_vars, tmp_refs = find_references(t)
            # Defend against := showing up in the LHS.
            assert len(tmp_bound_vars) == 0
            lhs_refs.update(tmp_refs)
    return bound_vars, lhs_refs


if sys.version_info >= (3, 10, 0):

    def find_match_case_references(
        target: ast.pattern,
    ) -> tuple[set[str], set[tuple[str, ...]]]:
        """Find variables assignments within match case statements."""
        binds = set()
        refs = set()
        if isinstance(target, ast.MatchValue):
            # This can match attributes like `x.a`, so we should use the
            # usual LHS rules.
            value_binds, value_refs = find_assignment_lhs_references([target.value])
            binds |= value_binds
            refs |= value_refs
        elif isinstance(target, ast.MatchSingleton):
            # Used for True/False/None.
            pass
        elif isinstance(target, ast.MatchSequence):
            find_multiple_match_case_references(target.patterns, binds, refs)
        elif isinstance(target, ast.MatchMapping):
            key_binds, key_refs = find_assignment_lhs_references(target.keys)
            binds |= key_binds
            refs |= key_refs
            find_multiple_match_case_references(target.patterns, binds, refs)
            if target.rest:
                binds.add(target.rest)
        elif isinstance(target, ast.MatchClass):
            cls_binds, class_refs = find_references(target.cls)
            binds |= cls_binds
            refs |= class_refs
            find_multiple_match_case_references(target.patterns, binds, refs)
            if target.kwd_patterns:
                find_multiple_match_case_references(target.kwd_patterns, binds, refs)
        elif isinstance(target, ast.MatchStar):
            if target.name:
                binds.add(target.name)
        elif isinstance(target, ast.MatchAs):
            if target.name:
                binds.add(target.name)
            if target.pattern:
                as_binds, as_refs = find_match_case_references(target.pattern)
                binds |= as_binds
                refs |= as_refs
        elif isinstance(target, ast.MatchOr):
            find_multiple_match_case_references(target.patterns, binds, refs)
        return binds, refs

    def find_multiple_match_case_references(
        patterns: list[ast.pattern], binds: set[str], refs: set[tuple[str, ...]]
    ):
        # We normally don't modify parameters, but the match semantics are
        # simple enough we can get away with it this time.
        for pattern in patterns:
            tmp_binds, tmp_refs = find_match_case_references(pattern)
            binds |= tmp_binds
            refs |= tmp_refs
