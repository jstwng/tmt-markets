# Rich Text Rendering in Chat

**Date:** 2026-04-08  
**Status:** Approved

## Problem

`TextBlock.tsx` currently parses markdown with a minimal regex approach — only fenced code blocks are handled. All other markdown syntax (`**bold**`, `` `inline code` ``, `- lists`, `1. numbered`, `| tables |`) renders as raw text, degrading readability of AI responses.

## Solution

Replace `TextBlock.tsx`'s custom parser with `react-markdown` + `remark-gfm`. Write custom React renderers for all markdown elements to match the app's dark theme.

## Scope

- **In scope:** AI assistant text blocks only (`TextBlock` component)
- **Out of scope:** User message bubbles (stay plain text), `TableBlock` (structured tool output, unchanged), all other block types

## Dependencies

Add to `packages/web`:
- `react-markdown` — React component wrapping a markdown parser
- `remark-gfm` — GFM plugin enabling tables, numbered lists, strikethrough

## Architecture

`TextBlock.tsx` is rewritten as a thin wrapper around `<ReactMarkdown>` with a `components` prop supplying custom renderers. The existing file is replaced entirely; no other files change.

## Custom Renderers

Each renderer applies inline Tailwind/style matching the existing dark theme:

| Element | Renderer |
|---|---|
| `strong` | Bold, white text (`color: #f0f0f0`) |
| `em` | Italic |
| `code` (inline) | Dark bg (`#1e2533`), blue tint (`#79c0ff`), border, monospace |
| `pre` + `code` (fenced) | Existing `<pre>` block styling — `bg-muted rounded px-3 py-2 text-xs font-mono` |
| `p` | `text-sm leading-relaxed` with bottom margin |
| `ul` | `list-disc pl-5 space-y-1` |
| `ol` | `list-decimal pl-5 space-y-1` |
| `li` | `text-sm leading-relaxed` |
| `table` | Full-width, `border-collapse`, `text-xs` |
| `thead` / `th` | Muted color, `font-medium`, bottom border |
| `tbody` / `tr` | Row divider via bottom border |
| `td` | `px-3 py-1.5`, right-align for numeric columns not handled (left-align default) |

## Fenced Code Block Behavior

The existing fenced code block experience is preserved: language hints are stripped, content is rendered in a monospace pre block. The `pre` renderer strips the outer `<pre>` and delegates to the `code` renderer's block variant.

## Markdown Tables vs. TableBlock

Markdown tables (inline prose from AI) render via the custom `table` renderer in `TextBlock`. Structured `TableBlock` (from tool output) is unrelated and unchanged. These two surfaces have separate styling but should feel visually consistent.

## Testing

- Render a message containing bold, italic, inline code, bullet list, numbered list, fenced code block, and a markdown table — verify each renders correctly
- Confirm fenced code blocks still strip language hints
- Confirm streaming (incremental text) does not cause layout thrash
- Confirm user message bubbles are unaffected
