import parser
import token
import symbol

import sys
from pprint import pprint

tree = parser.st2tuple(parser.suite(sys.argv[1]))

def convert_readable(tree):
    return tuple(((token.tok_name[i]
                   if token.tok_name.get(i) else
                   symbol.sym_name[i])
                  if isinstance(i, int) else
                  (i if isinstance(i, str) else convert_readable(i)))
                 for i in tree)

def find_tokens(tree):
    '''
    Returns (free, bound) variables from a readable parse tree

    If you can't tell if a variable should be free or bound, return as free
    '''
    # base case
    if isinstance(tree, str):
        return tuple(), tuple()
    if tree[0] == 'NAME':
        return (tree[1],), tuple()
    if tree[0] == 'import_name':
        return tuple(), find_tokens(tree[2])[0]
    # used only in imports
    if tree[0] == 'dotted_as_name' and len(tree) > 2:
        return (tree[3][1],), tuple()
    # used in decorators, only tree root as free
    if tree[0] == 'dotted_name':
        return (tree[1][1],), tuple()
    # handle assignment, left is bound, right is free
    if tree[0] == 'expr_stmt' and any(t[0] == 'EQUAL' for t in tree[1:]):
        i = (i for i,t in enumerate(tree[1:]) if t[0] == 'EQUAL').next()
        return (tuple(token for t in tree[i+1:] for token in find_tokens(t)[0]),
                tuple(token for t in tree[:i] for token in find_tokens(t)[0]))
    # handles cases like ('NEWLINE, '')
    if all(isinstance(t, str) for t in tree):
        return tuple(), tuple()
    # handle every other case, assuming at least one recursion (?)
    fb = tuple(find_tokens(t) for t in (p for p in tree if isinstance(p, tuple)))
    free, bound = zip(*fb)
    free = tuple(x for f in free for x in f)
    bound = tuple(x for f in bound for x in f)
    return tuple(free), tuple(bound)

read_tree = convert_readable(tree)
pprint(read_tree)
pprint(find_tokens(read_tree))
