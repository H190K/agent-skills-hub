---
name: verification-before-completion
description: Use when about to report work as done, fixed, passing or successful — before committing, opening a PR, or telling the user it works.
version: 1.1.0
author: adapted from obra/superpowers
license: MIT
platforms: [linux, macos, windows]
---

# Verification Before Completion

**Evidence before claims.** Every statement about the state of the work — "done", "fixed", "tests
pass", "deployed" — is a factual claim, and a factual claim needs output you have actually looked at
in this session.

The failure this prevents is specific and common: an agent runs a command, the command output is
ambiguous or truncated or the tool failed quietly, and the summary says "all tests pass". The user
finds out otherwise. Nothing else in a session erodes trust faster, because it means no other
summary can be relied on either.

## The gate

Run this before every completion claim:

1. **Identify** — what command, check or read-back would prove this specific claim?
2. **Run** it, fresh. Not a previous run, not a similar one.
3. **Read** the full output: exit code, failure count, the lines that matter. Truncated output is
   not read output.
4. **Check** — does the evidence actually support the claim, or only a weaker version of it?
5. **Then** state the claim, quoting the evidence.

Skipping a step is not a shorter report — it is an unverified one.

## What each claim needs

| Claim | Needs | Not enough |
|---|---|---|
| Tests pass | Test run output, 0 failures | An earlier run, "should pass now" |
| Build succeeds | Build command exited 0 | The linter passed |
| Bug is fixed | The original symptom reproduced and now passing | The code looks right now |
| Regression test works | Red → green actually observed | The test passes once |
| Command/feature works | It ran and you saw the output | It parsed, imported, or compiled |
| File was written | Read it back | The write call returned success |
| Change is published | The remote/API confirms the new state | The push command exited 0 |
| Requirements are met | A line-by-line pass against the request | The obvious subset works |
| A subagent finished | Inspect the actual artifact/diff | The subagent's own "success" report |

## Red flags

- "Should", "probably", "seems to", "looks good".
- Satisfaction before verification — "Perfect!", "Done!", "Great, that works."
- Committing, pushing or declaring completion without having run the check in this session.
- Trusting a tool's or a subagent's success message as the fact. Re-read the target.
- Partial verification treated as full: one of three commands run, one of five files checked.
- A count in the output ("12 of 14 passed") summarised as "tests pass".
- "Just this once", or being tired and wanting the work over.

## Gotchas

- **Exit code lies about content.** `grep` returning 1 because nothing matched, a pipeline whose exit
  status is the last command's, `cmd || true`, an HTTP 200 carrying an error body. Check the output,
  not just the status.
- **A cached or stale run is not evidence.** Re-run after the change, and confirm the output is from
  this run — timestamps, counts, or changed values.
- **Verify the state you changed, not the call you made.** After writing a file, reading it back is
  the check. After an external write, read the remote.
- **A green suite can be green for the wrong reason.** A skipped test, a test that no longer exercises
  changed code, a mock that returns success for anything. When a suite turns green suspiciously fast,
  check that the tests ran.
- **Declared totals are assertions.** "Found 6 items" while listing 5 means the count is wrong or the
  list is truncated — resolve which, rather than reporting either.
- **Don't restate an old verification as current.** Evidence has a time; a run from before the last
  edit proves nothing about the current tree.

## Reporting

State the claim, then the evidence, in one line: *"Tests pass — `pytest -q`: 34 passed, 0 failed."*
If verification is not possible, say that instead of implying success: *"I could not run the suite;
the command needs a database I don't have."* An honest gap is a normal report. A confident claim
that turns out to be false is a broken one.

## Related

- The `systematic-debugging` skill covers the investigation that has to happen before a fix exists.
- The `test-driven-development` skill is how the reproduction becomes permanent: write the failing
  test first, watch it fail against the broken version, then fix — the suite then proves the bug
  cannot return silently.
- The `plan` skill's self-review checklist is a plan-shaped version of this gate.

