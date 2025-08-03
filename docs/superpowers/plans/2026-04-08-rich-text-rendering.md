# Rich Text Rendering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace TextBlock's ad-hoc regex parser with react-markdown + remark-gfm to render bold, inline code, bullet lists, numbered lists, and markdown tables in AI chat responses.

**Architecture:** Add `react-markdown` and `remark-gfm` as dependencies, add `vitest` + `@testing-library/react` for testing, rewrite `TextBlock.tsx` as a thin wrapper around `<ReactMarkdown>` with custom styled renderers. No other files change.

**Tech Stack:** React 19, react-markdown, remark-gfm, vitest, @testing-library/react, Tailwind CSS v4

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `packages/web/package.json` | Modify | Add react-markdown, remark-gfm, vitest, @testing-library/react |
| `packages/web/vite.config.ts` | Modify | Add vitest config block |
| `packages/web/src/components/chat/TextBlock.tsx` | Rewrite | Use ReactMarkdown with custom renderers |
| `packages/web/src/components/chat/TextBlock.test.tsx` | Create | Tests for markdown rendering |

---

### Task 1: Install dependencies and configure vitest

**Files:**
- Modify: `packages/web/package.json`
- Modify: `packages/web/vite.config.ts`

- [ ] **Step 1: Install runtime and test dependencies**

Run in `packages/web/`:
```bash
npm install react-markdown remark-gfm
npm install -D vitest @testing-library/react @testing-library/jest-dom @vitejs/plugin-react jsdom
```

Expected: no errors, packages appear in `node_modules/`.

- [ ] **Step 2: Add vitest config to vite.config.ts**

Replace the contents of `packages/web/vite.config.ts` with:

```ts
import path from "path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5175,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
})
```

- [ ] **Step 3: Create test setup file**

Create `packages/web/src/test-setup.ts`:

```ts
import "@testing-library/jest-dom";
```

- [ ] **Step 4: Add test script to package.json**

In `packages/web/package.json`, add to `"scripts"`:
```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 5: Verify vitest is wired up**

Run:
```bash
cd packages/web && npx vitest run --reporter=verbose 2>&1 | head -20
```

Expected: "No test files found" or similar — no errors about missing config.

- [ ] **Step 6: Commit**

```bash
git add packages/web/package.json packages/web/package-lock.json packages/web/vite.config.ts packages/web/src/test-setup.ts
git commit -m "chore: add vitest + react-markdown + remark-gfm to web package"
```

---

### Task 2: Write failing tests for TextBlock

**Files:**
- Create: `packages/web/src/components/chat/TextBlock.test.tsx`

- [ ] **Step 1: Create the test file**

Create `packages/web/src/components/chat/TextBlock.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import TextBlock from "./TextBlock";

describe("TextBlock", () => {
  it("renders bold text", () => {
    render(<TextBlock text="**hello world**" />);
    const bold = screen.getByText("hello world");
    expect(bold.tagName).toBe("STRONG");
  });

  it("renders inline code", () => {
    render(<TextBlock text="call `optimize_portfolio` now" />);
    const code = screen.getByText("optimize_portfolio");
    expect(code.tagName).toBe("CODE");
  });

  it("renders bullet list", () => {
    render(<TextBlock text={"- first item\n- second item"} />);
    expect(screen.getByText("first item")).toBeInTheDocument();
    expect(screen.getByText("second item")).toBeInTheDocument();
    expect(document.querySelector("ul")).toBeInTheDocument();
  });

  it("renders numbered list", () => {
    render(<TextBlock text={"1. step one\n2. step two"} />);
    expect(screen.getByText("step one")).toBeInTheDocument();
    expect(screen.getByText("step two")).toBeInTheDocument();
    expect(document.querySelector("ol")).toBeInTheDocument();
  });

  it("renders fenced code block", () => {
    render(<TextBlock text={"```python\nprint('hello')\n```"} />);
    const pre = document.querySelector("pre");
    expect(pre).toBeInTheDocument();
    expect(pre?.textContent).toContain("print('hello')");
  });

  it("strips language hint from fenced code block", () => {
    render(<TextBlock text={"```python\nprint('hi')\n```"} />);
    const pre = document.querySelector("pre");
    expect(pre?.textContent).not.toContain("python");
  });

  it("renders markdown table", () => {
    const table = "| Metric | Value |\n|---|---|\n| Sharpe | 1.42 |";
    render(<TextBlock text={table} />);
    expect(document.querySelector("table")).toBeInTheDocument();
    expect(screen.getByText("Metric")).toBeInTheDocument();
    expect(screen.getByText("1.42")).toBeInTheDocument();
  });

  it("renders plain paragraph text", () => {
    render(<TextBlock text="This is a plain sentence." />);
    expect(screen.getByText("This is a plain sentence.")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd packages/web && npx vitest run src/components/chat/TextBlock.test.tsx --reporter=verbose
```

Expected: several tests FAIL — the current TextBlock doesn't render markdown elements.

---

### Task 3: Rewrite TextBlock with react-markdown

**Files:**
- Modify: `packages/web/src/components/chat/TextBlock.tsx`

- [ ] **Step 1: Rewrite TextBlock.tsx**

Replace the entire contents of `packages/web/src/components/chat/TextBlock.tsx` with:

```tsx
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

interface TextBlockProps {
  text: string;
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
  code({ children, className }) {
    // Fenced code block: className is "language-xxx"; inline code has no className
    const isBlock = Boolean(className);
    if (isBlock) {
      return (
        <pre className="bg-muted rounded px-3 py-2 text-xs overflow-x-auto font-mono leading-relaxed my-2">
          <code>{children}</code>
        </pre>
      );
    }
    return (
      <code className="bg-muted border border-border rounded px-1 py-0.5 text-xs font-mono text-blue-300">
        {children}
      </code>
    );
  },
  pre({ children }) {
    // react-markdown wraps fenced blocks in <pre><code>. We handle the <pre>
    // inside the code renderer above, so just pass through here.
    return <>{children}</>;
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
  return (
    <div className="space-y-0">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {text}
      </ReactMarkdown>
    </div>
  );
}
```

- [ ] **Step 2: Run tests**

```bash
cd packages/web && npx vitest run src/components/chat/TextBlock.test.tsx --reporter=verbose
```

Expected: all 8 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add packages/web/src/components/chat/TextBlock.tsx packages/web/src/components/chat/TextBlock.test.tsx
git commit -m "feat: render markdown in TextBlock using react-markdown + remark-gfm"
```

---

### Task 4: Manual smoke test

**Files:** none

- [ ] **Step 1: Start the dev server**

```bash
cd packages/web && npm run dev
```

- [ ] **Step 2: Send a chat message that triggers a markdown response**

Ask the AI something like: "tell me what tools you have" — this produces bold headers, bullet lists, and inline code.

Verify in the browser:
- `**bold**` renders as bold text, not raw asterisks
- `` `tool_name` `` renders as styled inline code, not raw backticks
- Bullet points render as a proper `<ul>` list
- Numbered steps render as an `<ol>` list
- Fenced code blocks still render in the `<pre>` block as before
- A response with a markdown table renders as a styled `<table>`

- [ ] **Step 3: Verify user message bubbles are unaffected**

Type a message containing `**bold**` as a user. Confirm it renders as plain text (no markdown parsing in user bubbles — `MessageBubble.tsx` renders user text directly without going through `TextBlock`).
