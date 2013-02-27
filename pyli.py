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
    if isinstance(tree, str):
        return tuple(), tuple()
    if tree[0] == 'NAME':
        return (tree[1],), tuple()
    if tree[0] == 'import_name':
        return tuple(), find_tokens(tree[2])[0]
    if tree[0] == 'expr_stmt' and any(t[0] == 'EQUAL' for t in tree[1:]):
        i = (i for i,t in enumerate(tree[1:]) if t[0] == 'EQUAL').next()
        return (tuple(token for t in tree[i+1:] for token in find_tokens(t)[0]),
                tuple(token for t in tree[:i] for token in find_tokens(t)[0]))
    if all(isinstance(t, str) for t in tree):
        return tuple(), tuple()
    fb = tuple(find_tokens(t) for t in (p for p in tree if isinstance(p, tuple)))
    print fb
    free, bound = zip(*fb)
    free = tuple(x for f in free for x in f)
    bound = tuple(x for f in bound for x in f)
    return tuple(free), tuple(bound)

read_tree = convert_readable(tree)
pprint(read_tree)
pprint(find_tokens(read_tree))
