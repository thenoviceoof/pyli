import ast
import builtins
import sys

BUILTIN_NAMES = set(name for name in dir(builtins) if not name.startswith('_'))

def find_free_references(node: ast.AST) -> set:
    '''Recurse through an AST and find all the unbound references, without the builtins'''
    # keywords are consumed by parsing the ast, so there's no need to worry about those.
    _, free_vars = find_all_references(node)
    return free_vars - BUILTIN_NAMES

def find_all_references(node: ast.AST, bound_vars: set | None = None) -> (set, set):
    '''Recurse through an AST and find all the bound and unbound references.'''
    if bound_vars is None:
        bound_vars = set()

    # Start by recursing past everything that doesn't deal directly with variables.
    # Nodes are ordered as in
    # https://docs.python.org/3/library/ast.html, except if there's
    # some special processing necessary.
    if isinstance(node, ast.Module):
        free_vars = set()
        return find_multiple_node_references(node.body, bound_vars = bound_vars)
    elif isinstance(node, ast.FormattedValue):
        return find_all_references(node.value, bound_vars = bound_vars)
    elif isinstance(node, ast.JoinedStr):
        return find_multiple_node_references(node.values, bound_vars = bound_vars)
    elif (isinstance(node, ast.List) or
          isinstance(node, ast.Tuple) or
          isinstance(node, ast.Set)):
        return find_multiple_node_references(node.elts, bound_vars = bound_vars)
    elif isinstance(node, ast.Dict):
        # Possible to unpack a dictionary, which has a matching None key.
        return find_multiple_node_references(
            [key for key in node.keys if key is not None] + node.values,
            bound_vars = bound_vars)
    elif isinstance(node, ast.Expr):
        return find_all_references(node.value, bound_vars = bound_vars)
    elif isinstance(node, ast.UnaryOp):
        return find_all_references(node.operand, bound_vars = bound_vars)
    elif isinstance(node, ast.BinOp):
        return find_multiple_node_references(
            [node.left, node.right], bound_vars = bound_vars)
    elif isinstance(node, ast.BoolOp):
        return find_multiple_node_references(node.values, bound_vars = bound_vars)
    elif isinstance(node, ast.Call):
        return find_multiple_node_references(
            [node.func] + list(node.args) + [keyword.value for keyword in node.keywords],
            bound_vars = bound_vars)
    elif isinstance(node, ast.Starred):
        return find_all_references(node.value, bound_vars = bound_vars)
    elif isinstance(node, ast.IfExp):
        return find_multiple_node_references(
            [node.test, node.body, node.orelse], bound_vars = bound_vars)
    elif isinstance(node, ast.Attribute):
        # I don't think it's possible to do shenanigans in the later parts of a dot reference.
        return find_all_references(node.value, bound_vars = bound_vars)
    elif isinstance(node, ast.Subscript):
        return find_multiple_node_references(
            [node.value, node.slice], bound_vars = bound_vars)
    elif isinstance(node, ast.Slice):
        nodes = [node.lower, node.upper]
        if node.step:
            nodes.append(node.step);
        return find_multiple_node_references(nodes, bound_vars = bound_vars)
    elif isinstance(node, ast.Raise):
        return find_multiple_node_references(
            [node.exc, node.cause], bound_vars = bound_vars)
    elif isinstance(node, ast.Delete):
        # TODO: warn users that we don't handle deletes gracefully.
        # For example: `math = 1; del math; math.exp(2)`
        # We still want to handle this, since `del math.whatever` is legal, if a bit odd.
        return find_multiple_node_references(
            node.targets, bound_vars = bound_vars)
    elif (isinstance(node, ast.If) or
          isinstance(node, ast.While)):
        return find_multiple_node_references(
            [node.test] + node.body + node.orelse, bound_vars = bound_vars)
    elif (isinstance(node, ast.Try) or
          (sys.version_info >= (3, 11, 0) and isinstance(node, ast.TryStar))):
        return find_multiple_node_references(
            node.body + node.handlers + node.orelse + node.finalbody,
            bound_vars = bound_vars)
    elif (isinstance(node, ast.Return) or
          isinstance(node, ast.Yield) or
          isinstance(node, ast.YieldFrom)):
        return find_multiple_node_references(node.body, bound_vars = bound_vars)
    elif isinstance(node, ast.Await):
        return find_all_references(node.value, bound_vars = bound_vars)
    # Handle syntax that temporarily binds values.
    elif (isinstance(node, ast.ListComp) or
          isinstance(node, ast.SetComp) or
          isinstance(node, ast.GeneratorExp) or
          isinstance(node, ast.DictComp)):
        free_vars = set()
        local_binds = set()
        for gen in node.generators:
            # Earlier generators can be used in later generators.
            _, iter_names = find_all_references(gen.target, bound_vars = local_binds)
            local_binds.update(iter_names)
            bound_vars, free_node_vars = find_all_references(gen.iter, bound_vars = bound_vars)
            free_vars.update(free_node_vars - local_binds)
        bound_vars, free_node_vars = find_all_references(node.elt, bound_vars = bound_vars)
        free_vars.update(free_node_vars - local_binds)
        return bound_vars, free_vars
    elif (isinstance(node, ast.For) or
          isinstance(node, ast.AsyncFor)):
        # TODO
        pass
    elif isinstance(node, ast.ExceptHandler):
        bound_vars, free_vars = find_multiple_node_references(node.body, bound_vars = bound_vars)
        if node.name is not None:
            free_vars.remove(node.name)
        return bound_vars, free_vars
    elif (isinstance(node, ast.With) or
          isinstance(node, ast.AsyncWith)):
        # TODO
        pass
    elif (sys.version_info >= (3, 10, 0) and isinstance(node, ast.Match)):
        # TODO
        pass
    elif (isinstance(node, ast.FunctionDef) or
          isinstance(node, ast.AsyncFunctionDef)):
        # TODO
        pass
    elif isinstance(node, ast.Lambda):
        # TODO
        pass
    elif isinstance(node, ast.ClassDef):
        # TODO
        pass
    # Handle actual binds.
    elif (isinstance(node, ast.Assign) or
          isinstance(node, ast.AnnAssign) or
          isinstance(node, ast.AugAssign)):
        for t in node.targets:
            if not isinstance(t, ast.Name):
                # TODO: Warn the user that something unexpected is happening.
                continue
            bound_vars.add(t.id)
        # Type annotated assignments can omit an actual assignment.
        # We could treat this var as free, or raise an error, but
        # instead of trying to guess the user's intent we just let
        # them deal with the runtime consequences of whatever they're
        # up to.
        if hasattr(node, 'value'):
            return find_all_references(node.value, bound_vars = bound_vars)
        else:
            return bound_vars, set()
    elif isinstance(node, ast.NamedExpr):
        if isinstance(node.target, ast.Name):
            bound_vars.add(node.target.id)
        else:
            # TODO: warn here if there's something else.
            pass
        return find_all_references(node.value, bound_vars = bound_vars)
    elif isinstance(node, ast.Name):
        # If we see a Name, and it isn't otherwise bound, it must be free.
        return (bound_vars, set([node.id]))
    elif (isinstance(node, ast.Import) or
          isinstance(node, ast.ImportFrom)):
        return find_multiple_node_references(node.names, bound_vars = bound_vars)
    elif isinstance(node, ast.alias):
        bound_vars.add(node.asname if node.asname else node.name)
        return bound_vars, set()
    # Explicitly don't do anything.
    elif (isinstance(node, ast.Constant) or
          isinstance(node, ast.Pass) or
          (sys.version_info >= (3, 12, 0) and isinstance(node, ast.TypeAlias)) or
          isinstance(node, ast.Break) or
          isinstance(node, ast.Continue) or
          # The referred variables aren't actually assigned this way.
          isinstance(node, ast.Global) or
          isinstance(node, ast.Nonlocal)):
        return bound_vars, set()
    # Fallback case.
    else:
        # TODO: transform this to a proper warning log.
        print('Skipping {}'.format(node))
        return (set(), set())

def find_multiple_node_references(nodes: list[ast.AST], bound_vars: set | None = None) -> (set, set):
    '''Helper function to gather all reference types from a list of nodes.'''
    free_vars = set()
    for n in nodes:
        bound_vars, node_free_vars = find_all_references(n, bound_vars = bound_vars)
        free_vars.update(node_free_vars)
    return bound_vars, free_vars
