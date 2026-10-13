---
name: merge-reconciler
description: Use when two agents' parallel branches collide — a git merge or rebase has halted on conflicts and neither author should self-adjudicate. A neutral third party inventories the conflict, classifies every hunk (disjoint / design-collision / superseded), resolves under an impartiality contract, and verifies both sides' intents survived.
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
---

# Merge Reconciler

Resolve a git merge conflict between two agents' branches as an impartial third party. An agent
resolving its own conflict with a peer's work reliably either overwrites the peer or abandons its
own change — it holds the peer's context only through the conflict markers and is biased toward
its own side. The fix is the merge-queue pattern: a neutral reconciler that takes both sides'
diffs plus both sides' stated intents and produces a merged result neither author would have
produced alone.

## When to use (and when not)

Use it when:

- Two agent branches or worktrees collide during a parallel run — a batch split one agent per
  domain, a parallel-PR wave, a multi-worktree refactor.
- A `git merge` or `git rebase` halts on conflicts between two agents' work and neither original
  agent should self-adjudicate.

Do not use it for:

- Conflicts from a single agent's own sequence of edits — it has full context; merge normally.
- Machine-generated file churn (lockfiles, codegen output) — regenerate with the real tool
  instead of hand-merging.
- A repo whose merge queue already arbitrates conflicts — then wait for the queue, and treat its
  decisions as the record.

## Who resolves

The reconciler must have no stake in either side: a fresh agent session with no prior context on
either branch, or a human. A session that either author spawned — or that wrote one of the two
sides — is structurally biased. If that is the only option available, say so explicitly in the
hand-back summary and weigh the other side's intent deliberately.

Give the reconciler, in its first message: the repo path, both branch names, and each side's
intent statement verbatim. Every fact it would otherwise reconstruct from git archaeology is a
fact it may guess wrong.

## Step 1 — Gather both sides

In the repo with the halted merge (the current side is `HEAD`/ours, the incoming side is
`MERGE_HEAD`/theirs):

```bash
git status --porcelain                # conflict classes: UU both-edited, AA both-added,
                                      # DU / UD one-deleted-one-modified
git diff --name-only --diff-filter=U  # every path with unmerged stages
git merge-base <branch-a> <branch-b>  # the common ancestor
git log --oneline <base>..<branch-a>  # side A's commits; repeat for branch-b
git diff    <base>..<branch-a> -- <path>   # side A's full change to the path; repeat for B
git log --merge --oneline -- <path>   # during a live conflict: both sides' commits touching it
```

(The same commands work for a halted `rebase`; the vocabulary flips, and `git status` names the
moving side.)

Then state each side's intent in one sentence — from its commit messages, its PR description, or
the task brief the orchestrator wrote for it. Do not touch a file until you can state both
intents. If a side's intent is unrecoverable, stop and escalate rather than guess: you cannot
classify a hunk against an unknown intent.

Done when: both intents are stated, and for every conflicted path you hold both sides' diffs.

## Step 2 — Read the conflict precisely

- `git ls-files -u <path>` lists the unmerged stages: **stage 1 = common ancestor, stage 2 =
  ours, stage 3 = theirs**. `git show :2:<path>` and `git show :3:<path>` print each side's exact
  bytes. Prefer these over reconstructing a side from the markers in the working tree.
- Work with the ancestor visible. `git config merge.conflictStyle zdiff3` (set before the merge)
  makes conflict blocks carry a `|||||||` section with the common-ancestor text, and hoists lines
  the two sides share out of the block — each hunk shrinks to its actual disagreement.
- To put the markers back after a botched edit, re-materialize the conflict:
  `git checkout -m -- <path>` (or `git checkout --conflict=diff3 -- <path>` to keep the base
  section). Gotcha, measured: re-materialized blocks lose the branch-name labels — `>>>>>>>`
  degrades to a plain `theirs`. After a re-materialization, refer to the sides by their index
  stages or by `MERGE_HEAD`, never by the marker labels.

## Step 3 — Classify every hunk

| Class | Definition | Resolution |
| --- | --- | --- |
| disjoint-intent | The two changes serve different goals and can coexist | Combine both |
| same-question-different-answer | Both sides answered one design question differently | Pick ONE answer, chosen by the stated intents; record the decision |
| superseded | One side's premise no longer holds after the other's change | Keep the surviving side; note the dead premise |

- Classify per hunk, never per file — one file routinely mixes classes: a design collision in
  one function, a disjoint addition in the next.
- Decompose hunks that bundle more than one decision — new logic that combines cleanly plus a
  constant both sides set differently — and classify each decision in turn.
- Judge by the stated intents, not by which diff looks nicer.
- Done when every hunk has a written class and a one-line rationale.

## Step 4 — Resolve under the impartiality contract

The contract: never favor the side that spawned you; touch only conflicted regions (no drive-by
formatting, renames, or opportunistic fixes); every same-question pick must appear verbatim in
the hand-back summary.

- **disjoint-intent** — write the hunk so both intents are fully served.
- **same-question-different-answer** — pick the answer the intents require: where a side's
  mandate was correctness, a strict-reading answer beats a convenient one. Never split the
  difference into a hybrid neither side designed — hybrids usually compile and are wrong for
  everyone.
- **superseded** — keep the survivor and delete the dead premise, even where it sits inside
  `<<<<<<<` / `>>>>>>>` markers. Dead code kept "to be safe" is how both sides' bugs coexist.

Mechanics, with measured semantics:

```bash
# whole-path picks, generated/lock files only — a per-path win, not a per-hunk resolution:
git checkout --ours -- <generated-path> && git add <generated-path>

# set-like files (.gitignore entries, lockfile import blocks): union both sides' additions.
#   Measured: git merge-file --union emits the OURS block FIRST, then THEIRS, with no
#   markers — the output is order-dependent. Fine for files whose lines are an unordered
#   set; never union-merge code or anything where line order carries meaning.

# delete/modify conflicts (porcelain UD/DU) — decide by intent, not by "git is confused":
#   accept the deletion    ->  git rm <path>
#   keep the modification  ->  restore the kept side's content (git show :2:<path> or :3:<path>),
#                              then git add <path>. A UD has no stage 3; a DU has no stage 2.

# add/add conflicts (AA, both sides created the same new path) — usually one whole-file
#   design question: hand-merge the content, or delete the loser after recording why.

git add <resolved-path>   # staging a path clears its unmerged stages
```

- Resolve from the working-tree markers, then `git add` each path. Staging is the per-path unit
  of "done"; `git status` stops listing a path once it is staged.
- If the two intents genuinely tie on a design question — both defensible, no stated mandate —
  escalate to the orchestrator instead of guessing. A tie settled by a coin is a bug the human
  must own.
- Escape hatch, measured: `git merge --abort` returns the tree to its clean pre-merge state; for
  a halted rebase it is `git rebase --abort`.

## Step 5 — Verify, then commit

1. **No silent loss.** For every conflicted path, extract each side's added lines
   (`git diff <base>..<side> -- <path>`) and confirm the merged file contains every one —
   except lines whose abandonment is a hunk decision you recorded and will name in the summary.
   A merge that compiles but quietly dropped one side's addition is the exact failure this skill
   exists to prevent.
2. **Run the project's tests** (or build) on the merged tree; at minimum execute or import the
   touched modules. Merged code can be textually clean and semantically wrong — the classic
   semantic conflict — so only behavior proves the merge.
3. **Both intents observable.** Side A's new semantics and side B's addition must both be
   demonstrable in the running result.
4. `git status` shows no unmerged paths; `git commit` completes the merge. Keep the default
   merge message and add a body listing the hunk decisions.

## Step 6 — Hand back

A per-hunk ledger, one line each:

```
path:start-end — class — kept side(s) — rationale
```

For every same-question-different-answer hunk, state the design question and the picked answer
explicitly, so a human can veto it without re-reading the diff. For superseded hunks, name the
dead premise. Never bury a design call in prose.

## Repeat conflicts: rerere and hotspots

If the same two branches will collide again during an ongoing parallel run, turn rerere on
before merging:

```bash
git config rerere.enabled true
```

Measured semantics: on a repeated conflict, rerere re-applies the previously recorded resolution
to the working tree — the file content is restored — but the path still shows `UU` and `git
commit` still refuses until the files are staged with `git add`. `git rerere status` prints
nothing once every recorded resolution has been replayed. Rerere replay is mechanical, not
neutral: it re-uses the last decision, which may no longer be right after either side moved.
Verify a replayed result exactly as in Step 5, then add and commit.

When the same file collides across repeated rounds, that file is a coordination hotspot, not
routine reconciliation work: report it to the orchestrator (who should decompose the file or
re-slice the agent domains) instead of reconciling each new collision serially.

## Verification checklist

- `git status` — clean tree, merge commit exists, no unmerged paths.
- No conflict markers remain anywhere (`grep -rn '<<<<<<<' <repo-root>` — ignoring vendored or
  generated files if the project vendors some).
- Tests/build pass on the merged tree; both intents are demonstrably present — or a dropped one
  is named in the summary with its superseded rationale.
- The hand-back ledger enumerates every hunk with class and rationale, and every design pick is
  veto-visible.

## Related

- `dispatching-parallel-agents` — prevent the collision: one focused agent per domain beats
  reconciling five shared files afterward.
- `using-git-worktrees` — isolated workspaces per task.
- `finishing-a-development-branch` — the merge and cleanup mechanics once a branch is done and
  single-owned.
- `verification-before-completion` — the evidence discipline behind Step 5.
- `code-review-reception` — how the original agents should weigh the reconciler's design picks
  they disagree with: on merit, not on reflex.