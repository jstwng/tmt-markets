# Vantage Rebrand Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename all "TMT Markets" branding to "Vantage" across the codebase and Vercel project.

**Architecture:** Pure find-and-replace across 5 files, then a Vercel CLI project rename. No logic changes, no new files.

**Tech Stack:** React/TypeScript (Vite), Vercel CLI

---

### Task 1: Rename brand text in code files

**Files:**
- Modify: `packages/web/index.html`
- Modify: `packages/web/src/App.tsx`
- Modify: `packages/web/src/pages/Login.tsx`
- Modify: `packages/web/src/pages/Chat.tsx`
- Modify: `package.json`

- [ ] **Step 1: Update `packages/web/index.html`**

Change line 6:
```html
<!-- Before -->
<title>TMT Markets</title>

<!-- After -->
<title>Vantage</title>
```

- [ ] **Step 2: Update `packages/web/src/App.tsx`**

Change line 39 (the header brand link):
```tsx
// Before
TMT Markets

// After
Vantage
```

- [ ] **Step 3: Update `packages/web/src/pages/Login.tsx`**

Change line 10:
```tsx
// Before
<h1 className="text-2xl font-semibold tracking-tight">TMT Markets</h1>

// After
<h1 className="text-2xl font-semibold tracking-tight">Vantage</h1>
```

- [ ] **Step 4: Update `packages/web/src/pages/Chat.tsx`**

Change line 162:
```tsx
// Before
<h2 className="text-2xl font-semibold tracking-tight">TMT Markets</h2>

// After
<h2 className="text-2xl font-semibold tracking-tight">Vantage</h2>
```

- [ ] **Step 5: Update root `package.json`**

Change the `name` field:
```json
// Before
"name": "tmt-markets",

// After
"name": "vantage",
```

- [ ] **Step 6: Verify no "TMT Markets" remains**

Run:
```bash
grep -r "TMT Markets\|tmt-markets" packages/web/src packages/web/index.html package.json
```
Expected: no output

- [ ] **Step 7: Commit**

```bash
git add packages/web/index.html packages/web/src/App.tsx packages/web/src/pages/Login.tsx packages/web/src/pages/Chat.tsx package.json
git commit -m "rebrand: rename TMT Markets to Vantage"
```

---

### Task 2: Rename Vercel project

**Files:** None (Vercel dashboard/CLI only)

- [ ] **Step 1: Rename via Vercel CLI**

```bash
vercel project rename tmt-markets vantage --scope jstwngs-projects
```

If the CLI isn't authenticated, run `vercel login` first.

- [ ] **Step 2: Verify the rename**

```bash
vercel project ls --scope jstwngs-projects
```

Expected: project named `vantage` appears in the list (no `tmt-markets`).

- [ ] **Step 3: Confirm new domain is live**

After the next deployment, the app will be available at:
`https://vantage.vercel.app`

Note: `tmt-markets.vercel.app` will stop responding — there is no automatic redirect.

- [ ] **Step 4: Push to trigger redeployment**

```bash
git push
```

Wait for Vercel to build and deploy. Check the Vercel dashboard to confirm the deployment succeeded under the `vantage` project.
