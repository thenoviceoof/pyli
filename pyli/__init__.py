################################################################################
# "THE BEER-WARE LICENSE" (Revision 42):
# <thenoviceoof> wrote this file. As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer in return
#  - thenoviceoof

import parser
import token
import random
import string
import symbol
import sys

from pprint import pprint

################################################################################
# constants

rtok_name = dict((v,k) for k,v in token.tok_name.iteritems())
rsym_name = dict((v,k) for k,v in symbol.sym_name.iteritems())

PYTHON_KEYWORDS = ['and','from','not','while','as','elif','global','print',
                   'or','with','assert','else','if','pass','yield','in','try',
                   'break','del','except','import','class','exec','raise',
                   'continue','finally','is','return','def','for','lambda']
PYTHON_BUILTINS = [
    'abs','divmod','input','open','staticmethod',
    'all','enumerate','int','ord','str',
    'any','eval','isinstance','pow','sum',
    'basestring','execfile','issubclass','print','super',
    'bin','file','iter','property','tuple',
    'bool','filter','len','range','type',
    'bytearray','float','list','raw_input','unichr',
    'callable','format','locals','reduce','unicode',
    'chr','frozenset','long','reload','vars',
    'classmethod','getattr','map','repr','xrange',
    'cmp','globals','max','reversed','zip',
    'compile','hasattr','memoryview','round','__import__',
    'complex','hash','min','set','apply',
    'delattr','help','next','setattr','buffer',
    'dict','hex','object','slice','coerce',
    'dir','id','oct','sorted','intern',
    ]

################################################################################
# parse tree utilities

def gensym(exclusion, length=8):
    gensym = None
    while True:
        gensym = ''.join(random.choice(string.ascii_letters)
                         for i in range(length))
        if gensym not in exclusion:
            break
    return gensym

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

def convert_expr(expr):
    return convert_readable(parser.st2tuple(parser.expr(expr)))
def convert_suite(suite):
    return convert_readable(parser.st2tuple(parser.suite(suite)))

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
        return (tuple(token for t in tree[i+2:] for token in find_tokens(t)[0]),
                tuple(token for t in tree[:i+1] for token in find_tokens(t)[0]))
    # in a list comprehension, assignments via in mask frees
    if (tree[0] in ('listmaker', 'dictorsetmaker', 'testlist_comp', 'argument')
        and len(tree) > 2 and tree[2][0] in ('list_for', 'comp_for')):
        alls = set(token for t in tree for token in find_tokens(t)[0])
        free, bound = find_tokens(tree[2])
        return (tuple(alls.intersection(free).difference(bound)),
                bound)
    # don't use assignments via in
    if tree[0] in ('list_for', 'comp_for', 'for_stmt'):
        alls = set(token for t in tree for token in find_tokens(t)[0])
        bound = set(find_tokens(tree[2])[0])
        return (tuple(alls.difference(bound)),
                tuple(bound))
    # don't consider things within a module/object
    if tree[0] == 'trailer' and tree[1][0] == 'DOT':
        return tuple(), tuple()
    # handles cases like ('NEWLINE, '')
    if all(isinstance(t, str) for t in tree):
        return tuple(), tuple()
    # handle every other case, assuming at least one recursion (?)
    fb = tuple(find_tokens(t) for t in (p for p in tree if isinstance(p, tuple)))
    # bound vars shadow later free vars
    free = []
    bound = []
    for fs,bs in fb:
        free.extend(list(set(fs) - set(bound)))
        bound.extend(bs)
    return tuple(free), tuple(bound)

################################################################################
# transformation utilities

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

def get_statements(tree):
    if isinstance(tree, basestring):
        return []
    if tree[0] == 'small_stmt':
        return [tree]
    return [stat for stats in tree for stat in get_statements(stats)]

def set_equal(tree, name, code):
    '''
    Insert `name = code` as the first expression in the tree
    '''
    equality = (('stmt',
                 ('simple_stmt',
                  ('small_stmt',
                   ('expr_stmt',
                    name,
                    ('EQUAL', '='),
                    code)),
                  ('NEWLINE', ''))),)
    return tuple(['file_input'] + list(equality) + list(tree[1:]))

def insert_suite(suite, tree):
    return tuple(['file_input'] + list(suite[1:-1]) + list(tree[1:]))

def print_last_statement(tree):
    # recurse through and get all the statements (small_stmt)
    stmts = get_statements(tree)
    # check if it's statement or expression
    last = stmts[-1]
    if last[1][0] == 'print_stmt':
        # we're already printing, skip
        return tree
    elif (last[1][0] == 'expr_stmt' and
        len(last[1]) > 2 and last[1][2][0] == 'EQUAL'):
        # extract the left hand side, replicate
        refs = ('stmt',
                ('simple_stmt',
                 ('small_stmt',
                  ('expr_stmt', last[1][1])),
                 ('NEWLINE', '')))
        ltree = list(tree)
        # get the last 
        i = (i for i,r in enumerate(reversed(ltree))
             if r[0].lower() == r[0]).next()
        ltree.insert(len(ltree)-i, refs)
        tree = tuple(ltree)
    # wrap the last statement in a print
    stack = []
    tmp_tree = tree
    while tmp_tree[0] != 'small_stmt':
        # get last non-token
        i = (i for i,r in enumerate(reversed(tmp_tree))
             if isinstance(r, tuple) and r[0].lower() == r[0]).next()
        stack.append(len(tmp_tree) - i -1)
        tmp_tree = tmp_tree[len(tmp_tree) - i - 1]
    # descend into the stack
    def replace_print(tree, stack):
        if tree[0] == 'small_stmt':
            # index past (expr_stmt, testlist)
            return ('small_stmt',
                    ('print_stmt',
                     ('NAME', 'print'),
                     tree[1][1][1]))
        return tuple(replace_print(r, stack[1:]) if i == stack[0] else r
                     for i,r in enumerate(tree))
    tree = replace_print(tree, stack)
    return tree

def wrap_for(tree, var, gen):
    '''
    Wrap all the current lines (stmt's) in file_input with a for loop
    '''
    var_expr = var
    while var_expr[0] != 'expr':
        var_expr = var_expr[1]
        if not isinstance(var_expr, tuple):
            raise ValueError('No expression in the variable expression')
    return ('file_input',
            ('stmt',
             ('compound_stmt',
              ('for_stmt',
               ('NAME', 'for'),
               ('exprlist',
                var_expr),
               ('NAME', 'in'),
               gen,
               ('COLON', ':'),
               tuple(['suite',
                      ('NEWLINE', ''),
                      ('INDENT', '')] +
                     list(tree[1:-2]) +
                     [('DEDENT', '')]),
               ))),
            ('NEWLINE', ''),
            ('ENDMARKER', ''))

################################################################################
# main

def main(command, debug=False):
    '''
    String representing pyli commands
    '''
    # get a readable parse tree
    read_tree = convert_suite(command)
    if debug:
        pprint(read_tree)

    # get variable references from the tree
    free, bound = find_tokens(read_tree)
    if debug:
        pprint((free, bound))

    # don't treat keywords as free
    free = list(set(free).difference(PYTHON_KEYWORDS))
    # don't treat builtins as free either
    free = list(set(free).difference(PYTHON_BUILTINS))

    # since we want the generator for line/lines behavior, combo them
    if set(free).intersection(['l', 'li', 'line'] + ['ls', 'lis', 'lines']):
        # insert code to read stdin.readlines() generators
        sym_def = gensym(free)
        sym_gen = gensym(list(free) + [sym_def])
        gensym_def = convert_expr(sym_def)[1]
        gensym_gen = convert_expr(sym_gen)[1]
        if set(free).intersection(['l', 'li', 'line']):
            # setup aliasing from the original line var
            line_sym = gensym(free)
            line_gensym = convert_expr(line_sym)[1]
            for line_var in set(free).intersection(['l', 'li', 'line']):
                line_code = convert_expr(line_var)[1]
                read_tree = set_equal(read_tree, line_code, line_gensym)
                free.remove(line_var)
            # insert code to generate `for li in lines:` + aliasing
            read_tree = wrap_for(read_tree, line_gensym, gensym_gen)
        if set(free).intersection(['ls', 'lis', 'lines']):
            # set the other vars equal to the gensym
            names = set(free).intersection(['ls', 'lis', 'lines'])
            for name in names:
                name_expr = convert_expr(name)[1]
                read_tree = set_equal(read_tree, name_expr, gensym_gen)
                free.remove(name)
        # create a generator to assign to the lines
        code = '''def {0}():
    while True:
        li = sys.stdin.readline()
        if not li: break
        yield li
{1} = {0}()
        '''.format(sym_def, sym_gen)
        line_generator = convert_suite(code)
        read_tree = insert_suite(line_generator, read_tree)
        # import sys
        read_tree = import_packages(read_tree, ['sys'])
        free = list(set(free).difference(['sys']))
        # get the result of the last expression/statement, and print it
        read_tree = print_last_statement(read_tree)
    elif set(free).intersection(['input', 'contents', 'conts']):
        # insert code to read the entirety of stdin into a gensym
        gensym = None
        while True:
            gensym = ''.join(random.choice(string.ascii_letters)
                             for i in range(8))
            if gensym not in free:
                break
        sys_tree = convert_expr('sys.stdin.read()')[1] # get the (testlist)
        gensym = convert_expr(gensym)[1]
        # set the other vars equal to the gensym
        names = set(free).intersection(['input', 'contents', 'conts'])
        for name in names:
            name_expr = convert_expr(name)[1]
            read_tree = set_equal(read_tree, name_expr, gensym)
            free.remove(name)
        # since we insert at the beginning
        read_tree = set_equal(read_tree, gensym, sys_tree)
        # import sys
        read_tree = import_packages(read_tree, ['sys'])
        free = list(set(free).difference(['sys']))
        # treat as a single input-less execution:
        # get the result of the last expression/statement, and print it
        read_tree = print_last_statement(read_tree)
    elif 'stdin' in free:
        pass
    else:
        # treat as a single input-less execution:
        # get the result of the last expression/statement, and print it
        read_tree = print_last_statement(read_tree)

    # add imports for remaining free variables
    read_tree = import_packages(read_tree, free)
    if debug:
        pprint(read_tree)

    # run the code
    tree = convert_numeric(read_tree)
    p = parser.tuple2st(tree)
    code = p.compile('test.py')
    eval(code)