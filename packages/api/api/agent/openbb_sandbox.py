"""AST-based code validation and sandboxed execution for OpenBB queries."""

import ast
import asyncio
from typing import Any

import datetime
import pandas as pd

__all__ = ["validate_code", "execute_openbb_code"]

# ---------------------------------------------------------------------------
# Module allowlist
# ---------------------------------------------------------------------------

ALLOWED_OBB_MODULES = {
    "obb.equity",
    "obb.derivatives",
    "obb.economy",
    "obb.etf",
    "obb.fixedincome",
    "obb.index",
    "obb.news",
    "obb.regulators",
    "obb.crypto",
    "obb.currency",
}

ALLOWED_IMPORTS = {"datetime"}

BANNED_BUILTINS = {
    "eval", "exec", "compile", "__import__", "open",
    "getattr", "globals", "locals", "vars", "delattr",
    "setattr", "breakpoint", "exit", "quit",
}

BANNED_MODULES = {
    "os", "sys", "subprocess", "shutil", "pathlib",
    "socket", "http", "urllib", "requests", "importlib",
    "ctypes", "signal", "threading", "multiprocessing",
}

# ---------------------------------------------------------------------------
# AST Validation
# ---------------------------------------------------------------------------

def validate_code(code: str) -> tuple[bool, str | None]:
    """Validate generated Python code against safety rules.

    Returns (True, None) if the code is safe to execute,
    or (False, reason) if it violates a rule.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    for node in ast.walk(tree):
        # Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_root = alias.name.split(".")[0]
                if module_root not in ALLOWED_IMPORTS:
                    return False, f"Import not allowed: {alias.name}"

        if isinstance(node, ast.ImportFrom):
            if node.module:
                module_root = node.module.split(".")[0]
                if module_root not in ALLOWED_IMPORTS:
                    return False, f"Import not allowed: from {node.module}"

        # Check function calls
        if isinstance(node, ast.Call):
            func_name = _get_call_name(node)
            if func_name in BANNED_BUILTINS:
                return False, f"Banned builtin call: {func_name}"

        # Check attribute access for obb.* modules
        if isinstance(node, ast.Attribute):
            chain = _get_attribute_chain(node)
            if chain and chain.startswith("obb."):
                # Extract the first two segments: obb.module
                parts = chain.split(".")
                if len(parts) >= 2:
                    obb_module = f"{parts[0]}.{parts[1]}"
                    if obb_module not in ALLOWED_OBB_MODULES:
                        return False, f"Disallowed OpenBB module: {obb_module}"

    return True, None


def _get_call_name(node: ast.Call) -> str | None:
    """Extract the function name from a Call node."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _get_attribute_chain(node: ast.Attribute) -> str | None:
    """Build the full dotted attribute chain, e.g. 'obb.equity.price.historical'."""
    parts = [node.attr]
    current = node.value
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return ".".join(reversed(parts))
    return None


# ---------------------------------------------------------------------------
# Sandbox Execution
# ---------------------------------------------------------------------------

SAFE_BUILTINS = {
    "len": len, "range": range, "enumerate": enumerate,
    "zip": zip, "map": map, "filter": filter,
    "sorted": sorted, "reversed": reversed,
    "list": list, "dict": dict, "tuple": tuple, "set": set,
    "str": str, "int": int, "float": float, "bool": bool,
    "min": min, "max": max, "sum": sum, "abs": abs, "round": round,
    "isinstance": isinstance, "type": type, "print": print,
    "None": None, "True": True, "False": False,
    "hasattr": hasattr,
}


async def execute_openbb_code(
    code: str,
    obb_client: Any,
    timeout_seconds: int = 30,
) -> dict | list:
    """Execute validated code in a restricted namespace.

    The code must define a `fetch()` function. That function is called
    and its return value serialized to JSON-compatible types.

    Args:
        code: Python source code defining a fetch() function.
        obb_client: Configured OpenBB client to inject as `obb`.
        timeout_seconds: Max seconds before the execution is cancelled.

    Returns:
        JSON-serializable dict or list.

    Raises:
        ValueError: If the code doesn't define fetch().
        asyncio.TimeoutError: If execution exceeds timeout.
    """
    namespace: dict[str, Any] = {
        "obb": obb_client,
        "datetime": datetime,
        "pd": pd,
        "__builtins__": SAFE_BUILTINS,
    }

    def _exec_sync():
        exec(code, namespace)  # noqa: S102 — intentional sandboxed exec
        if "fetch" not in namespace or not callable(namespace["fetch"]):
            raise ValueError("Generated code must define a callable fetch() function")
        result = namespace["fetch"]()
        return _serialize(result)

    return await asyncio.wait_for(
        asyncio.to_thread(_exec_sync),
        timeout=timeout_seconds,
    )


def _serialize(value: Any) -> dict | list:
    """Convert execution result to JSON-serializable types."""
    if isinstance(value, pd.DataFrame):
        return value.to_dict(orient="records")
    if isinstance(value, pd.Series):
        return value.to_dict()
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (int, float, str, bool)) or value is None:
        return value
    if hasattr(value, "to_df"):
        # OpenBB OBBject — convert to DataFrame first
        return value.to_df().to_dict(orient="records")
    raise TypeError(f"Cannot serialize result of type {type(value).__name__}")
