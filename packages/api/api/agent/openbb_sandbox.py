"""AST-based code validation and sandboxed execution for OpenBB queries."""

import ast
import asyncio
from typing import Any

import datetime as _dt_module
import pandas as pd

# Expose the class, not the module — generated code uses datetime.now(), datetime.strptime(), etc.
_datetime_cls = _dt_module.datetime
_timedelta_cls = _dt_module.timedelta
_date_cls = _dt_module.date

__all__ = ["validate_code", "execute_openbb_code", "_normalize", "_classify_error"]

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
# Result normalization and error classification
# ---------------------------------------------------------------------------

def _normalize(value):
    """Convert any OpenBB result to a JSON-serializable list of records."""
    import pandas as _pd
    if isinstance(value, _pd.DataFrame):
        return value.reset_index().to_dict(orient="records")
    if hasattr(value, "to_df"):
        return value.to_df().reset_index().to_dict(orient="records")
    if hasattr(value, "results"):
        results = value.results
        if isinstance(results, list):
            return [r.__dict__ if hasattr(r, "__dict__") else r for r in results]
        return results
    if isinstance(value, (list, dict)):
        return value
    return value


def _classify_error(exc: Exception) -> str:
    """Return an actionable hint for common OpenBB codegen errors."""
    msg = str(exc)
    if "to_df" in msg and "DataFrame" in msg:
        return "Don't call .to_df() — result is already a DataFrame with output_type='dataframe'"
    if "unexpected keyword argument" in msg or "got an unexpected" in msg:
        return "Check parameter names — the argument name may be wrong for this OpenBB function"
    if "'OBBject'" in msg or "OBBject" in msg:
        return "The expression returned an OBBject — _normalize() handles this, don't call methods on it directly"
    if isinstance(exc, KeyError):
        return "Don't access specific column names — return the full result and let _normalize handle it"
    if "AttributeError" in type(exc).__name__:
        return "Attribute doesn't exist — check the OpenBB function path and return type"
    return f"{type(exc).__name__}: {msg}"


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
    expression: str,
    obb_client: Any,
    timeout_seconds: int = 30,
) -> dict | list:
    """Execute a single OpenBB expression in a sandboxed namespace.

    The expression is wrapped in a fetch() function with _normalize helper injected.

    Args:
        expression: Single-line OpenBB call expression (e.g. obb.equity.price.historical(...)).
        obb_client: Configured OpenBB client to inject as `obb`.
        timeout_seconds: Max seconds before the execution is cancelled.

    Returns:
        JSON-serializable dict or list.

    Raises:
        asyncio.TimeoutError: If execution exceeds timeout.
    """
    import builtins as _builtins

    def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
        root = name.split(".")[0]
        if root in BANNED_MODULES:
            raise ImportError(f"Module '{name}' is not allowed in this sandbox")
        return _builtins.__import__(name, globals, locals, fromlist, level)

    code = f"def fetch():\n    result = {expression}\n    return _normalize(result)\n"

    namespace: dict[str, Any] = {
        "obb": obb_client,
        "datetime": _datetime_cls,   # datetime.now(), datetime.strptime(), etc.
        "timedelta": _timedelta_cls,  # timedelta(days=365)
        "date": _date_cls,            # date.today()
        "pd": pd,
        "_normalize": _normalize,
        "__builtins__": {**vars(_builtins), "__import__": _safe_import},
    }

    def _exec_sync():
        exec(code, namespace)  # noqa: S102 — intentional sandboxed exec
        result = namespace["fetch"]()
        return result

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
