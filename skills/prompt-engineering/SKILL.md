---
name: prompt-engineering
description: Use when writing or improving a prompt for another AI agent — task prompts, system prompts, agent definitions, or diagnosing why an existing prompt underperforms.
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
---

# Prompt Engineering

## Purpose

Produce a prompt that the receiving agent can execute without asking questions,
and that stays robust when the task runs long or something goes wrong. A good
prompt is written for the agent's context budget and failure modes, not read
like a spec.

## Workflow

1. **Identify the receiver and its surface.** A coding agent with shell access,
   a chat assistant, a background automation job, or a subagent spawned mid-run
   each constrain differently: file access, interactivity, whether it can ask
   questions, how much context it starts with.
2. **Understand the goal.** What artifact or state should exist when the agent
   is done? State the acceptance test, not the activity.
3. **Gather context the agent cannot fetch.** Working paths, environment facts,
   versions, conventions, and the exact error or text under discussion. Never
   make the agent guess an identifier that could have been pasted.
4. **Write the body.** Task first, constraints second, output shape third.
5. **Add safety rules** whenever the prompt can change real state — deletions,
   publishes, payments, messages to other people: name what must never happen,
   not just what should.
6. **Define the output format** explicitly — file paths, response structure,
   what to include, what to omit.
7. **Finalize.** Copy-ready in one block, no commentary before or after unless
   asked.

## Prompt Structure

```
# Role
Who the agent should act as, when it changes how it works.

# Context
Background, environment details, constraints, pasted inputs.

# Task
What to do — specific, actionable, with an acceptance test.

# Constraints / Rules
Boundaries, safety rules, what to avoid.

# Output Format
Deliverable shape: where files go, response structure, language.
```

Small task → shrink to Task + Output. Big task → do not grow the structure,
grow the specificity inside it.

## Rules for Strong Prompts

- **One prompt, one job.** Two deliverables in one prompt means one of them is
  done poorly. Split into two prompts or two subagent dispatches.
- **Acceptance test, not activity.** "The suite passes and the bug's failing
  test is in the commit" beats "make the tests work".
- **Complete on read.** The agent should never need to ask what to do next.
  If it would ask, that information goes in the prompt.
- **Paste, don't paraphrase.** Exact error messages, exact file paths, exact
  identifiers. A paraphrased error is a different bug.
- **Say what to do, not only what to avoid.** A prompt of pure prohibitions
  leaves the agent inventing the positive path.
- **State the output format explicitly** — the agent defaults to its own
  habits, which are almost never yours.
- **Name the escalation path.** What the agent should do when blocked: stop and
  report, skip and note, or pick the safest alternative.
- **Keep the failure story short.** One line telling it what to do on failure
  beats a contingency tree it will misread.

## Common Pitfalls and Fixes

| Pitfall | Fix |
| --- | --- |
| Vague task | State the deliverable and its acceptance test |
| No output format | Specify it; agents fill unspecified shapes with defaults |
| Missing context | Paste paths, versions, errors, conventions |
| Over-explaining inside the prompt | Notes to the reader go outside the block |
| Two tasks in one prompt | Split them |
| Safety rules forgotten | Any real-state change lists explicit boundaries |
| Prompt assumes a tool or file exists | Verify it does, or say what to install |

## Common Mistakes to Avoid

1. Being too vague about the task
2. Not specifying the output format
3. Missing important context (paths, language, framework)
4. Over-explaining within the prompt itself
5. Including analysis or notes in the final output
6. Making it non-self-contained (requiring context the receiver will not have)
7. Forgetting safety rules for destructive operations