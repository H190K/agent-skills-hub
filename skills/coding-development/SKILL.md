---
name: coding-development
description: Use when reviewing or refactoring code, debugging a failing program, or building a script, app, API or integration — any task that ends in changed code.
version: 1.4.0
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
- Before reporting the work as finished — the `verification-before-completion` skill states what
  counts as evidence for each kind of claim.
- Writing the plan rather than the code — the `plan` skill.

## Common Mistakes to Avoid

1. Over-engineering simple solutions
2. Not testing after changes
3. Missing error handling for edge cases
4. Hardcoding values that should be configurable
5. Not checking existing code before making changes
6. Skipping dependency documentation
7. Not verifying the code actually runs
