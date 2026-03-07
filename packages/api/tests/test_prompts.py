"""Tests for system prompt content."""


def test_system_prompt_has_citation_rules():
    from api.agent.prompts import SYSTEM_PROMPT
    assert "citation" in SYSTEM_PROMPT.lower()
    assert "fabricate" in SYSTEM_PROMPT.lower() or "hallucinate" in SYSTEM_PROMPT.lower() or "invent" in SYSTEM_PROMPT.lower()
    assert "superscript" in SYSTEM_PROMPT.lower() or "¹" in SYSTEM_PROMPT
