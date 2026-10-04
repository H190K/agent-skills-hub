---
name: dispatching-parallel-agents
description: Use when 2+ problems are independent — different failing test files, unrelated subsystems, separate bugs — and working them sequentially wastes time; spawn one focused agent per domain, dispatch all of them in one batch, then integrate and verify together.
version: 1.0.0
author: adapted from obra/superpowers (MIT)
license: MIT
platforms: [linux, macos, windows]
---

# Dispatching Parallel Agents

## Overview

You delegate work to fresh agents with isolated context. Each agent receives exactly the context you construct for it — never your session's history — which keeps it focused and keeps your own context free for coordination instead of execution.

When several unrelated failures exist (different test files, different subsystems, different bugs), investigating them sequentially wastes time. Each investigation is independent and can happen concurrently.

**Core principle:** one agent per independent problem domain; every dispatch issued in the same batch, so they run concurrently.

## When to Use

- 3+ test files failing with different root causes.
- Multiple subsystems broken independently.
- Each problem can be understood without context from the others.
- No shared state between investigations — same files would be touched nowhere, or only at well-separated seams.

**Don't use when:**

- The failures are related (fixing one may fix the others) — investigate together first.
- The work requires understanding the whole system at once.
- Agents would interfere: editing the same files, running tests that lock the same resources, or relying on each other's output.
- The problem is still exploratory — you cannot scope a domain you have not identified yet.

## The Pattern

### 1. Identify independent domains

Group the failures by what is actually broken, not by file name alone:

- `agent-tool-abort.test.ts`: timeout handling in the abort flow
- `batch-completion.test.ts`: event structure of batch completion
- `tool-approval.test.ts`: approval race conditions

Each domain is independent: fixing batch events does not touch abort timeouts. If two domains turn out to share a root cause, merge them into one task — parallel agents on the same bug produce conflicting fixes.

### 2. Craft focused tasks

Each agent's task must carry four things:

- **Specific scope** — one test file or subsystem. "Fix all the tests" produces a wandering agent.
- **Clear goal** — make these tests pass, stated as the acceptance condition.
- **Constraints** — what the agent must not touch ("do not change production code outside this module", "do not delete tests to make them pass").
- **Expected output** — what comes back: root cause found, what was changed, files touched.

The context is constructed, not inherited. Paste the real error messages and test names into the task; an agent that must go find its own context re-does your investigation from zero.

### 3. Dispatch in one batch

Issue every dispatch in the same response so the agents run concurrently. One dispatch per response is sequential and gains you nothing.

```
Agent 1: fix the agent-tool-abort tests (paste the 3 failing test names + errors)
Agent 2: fix the batch-completion tests (paste the 2 failing test names + errors)
Agent 3: fix the tool-approval tests (paste the failing test + error)
```

Three is a sound default fan-out. More agents means more integration cost and more conflicting suggestions, not wider coverage; keep the fan-out proportional to the number of genuinely independent domains.

### 4. Review and integrate

When the agents return:

1. **Read each summary** — what changed, and why.
2. **Check for conflicts** — did two agents edit the same code? Their summaries alone do not answer this; `git diff` does. Overlapping edits are resolved by you, in the open.
3. **Run the full suite** — each agent verified its own slice; only a suite run verifies the combination. A green slice over a red suite means integration, not implementation, broke.
4. **Spot-check** — agents make systematic errors (deleting a test instead of fixing it, stubbing a check). Sample the diffs, not just the summaries.

## Agent Prompt Shape

Good tasks are focused, self-contained, and specific about output:

```text
Fix the 3 failing tests in src/agents/tool_abort.test.ts:

1. "should abort tool with partial output capture" — expects 'interrupted at' in message
2. "should handle mixed completed and aborted tools" — fast tool aborted instead of completed
3. "should track pending tool count" — expects 3 results but gets 0

These are timing/race-condition issues. Your task:

1. Read the test file; understand what each test verifies.
2. Identify the root cause — timing issues or actual bugs?
3. Fix by replacing arbitrary timeouts with event-based waiting, fixing the
   abort implementation if it is wrong, or adjusting a test that asserts
   changed behavior. Do NOT just increase timeouts to make tests pass.
4. Do not modify files outside src/agents/.

Return: root cause per test, and the diff summary.
```

## Common Mistakes

| Too broad | Right |
|-----------|-------|
| "Fix all the tests" | "Fix the 3 tests in tool_abort.test.ts" |
| "Fix the race condition" (no context) | Paste the error messages and test names |
| No constraints — agent refactors everything | "Do NOT change production code outside this module" |
| "Fix it" — no defined output | "Return root cause + diff summary" |

## Real Example

Six test failures across three files after a major refactor. The domains are
independent: abort timeouts, batch event structure, approval execution counts.

Dispatched three agents, one per file, each with its failing tests and error
output. Results:

- Agent 1: replaced fixed timeouts with event-based waiting.
- Agent 2: fixed an event-structure bug (identifier recorded in the wrong field).
- Agent 3: added a wait for async execution before asserting the count.

All three fixes touched disjoint code. Full suite after integration: green on
the first run — the parallel split held.

## Verification Checklist

- [ ] One task per independent domain, not per test.
- [ ] Every task carries scope, goal, constraints, and expected output.
- [ ] All dispatches issued in one batch.
- [ ] Integration checked with `git diff`, not agent summaries alone.
- [ ] Full suite run after integrating, and spot-checked at least one diff against summary claims.