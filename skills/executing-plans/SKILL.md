---
name: executing-plans
description: Use when an implementation plan exists and you are executing it inline, task by task, yourself — when no subagent-per-task process is in play or the user chose inline execution; keeps the task brief, the RED-GREEN gate, the ledger, and the final fresh review in one loop.
version: 1.0.0
author: adapted from obra/superpowers (MIT)
license: MIT
platforms: [linux, macos, windows]
---

# Executing Plans

Execute a plan yourself, task by task, in this session: no implementer subagent
per task, no reviewer per task. One fresh-context review of the whole branch at
the end.

**Why inline:** per-task subagents pay for a fresh implementer plus a fresh
reviewer on every task. Inline pays for one context (yours) plus one reviewer
at the end. What it gives up is a fresh context and a second pair of eyes per
task — this skill keeps what those two bought, by other means: the brief is the
spec, the ledger is your memory, TDD is the per-task gate, and the final review
is the second pair of eyes.

**Core principle:** the plan already did the thinking. Execute it exactly, prove
each step with a test you watched fail and then pass, and leave a record that
survives your own forgetting.

**Continuous execution:** do not pause to check in between tasks. Only four
things stop you, and only these: an irreversible or destructive operation; a
security-sensitive action; a side effect outside this workspace that norms say
you ask about first (a merge, a push to a shared branch, a publish); and a plan
so broken that every path forward is a guess. For those, stop and ask.

**Rulings, not stalls.** Conflicts, ambiguities, plan defects — decide them.
The spec is the binding authority, the plan is its argument, and your judgment
settles what neither answers. Record every decision in the ledger as
`Ruling: <what you decided> — <why> — <what it costs if wrong>`, and keep
going. Deviating from the plan without a ledgered ruling is a decision made in
secret.

## When to use

- A plan file exists (from planning work) and execution is happening in this
  session, inline.
- Tasks are mostly independent — the same precondition as delegating one agent
  per task. When a review gate on every task is wanted instead, or the plan is
  long enough that its later tasks would run on a compacted context,
  per-task subagents are the stronger shape. Inline still works over a long
  plan — the ledger is what makes it recoverable — but the last tasks get the
  least of you.

## The pipeline

```
setup (worktree, ledger, read plan, pre-flight scan)
  → per task: brief + BASE → steps in RED-GREEN order → contract → ledger line
  → after all tasks: review package + fresh reviewer
  → re-grade findings → ONE fix pass, each fix red→green + green suite
  → report rulings + deferred minors → finish the branch
```

## Setup

Isolate the work: the `using-git-worktrees` skill covers creating or verifying a
worktree. Never start implementation on the main branch without the human's
explicit consent.

Conversation memory does not survive compaction. An inline executor that loses
its place re-implements tasks whose commits already exist. Track progress in a
ledger file, not only in any todo list — todos are a live view; the ledger is
the record.

### The workspace

Each plan owns one git-ignored scratch directory, home to its briefs, test
logs, review packages, and ledger:

```bash
mkdir -p .plans/<plan-basename>.exec
printf '*\n' > .plans/<plan-basename>.exec/.gitignore   # self-ignoring: nothing inside is ever staged
```

One directory per plan file, so a follow-up plan in the same tree can never
read or overwrite another plan's artifacts — a stale ledger misread as current
progress makes an executor skip whole task sequences. A sibling directory
belongs to another plan; never read or write it.

`git clean -fdx` destroys these workspaces (they are git-ignored scratch); if
that happens, recover from `git log` — for every completed task there are its
commits and a ledger line.

### The ledger

Check for this plan's ledger at `<workspace>/progress.md` before starting.

- Its first line names the plan file. Tasks with a `Task <N>: complete` line
  are DONE — do not redo them; resume at the first task without one. Their
  commits exist in git even when your context no longer remembers making them:
  after compaction, trust the ledger and `git log` over your own recollection.
- A first line naming a different plan file is another plan's ledger: leave it
  and start your own, fresh.
- A new ledger's first line is its identity: `# Plan ledger — plan: <plan file>`.

Read the plan once, note its context and global constraints, and create a todo
per task. If the plan names a spec, read that too: the spec is the authority
the plan argues from, and conflicts inside the plan resolve against it. A plan
with no reachable spec gets a ledger note saying so — rulings made without one
are provisional.

Before Task 1, load the `test-driven-development` skill: it governs every step
of every task below, even for a plan whose steps already say "write the failing
test first".

Then scan the plan for conflicts between tasks. The plan's interface blocks
(what each task produces, what each consumer expects) tell you where to look:
for every task that consumes what an earlier task produces, one ledger row —
the two tasks, what one produces against what the other consumes, and what you
found. Tasks that share nothing get no row; a plan whose tasks share nothing
gets the single line `Pre-flight: no shared interfaces`. Rule on each conflict
a row surfaces with the spec as the binding authority, and record the ruling
beside its row.

## The task loop

Everything you print, and every tool result, stays resident in your context for
the rest of the session. Redirect long test output to a file in the workspace
and read its tail; read a brief, not the whole plan. Bookkeeping rides along
with work — a ledger append in the same call as the commit, never in a call of
its own.

### 1. Take the task

Extract the current task's full text into a brief you read in one call, and
record BASE — the commit the task's review range is cut from:

```bash
# PLAN=docs/plans/feature-plan.md   N=1   WORKSPACE=.plans/feature-plan.exec
awk -v n="$N" '
  /^```/ { infence = !infence }
  !infence && /^#+[ \t]+Task[ \t]+[0-9]+/ { in_task = ($0 ~ ("^#+[ \t]+Task[ \t]+" n "([^0-9]|$)")) }
  in_task { print }
' "$PLAN" > "$WORKSPACE/task-$N-brief.md"

BASE=$(git rev-parse HEAD)
```

If the brief comes out tiny, the task heading did not match — `## Task 2:
Recovery modes` is the expected shape. Check the extraction before assuming
the task is one line long.

Read the brief for every task, including ones you remember from setup: what
you remember is a summary, the brief has the exact values, signatures, and
test cases.

### 2. Work the steps

The plan's steps are already in RED-GREEN order; follow them in that order
under the `test-driven-development` skill. A test step's code is written first
and run first. Watching it fail is a step, not a formality — a test that passes
before the implementation exists is a finding about the test.

Every step that runs a command has an `Expected:` line. Run the command, read
its output, and compare. Three outcomes:

- **Matches.** Next step.
- **The code is wrong.** Use the `systematic-debugging` skill. Find the cause;
  never patch the symptom to make the step's output match.
- **The plan is wrong** — a step contradicts the spec, an interface from an
  earlier task doesn't match what this task consumes, a command that cannot
  work. Rule on the smallest change that satisfies the spec, ledger it as
  `Task <N>: Ruling: <finding> — <what you decided and why>`, and continue.
  The ruling is carried, not remembered: later tasks that touch the same
  interface read it from the ledger.

Commit as the plan's commit steps say. A task that spans several commits is
fine; BASE is what the review range is cut from, never `HEAD~1`.

### 3. The completion contract

Before a task's ledger line, all of the following are true, with evidence in
this session — not inferred from the diff looking right:

- Every test the brief names exists and ran in this task, and you read the
  output.
- The final test run for the task passed — that run is the next section's
  command, and its result goes into the ledger line.
- Every `Expected:` line in the brief was compared against real output.
- Every deviation from the brief has a `Ruling:` line in the ledger.

The `verification-before-completion` skill governs the claim. If any item is
missing, the task is not complete: finish it.

### 4. Complete the task

Run the test command the brief names for the whole task — the full suite, not
only your own test file. Keep the full output in the workspace, read the tail,
and — only if it passed — append the completion line to the ledger, recording
the commit range and the test command with its last output line:

```bash
# WORKSPACE=.plans/<plan-basename>.exec   TASK=<N>   CMD="npm test"   BASE=<from step 1>
LOG="$WORKSPACE/task-$TASK-tests.log"
LEDGER="$WORKSPACE/progress.md"
if eval "$CMD" > "$LOG" 2>&1; then
  tail -5 "$LOG"
  printf 'Task %s: complete (commits %s..%s, tests: %s → %s)\n' "$TASK" \
    "$(git rev-parse --short=7 "$BASE")" "$(git rev-parse --short=7 HEAD)" "$CMD" \
    "$(grep -v '^[[:space:]]*$' "$LOG" | tail -1)" >> "$LEDGER"
else
  tail -5 "$LOG"
  echo "tests failed: Task $TASK NOT recorded (full output: $LOG)"
fi
```

`eval` runs the exact command string the brief named. A failing run records
nothing: the task is not complete — fix it under the `systematic-debugging`
skill and run again. When the line records, mark the todo complete and take
the next task.

## Final review

After the last task's ledger line, review the whole branch with a fresh
context — this is the one fresh pair of eyes the inline run buys. Do not skip
it, and do not replace it with your own read of the diff.

The `requesting-code-review` skill has the full procedure: the review-package
recipe (`git log --oneline`, `git diff --stat`, `git diff -U10` from
`MERGE_BASE=$(git merge-base main HEAD)` to `HEAD`, written to the workspace as
`review-<base>..<head>.diff` — named per range, so a re-review after fixes
gets a distinct fresh file), the range guards, and the reviewer template.
Dispatch the reviewer on the most capable available model, with the package
path, the plan and spec paths, the plan's review-focus section verbatim if it
has one (the input classes and failure modes the plan's tests do not
exercise — the reviewer checks each deliberately), and a pointer to the
ledger's `Ruling:` lines so it can weigh the calls you made.

Without subagent capability: perform that review yourself from the template,
as a separate pass after the last task's ledger line. Write
`Final review: self-review (no subagent tool)` to the ledger, and say so in
your final message — a self-review by the author is weaker, and the person
accepting the work decides whether that is enough.

### Sort the findings before acting on any of them

The reviewer's severity labels are advice; the gate is yours. Its "Declined to
judge" list is yours too: every line there is a ruling you make and ledger,
exactly like a plan conflict — `Final: Ruling: <behavior set aside> — <what a
reasonable person using this software gets, and why that stands, or why it is
now a finding> — <cost if wrong>`.

Re-grade first, by effect: a finding's grade is what a reasonable person using
this software gets if it ships, not whether the spec names the input that
triggers it — a reviewer who set a finding at Minor because the spec was
silent has graded the spec, not the effect. Then:

- **Critical and Important** enter the fix pass.
- **Minor** goes to the ledger as `Final: minor (deferred): <one-liner>` and
  to your final message under "Deferred minors". Minors never enter the fix
  pass, and never become rulings — a ruling is a decision about a conflict,
  not a note that you declined a polish suggestion.

Fix the Critical and Important findings yourself — you are the implementer
here — in ONE pass. Each fix is verified by TDD, not by a second reviewer:
write the test that reproduces the finding, watch it fail, make it pass, then
run the whole suite. Record each in the ledger as
`Final: fixed <finding> — <test name> RED→GREEN, suite <N>/<N>`. A fix without
a test that failed first is not verified; a suite that is not green after the
pass means the pass is not over. Do not dispatch a re-review: it would re-read
a diff whose covering tests already answer "addressed" and whose suite run
already answers "broke nothing".

A finding you decide not to fix is a ruling — `Final: Ruling: <finding> — <why
the code stands> — <cost if wrong>` — and reaches the human in the rulings
list. There is no second fix pass.

## Finish

Before you delete anything, collect every ledger line containing `Ruling:`
into your final message under "Rulings I made", in the order you made them,
each with what it costs if wrong, and every `minor (deferred)` line under
"Deferred minors". Both lists are exhaustive. Your final message is the only
place the decisions you took on the human's behalf — and the findings you
chose not to act on — reach them.

When the final review is clean and its fixes are committed, delete this plan's
workspace directory — the git history is the record now. Sibling directories
belong to other plans; leave them alone.

Use the `finishing-a-development-branch` skill for the merge or publication
decision.

## Common rationalizations

| Excuse | Reality |
|--------|---------|
| "I remember what Task N says" | You remember a summary. The brief has the exact values. Read it. |
| "The plan's code is right, skip watching the test fail" | A test you never saw fail proves nothing. It is one step. Run it. |
| "I'll run the full suite at the end instead of per task" | Per-task runs are how you learn which task broke it. The end-of-task run is the contract, not a substitute. |
| "The plan is wrong here, I'll just do the right thing" | Do the right thing and ledger the ruling. Unledgered deviation is a decision made in secret. |
| "I'll write the ledger lines after a few tasks" | Compaction does not wait for a convenient moment. One line per task, in the same message as the commit. |
| "Let me check in before the next task" | Inline execution was chosen to spend less. Only the four stops stop you. |
| "I read my own diff carefully; the final reviewer is redundant" | Same author, same blind spots. The reviewer is the only fresh context this run buys. |
| "Tests should pass, the change was trivial" | "Should" is not evidence. The contract requires the command and its output. |
| "Subagents are slow, I'll skip the final review too" | Inline already removed the per-task reviewers. One review of the whole branch is the floor, not the ceiling. |
| "The reviewer said Minor, so it's Minor" | The label graded the spec's silence. Grade what the person gets. Re-grade, then gate. |
| "The fix is obvious, no need for a failing test first" | The failing test is the only proof the finding was real and is now gone. |
| "I'll fix the minors too while I'm in there" | Every minor you fix is a test, a fix, and a suite run nobody asked for. Ledger them; the human decides. |

## Example

```text
Setup: worktree verified; ledger fresh; TDD loaded.
Pre-flight scan: 2 shared-interface rows, ruled and ledgered; clean.

Task 1: Hook installation script
- brief extracted (## Task 1 heading, 34 lines); BASE a1b2c3d
- Step 1: write failing test — written
- Step 2: run → FAIL: install_hook not defined. Matches Expected.
- Step 3: implement
- Step 4: run → PASS 1/1. Matches Expected.
- Step 5: commit d4e5f6a
- Contract: brief's tests ran, outputs read, all Expected compared, no deviations
- Whole-task run: npm test -- hooks → PASS; ledger: Task 1: complete
  (commits a1b2c3d..d4e5f6a, tests: npm test -- hooks → 1 passed)

Task 2: Recovery modes
- brief read
- Step 2 fails on an import error: Task 1 exported installHook, the brief
  consumes install_hook
- Ruling: the brief's consumer name is a typo against Task 1's Produces block;
  use installHook. Ledgered with cost (one rename).
- Steps continue; commit b7c8d9e; ledger: Task 2: complete

After all tasks: review package a1b2c3d..b7c8d9e; reviewer dispatched on the
most capable model, with the Ruling lines and the plan's review focus.
- One Important finding → fix pass: test_red_green, suite 12/12, ledgered.
- Two Minor → ledgered deferred, not fixed.

Final message: Rulings I made / Deferred minors — both exhaustive.
Workspace deleted.
```

## Related

- The `plan` skill writes the plan this one executes.
- The `test-driven-development` skill governs every step of every task.
- The `requesting-code-review` skill produces and reviews the final package.
- The `verification-before-completion` skill governs the completion contract.
- The `systematic-debugging` skill is the path when code is wrong.
- The `using-git-worktrees` and `finishing-a-development-branch` skills cover
  the two ends: the isolated workspace to build in, and the merge decision
  once the review is clean.