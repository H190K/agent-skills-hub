---
name: coding-development
description: Use when reviewing or refactoring code, debugging a failing program, or building a script, app, API or integration — any task that ends in changed code.
version: 1.14.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
---

# Coding and Development

## Purpose

Build, debug, review, and improve software quickly and professionally.

## When to Use

- Python scripts and apps
- JavaScript / TypeScript / Node.js
- HTML / CSS / frontend
- Bash scripts and automation
- REST APIs and integrations
- Edge and serverless runtimes
- GitHub projects and PRs
- Debugging and error analysis
- Code review and refactoring
- Web apps and tools

## Parallel Work Pattern

For coding tasks, split into parallel workstreams:

```
Workstream 1: Code inspection / error analysis
Workstream 2: Fix / feature implementation
Workstream 3: Test planning and verification
Workstream 4: Documentation and notes
```

## Workflow

1. **Understand** — What should the code do? What's the target behavior?
2. **Inspect** — Read existing code, check for issues
3. **Plan** — Identify the fix or implementation path
4. **Implement** — Create or modify files
5. **Verify** — Test the result works
6. **Document** — Explain how to run, test, and deploy

## Coding Rules

- Prefer simple working solutions first
- Avoid unnecessary complexity or over-engineering
- Include file names and paths in output
- Include install commands (pip, npm, etc.)
- Include run commands
- Make scripts safe and reusable
- Add comments only where useful
- Keep code clean and maintainable
- Use idempotent patterns when possible

## Output Format

When delivering code:

````markdown
## File: path/to/file.py

[Full file content in code block]

## Install
```bash
pip install -r requirements.txt
```

## Run
```bash
python file.py
```

## Notes
- Dependencies
- Edge cases
- Known limitations
````

## Write the test before the fix, whenever a test is possible

For any bug fix or behaviour change, a failing test comes first — see the `test-driven-development`
skill. It is the only cheap proof that the change addresses the reported problem rather than an
adjacent one, and it is what stops the same bug reappearing later. Where a test genuinely cannot be
written (a one-off migration, a manual UI flow), say so in the delivery notes rather than leaving
the gap implicit.

## Related skills

- A failing test, crash or unexplained behaviour — the `systematic-debugging` skill's four phases
  apply before any fix is proposed.
- Writing or changing tests — the `test-driven-development` skill's RED–GREEN–REFACTOR cycle and its
  list of test shapes that can never fail.
- Someone is reviewing your code and raised findings — the `code-review-reception` skill, before you
  start implementing the list.
- A stubborn bug or a high-stakes design where a second model's opinion is worth real context — the
  `oracle` skill sends your prompt plus selected files to GPT/Gemini/Claude in one shot; treat its
  advice like any other review finding.
- A cleanup pass over your own recent changes before merging, or a request to "simplify" them —
  the `simplify-code` skill runs three narrow parallel reviewers (reuse, quality, efficiency),
  aggregates, and applies only what survives.
- Multiple unrelated failures at once — different test files, different subsystems — the
  `dispatching-parallel-agents` skill turns them into one focused agent per domain, dispatched in
  a single batch and integrated afterward.
- Before reporting the work as finished — the `verification-before-completion` skill states what
  counts as evidence for each kind of claim.
- Worked from a written plan, task by task — the `executing-plans` skill runs the loop with per-task
  briefs, a ledger that survives compaction, and one fresh whole-branch review at the end.
- Handing completed work to a fresh reviewer — the `requesting-code-review` skill has the
  review-package recipe and the reviewer prompt template.
- Starting work that needs its own workspace, or finishing it — the `using-git-worktrees` and
  `finishing-a-development-branch` skills cover isolation up front and the integration decision at
  the end.
- Writing the plan rather than the code — the `plan` skill.
- A feasibility unknown the docs cannot settle — "can this even work?", "does approach A
  survive real inputs?" — the `spike` skill runs throwaway experiments that end in a verdict
  before any real build starts.
- A research-adjacent deliverable — a README claim, benchmark table or
  announcement that cites outside sources — the `grounded-citations` skill's
  ledger keeps those citations traceable to retrieval instead of memory.
- Rewriting the prose around the code — a commit message, PR description or README — so it does not
  read as machine-written — the `humanizer` skill.
- A bug that reading cannot explain, a value that is wrong deep in a call stack, or a process you
  cannot restart — the `python-debugging` skill covers breakpoints and post-mortem inspection; the
  `node-debugging` skill is its Node.js counterpart (probe mode, REPL, attaching to a live process).
- A database that fails `PRAGMA integrity_check` or opens with "database disk image is malformed" —
  the `sqlite-recovery` skill extracts the readable data and rebuilds the database and its indexes.
- A task that touches X/Twitter through the API — posting, reading post objects, search, timelines,
  engagement, DMs or raw v2 endpoints — the `xurl` skill drives the official CLI, with the
  secret-handling rules that keep credentials out of an agent session.
- The user wants a picture of a system's structure — "diagram the architecture", a cloud/infra or
  deployment map — the `architecture-diagram` skill produces one dark-themed, self-contained
  HTML+SVG file with working PNG/PDF export, verified rendered before delivery.

## Common Mistakes to Avoid

1. Over-engineering simple solutions
2. Not testing after changes
3. Missing error handling for edge cases
4. Hardcoding values that should be configurable
5. Not checking existing code before making changes
6. Skipping dependency documentation
7. Not verifying the code actually runs
