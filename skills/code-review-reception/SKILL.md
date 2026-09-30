---
name: code-review-reception
description: Use when someone reviews your code, a reviewer or linter raises findings, or review feedback seems wrong, vague or over-scoped — how to evaluate each item on technical merit instead of agreeing or complying on reflex.
version: 1.0.0
author: adapted from obra/superpowers
license: MIT
platforms: [linux, macos, windows]
---

# Receiving Code Review

## Overview

Review feedback is a technical claim to be checked, not an instruction to be obeyed and not a verdict
to be absorbed. The failure modes are symmetric: agreeing with everything to keep the peace, and
defending your first attempt because you wrote it.

**Core rule:** verify before implementing, and ask before assuming.

## The Response Pattern

```
1. READ      the whole list without reacting or replying
2. UNDERSTAND  restate each requirement in your own words
3. VERIFY    check it against what the code actually does
4. EVALUATE  is it right for THIS codebase?
5. RESPOND   technical acknowledgement, or reasoned pushback
6. IMPLEMENT one item at a time, testing each
```

Step 5 is where the discipline lives. Two legitimate responses exist: a statement of what you changed,
or a specific technical disagreement. Nothing else is needed.

## Responses To Avoid

- "You're absolutely right!" / "Great catch!" / "Excellent feedback!" — these assert agreement before
  any verification has happened. If the reviewer turns out to be wrong, the message is now a lie.
- "Let me implement that right now" — before step 3, this is compliance, not engineering.
- Gratitude as a substitute for substance. Fixing the thing is the acknowledgement; the code shows
  you heard it.

**Prefer instead:** restate the requirement, ask a clarifying question, push back with reasoning, or
just make the change and describe it — `Fixed: the retry counter now resets per request, in
client.py`. Actions over pleasantries.

## If Any Item Is Unclear, Stop

```
IF any item is unclear:
  STOP — do not implement anything yet
  ASK about the unclear items first
```

Review items are usually related. Implementing the parts you understood while guessing at the rest
produces a change that is coherent in none of them.

```
Wrong: implement 1, 2, 3 and 6 now; ask about 4 and 5 later.
Right: "I understand 1, 2, 3 and 6. I need clarification on 4 and 5 before I start."
```

## Handling An Unclear or Wrong Feedback Item

Before implementing feedback from someone who did not write the code — a reviewer, a bot, a
linter rule, a colleague — check all five:

1. Is it technically correct for **this** codebase (not for a generic one)?
2. Does it break existing functionality, callers, or an external contract?
3. Is there a reason the current implementation looks like that — history, compatibility, a platform
   constraint?
4. Does it hold on every platform, version and config this code must run under?
5. Does the reviewer have the full context, or only this diff?

If a suggestion looks wrong, say so with reasoning rather than implementing it and hoping. If you
genuinely cannot check it, say that plainly: "I can't confirm this without X — should I investigate,
or proceed and note it?" Where the suggestion contradicts a decision the caller already made
deliberately, stop and raise it rather than silently reverting their choice.

## The YAGNI Check For "Do It Properly"

Review advice to build the general version is often a request to build an unused one:

```bash
grep -rn "thingBeingReviewed" src/    # is anything actually calling this?
```

- **Not called anywhere** → "nothing invokes this path; remove it, or is there usage I'm missing?"
- **Called** → then yes, building it properly is warranted.

Adding configuration, retries, metrics or abstraction for a caller that does not exist is cost with
no benefit, and it is your job to surface that.

## Implementation Order

```
FOR multiple items:
  1. clarify anything unclear FIRST
  2. then fix in this order:
       blocking issues (crashes, data loss, security)
       simple and mechanical (typos, imports, naming)
       complex (refactors, behaviour, logic)
  3. test each fix on its own
  4. re-run the project's suite for regressions
```

Testing one item at a time is what tells you which change broke something. Batching six fixes and then
hunting the failure is slower, not faster.

## When To Push Back

Push back when the suggestion:

- breaks existing functionality or an external contract,
- rests on a misunderstanding of the context the reviewer cannot see,
- adds an unused feature (YAGNI),
- is technically wrong for this language, framework or runtime,
- conflicts with a deliberate earlier decision,
- is a preference restated as a defect.

**How:** name the specific technical fact, cite the working code or test that shows it, and ask a
concrete question. "That API needs version 13 while this project supports 10.5+, so I kept the
compatibility path — should we drop the older floor instead?" beats both silence and defensiveness.

If you notice you are reluctant to push back on something you believe is wrong, say the disagreement
out loud anyway. Withholding it to avoid friction is the expensive mistake.

## When You Were Wrong To Push Back

```markdown
Good: "You were right — I checked and the parser does normalise that. Implementing now."
Good: "Verified. My initial reading was wrong because the config is merged at load time. Fixing."
Bad:  a long apology, an explanation of why the mistake was reasonable, or a defence of the pushback
```

State the correction plainly and move on. The value is the corrected code.

## Common Mistakes

| Mistake | Fix |
|---|---|
| "You're right!" before checking | Verify first; then say what you changed |
| Implementing all items blindly | Check each against this codebase |
| Batching changes with no per-item test | One at a time, tested |
| Assuming the reviewer is right | Check whether it breaks something |
| Avoiding pushback to keep things pleasant | Technical correctness outranks comfort |
| Implementing the clear half of an ambiguous list | Clarify all items, then start |
| Building the general version nobody calls | Grep for usage; state what you found |
| Long apology after being wrong | One factual sentence, then the fix |
