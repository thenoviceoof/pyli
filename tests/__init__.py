import pyli
import StringIO
import sys
import re
import unittest

class StdoutManager(object):
    def __enter__(self):
        strin  = StringIO.StringIO()
        strout = StringIO.StringIO()
        strerr = StringIO.StringIO()

        self._stdin  = sys.stdin
        self._stdout = sys.stdout
        self._stderr = sys.stderr

        sys.stdin  = strin
        sys.stdout = strout
        sys.stderr = strerr
        return strin, strout, strerr

    def __exit__(self, type, value, traceback):
        sys.stdin = self._stdin
        sys.stdout = self._stdout
        sys.stderr = self._stderr

class TestPyli(unittest.TestCase):
    # test some basics
    def test_print(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('print "hello world"')
            assert stdout.getvalue() == 'hello world\n', stdout.getvalue()

    def test_basic_math(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('2+2')
            assert stdout.getvalue() == '4\n', stdout.getvalue()

    def test_import_math(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('math.sqrt(4)')
            assert stdout.getvalue() == '2.0\n', stdout.getvalue()

    def test_import_xml_child(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('xml.etree.ElementTree.fromstring('
                      '"<?xml version=\\"1.0\\"?><hello>world</hello>")')
            assert re.match('<Element \'hello\' at 0x\w+>',
                            stdout.getvalue()), stdout.getvalue()

    def test_assignments(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('x = 2')
            assert stdout.getvalue() == '2\n', stdout.getvalue()

    def test_multiple_statements(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('print "hello"; 1+1')
            assert stdout.getvalue() == 'hello\n2\n', stdout.getvalue()

    def test_loop(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('for x in range(2): x')
            assert stdout.getvalue() == '0\n1\n', stdout.getvalue()

    def test_euler_1(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main("sum(i for i in range(10) if i % 3 == 0 or i % 5 == 0)")
            assert stdout.getvalue() == '23\n', stdout.getvalue()

    def test_lambda(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main("sorted([1,2,3], key=lambda x: -x)")
            assert stdout.getvalue() == '[3, 2, 1]\n', stdout.getvalue()

    # test input, line/li/l
    def test_line(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write('hello world')
            stdin.seek(0)
            pyli.main('line')
            assert stdout.getvalue() == 'hello world\n', stdout.getvalue()

    def test_li_append(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write('hello world\nI am fine')
            stdin.seek(0)
            pyli.main('"constant " + li')
            assert stdout.getvalue() == 'constant hello world\nconstant I am fine\n', stdout.getvalue()

    def test_l_grep(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write('hi\nbye\nnye')
            stdin.seek(0)
            pyli.main("l if 'y' in l else None")
            assert stdout.getvalue() == 'bye\nnye\n', stdout.getvalue()

    def test_l_wc(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write('hi\nbye\nnye')
            stdin.seek(0)
            pyli.main("len(l)")
            assert stdout.getvalue() == '2\n3\n3\n', stdout.getvalue()

    # lines/lis/ls
    def test_lines_join(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write('hi\nbye\nnye')
            stdin.seek(0)
            pyli.main("''.join(l for l in lines)")
            assert stdout.getvalue() == 'hibyenye\n', stdout.getvalue()

    def test_lis_regex(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write('hi\nbye\nnye')
            stdin.seek(0)
            pyli.main("for l in lis: re.sub('ye', '', l)")
            assert stdout.getvalue() == 'hi\nb\nn\n', stdout.getvalue()

    def test_ls_wc(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write('hi\nbye\nnye')
            stdin.seek(0)
            pyli.main("sum(len(l) for l in ls)")
            assert stdout.getvalue() == '8\n', stdout.getvalue()

    # test contents/conts/cs
    def test_contents_sort(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write('hi\nbye\nnye')
            stdin.seek(0)
            pyli.main("''.join(sorted(list(''.join(contents.split('\\n')))))")
            assert stdout.getvalue() == 'beehinyy\n', stdout.getvalue()

    def test_conts_sorted_count(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write('hibyenye')
            stdin.seek(0)
            pyli.main("for c in sorted(set(conts)): print '%s %d' % (c, conts.count(c))")
            outcome = '''b 1
e 2
h 1
i 1
n 1
y 2
'''
            assert stdout.getvalue() == outcome, stdout.getvalue()

    def test_cs_wc(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write('hi\nbye\nnye')
            stdin.seek(0)
            pyli.main("len(cs)")
            assert stdout.getvalue() == '10\n', stdout.getvalue()

    # test direct access to stdin/stdout/stderr
    def test_stdin(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write('hi\nbye\nnye')
            stdin.seek(0)
            pyli.main("stdin.readline()")
            assert stdout.getvalue() == 'hi\n\n', stdout.getvalue()

    def test_stdout(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main("stdout.write('hello')")
            assert stdout.getvalue() == 'hello', stdout.getvalue()

    def test_stderr(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main("stderr.write('crap')")
            assert stdout.getvalue() == '', stdout.getvalue()
            assert stderr.getvalue() == 'crap', stderr.getvalue()

    # test multiple line one-liners
    def test_mult_line_if(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('''
if True:
    x = 10
else:
    x = 20
''')
            assert stdout.getvalue() == '10\n', stdout.getvalue()

    def test_mult_line_if_else(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('''
if False:
    x = 10
else:
    x = 20
''')
            assert stdout.getvalue() == '20\n', stdout.getvalue()

    def test_mult_line_elif(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('''
if False:
    x = 10
elif True:
    x = 20
else:
    x = 30
''')
            assert stdout.getvalue() == '20\n', stdout.getvalue()

    def test_mult_line_double_for(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('''
for i in range(1):
    for j in range(2):
        i,j
''')
            assert stdout.getvalue() == '(0, 0)\n(0, 1)\n', stdout.getvalue()

    def test_mult_line_block(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('''
for i in range(1):
    j = 10
    i,j
''')
            assert stdout.getvalue() == '(0, 10)\n', stdout.getvalue()

    def test_mult_line_for_else(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('''
for i in []:
    i
else:
    i = 20
''')
            assert stdout.getvalue() == '20\n', stdout.getvalue()

    def test_mult_line_try(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('''
try:
    x = 10
except:
    x = 20
''')
            assert stdout.getvalue() == '10\n', stdout.getvalue()

    def test_mult_line_except(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('''
try:
    x = int('')
except:
    x = 20
''')
            assert stdout.getvalue() == '20\n', stdout.getvalue()

    def test_mult_line_else(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('''
try:
    x = 10
except:
    x = 20
else:
    x = 30
''')
            assert stdout.getvalue() == '30\n', stdout.getvalue()


    def test_mult_line_finally(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('''
try:
    x = int('')
except:
    x = 20
else:
    x = 10
finally:
    x = 30
''')
            assert stdout.getvalue() == '30\n', stdout.getvalue()

    # ending with a func/class/decorated
    def test_end_func(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('''
def hello():
    return
''')
            assert re.match(r'<function hello at 0x\w+>', stdout.getvalue()), \
                stdout.getvalue()

    def test_end_class(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('''
class hello():
    pass
''')
            assert stdout.getvalue() == 'pyli.hello\n', stdout.getvalue()

    def test_end_decorator(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('''
@functools.wraps
def hello():
    pass
''')
            assert re.match(r'<functools.partial object at 0x\w+>',
                            stdout.getvalue()), stdout.getvalue()

    # eventually someone's going to try it
    def test_end_import(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('''
import math
''')
            assert stdout.getvalue() == '', stdout.getvalue()
