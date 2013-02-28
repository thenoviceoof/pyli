import parser
import token
import symbol

import sys
from pprint import pprint

def convert_readable(tree):
    def int2sym(i):
        if isinstance(i, int):
            if token.tok_name.get(i) is not None:
                return token.tok_name[i]
            else:
                return symbol.sym_name[i]
        else:
            if isinstance(i, basestring):
                return i
            else:
                return convert_readable(i)
    return tuple(int2sym(i) for i in tree)

rtok_name = dict((v,k) for k,v in token.tok_name.iteritems())
rsym_name = dict((v,k) for k,v in symbol.sym_name.iteritems())

def convert_numeric(tree):
    def sym2int(s):
        if isinstance(s, basestring):
            if rtok_name.get(s) is not None:
                return rtok_name[s]
            elif rsym_name.get(s) is not None:
                return rsym_name[s]
            elif not s:
                return s
            else:
                raise ValueError('Unexpected token %s' % s)
        elif isinstance(s, tuple):
            if rtok_name.get(s[0]) is not None:
                return (sym2int(s[0]), s[1])
            else:
                return convert_numeric(s)
    return tuple(sym2int(i) for i in tree)

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
    # handl
    if tree[0] == 'trailer' and tree[1][0] == 'DOT':
        return tuple(), tuple()
    # handles cases like ('NEWLINE, '')
    if all(isinstance(t, str) for t in tree):
        return tuple(), tuple()
    # handle every other case, assuming at least one recursion (?)
    fb = tuple(find_tokens(t) for t in (p for p in tree if isinstance(p, tuple)))
    free, bound = zip(*fb)
    free = tuple(x for f in free for x in f)
    bound = tuple(x for f in bound for x in f)
    return tuple(free), tuple(bound)

def import_packages(tree, packages):
    if tree[0] != 'file_input':
        raise ValueError('This function must be given a full parse tree')
    imports = [('stmt',
                ('simple_stmt',
                 ('small_stmt',
                  ('import_stmt',
                   ('import_name',
                    ('NAME', 'import'),
                    ('dotted_as_names',
                     ('dotted_as_name',
                      ('dotted_name',
                       ('NAME', p))))))),
                 ('NEWLINE', ''))) for p in packages]
    ntree = tuple(['file_input'] + list(imports) + list(tree[1:]))
    return ntree

if __name__ == '__main__':
    tree = parser.st2tuple(parser.suite(sys.argv[1]))
    read_tree = convert_readable(tree)
    pprint(read_tree)
    free, bound = find_tokens(read_tree)
    pprint((free, bound))
    # right now assume that we want to try and import each free thing
    free = list(set(free).difference(['print']))
    read_tree = import_packages(read_tree, free)
    tree = convert_numeric(read_tree)
    p = parser.tuple2st(tree)
    code = p.compile('test.py')
    eval(code)
