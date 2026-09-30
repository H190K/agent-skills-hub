---
name: test-driven-development
description: Use when writing or changing tests, reproducing a bug as a test, or making any behaviour change that needs proof it works — the RED-GREEN-REFACTOR cycle and the rules that stop a test passing for the wrong reason.
version: 1.0.0
author: adapted from obra/superpowers
license: MIT
platforms: [linux, macos, windows]
---

# Test-Driven Development

## Overview

Write the test first, watch it fail for the right reason, then make it pass. The order is the point:
a test you never saw fail has not been shown to be capable of failing.

**Core rule:** no production code without a failing test that demands it.

## The Cycle

```
RED    → write one failing test
GREEN  → simplest code that passes it
REFACTOR → clean up, tests stay green
REPEAT → next behaviour
```

One behaviour per cycle. If the test name contains "and", it is two tests.

## RED — Write the Test, Then Watch It Fail

**Do not skip the run.** Running it is the step that separates a test from a wish.

1. Write the smallest test for the next behaviour.
2. Run it.
3. Confirm three things:
   - it **fails** (not errors out on a syntax or import problem),
   - the failure message is the one you expected,
   - it fails because the behaviour is missing — not because of a typo.

Then, and only then, move on.

| What you see | What it means | Do |
|---|---|---|
| Test passes immediately | You are testing behaviour that already exists | Rewrite the test to target the new behaviour |
| Test errors (import/syntax) | The test is broken, not the code | Fix the test, re-run until it fails correctly |
| Test fails on an unexpected assertion | Your expectation is wrong, or you misunderstood the API | Settle which is right before writing production code |

## GREEN — The Least Code That Passes

Write the simplest thing that turns the test green. Resist the pull to add the next feature, refactor
a neighbour, or generalise while you are here — that is the code you have no test for yet.

**Run the test again and watch it pass.** Confirm:

- the test passes,
- the other tests still pass,
- the output is clean (no new warnings or swallowed errors).

Failed? Fix the code, not the assertion. Other tests red? Fix them now, before adding anything else.

### Gotcha — "other tests" means the project's suite

A green run of the file you just wrote is **not** a green suite. Before calling the change done, run
the project's own test command (`pytest`, `npm test`, `cargo test`, `go test ./...` — whatever the
repo uses), even when your task named only one test file.

A scope statement in the task bounds the **deliverable**, not your **verification**. Any failure that
full run shows — including one you did not cause — goes in your report by name. A red test you
watched scroll past and said nothing about is a report falsified by omission.

## REFACTOR — Only After Green

With every test passing, you may now remove duplication, rename for clarity, and extract helpers.
Keep the tests green and **add no behaviour**: a change that needs a new assertion is a new RED.

## Tests That Can Actually Fail

Most worthless tests fail one of these checks. Run them against anything you write.

### Name the break before you name the test

Before writing the body, answer: *what production change should make this test fail — and is that
change a bug or a decision?*

- **Cannot name one** → the test asserts nothing useful. Redesign around an observable behaviour.
- **"The source text changed"** → run the artifact against a controlled input and assert its output,
  side effects, or exit code instead of asserting that a line exists.
- **Only intentional decisions can fail it** (a constant's value, exact wording, private structure)
  → that is a change detector: it fires on every redesign and sleeps through every bug. Test the
  behaviour that depends on the decision — not `MAX_RETRIES == 5`, but "a failing call is retried 5
  times and the 6th attempt never happens".

### Derive the expectation without the code under test

Use literals and hand-checked fixtures. An expectation computed by the code under test — or by its
own helpers — passes no matter what that code does:

```python
# WRONG — the same builder computes both sides; always true
expected = build_query(tag="urgent")
assert build_query(tag="urgent") == expected

# RIGHT — hand-derived literal
assert build_query(tag="urgent") == 'tag:"urgent"'
```

If the expected value reuses the implementation's logic, replace it with a literal.

### A mock assertion is not a test

An assertion on a mock passes when the mock is present and fails when it is absent — it proves
nothing about the component. Assert the real component's behaviour. If the mock is the thing you are
checking, unmock it or delete the assertion.

When you do need a mock, mock the **slow or external** operation and keep what is under test real —
and learn what the real method does before replacing it, or you will silently drop the side effect
the test exists to protect.

### Test your boundary, not your framework's

Test the contract your code makes: the route you register, the query you emit, the payload you
produce. Asserting that your router calls a handler you handed it is the framework's test, not
yours. If upstream behaviour genuinely surprised you, write one narrow test that records the
assumption and move on.

## Test Quality

| Quality | Good | Bad |
|---|---|---|
| **Minimal** | One thing. "and" in the name? Split it. | `test('parses and validates and renders')` |
| **Clear** | The name describes the behaviour | `test('retry works')`, `test('test1')` |
| **Real** | Exercises the code path under test | `expect(mock).toHaveBeenCalledTimes(3)` |
| **Intent** | Shows how the API is meant to be used | Obscures what the code should do |

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "Too simple to test" | Simple code breaks. The test takes a minute. |
| "I'll test after" | Tests written after pass immediately, which proves nothing — they are biased toward the cases you happened to remember, and you never saw them catch anything. |
| "Manually tested already" | Ad-hoc testing leaves no record of the cases you covered and cannot be re-run when the code changes. |
| "Throwing away hours of work is wasteful" | That time is already spent either way. The real choice is a rewrite with tests you trust against code you bolted tests onto afterwards. |
| "The mock lets me test it fast" | A fast test of a mock asserts the mock. Mock the boundary, keep the logic under test real. |

## Common Mistakes

1. Writing production code with no failing test demanding it.
2. Skipping the RED run, so nothing proves the test can fail.
3. Passing the test by weakening the assertion instead of fixing the code.
4. Adding scope during GREEN — extra parameters, options, or "proper" abstractions that no test asked for.
5. Asserting on mocks rather than on real behaviour.
6. Reporting done after running only your own test file.
7. Fixing a red test by deleting or skipping it.
