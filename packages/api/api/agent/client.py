"""Gemini client factory for the TMT Markets agent."""

import os

from dotenv import load_dotenv
from google import genai

from api.agent.prompts import SYSTEM_PROMPT

load_dotenv()  # Load .env from the current working directory (packages/api)

__all__ = ["create_gemini_client", "MODEL_NAME"]

MODEL_NAME = "gemini-2.5-flash"


def create_gemini_client() -> genai.Client:
    """Create and configure a Gemini Client instance.

    Reads GEMINI_API_KEY from the environment. Uses gemini-2.5-flash
    for its strong reasoning and Function Calling capabilities.

    Returns:
        Configured genai.Client ready for use.

    Raises:
        EnvironmentError: If GEMINI_API_KEY is not set.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY environment variable is not set. "
            "Set it in packages/api/.env before starting the server."
        )

    return genai.Client(api_key=api_key)
