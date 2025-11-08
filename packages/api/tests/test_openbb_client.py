"""Tests for OpenBB client credential configuration."""
import os
from unittest.mock import patch, MagicMock


def test_fred_key_applied_when_env_set():
    with patch.dict(os.environ, {"FRED_API_KEY": "test_key_123"}):
        with patch("api.agent.openbb_client.obb") as mock_obb:
            from api.agent.openbb_client import get_obb_client
            client = get_obb_client()
    assert mock_obb.user.credentials.fred_api_key == "test_key_123"
    assert client is mock_obb


def test_fred_key_skipped_when_env_missing():
    env = {k: v for k, v in os.environ.items() if k != "FRED_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        with patch("api.agent.openbb_client.obb") as mock_obb:
            from api.agent.openbb_client import get_obb_client
            get_obb_client()
    # Verify fred_api_key was never assigned — it should still be an unset MagicMock
    assert not isinstance(mock_obb.user.credentials.fred_api_key, str)
