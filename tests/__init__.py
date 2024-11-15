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

from future import standard_library
standard_library.install_aliases()
from builtins import object
import pyli
import io
import sys
import re
import unittest

class StdoutManager(object):
    def __enter__(self):
        strin  = io.StringIO()
        strout = io.StringIO()
        strerr = io.StringIO()

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
            pyli.main('print("hello world")')
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
            if sys.version_info < (2, 7):
                assert re.match('<Element hello at \w+>',
                                stdout.getvalue()), stdout.getvalue()
            else:
                assert re.match('<Element \'hello\' at 0x\w+>',
                                stdout.getvalue()), stdout.getvalue()

    def test_assignments(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('x = 2')
            assert stdout.getvalue() == '2\n', stdout.getvalue()

    def test_multiple_statements(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('print("hello"); 1+1')
            assert stdout.getvalue() == 'hello\n2\n', stdout.getvalue()

    def test_loop(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('for x in range(2): x')
            assert stdout.getvalue() == '0\n1\n', stdout.getvalue()

    def test_lambda(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main("sorted([1,2,3], key=lambda x: -x)")
            assert stdout.getvalue() == '[3, 2, 1]\n', stdout.getvalue()

    def test_euler_1(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main("sum(i for i in range(10) if i % 3 == 0 or i % 5 == 0)")
            assert stdout.getvalue() == '23\n', stdout.getvalue()

    def test_calls(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('html.escape(json.dumps({"hello": "world"}))')
            result = '{&quot;hello&quot;: &quot;world&quot;}\n'
            assert stdout.getvalue() == result, stdout.getvalue()

    def test_empty_list(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('[]', pprint_opt=True)
            assert stdout.getvalue() == '[]\n', stdout.getvalue()

    def test_double_loop(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('[y for x in range(int(math.sqrt(4))) for y in range(x)]')
            assert stdout.getvalue() == '[0]\n', stdout.getvalue()

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
            pyli.main("for c in sorted(set(conts)): print('%s %d' % (c, conts.count(c)))")
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
            pyli.main("stderr.write('example')")
            # The last line print prints the number of characters written.
            assert stdout.getvalue() == '7\n', stdout.getvalue()
            assert stderr.getvalue() == 'example', stderr.getvalue()

    # part/p
    def test_p_len(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write('abs bad\ncod dud egg')
            stdin.seek(0)
            pyli.main("len(p)")
            assert stdout.getvalue() == '2\n3\n', stdout.getvalue()

    def test_part_interpolate(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write('1 thing\n2 brah')
            stdin.seek(0)
            pyli.main("'%s: %s' % (part[0], part[1])")
            assert stdout.getvalue() == '1: thing\n2: brah\n', stdout.getvalue()

    def test_part_unequal(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write('1 2\n3')
            stdin.seek(0)
            self.assertRaises(
                IndexError,
                pyli.main,
                "part[1]")

    # parts/ps
    def test_ps_dict(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write('abs bad\n')
            stdin.seek(0)
            pyli.main("dict(ps)")
            assert stdout.getvalue() == "{'abs': 'bad'}\n", stdout.getvalue()

    def test_parts_dict(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write('1 thing\n2 brah')
            stdin.seek(0)
            pyli.main("dict((int(i),v) for i,v in parts)")
            assert stdout.getvalue() == "{1: 'thing', 2: 'brah'}\n", \
                stdout.getvalue()

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

    def test_mult_line_with(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('''
class CM(object):
    def __enter__(self):
        print('enter')
    def __exit__(self, *args):
        print('exit')
with CM():
    print('pony times')
''')
            assert stdout.getvalue() == 'enter\npony times\nexit\n', \
                stdout.getvalue()

    def test_mult_line_with_as(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('''
class CM(object):
    def __enter__(self):
        print('enter')
        return 'pony times'
    def __exit__(self, *args):
        print('exit')
with CM() as s:
    print(s)
''')
            assert stdout.getvalue() == 'enter\npony times\nexit\n', \
                stdout.getvalue()

    def test_mult_line_with_as_file(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('''
with open('setup.py') as f:
    print('pony times')
''')
            assert stdout.getvalue() == 'pony times\n', \
                stdout.getvalue()

    def test_pprint(self):
        output = '''{0: 'thing',
 1: 'thing',
 2: 'thing',
 3: 'thing',
 4: 'thing',
 5: 'thing',
 6: 'thing',
 7: 'thing',
 8: 'thing',
 9: 'thing'}
'''
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('math.exp; dict((i,"thing") for i in range(10))', pprint_opt=True)
            assert stdout.getvalue() == output, stdout.getvalue()

    # ending with a func/class/decorated
    def test_end_func(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('''
def hello():
    return
''')
            assert stdout.getvalue() == '', stdout.getvalue()

    def test_end_class(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('''
class hello():
    pass
''')
            assert stdout.getvalue() == '', stdout.getvalue()

    def test_end_decorator(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('''
@functools.wraps
def hello():
    pass
''')
            assert stdout.getvalue() == '', stdout.getvalue()

    # eventually someone's going to try it
    def test_end_import(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('''
import math
''')
            assert stdout.getvalue() == '', stdout.getvalue()

    # test kwarg passing
    def test_cli_switch_passing(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('print(x)', variables={'x': 'hello'})
            assert stdout.getvalue() == 'hello\n', stdout.getvalue()

    def test_cli_switch_end_quote(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('print(x)', variables={'x': 'hello"'})
            assert stdout.getvalue() == 'hello"\n', stdout.getvalue()

    # various bugs
    def test_dir_module(self):
        with StdoutManager() as (stdin, stdout, stderr):
            pyli.main('dir(math)[0]')
            assert stdout.getvalue() == '__doc__\n', stdout.getvalue()
