import ast
import builtins
import sys
from collections.abc import Sequence

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

BUILTIN_NAMES = set((name,) for name in dir(builtins) if not name.startswith('_'))

def find_free_references(node: ast.AST) -> set[tuple[str]]:
    '''Recurse through an AST and find all the unbound references, without the builtins'''
    # TODO: check `a = "..."; a.split()` does not have weird behavior.
    # Python keywords are consumed by parsing the ast, so there's no
    # need to worry about those.
    bound_vars, refs = find_all_references(node)
    return (refs - BUILTIN_NAMES) - bound_vars

def find_all_references(node: ast.AST) -> (set[tuple[str]], set[tuple[str]]):
    '''Recurse through an AST and find all the bound variables and references.'''
    # Start by recursing past everything that doesn't deal directly with variables.
    # Nodes are ordered as in
    # https://docs.python.org/3/library/ast.html, except if there's
    # some special processing necessary.
    if isinstance(node, ast.Module):
        return find_multiple_node_references(node.body)
    elif isinstance(node, ast.FormattedValue):
        return find_all_references(node.value)
    elif isinstance(node, ast.JoinedStr):
        return find_multiple_node_references(node.values)
    elif (isinstance(node, ast.List) or
          isinstance(node, ast.Tuple) or
          isinstance(node, ast.Set)):
        return find_multiple_node_references(node.elts)
    elif isinstance(node, ast.Dict):
        # Possible to unpack a dictionary into a literal, which has a None key.
        # Example: `{'a': 1, **existing_dict}`
        return find_multiple_node_references(
            [key for key in node.keys if key is not None] + node.values)
    elif isinstance(node, ast.Expr):
        return find_all_references(node.value)
    elif isinstance(node, ast.UnaryOp):
        return find_all_references(node.operand)
    elif isinstance(node, ast.BinOp):
        return find_multiple_node_references([node.left, node.right])
    elif isinstance(node, ast.BoolOp):
        return find_multiple_node_references(node.values)
    elif isinstance(node, ast.Compare):
        # Interestingly, this is not a BoolOp.
        return find_multiple_node_references([node.left] + node.comparators)
    elif isinstance(node, ast.Call):
        return find_multiple_node_references(
            [node.func] + list(node.args) + [keyword.value for keyword in node.keywords])
    elif isinstance(node, ast.Starred):
        return find_all_references(node.value)
    elif isinstance(node, ast.IfExp):
        return find_multiple_node_references([node.test, node.body, node.orelse])
    elif isinstance(node, ast.Attribute):
        # Check if this is a simple a.b.c reference. This does some
        # duplicate work with long attribute chains, but it is trivial
        # in the context of a CLI call.
        unwrap = node
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
        return find_all_references(node.value)
    elif isinstance(node, ast.Subscript):
        return find_multiple_node_references([node.value, node.slice])
    elif isinstance(node, ast.Slice):
        nodes = [node.lower, node.upper]
        if node.step:
            nodes.append(node.step);
        return find_multiple_node_references(nodes)
    elif isinstance(node, ast.Raise):
        return find_multiple_node_references([node.exc, node.cause])
    elif isinstance(node, ast.Delete):
        # TODO: warn users that we don't handle deletes gracefully.
        # For example: `math = 1; del math; math.exp(2)`
        # We don't want to disallow `del`, since __delattr__ might do something significant.
        return find_multiple_node_references(node.targets)
    elif (isinstance(node, ast.If) or
          isinstance(node, ast.While)):
        return find_multiple_node_references([node.test] + node.body + node.orelse)
    elif (isinstance(node, ast.Try) or
          (sys.version_info >= (3, 11, 0) and isinstance(node, ast.TryStar))):
        return find_multiple_node_references(
            node.body + node.handlers + node.orelse + node.finalbody)
    elif (isinstance(node, ast.Return) or
          isinstance(node, ast.Yield) or
          isinstance(node, ast.YieldFrom)):
        if node.value:
            return find_all_references(node.value)
        else:
            return set(), set()
    elif isinstance(node, ast.Await):
        return find_all_references(node.value)
    # Handle syntax that temporarily binds values.
    elif (isinstance(node, ast.ListComp) or
          isinstance(node, ast.SetComp) or
          isinstance(node, ast.GeneratorExp) or
          isinstance(node, ast.DictComp)):
        refs = set()
        local_binds = set()
        for gen in node.generators:
            # TODO - fix list handling from this point.
            # Earlier generators can be used in later generators.
            _, iter_names = find_all_references(gen.target)
            local_binds.update(iter_names)
            # Inline assignments cannot be used in iterables, so we
            # don't have to worry about a more permanent bind
            # overwriting the temporary one.
            _, node_refs = find_all_references(gen.iter)
            refs.update(node_refs - local_binds)
        bound_vars, node_refs = find_all_references(node.elt)
        refs.update(node_refs - local_binds)
        return bound_vars, refs
    elif isinstance(node, ast.ExceptHandler):
        bound_vars, refs = find_multiple_node_references(node.body)
        if node.name is not None:
            refs.remove(node.name)
        return bound_vars, refs
    elif (isinstance(node, ast.With) or
          isinstance(node, ast.AsyncWith)):
        # TODO
        return (set(), set())
    elif (sys.version_info >= (3, 10, 0) and isinstance(node, ast.Match)):
        # TODO
        return (set(), set())
    # Handle actual binds.
    elif (isinstance(node, ast.Assign) or
          isinstance(node, ast.AnnAssign) or
          isinstance(node, ast.AugAssign)):
        # TODO: Warn the user that something unexpected is if these are not all names.
        # TODO: handle subscripts and attribute sets.
        bound_vars = {(t.id,) for t in node.targets if isinstance(t, ast.Name)}
        # Type annotated assignments can omit an actual assignment.
        # We could treat this var as free, or raise an error, but
        # instead of trying to guess the user's intent we just let
        # them deal with the runtime consequences of whatever they're
        # up to.
        if hasattr(node, 'value'):
            node_bound_vars, refs = find_all_references(node.value)
            return bound_vars | node_bound_vars, refs
        else:
            return bound_vars, set()
    elif isinstance(node, ast.NamedExpr):
        # Example syntax: (x := 4) (walrus operator).
        # Walrus disallowed with attributes, subscripts, or tuple
        # unpacking (as of 3.11.2).
        assert isinstance(node.target, ast.Name), 'Walrus operator unexpectedly not assigning to a Name'
        name = (node.target.id,)
        bound_vars, refs = find_all_references(node.value)
        return bound_vars | {name}, refs
    elif isinstance(node, ast.Name):
        # If we see a Name, and it isn't otherwise bound, it must be free.
        return (set(), {(node.id,)})
    elif (isinstance(node, ast.Import) or
          isinstance(node, ast.ImportFrom)):
        return find_multiple_node_references(node.names)
    elif isinstance(node, ast.alias):
        # TODO: handle dot-names.
        return {(node.asname,) if node.asname else (node.name,)}, set()
    elif (isinstance(node, ast.For) or
          isinstance(node, ast.AsyncFor)):
        # Unlike generators, `for` bindings stick around afterwards.
        _, target_refs = find_all_references(node.target)
        body_bindings, refs = find_multiple_node_references(
            [node.iter] + node.body + node.orelse)
        return target_refs | body_bindings, refs
    elif (isinstance(node, ast.FunctionDef) or
          isinstance(node, ast.AsyncFunctionDef)):
        bound_vars, refs = find_multiple_node_references(
            [node.args] + node.body + node.decorator_list)
        return bound_vars | {node.name}, refs
    elif isinstance(node, ast.Lambda):
        return find_multiple_node_references([node.args, node.body])
    elif isinstance(node, ast.arguments):
        nodes = node.posonlyargs + node.args + node.kwonlyargs + \
            [node.vararg] + [node.kwarg] + node.kw_defaults + node.defaults
        return find_multiple_node_references([n for n in nodes if n])
    elif isinstance(node, ast.arg):
        return {(node.arg,)}, set()
    elif isinstance(node, ast.ClassDef):
        # Keywords are not actually used anywhere (not real bindings), but the values can have refs.
        bindings, refs = find_multiple_node_references(
            node.bases + node.keywords + node.body + node.decorator_list)
        return {(node.name,)} | bindings, refs
    # Explicitly don't do anything.
    elif (isinstance(node, ast.Constant) or
          isinstance(node, ast.Pass) or
          (sys.version_info >= (3, 12, 0) and isinstance(node, ast.TypeAlias)) or
          isinstance(node, ast.Break) or
          isinstance(node, ast.Continue) or
          # The referred variables aren't actually assigned this way.
          isinstance(node, ast.Global) or
          isinstance(node, ast.Nonlocal)):
        return set(), set()
    # Fallback case.
    else:
        # TODO: transform this to a proper warning log.
        print('Skipping reference checking for {}'.format(node))
        return (set(), set())

def find_multiple_node_references(nodes: Sequence[ast.AST]) -> (set, set):
    '''Helper function to gather all reference types from a list of nodes.'''
    bound_vars = set()
    refs = set()
    for node in nodes:
        node_bound_vars, node_refs = find_all_references(node)
        bound_vars.update(node_bound_vars)
        refs.update(node_refs)
    return bound_vars, refs
