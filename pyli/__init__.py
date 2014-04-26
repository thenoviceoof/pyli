################################################################################
# "THE BEER-WARE LICENSE" (Revision 42):
# <thenoviceoof> wrote this file. As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer in return
#  - thenoviceoof

import parser
import token
import random
import re
import string
import symbol
import sys

from pprint import pprint

__version__ = (1, 4, 1)

################################################################################
# constants

rtok_name = dict((v,k) for k,v in token.tok_name.iteritems())
rsym_name = dict((v,k) for k,v in symbol.sym_name.iteritems())

PYTHON_KEYWORDS = ['and','from','not','while','as','elif','global','print',
                   'or','with','assert','else','if','pass','yield','in','try',
                   'break','del','except','import','class','exec','raise',
                   'continue','finally','is','return','def','for','lambda',
                   'True', 'False', 'None']
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

class GensymGenerator(object):
    def __init__(self, initial_set):
        self.exclude = set(initial_set)
        super(GensymGenerator, self).__init__()

    def add(self, new_exclude):
        self.exclude.add(new_exclude)

    def gensym(self, length=8):
        gensym = None
        while True:
            gensym = ''.join(random.choice(string.ascii_letters)
                             for i in range(length))
            if gensym not in self.exclude:
                break
        # add to the exclusion set
        self.add(gensym)
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
    if isinstance(tree, basestring):
        return tuple(), tuple(), tuple()
    if tree[0] == 'NAME':
        return (tree[1],), tuple(), ((tree[1],),)
    if tree[0] == 'import_name':
        return tuple(), find_tokens(tree[2])[0], tuple()
    # used only in imports
    if tree[0] in ('dotted_as_name', 'import_as_name') and len(tree) > 2:
        return (tree[3][1],), tuple(), tuple()
    # used in decorators/imports, only tree root as free
    if tree[0] == 'dotted_name':
        module = [t[1] for t in tree[1:] if t[0] == 'NAME']
        return (tree[1][1],), tuple(), (tuple(module),)
    # handle assignment, left is bound, right is free
    if tree[0] == 'expr_stmt' and any(t[0] == 'EQUAL' for t in tree[1:]):
        i = (i for i,t in enumerate(tree[1:]) if t[0] == 'EQUAL').next()
        bound = tuple(tok for t in tree[:i+1] for tok in find_tokens(t)[0])
        free  = tuple(tok for t in tree[i+2:] for tok in find_tokens(t)[0])
        modules = tuple(tok for t in tree[i+2:] for tok in find_tokens(t)[2])
        return (free, bound, modules)
    # in a list comprehension, assignments via in mask frees
    if (tree[0] in ('listmaker', 'dictorsetmaker', 'testlist_comp', 'argument')
        and len(tree) > 2 and tree[2][0] in ('list_for', 'comp_for', 'gen_for')):
        alls = set(token for t in tree for token in find_tokens(t)[0])
        modules = set(token for t in tree for token in find_tokens(t)[2])
        free, bound, _ = find_tokens(tree[2])
        free = tuple(alls.intersection(free).difference(bound))
        modules = tuple(m for m in modules if m[0] not in bound)
        return (free, bound, modules)
    # don't use assignments via in
    if tree[0] in ('list_for', 'comp_for', 'for_stmt', 'gen_for'):
        alls = set(token for t in tree for token in find_tokens(t)[0])
        modules = tuple(token for t in tree for token in find_tokens(t)[2])
        bound = set(find_tokens(tree[2])[0])
        modules = tuple(m for m in modules if m[0] not in bound)
        return (tuple(alls.difference(bound)),
                tuple(bound), modules)
    # when passing kwargs, don't count the params as free
    if tree[0] == 'varargslist':
        # don't shift it by 1, just use tree[1:] forever
        ie = [i for i,t in enumerate(tree[1:]) if t[1] == '=']
        params = [find_tokens(t)
                  for i,t in enumerate(tree[1:]) if i+1 in ie]
        tokens = [find_tokens(t) for i,t in enumerate(tree[1:]) if i+1 not in ie]
        free = set(tok for f,b,m in tokens for tok in f)
        bound = set(tok for f,b,m in tokens for tok in b)
        modules = set(tok for f,b,m in tokens for tok in m)
        free = set(free) - set(params)
        bound = set(bound) | set(params)
        modules = tuple(m for m in modules if m[0] not in bound)
        return (tuple(free), tuple(bound), tuple(modules))
    if tree[0] == 'arglist':
        free = []
        bound = []
        modules = []
        for t in tree:
            if isinstance(t, tuple) and len(t) > 2 and t[2][1] == '=':
                f, _, mods = find_tokens(t[3])
                free.extend(f)
                modules.extend(mods)
                bound.extend(find_tokens(t[1])[0])
            else:
                f,b,m = find_tokens(t)
                free.extend(f)
                bound.extend(b)
                modules.extend(m)
        return tuple(free), tuple(bound), tuple(modules)
    # don't consider names/parameters of funcs
    if tree[0] == 'funcdef':
        name = set(find_tokens(tree[2])[0])
        params = set(find_tokens(tree[3])[0])
        free, bound, modules = find_tokens(tree[5])
        free = set(free) - name - params
        bound = set(bound) & name & params
        modules = [m for m in modules if m[0] not in bound]
        return tuple(free), tuple(bound), tuple(modules)
    if tree[0] == 'classdef':
        name = find_tokens(tree[2])[0][0]
        toks = [find_tokens(t) for i,t in enumerate(tree[1:]) if i != 1]
        free = set(tok for f,b,m in toks for tok in f)
        bound = set(tok for f,b,m in toks for tok in b)
        modules = set(tok for f,b,m in toks for tok in m)
        bound.add(name)
        modules = [m for m in modules if m[0] not in bound]
        return tuple(free), tuple(bound), tuple(modules)
    if tree[0] == 'lambdef':
        params = find_tokens(tree[2])[0]
        free, bound, modules = find_tokens(tree[-1])
        bound = set(params) | set(bound)
        free = set(free) - set(params)
        modules = [m for m in modules if m[0] not in bound]
        return tuple(free), tuple(bound), tuple(modules)
    # handle with X as Y, binding Y (context managers)
    if tree[0] == 'with_item' and len(tree) > 2:
        free, bound, modules = find_tokens(tree[1:])
        as_vars = find_tokens(tree[3])[0]
        bound = set(bound) | set(as_vars)
        free = set(free) - set(as_vars)
        modules = [m for m in modules if m[0] not in bound]
        return tuple(free), tuple(bound), tuple(modules)
    # handle with X as Y, binding Y (context managers), python 2.6 edition
    if tree[0] == 'with_var' and len(tree) > 2:
        free, bound, modules = find_tokens(tree[1:])
        as_vars = find_tokens(tree[2])[0]
        bound = set(bound) | set(as_vars)
        free = set(free) - set(as_vars)
        modules = [m for m in modules if m[0] not in bound]
        return tuple(free), tuple(bound), tuple(modules)
    # don't consider things within a module/object
    if tree[0] == 'trailer' and tree[1][0] == 'DOT':
        return tuple(), tuple(), tuple()
    if (tree[0] == 'power' and tree[1][1][0] == 'NAME' and
        any(t[0] == 'trailer' and t[1][0] == 'DOT'
            for t in tree[1:])):
        module = [t[2][1] for t in tree[1:]
                  if t[0] == 'trailer' and t[1][0] == 'DOT']
        module = [tree[1][1][1]] + module
        free, bound, modules = find_tokens(tree[1:])
        if module[0] not in bound:
            modules = tuple(list(modules) + [tuple(module)])
        # generate all the sub modules
        return free, bound, modules
    # handles cases like ('NEWLINE, '')
    if all(isinstance(t, str) for t in tree):
        return tuple(), tuple(), tuple()
    # handle every other case, assuming at least one recursion (?)
    fbm = tuple(find_tokens(t) for t in (p for p in tree
                                         if isinstance(p, tuple)))
    # bound vars shadow later free vars
    free = []
    bound = []
    modules = []
    for fs,bs,ms in fbm:
        free.extend(list(set(fs) - set(bound)))
        bound.extend(bs)
        modules.extend(m for m in ms if m[0] not in bs)
    return tuple(free), tuple(bound), tuple(modules)

################################################################################
# transformation utilities

IMPORT_TEMPLATE = '''
try:
    import {0}
except ImportError:
'''

def import_packages(tree, packages):
    if tree[0] != 'file_input':
        raise ValueError('This function must be given a full parse tree')
    import_str = ''
    for plist in packages:
        indent = ''
        while plist:
            package = '.'.join(plist)
            if len(plist) > 1:
                pack_str = IMPORT_TEMPLATE.format(package)
            else:
                pack_str = 'import {0}'.format(package)
            pack_str = '\n'.join([indent + line
                                  for line in pack_str.split('\n')])
            import_str += pack_str + '\n'
            indent += '\t'
            plist = plist[:-1]
    imports = convert_suite(import_str)[1:-2]
    ntree = tuple(['file_input'] + list(imports) + list(tree[1:]))
    return ntree

def get_statements(tree):
    if isinstance(tree, basestring):
        return []
    if tree[0] == 'small_stmt':
        return [tree]
    return [stat for stats in tree for stat in get_statements(stats)]

def insert_set_equal(tree, name, code):
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

def edit_last_stmt(tree, expr=None, last_stmt_fn=None):
    return edit_last_stmt_runner(tree, expr, last_stmt_fn)[0]

def edit_last_stmt_runner(tree, expr=None, last_stmt_fn=None):
    '''
    Inserts an arbitrary stmt or small_stmt at the end of the last
    code block

    Returns (edited_tree, set(True, False, None))
        True: needs munging
        False: no munging
    '''
    # try recursing into the stmts in reverse order
    if tree[0] in ('file_input', 'suite'):
        si = [i for i,t in reversed(list(enumerate(tree[1:])))
              if t[0] in ('stmt', 'simple_stmt')][0] + 1
        rtree, mung = edit_last_stmt_runner(tree[si], expr, last_stmt_fn)
        ltree = list(tree)
        ltree[si] = rtree
        # do munging
        if mung:
            # handle suite -> simple_stmt case
            if ltree[si][0] == 'simple_stmt':
                # convert to straight stmt
                ltree = (ltree[:si] +
                         [('NEWLINE', ''),
                          ('INDENT', ''),
                          ('stmt', ltree[si]),
                          ('DEDENT', '')] +
                         ltree[si+1:])
                si += 2
            # do an in-place edit of the statement
            if last_stmt_fn:
                ltree[si] = last_stmt_fn(ltree[si])
            # insert our stmt right afterwards the last statement
            if expr:
                ltree = (ltree[:si+1] +
                         [expr] +
                         ltree[si+1:])
        tree = tuple(ltree)
        return (tree, False)
    # found a simple_stmt, recurse back up and let people know
    if tree[0] == 'simple_stmt':
        return (tree, True)
    # recurse into intermediate states
    if tree[0] in ('compound_stmt', 'stmt'):
        rtree, change = edit_last_stmt_runner(tree[1], expr, last_stmt_fn)
        return ((tree[0], rtree), change)
    # find the last suite, recurse into it
    if tree[0] in ('if_stmt', 'while_stmt', 'for_stmt', 'try_stmt', 'with_stmt'):
        # only recurse into finally
        if tree[0] == 'try_stmt' and any(t[1] == 'finally' for t in tree[1:]):
            fi = [t[1] for t in tree[1:]].index('finally') + 1  # comp for [1:]
            si = fi + 2  # suite always `finally : suite`
            tree = tuple(edit_last_stmt_runner(t, expr, last_stmt_fn)[0]
                         if i == si else
                         t
                         for i,t in enumerate(tree))
        # if there's an else, don't edit the try block
        elif tree[0] == 'try_stmt' and any(t[1] == 'else' for t in tree[1:]):
            tree = tuple(edit_last_stmt_runner(t, expr, last_stmt_fn)[0]
                         if i != 3 and t[0] == 'suite' else
                         t
                         for i,t in enumerate(tree))
        else:
            # for each suite
            tree = tuple(edit_last_stmt_runner(t, expr, last_stmt_fn)[0]
                         if isinstance(t,tuple) and t[0] == 'suite' else
                         t
                         for t in tree)
        return (tree, False)
    if tree[0] in ('funcdef', 'classdef', 'decorated'):
        return (tree, True)
    # otherwise unexpected
    raise ValueError('Unexpected Value')

def print_last_statement(tree, gensym_generator=None, pprint_opt=False):
    token = [None]
    def ensure_equality(stmt):
        if stmt[1][0] == 'simple_stmt':
            # get the last small_stmt
            esi = [i for i,t in enumerate(stmt[1][1:])
                   if t[0] == 'small_stmt'][-1] + 1
            # make sure the last expression is a set
            if stmt[1][esi][1][0] == 'expr_stmt' and len(stmt[1][esi][1]) > 2:
                # just get the name (testlist)
                name_def = stmt[1][esi][1][1]
            elif stmt[1][esi][1][0] == 'expr_stmt' and len(stmt[1][esi][1]) == 2:
                # transform into an equality
                sym_def = gensym_generator.gensym()
                name_def = convert_expr(sym_def)[1]
                code = stmt[1][esi][1][1]
                # mung the stmt itself
                stmt = ('stmt',
                        tuple(list(stmt[1][:esi]) +
                              [('small_stmt',
                                ('expr_stmt',
                                 name_def,
                                 ('EQUAL', '='),
                                 code))] +
                              list(stmt[1][esi+1:])))
            else:
                name_def = None
            # handle tuples in the name
            if name_def:
                def extract_name(expr):
                    while isinstance(expr, tuple):
                        expr = expr[1]
                    return expr

                if len(name_def) > 2:
                    name = ','.join([extract_name(t) for t in name_def
                                     if t[0] == 'test'])
                    name = '({0})'.format(name)
                else:
                    e = name_def
                    while isinstance(e, tuple):
                        e = e[1]
                    name = e
            else:
                name = None
        elif (stmt[1][0] == 'compound_stmt' and
              stmt[1][1][0] in ('funcdef', 'classdef', 'decorated')):
            def_tuple = stmt[1][1]
            if def_tuple[0] in ('funcdef', 'classdef'):
                name = def_tuple[2][1]
            else:
                # decorated: decorators (def (token) (NAME) ...)
                name = def_tuple[-1][2][1]
        else:
            raise ValueError('Something has gone wrong')
        # work around for dumb scoping rules
        token[0] = name
        return stmt
    # do the equality groundwork
    tree = edit_last_stmt(tree, last_stmt_fn=ensure_equality)
    # do the conditional print
    if token[0]:
        if pprint_opt:
            print_expr = convert_suite('''if {0} is not None:
    pprint.pprint({0})'''.format(token[0]))[1]
        else:
            print_expr = convert_suite('''if {0} is not None:
    print {0}'''.format(token[0]))[1]
        tree = edit_last_stmt(tree, expr=print_expr)
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
    # find last non-newline/endmarker, for pre-2.7
    for i in range(len(tree)):
        if tree[len(tree) - i - 1][0] not in ('NEWLINE', 'ENDMARKER'):
            break
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
                     list(tree[1:-i]) +
                     [('DEDENT', '')]),
               ))),
            ('NEWLINE', ''),
            ('ENDMARKER', ''))

################################################################################
# main

# don't overwrite pprint with the arg
def main(command, debug=False, pprint_opt=False, variables={}):
    '''
    String representing pyli commands
    '''
    # get a readable parse tree
    read_tree = convert_suite(command)
    if debug:
        pprint(read_tree)
    # run some basic checks over the input
    if (len(read_tree) < 2 or
            read_tree[0] != 'file_input' or
            read_tree[1][0] != 'stmt'):
        return

    # get variable references from the tree
    free, bound, modules = find_tokens(read_tree)
    if debug:
        pprint((free, bound, modules))
    if pprint_opt:
        free = tuple(list(free) + ['pprint'])
        modules = tuple(list(modules) + [('pprint', 'pprint')])

    # don't treat keywords as free
    bound = set(bound).union(PYTHON_KEYWORDS).union(PYTHON_BUILTINS)
    # handle CLI switch vars
    bound = bound.union(set(variables.keys()))
    free = list(set(free).difference(bound))
    # make sure the builtins don't collide
    modules = tuple(m for m in modules if m[0] not in bound)
    # make a gensyms
    gensym_generator = GensymGenerator(set(free).union(bound))
    gensym_generator.add('sys')  # prevalent in branches below

    # since we want the generator for line/lines behavior, combo them
    if set(free).intersection(['l', 'li', 'line'] + ['ls', 'lis', 'lines']):
        # insert code to read stdin.readlines() generators
        sym_def = gensym_generator.gensym()
        sym_gen = gensym_generator.gensym()
        gensym_def = convert_expr(sym_def)[1]
        gensym_gen = convert_expr(sym_gen)[1]
        if set(free).intersection(['l', 'li', 'line']):
            # setup aliasing from the original line var
            line_sym = gensym_generator.gensym()
            line_gensym = convert_expr(line_sym)[1]
            for line_var in set(free).intersection(['l', 'li', 'line']):
                line_code = convert_expr(line_var)[1]
                read_tree = insert_set_equal(read_tree, line_code, line_gensym)
                free.remove(line_var)
            # insert code to generate `for li in lines:` + aliasing
            read_tree = wrap_for(read_tree, line_gensym, gensym_gen)
        if set(free).intersection(['ls', 'lis', 'lines']):
            # set the other vars equal to the gensym
            names = set(free).intersection(['ls', 'lis', 'lines'])
            for name in names:
                name_expr = convert_expr(name)[1]
                read_tree = insert_set_equal(read_tree, name_expr, gensym_gen)
                free.remove(name)
        # create a generator to assign to the lines
        code = '''def {0}():
    while True:
        li = sys.stdin.readline()
        if not li: break
        yield li.rstrip('\\n')
{1} = {0}()
'''.format(sym_def, sym_gen)
        line_generator = convert_suite(code)
        read_tree = insert_suite(line_generator, read_tree)
        # import sys
        read_tree = import_packages(read_tree, [['sys']])
        free = list(set(free).difference(['sys']))
        # get the result of the last expression/statement, and print it
        read_tree = print_last_statement(read_tree, gensym_generator, pprint_opt)
    elif set(free).intersection(['contents', 'conts', 'cs']):
        # insert code to read the entirety of stdin into a gensym
        gensym_stdin = gensym_generator.gensym()
        sys_tree = convert_expr('sys.stdin.read()')[1] # get the (testlist)
        gensym_stdin = convert_expr(gensym_stdin)[1]
        # set the other vars equal to the gensym
        names = set(free).intersection(['contents', 'conts', 'cs'])
        for name in names:
            name_expr = convert_expr(name)[1]
            read_tree = insert_set_equal(read_tree, name_expr, gensym_stdin)
            free.remove(name)
        # since we insert at the beginning
        read_tree = insert_set_equal(read_tree, gensym_stdin, sys_tree)
        # import sys
        read_tree = import_packages(read_tree, [['sys']])
        free = list(set(free).difference(['sys']))
        # treat as a single input-less execution:
        # get the result of the last expression/statement, and print it
        read_tree = print_last_statement(read_tree, gensym_generator, pprint_opt)
    elif set(['stdin', 'stdout', 'stderr']).intersection(free):
        stdvars = ['stdin', 'stdout', 'stderr']
        for stdv in stdvars:
            if stdv in free:
                std_suite = convert_suite('{0} = sys.{0}'.format(stdv))
                read_tree = insert_suite(std_suite, read_tree)
                free.remove(stdv)
        # import sys
        read_tree = import_packages(read_tree, [['sys']])
        # treat as a single input-less execution:
        # get the result of the last expression/statement, and print it
        read_tree = print_last_statement(read_tree, gensym_generator, pprint_opt)
    if set(free).intersection(['p', 'part'] + ['ps', 'parts']):
        # insert code to read stdin.readlines() generators
        sym_def = gensym_generator.gensym()
        sym_gen = gensym_generator.gensym()
        gensym_def = convert_expr(sym_def)[1]
        gensym_gen = convert_expr(sym_gen)[1]
        if set(free).intersection(['p', 'part']):
            # setup aliasing from the original line/part vars
            line_sym = gensym_generator.gensym()
            line_gensym = convert_expr(line_sym)[1]
            part_sym = gensym_generator.gensym()
            part_gensym = convert_expr(part_sym)[1]
            for part_var in set(free).intersection(['p', 'part']):
                part_code = convert_expr(part_var)[1]
                read_tree = insert_set_equal(read_tree, part_code, line_gensym)
                free.remove(part_var)
            # insert code to generate `for part in lines:` + aliasing
            read_tree = wrap_for(read_tree, line_gensym, gensym_gen)
        if set(free).intersection(['ps', 'parts']):
            # set the other vars equal to the gensym
            names = set(free).intersection(['ps', 'parts'])
            for name in names:
                name_expr = convert_expr(name)[1]
                read_tree = insert_set_equal(read_tree, name_expr, gensym_gen)
                free.remove(name)
        # create a generator to assign to the lines
        code = '''def {0}():
    while True:
        li = sys.stdin.readline()
        if not li: break
        yield li.rstrip('\\n').split(' ')
{1} = {0}()
'''.format(sym_def, sym_gen)
        line_generator = convert_suite(code)
        read_tree = insert_suite(line_generator, read_tree)
        # import sys
        read_tree = import_packages(read_tree, [['sys']])
        free = list(set(free).difference(['sys']))
        # get the result of the last expression/statement, and print it
        read_tree = print_last_statement(read_tree, gensym_generator, pprint_opt)
    else:
        # treat as a single input-less execution:
        # get the result of the last expression/statement, and print it
        read_tree = print_last_statement(read_tree, gensym_generator, pprint_opt)

    # handle the CLI switch vars
    for k,v in variables.iteritems():
        name_expr = convert_expr(k)[1]
        # wrap in ''' for extra newline durability
        value_esc = re.sub('"', r'\"',v)
        value_expr = convert_expr('"""{0}"""'.format(value_esc))[1]
        read_tree = insert_set_equal(read_tree, name_expr, value_expr)

    # add imports for remaining module-looking things
    modules = [m for m in modules if m[0] in free]
    # dedupe
    modules = set(tuple(m) for m in modules)
    read_tree = import_packages(read_tree, modules)
    if debug:
        pprint(read_tree)

    # run the code
    tree = convert_numeric(read_tree)
    p = parser.tuple2st(tree)
    code = p.compile('test.py')
    eval(code)
