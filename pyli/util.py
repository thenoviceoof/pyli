def var_base_intersection(vars_path: set[tuple[str]], vars_base: set[str]) -> set[str]:
    """
    Check whether any variable paths share a common base reference.
    This handles cases like `stdin.write` or `contents.split`.
    """
    return vars_base & {v[0] for v in vars_path}


def var_base_difference(
    vars_path: set[tuple[str]], vars_base: set[str]
) -> set[tuple[str]]:
    """
    Check whether any variable paths share a common base reference.
    This handles cases like `stdin.write` or `contents.split`.
    """
    return {v for v in vars_path if v[0] not in vars_base}
