---
name: finishing-a-development-branch
description: Use when implementation is complete and the tests pass — to decide how finished work leaves the branch (merge, push for review, keep as-is, or discard) and to clean up the workspace the work was built in.
version: 1.0.0
author: adapted from obra/superpowers
license: MIT
platforms: [linux, macos, windows]
---

# Finishing a Development Branch

Integration is a decision, not a formality. The work being finished is not the same as the work
being accepted: a green implementation still needs someone to choose where it goes, and that choice
belongs to the person who owns the repository.

**Order: verify tests → detect the environment → confirm the base → present the choice → execute →
clean up.** Skipping to the merge turns a reversible decision into an expensive one.

## Step 1 — Verify the tests on the tree you are about to integrate

Run the project's full suite (`npm test` / `cargo test` / `pytest` / `go test ./...`).

A suite that passed earlier in the session proves the tree it ran on, not the tree in front of you.
If it fails now, report the failures and stop — the integration menu comes after a green suite:

```
Tests failing (<N> failures). Not ready to integrate:

<failures>
```

## Step 2 — Detect the environment, and capture paths before changing directory

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" && pwd -P)
WORKTREE_PATH=$(git rev-parse --show-toplevel)
```

Capture all three **now**. Later steps change directory — cleanup has to run from outside the
workspace, so these values have to survive that move. What they tell you:

| State | Menu | Cleanup |
|---|---|---|
| `GIT_DIR == GIT_COMMON` — normal checkout | Three options | Nothing to remove |
| Linked worktree, on a named branch | Three options | Only if you created it |
| Linked worktree, detached HEAD | Two options — no merge | Externally managed, leave in place |

## Step 3 — Determine the base branch, and confirm it

The base is whatever this work forked from — usually named in the plan, the conversation, or the
branch's upstream. If it is not certain, ask: *"This branched from `<best guess>` — right?"*

Merging into the wrong branch is expensive to undo, and a guess here is the cheapest mistake in this
skill to avoid.

## Step 4 — Present the choice and wait

For a normal checkout and a named-branch worktree, present exactly these:

```
Implementation complete. What would you like to do?

1. Merge back to <base-branch> locally
2. Push and open a merge request
3. Keep the branch as-is (I'll handle it later)

Which option?
```

On a detached HEAD, present exactly two — push for review, or keep as-is. There is no local merge
target to check out.

Present the menu as written. Discarding is not on it: that path exists only when the user asks for it
in those words.

## Step 5 — Execute the choice

**Merge locally.** Merge first, verify the merged result, and only then remove anything — nothing has
been pushed, so an unpushed merge is fully recoverable.

```bash
MAIN_ROOT=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
cd "$MAIN_ROOT"
git checkout <base-branch>
git merge <feature-branch>
<test command>
```

If the merged result fails, stop. Leave the branch and the worktree exactly where they are and
investigate — a merged-result failure is a real finding about the integration, not a flake to
re-run.

Once the merged tree is green, clean up the workspace (Step 6), then delete the branch:

```bash
git branch -d <feature-branch>
```

**Push for review.** Push the branch, then open the merge request with whatever tooling the forge
provides — a CLI if one is installed, otherwise the creation URL most forges print when you push.
Follow the repository's template if one exists, and report the URL you got back. Keep the workspace:
review feedback gets fixed there.

**Keep as-is.** Report the branch name and the workspace path. Done.

**Discard — only on an explicit request.** Confirm by listing what will be destroyed, and accept
only the typed word:

```
This will permanently delete:
- Branch <name>
- Commits: <commit list>
- Worktree at <path>

Type 'discard' to confirm.
```

"Yes, get rid of it" is not the word. When it arrives, return to the main repository root, clean up
(Step 6), then `git branch -D <feature-branch>`.

## Step 6 — Clean up the workspace, only if you own it

Cleanup runs for a local merge and for a confirmed discard. The other choices keep the workspace.

- **Normal checkout** — nothing to remove.
- **Path under `.worktrees/` or `worktrees/`** — you own it:

```bash
git worktree remove "$WORKTREE_PATH"
git worktree prune
```

- **Removal refused** (`contains modified or untracked files`) — files exist in that workspace and
  nowhere else: uncommitted notes, a scratch plan, a stray artifact. Never reach for `--force` on
  your own initiative. Show what is at stake and ask:

```bash
git -C "$WORKTREE_PATH" status --porcelain -uall
```

Offer three outcomes — commit them to the branch, move them into the main checkout, or delete them
knowingly — then carry out the answer.

- **Any other path** — the host environment owns this workspace. Leave it in place; use the
  platform's own workspace-exit if it has one.

## Gotchas

- **A rejected push means the remote moved.** Investigate what landed; a force-push is only ever the
  answer when the user asks for one. On a shared branch it can destroy someone else's work.
- **`--force` on a refused worktree removal is not cleanup.** The refusal means the files exist
  nowhere else. It is the one step here that cannot be undone.
- **Delete the branch after the workspace, not before.** Removing a worktree whose branch is gone
  leaves a confusing half-state; `git worktree prune` only cleans registrations whose directory has
  already gone.
- **The base branch is a guess until it is confirmed.** "Everyone merges to main" is exactly the
  assumption that merges a hotfix into a release branch.
- **Keep the workspace when a review is open.** Feedback arrives against that branch, in that
  directory.
- **A local merge is not a publish.** Merge locally, run the suite on the merged result, and report
  the SHA you produced — do not describe it as shipped.

## Quick reference

| Choice | Merge | Push | Keep workspace |
|---|---|---|---|
| Merge locally | yes | — | no |
| Push for review | — | yes | yes |
| Keep as-is | — | — | yes |
| Discard (explicit request only) | — | — | no |

| Situation | Action |
|---|---|
| Tests fail now | Report, stop, do not integrate |
| Base branch uncertain | Confirm before merging |
| Merged result fails tests | Stop, leave everything, investigate |
| Worktree removal refused | Show the files, ask, never `--force` |
| Push rejected | Investigate the remote, do not force |

## Related

- The `using-git-worktrees` skill covers creating the isolated workspace this skill finishes and, if
  it created it, the cleanup rules here apply to it.
- The `verification-before-completion` skill is what to run over your final report: the merged
  result's test output is the evidence, not the statement that tests pass.
