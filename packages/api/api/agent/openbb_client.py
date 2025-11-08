"""OpenBB Platform client singleton for sandboxed code execution."""

import os

from dotenv import load_dotenv
from openbb import obb

load_dotenv()

# Use DataFrame output by default — generated code often transforms DataFrames
obb.user.preferences.output_type = "dataframe"


def get_obb_client():
    """Return the configured OpenBB client singleton.

    Applies FRED_API_KEY from environment if present.
    Free providers (yfinance, SEC EDGAR) are available without API keys.
    """
    fred_key = os.getenv("FRED_API_KEY")
    if fred_key:
        obb.user.credentials.fred_api_key = fred_key
    return obb
