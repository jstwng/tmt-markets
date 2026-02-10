# Inline Citations & Source Integrity — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure all citation sources come from real search grounding (zero hallucinated sources), display superscript citation numbers inline in chat text, and tighten the classifier so source-needing queries never land in the ungrounded conversational path.

**Architecture:** Three backend prompt changes (classifier rules, system prompt citation rules, search prompt citation format) plus one frontend change (superscript rendering in TextBlock). No new files — all modifications to existing code.

**Tech Stack:** Python (FastAPI agent prompts), React + TypeScript (TextBlock component), Vitest (frontend tests), Pytest (backend tests)

---

### Task 1: Tighten classifier — uncertain conversational → search

**Files:**
- Modify: `packages/api/api/agent/classifier.py:15-38` (CLASSIFIER_SYSTEM_PROMPT)
- Modify: `packages/api/tests/test_classifier.py`

- [ ] **Step 1: Write a failing test for the new classification rule**

Add a test that verifies the classifier prompt contains the new routing rule. We can't unit-test LLM output deterministically, but we can verify the prompt text that governs behavior:

```python
def test_classifier_prompt_prefers_search_over_conversational():
    """Classifier should route uncertain conversational/search to search."""
    from api.agent.classifier import CLASSIFIER_SYSTEM_PROMPT
    assert "uncertain between conversational and search" in CLASSIFIER_SYSTEM_PROMPT.lower()
    assert "search" in CLASSIFIER_SYSTEM_PROMPT.lower()
```

Run: `cd packages/api && python -m pytest tests/test_classifier.py::test_classifier_prompt_prefers_search_over_conversational -v`
Expected: FAIL — the prompt doesn't contain this text yet.

- [ ] **Step 2: Update CLASSIFIER_SYSTEM_PROMPT**

In `packages/api/api/agent/classifier.py`, update the `CLASSIFIER_SYSTEM_PROMPT` Rules section. Replace the existing rules block:

```python
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
- "conversational": answerable purely from definitional or conceptual knowledge — \
explanations of financial terms, methodology questions, follow-up clarifications \
about a prior response. Does NOT include questions that reference specific companies, \
market events, or current data.

Rules:
- If the query references recent events, specific dates, or "latest"/"last"/"recent" \
+ a company event → search or hybrid
- If the query asks for numbers, optimization, backtesting, risk analysis, or uses \
tickers with an analytical verb → quant
- If uncertain between search and hybrid, choose hybrid
- If uncertain between conversational and quant, choose quant
- If uncertain between conversational and search, choose search
- conversational is ONLY for pure concept/definition questions with no company or \
market-specific content

Output ONLY valid JSON: {"intent": "<category>"}
"""
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `cd packages/api && python -m pytest tests/test_classifier.py -v`
Expected: ALL PASS (existing tests still pass, new test passes)

- [ ] **Step 4: Commit**

```bash
git add packages/api/api/agent/classifier.py packages/api/tests/test_classifier.py
git commit -m "fix: tighten classifier to route uncertain conversational queries to search"
```

---

### Task 2: Add citation discipline rules to SYSTEM_PROMPT

**Files:**
- Modify: `packages/api/api/agent/prompts.py` (add Citation Rules section)

- [ ] **Step 1: Write a failing test for citation rules in prompt**

Create a simple test that verifies the system prompt contains citation discipline:

```python
# In a new or existing test file: packages/api/tests/test_prompts.py
def test_system_prompt_has_citation_rules():
    from api.agent.prompts import SYSTEM_PROMPT
    assert "citation" in SYSTEM_PROMPT.lower()
    assert "fabricate" in SYSTEM_PROMPT.lower() or "hallucinate" in SYSTEM_PROMPT.lower() or "invent" in SYSTEM_PROMPT.lower()
    assert "superscript" in SYSTEM_PROMPT.lower() or "¹" in SYSTEM_PROMPT
```

Run: `cd packages/api && python -m pytest tests/test_prompts.py::test_system_prompt_has_citation_rules -v`
Expected: FAIL — no citation rules exist yet.

- [ ] **Step 2: Add Citation Rules section to SYSTEM_PROMPT**

In `packages/api/api/agent/prompts.py`, add the following section to `SYSTEM_PROMPT` right before the `## When Research Context Is Provided` section at the end:

```python
## Citation Rules
- When your response includes information from web search results, cite sources using \
Unicode superscript numbers (¹, ², ³, ⁴, ⁵, ⁶, ⁷, ⁸, ⁹) corresponding to the \
search result indices. Place the superscript immediately after the relevant claim.
- NEVER fabricate source attributions. Do not write "according to Bloomberg", \
"Reuters reports", "analysts at Goldman say", or any similar attribution unless it \
is directly backed by a numbered search result you are citing.
- NEVER invent URLs, source names, or publication names.
- If no web search context is available in this response, state facts without any \
source attribution. Do not reference sources you do not have.
- Multiple claims from the same source use the same superscript number.
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `cd packages/api && python -m pytest tests/test_prompts.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add packages/api/api/agent/prompts.py packages/api/tests/test_prompts.py
git commit -m "fix: add citation discipline rules to system prompt — no fabricated sources"
```

---

### Task 3: Update SEARCH_SYSTEM_PROMPT to require superscript citations

**Files:**
- Modify: `packages/api/api/agent/search.py:16-20` (SEARCH_SYSTEM_PROMPT)
- Modify: `packages/api/tests/test_search_phase.py`

- [ ] **Step 1: Write a failing test for citation format in search prompt**

```python
def test_search_prompt_requires_superscript_citations():
    from api.agent.search import SEARCH_SYSTEM_PROMPT
    assert "superscript" in SEARCH_SYSTEM_PROMPT.lower() or "¹" in SEARCH_SYSTEM_PROMPT
    assert "fabricate" in SEARCH_SYSTEM_PROMPT.lower() or "invent" in SEARCH_SYSTEM_PROMPT.lower()
```

Run: `cd packages/api && python -m pytest tests/test_search_phase.py::test_search_prompt_requires_superscript_citations -v`
Expected: FAIL

- [ ] **Step 2: Update SEARCH_SYSTEM_PROMPT**

In `packages/api/api/agent/search.py`, replace the `SEARCH_SYSTEM_PROMPT`:

```python
SEARCH_SYSTEM_PROMPT = """\
You are an experienced TMT portfolio manager answering a financial research question \
using web search. Be concise, data-anchored, and cite specific figures when available. \
Institutional tone — no hype or colloquialisms.

Citation format: use Unicode superscript numbers (¹, ², ³, ⁴, ⁵) immediately after \
each claim, corresponding to the search result index that supports it. Every factual \
claim from a search result MUST have a superscript citation. \
Never fabricate source attributions — do not write "according to X" or "X reports" \
unless it is backed by a numbered search result.\
"""
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `cd packages/api && python -m pytest tests/test_search_phase.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add packages/api/api/agent/search.py packages/api/tests/test_search_phase.py
git commit -m "fix: require superscript citations in search prompt"
```

---

### Task 4: Render superscript citations in TextBlock

**Files:**
- Modify: `packages/web/src/components/chat/TextBlock.tsx`
- Modify: `packages/web/src/components/chat/TextBlock.test.tsx`

- [ ] **Step 1: Write failing tests for superscript citation rendering**

Add tests to `packages/web/src/components/chat/TextBlock.test.tsx`:

```tsx
it("renders Unicode superscript digits as styled citation markers", () => {
  render(<TextBlock text="NVDA beat estimates¹ and raised guidance²" />);
  const sups = document.querySelectorAll("sup");
  expect(sups.length).toBe(2);
  expect(sups[0].textContent).toBe("1");
  expect(sups[1].textContent).toBe("2");
});

it("renders grouped superscript digits as separate markers", () => {
  render(<TextBlock text="Revenue grew¹² driven by data center" />);
  const sups = document.querySelectorAll("sup");
  expect(sups.length).toBe(2);
  expect(sups[0].textContent).toBe("1");
  expect(sups[1].textContent).toBe("2");
});

it("does not alter text without superscript digits", () => {
  render(<TextBlock text="No citations here, just regular text." />);
  const sups = document.querySelectorAll("sup");
  expect(sups.length).toBe(0);
  expect(screen.getByText(/No citations here/)).toBeInTheDocument();
});
```

Run: `cd packages/web && npx vitest run src/components/chat/TextBlock.test.tsx`
Expected: FAIL — superscript digits render as plain text, not `<sup>` elements.

- [ ] **Step 2: Implement superscript citation preprocessing in TextBlock**

In `packages/web/src/components/chat/TextBlock.tsx`, add a preprocessing function and apply it before passing text to ReactMarkdown:

```tsx
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

interface TextBlockProps {
  text: string;
}

const SUPERSCRIPT_MAP: Record<string, string> = {
  "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
  "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
};

const SUPERSCRIPT_RE = /[⁰¹²³⁴⁵⁶⁷⁸⁹]+/g;

function preprocessCitations(text: string): string {
  return text.replace(SUPERSCRIPT_RE, (match) => {
    return [...match]
      .map((ch) => `<sup>${SUPERSCRIPT_MAP[ch] ?? ch}</sup>`)
      .join("");
  });
}

const components: Components = {
  p({ children }) {
    return <p className="text-sm leading-relaxed mb-2 last:mb-0">{children}</p>;
  },
  strong({ children }) {
    return <strong className="font-semibold text-foreground">{children}</strong>;
  },
  em({ children }) {
    return <em className="italic">{children}</em>;
  },
  sup({ children }) {
    return (
      <sup className="text-[10px] text-blue-400 font-medium ml-[1px] cursor-default">
        {children}
      </sup>
    );
  },
  pre({ children }) {
    return (
      <pre className="bg-muted rounded px-3 py-2 text-xs overflow-x-auto font-mono leading-relaxed my-2">
        {children}
      </pre>
    );
  },
  code({ children, className }) {
    if (className) {
      return <code>{children}</code>;
    }
    const text = typeof children === "string" ? children : "";
    if (text.includes("\n")) {
      return <code>{children}</code>;
    }
    return (
      <code className="bg-muted border border-border rounded px-1 py-0.5 text-xs font-mono text-blue-300">
        {children}
      </code>
    );
  },
  ul({ children }) {
    return <ul className="list-disc pl-5 space-y-1 my-2 text-sm">{children}</ul>;
  },
  ol({ children }) {
    return <ol className="list-decimal pl-5 space-y-1 my-2 text-sm">{children}</ol>;
  },
  li({ children }) {
    return <li className="leading-relaxed">{children}</li>;
  },
  table({ children }) {
    return (
      <div className="overflow-x-auto my-2">
        <table className="w-full border-collapse text-xs">{children}</table>
      </div>
    );
  },
  thead({ children }) {
    return <thead className="border-b border-border">{children}</thead>;
  },
  tbody({ children }) {
    return <tbody>{children}</tbody>;
  },
  tr({ children }) {
    return <tr className="border-b border-border/50 last:border-0">{children}</tr>;
  },
  th({ children }) {
    return (
      <th className="text-left px-3 py-1.5 text-muted-foreground font-medium">
        {children}
      </th>
    );
  },
  td({ children }) {
    return <td className="px-3 py-1.5">{children}</td>;
  },
};

export default function TextBlock({ text }: TextBlockProps) {
  const processed = preprocessCitations(text);
  return (
    <div className="space-y-0">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={components}
        allowedElements={undefined}
        unwrapDisallowed={false}
      >
        {processed}
      </ReactMarkdown>
    </div>
  );
}
```

Note: ReactMarkdown v10 with `remark-gfm` passes through HTML tags like `<sup>` by default when using `rehype-raw`. However, by default it sanitizes HTML. We need to add `rehype-raw` to allow the `<sup>` tags through. Install it:

```bash
cd packages/web && npm install rehype-raw
```

Then update the ReactMarkdown usage:

```tsx
import rehypeRaw from "rehype-raw";

// In the component:
<ReactMarkdown
  remarkPlugins={[remarkGfm]}
  rehypePlugins={[rehypeRaw]}
  components={components}
>
  {processed}
</ReactMarkdown>
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `cd packages/web && npx vitest run src/components/chat/TextBlock.test.tsx`
Expected: ALL PASS (new citation tests + existing tests)

- [ ] **Step 4: Commit**

```bash
git add packages/web/src/components/chat/TextBlock.tsx packages/web/src/components/chat/TextBlock.test.tsx packages/web/package.json packages/web/package-lock.json
git commit -m "feat: render superscript citation numbers in chat text"
```

---

### Task 5: Verify end-to-end — all existing tests pass

**Files:** None (verification only)

- [ ] **Step 1: Run all backend tests**

Run: `cd packages/api && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 2: Run all frontend tests**

Run: `cd packages/web && npx vitest run`
Expected: ALL PASS

- [ ] **Step 3: Commit (if any fixups needed)**

```bash
git add -u
git commit -m "fix: address test failures from citation changes"
```

Only commit if Step 1 or 2 required fixes. Skip if everything passed clean.
