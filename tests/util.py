# Exercise auto-import for more unusual language features.


def ExampleClassDecorator(cls):
    setattr(cls, "hello", lambda self: "world")
    return cls


class ExampleMetaclass(type):
    def __new__(cls, name, bases, attrs):
        attrs["hello"] = lambda self: "world"
        return type(name, bases, attrs)


class ExampleContextManager:
    def __enter__(self):
        return "hello world"

    def __exit__(self, type, value, traceback):
        pass


class ExampleMatchClass:
    __match_args__ = ("x", "y")

    def __init__(self, x, y):
        self.x = x
        self.y = y


# Switch this to a Standard library class?
EXAMPLE_MATCH_CLASS = ExampleMatchClass(1, 2)

import datetime

EXAMPLE_TIMEDELTA = datetime.timedelta(days=2)
