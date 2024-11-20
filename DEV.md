# Development notes

## Run tests

```tox```

This will run:

- The `black` linter.
- The `mypy` type checker.
- The default `unittest` runner on the existing tests.

## Packaging

Build the wheel:

```
python3 -m build
```

Upload to pypi:

```
python3 -m twine upload --repository pypi dist/*
```
