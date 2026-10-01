---
name: plan
description: Use when the user wants a plan written down instead of code changed — design work, multi-step features, or a task worth planning before touching it.
version: 2.4.0
author: adapted from obra/superpowers
license: MIT
platforms: [linux, macos, windows]
---

# Plan Mode

Use this skill when the user wants a plan instead of execution.

## Core behavior

For this turn, you are planning only.

- Do not implement code.
- Do not edit project files except the plan markdown file.
- Do not run mutating terminal commands, commit, push, or perform external actions.
- You may inspect the repo or other context with read-only commands/tools when needed.
- Your deliverable is a markdown plan saved inside the active workspace under `.plans/`.

## Output requirements

Write a markdown plan that is concrete and actionable.

Include, when relevant:
- Goal
- Current context / assumptions
- Proposed approach
- Step-by-step plan
- Files likely to change
- Tests / validation
- Risks, tradeoffs, and open questions

If the task is code-related, include exact file paths, likely test targets, and verification steps.

## Save location

Save the plan under:
- `.plans/YYYY-MM-DD_HHMMSS-<slug>.md`

Treat that as relative to the active working directory / project root. Keeping the plan relative to
the workspace means it travels with the checkout, whichever machine or container you are working in.

If the runtime provides a specific target path, use that exact path.
If not, create a sensible timestamped filename yourself under `.plans/`.

## Interaction style

- If the request is clear enough, write the plan directly.
- If no explicit instruction accompanies `/plan`, infer the task from the current conversation context.
- If it is genuinely underspecified, ask a brief clarifying question instead of guessing.
- After saving the plan, reply briefly with what you planned and the saved path.

---

# Writing the Plan Well

The rest of this skill is the craft of authoring a *good* implementation plan — the content that goes inside the markdown file above.

## Overview

Write comprehensive implementation plans assuming the implementer has zero context for the codebase and questionable taste. Document everything they need: which files to touch, the interfaces and signatures, testing commands, docs to check, how to verify. Give them bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume the implementer is a skilled developer but knows almost nothing about the toolset or problem domain. Assume they don't know good test design very well.

**Core principle:** A good plan makes implementation obvious. If someone has to guess, the plan is incomplete.

A plan is the set of decisions the implementer cannot make alone. Anything they can determine from
the signature and the test is not the plan's business.

## When a Full Implementation Plan Helps

**Always use before:**
- Implementing multi-step features
- Breaking down complex requirements
- Delegating execution to subagents, one task each

**Don't skip when:**
- Feature seems simple (assumptions cause bugs)
- You plan to implement it yourself (future you needs guidance)
- Working alone (documentation matters)

**Scope check:** if the request covers several independent subsystems, write one plan per subsystem
rather than one long plan. Each plan should produce working, testable software on its own.

## Task and Step Granularity

**Task boundaries.** A task is the smallest unit that carries its own test cycle and is worth a
fresh reviewer's gate. Fold setup, configuration, scaffolding and documentation into the task whose
deliverable needs them; split only where a reviewer could meaningfully reject one task while
approving its neighbour. Every task ends with an independently testable deliverable — a task you
cannot test on its own is either part of the previous task or too big.

**Steps.** Each step is one action with a checkable result:

- "Write the failing test" — step
- "Run it to make sure it fails" — step
- "Implement the minimal code to make the test pass" — step
- "Run the tests and make sure they pass" — step
- "Commit" — step

**Too big:**
```markdown
### Task 1: Build authentication system
[50 lines of code across 5 files]
```

**Right size:**
```markdown
### Task 1: Create User model with email field
[1 file, 1 test]

### Task 2: Add password hash field to User
[1 file, 1 test]

### Task 3: Create password hashing utility
[1 file, 1 test]
```

## Plan Document Structure

### Header (Required)

Every plan MUST start with:

```markdown
# [Feature Name] Implementation Plan

> **Execution:** implement this plan task by task with one fresh subagent per task (see Execution Handoff).

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

**Global Constraints:** [The project-wide requirements — version floors, dependency limits, naming
and copy rules, platform targets — one line each, with the exact values copied verbatim from the
request or spec. Every task's requirements implicitly include this section.]

**Review Focus:** [The five input classes or failure modes that no task's tests exercise and that
are most likely to bite a user of this software — one line each, naming the input or condition and
the behaviour a reasonable person would expect. Silence in the spec about an input is not permission
for the program to break on it. Then, for each line, add the test that pins it, in the task that
owns that code. An empty section means you checked and found none.]

---
```

### Task Structure

Each task follows this format:

````markdown
### Task N: [Descriptive Name]

**Objective:** What this task accomplishes (one sentence)

**Files:**
- Create: `exact/path/to/new_file.py`
- Modify: `exact/path/to/existing.py:45-67` (line numbers if known)
- Test: `tests/path/to/test_file.py`

**Interfaces:**
- Consumes: [what this task uses from earlier tasks — exact signatures]
- Produces: [what later tasks rely on — exact function names, parameter and return types. An
  implementer sees only their own task; this block is how they learn the names and types their
  neighbours use.]

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/path/test.py::test_specific_behavior -v`
Expected: FAIL — "function not defined"

- [ ] **Step 3: Implement `function(input: InputType) -> ResultType` in `exact/path/to/new_file.py`**

One line on the approach when the signature and the test leave a real choice (which library call,
which data structure). A code block only for an algorithm the signature and tests do not determine,
or for exact text the spec fixes.

- [ ] **Step 4: Run test to verify pass**

Run: `pytest tests/path/test.py::test_specific_behavior -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

### What a step contains

A step is done when the implementer can write exactly one reasonable thing from it. That is the whole
requirement — unambiguous, not complete. Each kind of step carries only what makes it unambiguous:

- **A test step:** the test's name and its assertions, as code, with the exact values.
- **A code step:** the exact signature (name, parameters, return type), the file it lives in, and the
  specific values that are pinned. The implementer writes the body. A body appears only for an
  algorithm the signature and tests do not determine, or for exact copy that must match verbatim.
- **A verification step:** the command to run and the output that means it passed.
- **A reference to another task:** that task's Interfaces block says what to use; do not repeat that
  task's code here.

Lines that decide nothing — "handle edge cases", "add appropriate validation", "write tests for the
above", a function no task defines — are the opposite failure. The self-review catches both.

## Writing Process

### Step 1: Understand Requirements

Read and understand:
- Feature requirements
- Design documents or user description
- Acceptance criteria
- Constraints

### Step 2: Explore the Codebase

Understand the project before planning. Map the files you will create or modify and what each is
responsible for — this is where decomposition gets locked in, and it is what makes task boundaries
obvious. Prefer small, focused files; follow the codebase's existing patterns rather than
restructuring it as a side effect of your feature.

```bash
# Understand project structure
ls -R src/

# Look at similar features
grep -rn "similar_pattern" src/

# Check existing tests
ls tests/

# Read key files
cat src/app.py
```

### Step 3: Design Approach

Decide:
- Architecture pattern
- File organization
- Dependencies needed
- Testing strategy

### Step 4: Write Tasks

Create tasks in order, each ending in its own test cycle:
1. Setup/infrastructure (folded into the first task that needs it)
2. Core functionality (TDD for each)
3. Edge cases
4. Integration
5. Cleanup/documentation

### Step 5: Add Complete Details

For each task, include:
- **Exact file paths** (not "the config file" but `src/config/settings.py`)
- **Exact signatures and interfaces** — and the values that are pinned
- **Exact commands** with expected output
- **Verification steps** that prove the task works

### Step 6: Self-Review

After writing the plan, re-read the original request and check the plan against it. This is a
checklist you run yourself, not a dispatch to another agent.

- [ ] **Spec coverage:** can you point to a task implementing each requirement? List the gaps.
- [ ] **Step scan:** every step lets the implementer write exactly one reasonable thing — no step
      that decides nothing, and no step that transcribes code the signature and tests already fix.
- [ ] **Interface consistency:** do the names, signatures and types in later tasks match what earlier
      tasks defined? A function called `clearLayers()` in Task 3 and `clearFullLayers()` in Task 7 is
      a bug the implementer will hit.
- [ ] **Review Focus:** does each uncovered input class have a test in the task owning that code?
- [ ] **Proportion:** compare the plan's length to the request's. A plan several times longer than
      the thing it implements is a transcript of the program, not a plan. If code blocks are most of
      the document, replace bodies with signatures, test names and assertions.
- [ ] **Sequencing:** tasks are in dependency order; each is bite-sized and independently testable.
- [ ] **DRY, YAGNI, TDD principles applied.**

Fix issues inline as you find them; no need for a second review pass.

## Principles

### DRY (Don't Repeat Yourself)

**Bad:** Copy-paste validation in 3 places
**Good:** Extract validation function, use everywhere

### YAGNI (You Aren't Gonna Need It)

**Bad:** Add "flexibility" for future requirements
**Good:** Implement only what's needed now

```python
# Bad — YAGNI violation
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
        self.preferences = {}  # Not needed yet!
        self.metadata = {}     # Not needed yet!

# Good — YAGNI
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
```

### TDD (Test-Driven Development)

Every task that produces code includes the full TDD cycle:
1. Write failing test
2. Run to verify failure
3. Write minimal code
4. Run to verify pass

Run the test, watch it fail, write the minimal code, run it again. Never write the implementation before the failing test exists.

The `test-driven-development` skill carries the detail when you reach execution: what counts as failing
*for the right reason*, the assertion shapes that can never fail (expectations computed by the code
under test, assertions on mocks), and why "the other tests still pass" means the project's whole suite
rather than the one file being changed.

### Frequent Commits

Commit after every task:
```bash
git add [files]
git commit -m "type: description"
```

## Common Mistakes

### Vague Tasks

**Bad:** "Add authentication"
**Good:** "Create User model with email and password_hash fields"

### Deciding Nothing

**Bad:** "Step 1: Add validation function"
**Good:** the exact signature, the file, and the values it must enforce

### Writing the Code Instead

**Bad:** 40 lines of implementation in a step whose signature and test already determine the body
**Good:** the signature, the test, and one line on the approach where a real choice remains

### Missing Verification

**Bad:** "Step 3: Test it works"
**Good:** "Step 3: Run `pytest tests/test_auth.py -v`, expected: 3 passed"

### Missing File Paths

**Bad:** "Create the model file"
**Good:** "Create: `src/models/user.py`"

## Execution Handoff

After saving the plan, offer to execute it:

**"Plan complete and saved. Ready to execute — I'll take one task at a time in a fresh subagent, with two reviews per task (spec compliance, then code quality). Shall I proceed?"**

If the user says yes, implement it task by task:
- One fresh subagent per task, given the full context for that task
- Spec compliance review after each task — did it do what the task said?
- Code quality review only after spec compliance passes
- Proceed to the next task only when both reviews approve

If the runtime has no subagent capability, execute the tasks yourself in order and still run both review passes before moving on.

Before the first task, and again when the last one is done, the `using-git-worktrees` and
`finishing-a-development-branch` skills cover the two ends of execution: an isolated workspace to
build the tasks in, and the merge/publish decision once the suite is green.

## Remember

```
Bite-sized tasks, each with its own test cycle
Exact file paths and interfaces
Pinned values, not bodies
Exact commands with expected output
Verification steps
DRY, YAGNI, TDD
Frequent commits
A plan the implementer cannot misread
```

**A good plan makes implementation obvious.**
