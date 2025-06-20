"""OpenBB Platform client singleton for sandboxed code execution."""

from openbb import obb

# Use DataFrame output by default — generated code often transforms DataFrames
obb.user.preferences.output_type = "dataframe"


def get_obb_client():
    """Return the configured OpenBB client singleton.

    Free providers (yfinance, FRED, SEC EDGAR) are available
    without API keys. Paid providers can be added later via
    obb.user.credentials.
    """
    return obb
