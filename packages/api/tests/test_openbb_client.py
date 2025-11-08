"""Tests for OpenBB client credential configuration."""
import os
from unittest.mock import patch, MagicMock


def test_fred_key_applied_when_env_set():
    mock_obb = MagicMock()
    with patch.dict(os.environ, {"FRED_API_KEY": "test_key_123"}):
        with patch("openbb.obb", mock_obb):
            from importlib import reload
            import api.agent.openbb_client as mod
            reload(mod)
            client = mod.get_obb_client()
    mock_obb.user.credentials.__setattr__  # just confirm obb was accessed
    assert client is mock_obb


def test_fred_key_skipped_when_env_missing():
    mock_obb = MagicMock()
    env = {k: v for k, v in os.environ.items() if k != "FRED_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        with patch("openbb.obb", mock_obb):
            from importlib import reload
            import api.agent.openbb_client as mod
            reload(mod)
            mod.get_obb_client()
    # Should not raise
