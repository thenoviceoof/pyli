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

read_tree = convert_readable(tree)
pprint(read_tree)
