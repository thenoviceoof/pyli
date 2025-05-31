# Development notes

## Setting up the environment

If you are using `uv`:

```
uv sync
```

## Run tests

```uv run tox```

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
