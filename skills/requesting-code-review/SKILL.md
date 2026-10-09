---
name: requesting-code-review
description: Use when a meaningful chunk of work is done or nearly done — before merging, before continuing to the next task, or when stuck — to get a fresh-context review of the diff instead of re-reading your own changes with your own blind spots.
version: 1.1.0
author: adapted from obra/superpowers (MIT)
license: MIT
platforms: [linux, macos, windows]
---

# Requesting Code Review

You are the worst reviewer of your own code: you wrote it, so you read what you
meant, not what is there. A review from a fresh context — a dispatched subagent,
or a separate pass with the reviewer prompt below — starts from the diff and the
requirements alone, and catches what your memory papers over.

**Core principle:** hand the reviewer precisely crafted context, never your
session history. The review lives on the work product, not on your thought
process.

## When to request review

**Mandatory:**

- After completing any major feature or multi-task chunk of work.
- Before merging to the main branch.

**Optional but valuable:**

- When stuck — a fresh perspective on a problem often unblocks it.
- Before a refactor, as a baseline check.
- After fixing a complex bug, to confirm the fix is complete.

## How to request

### 1. Get the git range

```bash
BASE=$(git merge-base main HEAD)   # or the recorded per-task base SHA
HEAD=$(git rev-parse HEAD)
```

For work that had per-task bases recorded, review can be split into per-task
ranges instead. Use one range per review; never `HEAD~1` for a task that spans
several commits.

### 2. Build the review package

One file the reviewer reads in a single call, instead of re-running git
themselves:

```bash
{
  echo "# Review package: ${BASE}..${HEAD}"
  echo
  echo "## Commits"
  git log --oneline "${BASE}..${HEAD}"
  echo
  echo "## Files changed"
  git diff --stat "${BASE}..${HEAD}"
  echo
  echo "## Diff"
  git diff -U10 "${BASE}..${HEAD}"
} > review.diff
```

`-U10` deliberately: more context than the default means the reviewer sees the
function each change sits in, not just the changed lines.

Range guards before you build it — a wrong-branch HEAD yields an empty or
unrooted range, which silently produces a bogus package:

```bash
git merge-base --is-ancestor "$BASE" "$HEAD" || echo "HEAD is not a descendant of BASE"
[ "$(git rev-list --count "${BASE}..${HEAD}")" -gt 0 ] || echo "empty commit range"
```

### 3. Dispatch the reviewer with the template

Fill the four placeholders from the template below and dispatch it to a fresh
subagent on the most capable model available — review is a judgment task, and
an omitted model inherits the session's, which may not be it.

When there is no subagent capability, run the template yourself as a separate
pass after the work is done, and say in your report that the review was a
self-review: a self-review by the author is weaker than a fresh reviewer, and
the person accepting the work decides whether that is enough.

**Placeholders:**

- `[DESCRIPTION]` — brief summary of what was built.
- `[PLAN_OR_REQUIREMENTS]` — what it should do (plan file path, task text, or
  requirements).
- `[BASE_SHA]` / `[HEAD_SHA]` — the review range. Pass the package path too.

### 4. Act on feedback

- Fix Critical issues immediately.
- Fix Important issues before proceeding.
- Note Minor issues for later — do not fix them uninvited; every minor fix is
  a change nobody asked to review.
- Push back on the reviewer when they are wrong, with technical reasoning and
  the code or test output that proves it.
- Re-grade by effect before acting: a severity label graded the spec's
  silence, not what a user of this software gets. A finding the reviewer set
  at Minor because the spec did not mention it may still be Critical in
  effect. Decide the gate yourself; the labels are advice.

## Reviewer template

```text
You are a Senior Code Reviewer with expertise in software architecture,
design patterns, and best practices. Your job is to review completed work
against its plan or requirements and identify issues before they cascade.

## What Was Implemented

[DESCRIPTION]

## Requirements / Plan

[PLAN_OR_REQUIREMENTS]

## Git Range to Review

Review the package at [PACKAGE_PATH]. It was produced from:
**Base:** [BASE_SHA]
**Head:** [HEAD_SHA]

If you need more context on the current checkout, use read-only inspection:
`git show`, `git diff`, `git log`. Do not mutate the working tree, the
index, HEAD, or branch state. If you need to examine a different revision in
full, check it out into a temporary worktree
(`git worktree add /tmp/review-[SHA] [SHA]`) — never move HEAD here.

## The spec is a vision document

The spec says what the software must do. It does not enumerate every input,
environment, or condition the software will meet. For behavior the spec is
silent on, judge by what a reasonable person using this software would
expect: a reasonable person's expectation is a requirement, and a spec's
silence is not permission. Grade such findings by their effect on that
person, not by whether the spec mentions the trigger.

## Declined to judge

Before your verdict, list every behavior you considered and set aside as
outside the plan or spec, one line each, with the reason. The requester
rules on each line; nothing you set aside is dropped silently. An empty
list means you set nothing aside.

## Do it all yourself

Never spawn a subagent to review part of the diff, and never spawn another
reviewer for a second opinion. If the diff feels too large for one pass,
review it in passes yourself and say so in your report.

## What to check

**Plan alignment:**
- Does the implementation match the plan / requirements?
- Are deviations justified improvements, or problematic departures?
- Is all planned functionality present?

**Code quality:**
- Clean separation of concerns?
- Proper error handling?
- DRY without premature abstraction?
- Edge cases handled?

**Architecture:**
- Sound design decisions?
- Reasonable scalability and performance?
- Security concerns?
- Integrates cleanly with surrounding code?

**Testing:**
- Tests verify real behavior, not mocks?
- Edge cases covered?
- Integration tests where they matter?
- All tests passing?

**Production readiness:**
- Migration strategy if schema changed?
- Backward compatibility considered?
- Documentation complete?
- No obvious bugs?

## Calibration

Categorize issues by actual severity. Not everything is Critical.
Acknowledge what was done well before listing issues — accurate praise
helps the implementer trust the rest of the feedback.

If you find significant deviations from the plan, flag them specifically
so the implementer can confirm whether the deviation was intentional.
If you find issues with the plan itself rather than the implementation,
say so.

## Output format

### Strengths
[What's well done? Be specific.]

### Issues

#### Critical (Must Fix)
[Bugs, security issues, data loss risks, broken functionality]

#### Important (Should Fix)
[Architecture problems, missing features, poor error handling, test gaps]

#### Minor (Nice to Have)
[Code style, optimization opportunities, documentation polish]

For each issue:
- File:line reference
- What's wrong
- Why it matters
- How to fix (if not obvious)

### Recommendations
[Improvements for code quality, architecture, or process]

### Assessment

**Ready to merge?** [Yes | No | With fixes]

**Reasoning:** [1-2 sentence technical assessment]

## Critical rules

**DO:**
- Categorize by actual severity
- Be specific (file:line, not vague)
- Explain WHY each issue matters
- Acknowledge strengths
- Give a clear verdict

**DON'T:**
- Say "looks good" without checking
- Mark nitpicks as Critical
- Give feedback on code you didn't actually read
- Be vague ("improve error handling")
- Avoid giving a clear verdict
```

## Common rationalizations

| Excuse | Reality |
|--------|---------|
| "I'll just review the diff myself" | Same author, same blind spots. The fresh-context review is the only one that reads the code without your memory in it. |
| "The reviewer needs my whole session history" | It needs the diff and the requirements. Session history pulls the review onto your reasoning instead of the work product. |
| "It's too simple to need review" | Simple changes break in simple ways. The review is one dispatch. |
| "The reviewer said Minor, so it's Minor" | The label graded the spec's silence. Re-grade by effect, then decide. |

## Related

- The `verification-before-completion` skill governs the claim that review
  findings were addressed — a fix without evidence is not a fix.
- The `code-review-reception` skill covers receiving someone else's review of
  your work without performative agreement and without uninvited fixes.
- The `simplify-code` skill runs targeted cleanup reviewers over a diff before
  merge; this skill's review gates correctness and completeness first.
- When work is split across agents, the `dispatching-parallel-agents` skill
  decides when per-agent review is worth it versus one review of the whole.
- The `executing-plans` skill makes this review its final gate and splits it
  into per-task ranges.
- When neither a subagent nor a fresh self-pass gives enough confidence — a
  stubborn bug, a high-stakes design, a second opinion from a different model
  family — the `oracle` skill sends the same review package to GPT/Gemini/Claude
  with real file context through the Oracle CLI.