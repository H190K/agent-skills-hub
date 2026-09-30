---
name: systematic-debugging
description: Use when a bug, test failure, crash or unexpected behaviour needs fixing — especially when a fix "should have worked" but didn't, or when the temptation is to try another change and see.
version: 1.0.0
author: adapted from obra/superpowers
license: MIT
platforms: [linux, macos, windows]
---

# Systematic Debugging

Find the root cause before touching the code. A fix applied to a symptom hides the cause, and the
next symptom usually costs more than the investigation would have.

The rule this skill exists to enforce: **no fix before the root cause is understood.** If you have
not completed the investigation phase, you are not yet allowed to propose a change.

## When to use

- A test fails, a build breaks, a program crashes, or behaviour diverges from what the code says.
- A first fix didn't work and a second is about to be attempted.
- The cause is "obviously" X and the fix is one line.
- Performance or intermittent failures where you have no reproduction yet.

Use it **especially** under time pressure and when the fix looks trivial — those are the two
conditions under which skipping straight to a change is most tempting and most expensive.

## The four phases

Each phase ends with a stated condition. Do not start the next one until it holds.

### Phase 1 — Root cause investigation

- **Read the error completely.** The stack trace, the exit code, the line numbers, the warnings you
  were about to scroll past. Most errors contain the answer.
- **Reproduce it reliably.** Write down the exact steps. If it does not reproduce every time, record
  the frequency and what differs between runs — an intermittent failure is a different investigation,
  not a reason to guess.
- **Check what changed.** Recent commits, a dependency bump, a config or environment difference.
  A bug that appeared today has a change that caused it.
- **Multi-component systems: instrument the boundaries first.** When the path is
  client → API → service → database, or workflow → build → sign → publish, log what enters and
  leaves each component and run once. That tells you *which* boundary breaks instead of guessing
  between layers. Then investigate only the failing component.
- **Trace the bad value backwards.** Where did the wrong value originate, what produced it, and what
  called *that*? Follow it up the chain to its source. Fixing it where it surfaced leaves the
  producer broken.

**Done when** you can state what happens, where, and why — in your own words, not the error's.

### Phase 2 — Pattern analysis

- Find a working example of the same thing in the same codebase. What differs between the working
  and broken paths?
- If you are implementing a pattern, read the reference implementation completely. Skimming a
  reference and then adapting it is how partial understanding gets shipped.
- List every difference, including the ones that "cannot possibly matter". Those are usually it.

**Done when** you have a concrete, checkable difference between working and broken.

### Phase 3 — Hypothesis

- State one hypothesis explicitly: "X is the root cause because Y." Write it down.
- Test it with the **smallest possible change** — one variable at a time.
- Worked? Go to Phase 4. Didn't? Form a *new* hypothesis. Do not stack a second fix on the first;
  you will not be able to tell which one mattered.
- If you do not understand something, say so and go find out. An admitted gap is recoverable; a
  pretended certainty is not.

**Done when** one hypothesis is confirmed by evidence, not by plausibility.

### Phase 4 — Implement the fix

- **Write the reproduction first** — a failing test, or a one-off script if there is no test
  framework. Something that fails now and will pass afterwards. Without it you cannot prove the fix
  worked, and you cannot prove it stays fixed.
- Make one change, at the root cause. No "while I'm here" cleanups, no bundled refactors — they
  make the fix unverifiable and unreviewable.
- Run the reproduction and the surrounding test suite. Confirm the original symptom is gone and
  nothing else broke.
- Report what you actually observed, not what you expect.

## When three fixes have failed

Two failed attempts are information. Three means the **architecture** is wrong, not the hypothesis —
each fix has been revealing a new problem somewhere else, or each fix needs a restructuring to land.

Stop. Say so plainly. The question is no longer "what is the next fix" but "is this design sound".
Raise it with the user before attempting a fourth change.

## Gotchas

- **A symptom that moves is not progress.** If fixing the timeout makes a different test flake, the
  cause was never the timeout.
- **"It's environmental" is a conclusion, not a starting assumption.** It is the right answer far
  less often than it is claimed. Reach it only after Phase 1, and then document what you checked:
  retry, timeout and improved error messages are appropriate handling, not a root cause.
- **Do not adjust the test to match the implementation** unless the test encoded the wrong
  behaviour — and then say so explicitly, because it is a specification change wearing a test fix's
  clothes.
- **Silent failure modes**: swallowed exceptions, `|| true`, an empty catch block, a retry that
  hides the first error, a mock that returns success for any call. When something "works" for no
  reason, check that it is actually running.
- **Time-dependent and ordering bugs** are usually exposed by running the suite in a different order
  or with a fixed clock, not by reading harder.
- **A green suite after a fix proves nothing** if the reproduction was never run against the broken
  version. Check that it fails before the fix — `git stash` the change and watch it fail.

## Red flags

If you notice any of these, return to Phase 1:

- "Quick fix now, investigate properly later."
- "Let me just try changing this and see."
- "It's probably X" followed directly by an edit.
- Changing several things, then running the tests.
- Adding a retry, a sleep, or a larger timeout as the *first* response.
- "I don't fully understand it, but this might work."
- Proposing a list of fixes before tracing the data flow once.
- "One more attempt" after two have already failed.

## Quick reference

| Phase | Do | Done when |
|---|---|---|
| 1. Root cause | Read errors, reproduce, check changes, instrument boundaries, trace the value back | You can explain what, where and why |
| 2. Pattern | Find working code, compare, list every difference | You have a concrete difference |
| 3. Hypothesis | One theory, smallest test | Evidence confirms one cause |
| 4. Fix | Failing reproduction first, one change, verify | Reproduction passes; suite green; you observed it |
