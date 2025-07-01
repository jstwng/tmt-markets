# Project Instructions for AI Agents

**IMPORTANT: This project uses `bd` (beads) for task tracking. When asked to "work on the next task" or similar, ALWAYS run `bd ready` first to find unblocked tasks. Do NOT use TodoWrite, TaskCreate, TaskList, or any built-in task system. Beads is the ONLY task tracker.**

---

## Workflow

Superpowers and Beads work together. Superpowers handles HOW you work. Beads handles WHAT you work on.

### Starting a Session

1. Run `bd ready` to see unblocked tasks. This is ALWAYS the first step.
2. Check `docs/superpowers/plans/` for the implementation plan matching the task. Read the detailed steps for the task (match by task title/number).
3. Run `bd show <id>` for task details, then `bd update <id> --claim` to claim it.
4. Execute the task following the skills workflow below.

### New Features (Brainstorming -> Plan -> Execute)

1. **Brainstorm** — Invoke `superpowers:brainstorming` via the Skill tool to design the feature. Produces a spec in `docs/superpowers/specs/`.
2. **Plan** — Invoke `superpowers:writing-plans` via the Skill tool to break the spec into granular 2-5 minute tasks. Produces a plan in `docs/superpowers/plans/`.
3. **Create beads issues** — Convert EVERY plan task into a beads issue with `bd create`. Set dependencies with `bd dep add`. The beads database is the source of truth, NOT the markdown plan.
4. **Execute** — Work through tasks one at a time using the workflow below.

### Executing Each Task — Required Skills

**You MUST use superpowers skills via the Skill tool. Do NOT implement your own versions of these processes.**

**For coding tasks** (writing code, tests, scripts):
1. **Before writing any code:** Invoke `superpowers:test-driven-development` via the Skill tool. Follow it exactly — red/green/refactor. Do NOT write tests or production code without invoking this skill first.
2. **If a test fails unexpectedly or you hit a bug:** Invoke `superpowers:systematic-debugging` via the Skill tool. Do NOT guess at fixes.
3. **After completing the task:** Invoke `superpowers:requesting-code-review` via the Skill tool. Do NOT skip this step. Fix any critical issues before closing.

**For non-coding tasks** (creating directories, writing docs, curating data):
1. Follow the plan steps directly — TDD does not apply.
2. Still invoke `superpowers:requesting-code-review` after completing if any files were created or modified.

### Discovered Work

If you find a bug, TODO, or missing feature while working on a task, do NOT fix it inline. Instead:
```bash
bd create "Description of discovered issue" -t bug -p 2
bd dep add <new-id> --blocked-by <current-task-id> -t discovered-from
```
Then continue with the original task.

### Closing a Task

```bash
bd close <id> --reason "Done: <what was accomplished>"
bd remember "<anything surprising or useful for future tasks>"
bd ready              # See what just unblocked
```

### Git Branching

- Create a feature branch for each epic or major feature: `git checkout -b feat/<feature-name>`
- Commit after each completed task with a descriptive message
- Do NOT work directly on main

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files
- ALWAYS run `bd ready` before starting work — never guess what to do next
- ALWAYS read the implementation plan for detailed steps before starting a task
- ALWAYS invoke superpowers skills (TDD, debugging, code-review) via the Skill tool — never roll your own
- ALWAYS run `bd remember` after completing a task with anything useful for future work
- Plans are reference material. Beads is the source of truth for task status.
- When you discover new work during a task, create a beads issue — do NOT fix it inline.

---

## Build & Test

```bash
# Install dependencies
npm install

# Run tests
npm test

# Start dev server
npm run dev
```

## Conventions & Patterns

_Add your project-specific conventions here (language, formatting, style)._

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create beads issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
