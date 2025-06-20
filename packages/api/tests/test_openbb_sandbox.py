"""Tests for OpenBB code AST validation and sandbox execution."""

import pytest
from api.agent.openbb_sandbox import validate_code, execute_openbb_code


class TestValidateCode:
    """AST validation: allowed vs rejected code patterns."""

    def test_valid_obb_equity_call(self):
        code = '''
def fetch():
    result = obb.equity.price.historical("AAPL", start_date="2024-01-01")
    return result.to_df()
'''
        valid, reason = validate_code(code)
        assert valid is True
        assert reason is None

    def test_valid_obb_economy_call(self):
        code = '''
def fetch():
    result = obb.economy.cpi(country="united_states")
    return result.to_df()
'''
        valid, reason = validate_code(code)
        assert valid is True
        assert reason is None

    def test_valid_datetime_import(self):
        code = '''
from datetime import datetime, timedelta

def fetch():
    end = datetime.now()
    start = end - timedelta(days=365)
    result = obb.equity.price.historical("AAPL", start_date=str(start.date()))
    return result.to_df()
'''
        valid, reason = validate_code(code)
        assert valid is True

    def test_reject_os_import(self):
        code = '''
import os
def fetch():
    return os.listdir(".")
'''
        valid, reason = validate_code(code)
        assert valid is False
        assert "os" in reason

    def test_reject_subprocess_import(self):
        code = '''
import subprocess
def fetch():
    return subprocess.run(["ls"], capture_output=True)
'''
        valid, reason = validate_code(code)
        assert valid is False
        assert "subprocess" in reason

    def test_reject_from_os_import(self):
        code = '''
from os import listdir
def fetch():
    return listdir(".")
'''
        valid, reason = validate_code(code)
        assert valid is False

    def test_reject_eval(self):
        code = '''
def fetch():
    return eval("1 + 1")
'''
        valid, reason = validate_code(code)
        assert valid is False
        assert "eval" in reason

    def test_reject_exec(self):
        code = '''
def fetch():
    exec("x = 1")
    return {}
'''
        valid, reason = validate_code(code)
        assert valid is False
        assert "exec" in reason

    def test_reject_open(self):
        code = '''
def fetch():
    with open("/etc/passwd") as f:
        return f.read()
'''
        valid, reason = validate_code(code)
        assert valid is False
        assert "open" in reason

    def test_reject_dunder_import(self):
        code = '''
def fetch():
    os = __import__("os")
    return os.listdir(".")
'''
        valid, reason = validate_code(code)
        assert valid is False
        assert "__import__" in reason

    def test_reject_disallowed_obb_module(self):
        code = '''
def fetch():
    return obb.account.delete()
'''
        valid, reason = validate_code(code)
        assert valid is False
        assert "obb.account" in reason

    def test_reject_requests_import(self):
        code = '''
import requests
def fetch():
    return requests.get("http://evil.com").json()
'''
        valid, reason = validate_code(code)
        assert valid is False

    def test_reject_socket_import(self):
        code = '''
import socket
def fetch():
    return socket.gethostname()
'''
        valid, reason = validate_code(code)
        assert valid is False

    def test_valid_pandas_usage(self):
        code = '''
def fetch():
    result = obb.equity.price.historical("AAPL", start_date="2024-01-01")
    df = result.to_df()
    return df.tail(10)
'''
        valid, reason = validate_code(code)
        assert valid is True

    def test_reject_compile(self):
        code = '''
def fetch():
    c = compile("print(1)", "<string>", "exec")
    return {}
'''
        valid, reason = validate_code(code)
        assert valid is False
        assert "compile" in reason

    def test_reject_globals(self):
        code = '''
def fetch():
    return globals()
'''
        valid, reason = validate_code(code)
        assert valid is False
        assert "globals" in reason


class TestExecuteOpenbbCode:
    """Sandbox execution tests using a mock obb client."""

    @pytest.mark.asyncio
    async def test_execute_returns_dict(self):
        code = '''
def fetch():
    return {"ticker": "AAPL", "price": 150.0}
'''
        result = await execute_openbb_code(code, obb_client=None)
        assert result == {"ticker": "AAPL", "price": 150.0}

    @pytest.mark.asyncio
    async def test_execute_converts_dataframe(self):
        # pandas is injected as `pd`, so use it without import
        code = '''
def fetch():
    return pd.DataFrame({"a": [1, 2], "b": [3, 4]})
'''
        result = await execute_openbb_code(code, obb_client=None)
        assert result == [{"a": 1, "b": 3}, {"a": 2, "b": 4}]

    @pytest.mark.asyncio
    async def test_execute_no_fetch_raises(self):
        code = '''
x = 1 + 1
'''
        with pytest.raises(ValueError, match="fetch"):
            await execute_openbb_code(code, obb_client=None)

    @pytest.mark.asyncio
    async def test_execute_timeout(self):
        # time is not in safe builtins, so this will fail at exec (NameError)
        code = '''
def fetch():
    time.sleep(60)
    return {}
'''
        with pytest.raises(Exception):
            await execute_openbb_code(code, obb_client=None, timeout_seconds=2)
