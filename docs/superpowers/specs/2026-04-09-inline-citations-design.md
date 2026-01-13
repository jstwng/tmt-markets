# Inline Citations & Source Integrity

**Date**: 2026-04-09
**Status**: Approved

## Problem

1. The LLM generates text referencing sources by name ("according to Bloomberg...") but no numbered citation markers appear inline.
2. Users cannot distinguish hallucinated source attributions from real grounded sources.
3. The `conversational` intent path calls `call_llm_text` without any search tool, so any source references in that path are 100% fabricated.

## Solution

### 1. Classifier Tightening

**File**: `packages/api/api/agent/classifier.py`

Update `CLASSIFIER_SYSTEM_PROMPT` rules:
- Add: "If uncertain between conversational and search, choose search"
- Narrow conversational to only concept explanations, definitional questions, and follow-up clarifications that don't reference real-world events, companies, or data points

### 2. Citation Discipline in System Prompt

**File**: `packages/api/api/agent/prompts.py`

Add `## Citation Rules` section to `SYSTEM_PROMPT`:
- When web search context is available, use Unicode superscript numbers (¹, ², ³...) to cite inline, matching grounding source indices
- Never fabricate source attributions (no "according to Bloomberg" unless backed by a grounding source)
- Never invent URLs or source names
- If no search context is available, state facts without attribution

### 3. Search Prompt Citation Format

**File**: `packages/api/api/agent/search.py`

Update `SEARCH_SYSTEM_PROMPT`:
- Require Unicode superscript citation numbers (¹, ², ³...) corresponding to search result indices
- Never attribute information to a source not provided by the search tool

### 4. Frontend Superscript Rendering

**File**: `packages/web/src/components/chat/TextBlock.tsx`

Pre-process text before passing to ReactMarkdown:
- Match Unicode superscript digit sequences (¹²³⁴⁵⁶⁷⁸⁹⁰) and group consecutive ones
- Wrap in styled `<sup>` spans with distinct visual treatment (small text, blue color, slight offset)

**File**: `packages/web/src/components/chat/TextBlock.test.tsx`

Add tests for superscript citation rendering.

### 5. Files NOT Changing

- `GroundingSource` data model — already correct
- `CitationsFooter` component — already correct
- `useChat.ts` SSE handling — already collects grounding_sources
- `MessageBubble.tsx` — already renders CitationsFooter
- Backend grounding extraction in `llm.py` and `search.py` — already pulls from API metadata

## Change Summary

| File | Change |
|---|---|
| `classifier.py` | Tighten routing: uncertain between conversational/search → search |
| `prompts.py` | Add citation discipline rules to SYSTEM_PROMPT |
| `search.py` | Add citation format instructions to SEARCH_SYSTEM_PROMPT |
| `TextBlock.tsx` | Render superscript citation numbers with styling |
| `TextBlock.test.tsx` | Add tests for citation rendering |
