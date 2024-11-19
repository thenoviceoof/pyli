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
