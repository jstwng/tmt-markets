"""Intent classifier for routing queries to the correct execution path."""

import json
import logging
from dataclasses import dataclass

from api.agent.llm import call_llm_text

logger = logging.getLogger(__name__)

__all__ = ["classify_intent", "IntentResult"]

_VALID_INTENTS = {"search", "quant", "hybrid", "conversational"}

CLASSIFIER_SYSTEM_PROMPT = """\
Classify the user's financial research query into exactly one category.

Categories:
- "search": needs real-time or recent information from the web — earnings call summaries, \
analyst commentary, recent news, management guidance, event reactions, "what did X say"
- "quant": needs computation with financial tools — portfolio optimization, backtesting, \
covariance/correlation, risk metrics, price data fetching, efficient frontier, stress \
testing, factor analysis, charts
- "hybrid": needs BOTH web search context AND quantitative computation — e.g., "how did \
the market react to the last CPI print" (needs search for what happened + price data \
for the move)
- "conversational": answerable from general knowledge without tools or search — \
explanations of concepts, follow-up clarifications, opinions, strategy discussion

Rules:
- If the query references recent events, specific dates, or "latest"/"last"/"recent" \
+ a company event → search or hybrid
- If the query asks for numbers, optimization, backtesting, risk analysis, or uses \
tickers with an analytical verb → quant
- If uncertain between search and hybrid, choose hybrid
- If uncertain between conversational and quant, choose quant

Output ONLY valid JSON: {"intent": "<category>"}
"""


@dataclass
class IntentResult:
    intent: str  # "search" | "quant" | "hybrid" | "conversational"


async def classify_intent(
    message: str,
    conversation_context: str | None = None,
) -> IntentResult:
    """Classify user message intent for routing.

    Args:
        message: The user's message.
        conversation_context: Optional one-line summary of recent conversation state.

    Returns:
        IntentResult with one of: search, quant, hybrid, conversational.
        Defaults to hybrid on any failure (safest — runs both phases).
    """
    user_input = message
    if conversation_context:
        user_input = f"{message}\n\nConversation context: {conversation_context}"

    try:
        raw = await call_llm_text(
            CLASSIFIER_SYSTEM_PROMPT,
            user_input,
            temperature=0.0,
            max_tokens=64,
        )
        parsed = json.loads(raw.strip())
        intent = parsed.get("intent", "hybrid")
        if intent not in _VALID_INTENTS:
            logger.warning("Classifier returned unknown intent %r, defaulting to hybrid", intent)
            intent = "hybrid"
        return IntentResult(intent=intent)
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Classifier JSON parse failed (%s), defaulting to hybrid", e)
        return IntentResult(intent="hybrid")
    except Exception as e:
        logger.warning("Classifier call failed (%s), defaulting to hybrid", e)
        return IntentResult(intent="hybrid")
