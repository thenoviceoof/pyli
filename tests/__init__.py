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

import io
import sys
import re
import unittest
from pyli.main import main


class StdoutManager:
    """
    Temporarily replace std* streams with StringIO objects.
    """

    def __enter__(self):
        strin = io.StringIO()
        strout = io.StringIO()
        strerr = io.StringIO()

        self._stdin = sys.stdin
        self._stdout = sys.stdout
        self._stderr = sys.stderr

        sys.stdin = strin
        sys.stdout = strout
        sys.stderr = strerr
        return strin, strout, strerr

    def __exit__(self, type, value, traceback):
        sys.stdin = self._stdin
        sys.stdout = self._stdout
        sys.stderr = self._stderr


class TestLastStatementPrint(unittest.TestCase):
    def test_constants(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("'a', 1, None")
            assert stdout.getvalue() == "('a', 1, None)\n", stdout.getvalue()

    def test_math(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("2+2")
            assert stdout.getvalue() == "4\n", stdout.getvalue()

    def test_print_call(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("print('hello world')")
            assert stdout.getvalue() == "hello world\n", stdout.getvalue()

    def test_if_branches(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
if None:
  1
else:
  2
            """
            )
            assert stdout.getvalue() == "2\n", stdout.getvalue()

    def test_assignments(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("x = 2")
            assert stdout.getvalue() == "2\n", stdout.getvalue()

    def test_walrus(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("y = 3 + (x := 2); x+y")
            assert stdout.getvalue() == "7\n", stdout.getvalue()

    def test_multiple_statements(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main('print("hello"); 1+1')
            assert stdout.getvalue() == "hello\n2\n", stdout.getvalue()

    def test_loop(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("for x in range(2): x")
            assert stdout.getvalue() == "0\n1\n", stdout.getvalue()

    def test_lambda(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("sorted([1,2,3], key=lambda x: -x)")
            assert stdout.getvalue() == "[3, 2, 1]\n", stdout.getvalue()

    def test_euler_1(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("sum(i for i in range(10) if i % 3 == 0 or i % 5 == 0)")
            assert stdout.getvalue() == "23\n", stdout.getvalue()

    def test_empty_list(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("[]", pprint_opt=True)
            assert stdout.getvalue() == "[]\n", stdout.getvalue()

    def test_double_list_comprehension(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("[y for x in range(int(math.sqrt(4))) for y in range(x)]")
            assert stdout.getvalue() == "[0]\n", stdout.getvalue()

    # test multiple line one-liners
    def test_mult_line_if(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
if True:
    x = 10
else:
    x = 20
"""
            )
            assert stdout.getvalue() == "10\n", stdout.getvalue()

    def test_mult_line_if_else(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
if False:
    x = 10
else:
    x = 20
"""
            )
            assert stdout.getvalue() == "20\n", stdout.getvalue()

    def test_mult_line_elif(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
if False:
    x = 10
elif True:
    x = 20
else:
    x = 30
"""
            )
            assert stdout.getvalue() == "20\n", stdout.getvalue()

    def test_mult_line_double_for(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
for i in range(1):
    for j in range(2):
        i,j
"""
            )
            assert stdout.getvalue() == "(0, 0)\n(0, 1)\n", stdout.getvalue()

    def test_mult_line_block(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
for i in range(1):
    j = 10
    i,j
"""
            )
            assert stdout.getvalue() == "(0, 10)\n", stdout.getvalue()

    def test_mult_line_for_else(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
for i in []:
    i
else:
    i = 20
"""
            )
            assert stdout.getvalue() == "20\n", stdout.getvalue()

    def test_mult_line_try(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
try:
    x = 10
except:
    x = 20
"""
            )
            assert stdout.getvalue() == "10\n", stdout.getvalue()

    def test_mult_line_except(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
try:
    x = int('')
except:
    x = 20
"""
            )
            assert stdout.getvalue() == "20\n", stdout.getvalue()

    def test_mult_line_else(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
try:
    x = 10
except:
    x = 20
else:
    x = 30
"""
            )
            assert stdout.getvalue() == "30\n", stdout.getvalue()

    def test_mult_line_finally(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
try:
    x = int('')
except:
    x = 20
else:
    x = 10
finally:
    x = 30
"""
            )
            assert stdout.getvalue() == "30\n", stdout.getvalue()

    def test_mult_line_with(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
class CM(object):
    def __enter__(self):
        print('enter')
    def __exit__(self, *args):
        print('exit')
with CM():
    print('pony times')
"""
            )
            assert stdout.getvalue() == "enter\npony times\nexit\n", stdout.getvalue()

    def test_mult_line_with_as(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
class CM(object):
    def __enter__(self):
        print('enter')
        return 'pony times'
    def __exit__(self, *args):
        print('exit')
with CM() as s:
    print(s)
"""
            )
            assert stdout.getvalue() == "enter\npony times\nexit\n", stdout.getvalue()

    def test_mult_line_with_as_file(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
with open('pyproject.toml') as f:
    print('pony times')
"""
            )
            assert stdout.getvalue() == "pony times\n", stdout.getvalue()

    def test_match(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
match 1:
  case 1:
    2
  case 2:
    1
            """
            )
            assert stdout.getvalue() == "2\n", stdout.getvalue()

    def test_pprint(self):
        output = """{0: 'thing',
 1: 'thing',
 2: 'thing',
 3: 'thing',
 4: 'thing',
 5: 'thing',
 6: 'thing',
 7: 'thing',
 8: 'thing',
 9: 'thing'}
"""
        with StdoutManager() as (stdin, stdout, stderr):
            main('math.exp; dict((i,"thing") for i in range(10))', pprint_opt=True)
            assert stdout.getvalue() == output, stdout.getvalue()

    # ending with a func/class/decorated
    def test_end_func(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
def hello():
    return
"""
            )
            assert stdout.getvalue() == "", stdout.getvalue()

    def test_end_class(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
class hello():
    pass
"""
            )
            assert stdout.getvalue() == "", stdout.getvalue()

    def test_end_decorator(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
@functools.wraps
def hello():
    pass
"""
            )
            assert stdout.getvalue() == "", stdout.getvalue()

    # eventually someone's going to try it
    def test_end_import(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
import math
"""
            )
            assert stdout.getvalue() == "", stdout.getvalue()

    # Bug fix: see https://github.com/thenoviceoof/pyli/issues/15
    def test_dir_module(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("dir(math)[0]")
            assert stdout.getvalue() == "__doc__\n", stdout.getvalue()

    def test_non_idempotent(self):
        # If we interpolate the expression into a None check and a
        # print, then we will end up with 4 instead.
        with StdoutManager() as (stdin, stdout, stderr):
            main("y = 1; 1 + (y := y + 1)")
            assert stdout.getvalue() == "3\n", stdout.getvalue()

    def test_assign_destructuring(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("x, y = [1, 2]")
            assert stdout.getvalue() == "(1, 2)\n", stdout.getvalue()


class TestAutoImport(unittest.TestCase):
    def tearDown(self):
        # The math module is the only one we modify, which messes with
        # the copy in the module cache, which persists between test
        # cases. Delete it from the cache so it gets imported new each
        # time.
        if "math" in sys.modules:
            del sys.modules["math"]

    def test_import_math(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("math.sqrt(4)")
            assert stdout.getvalue() == "2.0\n", stdout.getvalue()

    def test_import_as(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("import math as m; m.sqrt(4)")
            assert stdout.getvalue() == "2.0\n", stdout.getvalue()

    def test_import_xml_child(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                "xml.etree.ElementTree.fromstring("
                '"<?xml version=\\"1.0\\"?><hello>world</hello>")'
            )
            if sys.version_info < (2, 7):
                assert re.match(
                    "<Element hello at \\w+>", stdout.getvalue()
                ), stdout.getvalue()
            else:
                assert re.match(
                    "<Element 'hello' at 0x\\w+>", stdout.getvalue()
                ), stdout.getvalue()

    def test_nested_calls(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main('html.escape(json.dumps({"hello": "world"})).split()')
            result = "['{&quot;hello&quot;:', '&quot;world&quot;}']\n"
            assert stdout.getvalue() == result, stdout.getvalue()

    def test_list(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("[math.sqrt(4)]")
            assert stdout.getvalue() == "[2.0]\n", stdout.getvalue()

    def test_dict(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("{1: math.sqrt(4)}")
            assert stdout.getvalue() == "{1: 2.0}\n", stdout.getvalue()

    def test_compare(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("5 < math.sqrt(4)")
            assert stdout.getvalue() == "False\n", stdout.getvalue()

    def test_call_starred(self):
        # Don't think there's a way to put something that should be auto-imported into a starred node.
        with StdoutManager() as (stdin, stdout, stderr):
            main("a = [1]; (lambda x: x)(*a)")
            assert stdout.getvalue() == "1\n", stdout.getvalue()

    def test_inline_if_case(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("math.sqrt(4) if True else False")
            assert stdout.getvalue() == "2.0\n", stdout.getvalue()

    def test_inline_else_case(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("None if False else math.sqrt(4)")
            assert stdout.getvalue() == "2.0\n", stdout.getvalue()

    def test_inline_test_case(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("False if math.sqrt(4) else True")
            assert stdout.getvalue() == "False\n", stdout.getvalue()

    def test_attribute_base(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("(math.sqrt(4)).real")
            assert stdout.getvalue() == "2.0\n", stdout.getvalue()

    def test_subscript(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("[10,20,30][int(math.sqrt(4))]")
            assert stdout.getvalue() == "30\n", stdout.getvalue()

    def test_slice(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("[10,20,30][int(math.sqrt(1)):]")
            assert stdout.getvalue() == "[20, 30]\n", stdout.getvalue()

    def test_raise(self):
        import pickle

        with StdoutManager() as (stdin, stdout, stderr):
            with self.assertRaises(pickle.PickleError):
                main("raise pickle.PickleError()")

    def test_del(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("del math.sqrt")
            assert stdout.getvalue() == "", stdout.getvalue()

    def test_if(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
if True:
  math.sqrt(4)
else:
  True
            """
            )
            assert stdout.getvalue() == "2.0\n", stdout.getvalue()

    def test_else(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
if False:
  True
else:
  math.sqrt(4)
            """
            )
            assert stdout.getvalue() == "2.0\n", stdout.getvalue()

    def test_if_test(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
if math.sqrt(4):
  True
else:
  None
            """
            )
            assert stdout.getvalue() == "True\n", stdout.getvalue()

    def test_try_body(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
try:
  math.sqrt(4)
except Exception:
  None
            """
            )
            assert stdout.getvalue() == "2.0\n", stdout.getvalue()

    def test_try_except(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
try:
  raise Exception('')
except Exception:
  math.sqrt(4)
            """
            )
            assert stdout.getvalue() == "2.0\n", stdout.getvalue()

    def test_try_except_catch(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
try:
  1
except pickle.PickleError:
  None
            """
            )
            assert stdout.getvalue() == "1\n", stdout.getvalue()

    def test_try_except_catch_as(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
try:
  1
except pickle.PickleError as not_a_module:
  not_a_module
            """
            )
            assert stdout.getvalue() == "1\n", stdout.getvalue()

    def test_try_else(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
try:
  1
except Exception:
  None
else:
  math.sqrt(4)
            """
            )
            assert stdout.getvalue() == "2.0\n", stdout.getvalue()

    def test_try_finally(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
try:
  1
except Exception:
  None
else:
  2
finally:
  math.sqrt(4)
            """
            )
            assert stdout.getvalue() == "2.0\n", stdout.getvalue()

    def test_list_comp_item(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("[int(math.sqrt(i)) for i in range(5)]")
            assert stdout.getvalue() == "[0, 1, 1, 1, 2]\n", stdout.getvalue()

    def test_list_comp_iter(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("[i for i in range(int(math.sqrt(4)))]")
            assert stdout.getvalue() == "[0, 1]\n", stdout.getvalue()

    def test_list_comp_if(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("[i for i in range(4) if math.sqrt(3*i) < 2.5]")
            assert stdout.getvalue() == "[0, 1, 2]\n", stdout.getvalue()

    def test_with_item_assigned(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
with tests.util.ExampleContextManager() as x:
  x
            """
            )
            assert stdout.getvalue() == "hello world\n", stdout.getvalue()

    def test_with(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
with contextlib.nullcontext():
  math.sqrt(4)
            """
            )
            assert stdout.getvalue() == "2.0\n", stdout.getvalue()

    def test_match_subject(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
match math.sqrt(4):
  case 2.0:
    print('hello world')
            """
            )
            assert stdout.getvalue() == "hello world\n", stdout.getvalue()

    def test_match_body(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
match 1:
  case 1:
    math.sqrt(9)
            """
            )
            assert stdout.getvalue() == "3.0\n", stdout.getvalue()

    def test_match_pattern_guard(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
match 1:
  case 1 if math.sqrt(4) > 0:
    print("hello world")
            """
            )
            assert stdout.getvalue() == "hello world\n", stdout.getvalue()

    def test_match_pattern_simple(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
match 1:
  case not_a_module:
    print(not_a_module)
            """
            )
            assert stdout.getvalue() == "1\n", stdout.getvalue()

    def test_match_pattern_attribute(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
match (50, 1):
  case (logging.CRITICAL, 1):
    print("hello world")
            """
            )
            assert stdout.getvalue() == "hello world\n", stdout.getvalue()

    def test_match_pattern_mapping_key(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
match {50: 2}:
  case {logging.CRITICAL: 2}:
    print("hello world")
            """
            )
            assert stdout.getvalue() == "hello world\n", stdout.getvalue()

    def test_match_pattern_mapping_value(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
match {1: 2}:
  case {1: not_a_module}:
    print(not_a_module)
            """
            )
            assert stdout.getvalue() == "2\n", stdout.getvalue()

    def test_match_pattern_mapping_rest(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
match {1: 2, 3: 4}:
  case {1: 2, **not_a_module}:
    print(not_a_module)
            """
            )
            assert stdout.getvalue() == "{3: 4}\n", stdout.getvalue()

    def test_match_pattern_class_name(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
match tests.util.EXAMPLE_TIMEDELTA:
  case datetime.timedelta(days=2):
    print("hello world")
            """
            )
            assert stdout.getvalue() == "hello world\n", stdout.getvalue()

    def test_match_pattern_class_pattern(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
match tests.util.EXAMPLE_MATCH_CLASS:
  case tests.util.ExampleMatchClass(1, not_a_module):
    print(not_a_module)
            """
            )
            assert stdout.getvalue() == "2\n", stdout.getvalue()

    def test_match_pattern_class_kwd(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
match tests.util.EXAMPLE_MATCH_CLASS:
  case tests.util.ExampleMatchClass(x=not_a_module_1, y=2):
    print(not_a_module_1)
            """
            )
            assert stdout.getvalue() == "1\n", stdout.getvalue()

    def test_match_pattern_star(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
match [1, 2, 3]:
  case [1, *not_a_module]:
    print(not_a_module)
            """
            )
            assert stdout.getvalue() == "[2, 3]\n", stdout.getvalue()

    def test_match_pattern_as(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
match [1]:
  case [not_a_module_1] as not_a_module_2:
    print(not_a_module_1, not_a_module_2)
            """
            )
            assert stdout.getvalue() == "1 [1]\n", stdout.getvalue()

    def test_match_pattern_or(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
match [1]:
  case [not_a_module] | (not_a_module):
    print(not_a_module)
            """
            )
            assert stdout.getvalue() == "1\n", stdout.getvalue()

    def test_assign(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("x = math.sqrt(4)")
            assert stdout.getvalue() == "2.0\n", stdout.getvalue()

    def test_assign_lhs(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("math.weird_attribute = 1")
            assert stdout.getvalue() == "1\n", stdout.getvalue()

    def test_annotated_assign(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("x: float = math.sqrt(4)")
            assert stdout.getvalue() == "2.0\n", stdout.getvalue()

    def test_augmented_assign(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("x = 1; x += math.sqrt(4)")
            assert stdout.getvalue() == "3.0\n", stdout.getvalue()

    def test_walrus(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("1 + (x := math.sqrt(4))")
            assert stdout.getvalue() == "3.0\n", stdout.getvalue()

    def test_for_test(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
for i in range(int(math.sqrt(4))):
  i
            """
            )
            assert stdout.getvalue() == "0\n1\n", stdout.getvalue()

    def test_for_body(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
for i in range(2):
  math.sqrt(4*i)
            """
            )
            assert stdout.getvalue() == "0.0\n2.0\n", stdout.getvalue()

    def test_for_else(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
for i in range(2):
  i
else:
  math.sqrt(4)
            """
            )
            assert stdout.getvalue() == "2.0\n", stdout.getvalue()

    def test_function_body(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
def fn():
  return math.sqrt(4)
fn()
            """
            )
            assert stdout.getvalue() == "2.0\n", stdout.getvalue()

    def test_function_args(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
def fn(a = math.sqrt(4)):
  return a
fn()
            """
            )
            assert stdout.getvalue() == "2.0\n", stdout.getvalue()

    def test_function_decorators(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
@functools.cache
def fn():
  return 1
fn()
            """
            )
            assert stdout.getvalue() == "1\n", stdout.getvalue()

    def test_class_body(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
class A:
  def fn(self):
    return math.sqrt(4)
A().fn()
            """
            )
            assert stdout.getvalue() == "2.0\n", stdout.getvalue()

    def test_class_base(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
class A(random.Random):
  pass
'getstate' in dir(A())
            """
            )
            assert stdout.getvalue() == "True\n", stdout.getvalue()

    def test_class_keywords(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
class A(metaclass=tests.util.ExampleMetaclass):
  pass
A().hello()
            """
            )
            assert stdout.getvalue() == "world\n", stdout.getvalue()

    def test_class_decorators(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main(
                """
@tests.util.ExampleClassDecorator
class A():
  pass
A().hello()
            """
            )
            assert stdout.getvalue() == "world\n", stdout.getvalue()

    def test_bound_variables_with_attributes(self):
        # This should NOT be treated as an import.
        with StdoutManager() as (stdin, stdout, stderr):
            main("x = 'hello world'; x.split()[1]")
            assert stdout.getvalue() == "world\n", stdout.getvalue()


class TestSpecialVariables(unittest.TestCase):
    # test input, line/li/l
    def test_line(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write("hello world")
            stdin.seek(0)
            main("line")
            assert stdout.getvalue() == "hello world\n", stdout.getvalue()

    def test_li_append(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write("hello world\nI am fine")
            stdin.seek(0)
            main('"constant " + li')
            assert (
                stdout.getvalue() == "constant hello world\nconstant I am fine\n"
            ), stdout.getvalue()

    def test_l_grep(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write("hi\nbye\nnye")
            stdin.seek(0)
            main("l if 'y' in l else None")
            assert stdout.getvalue() == "bye\nnye\n", stdout.getvalue()

    def test_l_wc(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write("hi\nbye\nnye")
            stdin.seek(0)
            main("len(l)")
            assert stdout.getvalue() == "2\n3\n3\n", stdout.getvalue()

    # lines/lis/ls
    def test_lines_join(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write("hi\nbye\nnye")
            stdin.seek(0)
            main("''.join(l for l in lines)")
            assert stdout.getvalue() == "hibyenye\n", stdout.getvalue()

    def test_lis_regex(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write("hi\nbye\nnye")
            stdin.seek(0)
            main("for l in lis: re.sub('ye', '', l)")
            assert stdout.getvalue() == "hi\nb\nn\n", stdout.getvalue()

    def test_ls_wc(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write("hi\nbye\nnye")
            stdin.seek(0)
            main("sum(len(l) for l in ls)")
            assert stdout.getvalue() == "8\n", stdout.getvalue()

    # test contents/conts/cs
    def test_contents_sort(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write("hi\nbye\nnye")
            stdin.seek(0)
            main("''.join(sorted(list(''.join(contents.split('\\n')))))")
            assert stdout.getvalue() == "beehinyy\n", stdout.getvalue()

    def test_conts_sorted_count(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write("hibyenye")
            stdin.seek(0)
            main("for c in sorted(set(conts)): print('%s %d' % (c, conts.count(c)))")
            outcome = """b 1
e 2
h 1
i 1
n 1
y 2
"""
            assert stdout.getvalue() == outcome, stdout.getvalue()

    def test_cs_wc(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write("hi\nbye\nnye")
            stdin.seek(0)
            main("len(cs)")
            assert stdout.getvalue() == "10\n", stdout.getvalue()

    # test direct access to stdin/stdout/stderr
    def test_stdin(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write("hi\nbye\nnye")
            stdin.seek(0)
            main("stdin.readline()")
            assert stdout.getvalue() == "hi\n\n", stdout.getvalue()

    def test_stdout(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("stdout.write('hello')")
            assert stdout.getvalue() == "hello", stdout.getvalue()

    def test_stderr(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("stderr.write('example')")
            # The last line print prints the number of characters written.
            assert stdout.getvalue() == "7\n", stdout.getvalue()
            assert stderr.getvalue() == "example", stderr.getvalue()

    # part/p
    def test_p_len(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write("abs bad\ncod dud egg")
            stdin.seek(0)
            main("len(p)")
            assert stdout.getvalue() == "2\n3\n", stdout.getvalue()

    def test_part_interpolate(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write("1 thing\n2 brah")
            stdin.seek(0)
            main("'%s: %s' % (part[0], part[1])")
            assert stdout.getvalue() == "1: thing\n2: brah\n", stdout.getvalue()

    def test_part_unequal(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write("1 2\n3")
            stdin.seek(0)
            self.assertRaises(IndexError, main, "part[1]")

    # parts/ps
    def test_ps_dict(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write("abs bad\n")
            stdin.seek(0)
            main("dict(ps)")
            assert stdout.getvalue() == "{'abs': 'bad'}\n", stdout.getvalue()

    def test_parts_dict(self):
        with StdoutManager() as (stdin, stdout, stderr):
            stdin.write("1 thing\n2 brah")
            stdin.seek(0)
            main("dict((int(i),v) for i,v in parts)")
            assert stdout.getvalue() == "{1: 'thing', 2: 'brah'}\n", stdout.getvalue()

    # test kwarg passing
    def test_cli_switch_passing(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("print(x)", variables={"x": "hello"})
            assert stdout.getvalue() == "hello\n", stdout.getvalue()

    def test_cli_switch_end_quote(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("print(x)", variables={"x": 'hello"'})
            assert stdout.getvalue() == 'hello"\n', stdout.getvalue()

    def test_cli_switch_ref(self):
        with StdoutManager() as (stdin, stdout, stderr):
            main("print(x.split()[1])", variables={"x": "hello world"})
            assert stdout.getvalue() == "world\n", stdout.getvalue()
