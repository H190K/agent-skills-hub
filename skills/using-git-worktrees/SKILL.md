---
name: using-git-worktrees
description: Use when starting feature work that needs isolation from the current workspace, or before executing an implementation plan task by task — establishes a separate working directory and confirms a clean baseline before any code changes.
version: 1.0.0
author: adapted from obra/superpowers
license: MIT
platforms: [linux, macos, windows]
---

# Using Git Worktrees

Isolate the work before you start it. A feature built directly on the branch you happen to be reading
turns an abandoned experiment into a dirty tree, and makes "what did I actually change" unanswerable.

**Core order: detect, then use the platform's own tool, then fall back to git.** Never hand-roll what
the environment already manages — a workspace created behind the harness's back is invisible to it,
so it will not be reported, cleaned up, or exited correctly.

## Step 0 — Detect existing isolation first

You are often already isolated: you were launched into a workspace prepared for you, or the
directory is a submodule. Both read as "in a worktree" if you only glance at the git dirs, and only
one of them is.

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" && pwd -P)
git branch --show-current
git rev-parse --show-superproject-working-tree
```

- `GIT_DIR != GIT_COMMON` and the superproject command printed nothing → **already in a linked
  worktree.** Report the path and branch. Do not create another one. Continue at *Baseline*.
- `GIT_DIR != GIT_COMMON` and the superproject command printed a path → **you are in a submodule.**
  That is a normal checkout for this purpose; do not treat it as an isolated workspace.
- `GIT_DIR == GIT_COMMON` → **normal checkout.** Decide whether to isolate before writing code.

Isolating is worth it when the work is exploratory, spans several commits, or would leave the shared
checkout in a state someone else depends on. It is not worth it for a one-line fix in a repo nobody
else is touching. If the user has already stated a preference, honour it without asking again;
otherwise say what you are about to do and why, in one line.

## Step 1 — Create the workspace

**Prefer a native worktree tool if your environment has one** — a tool or command whose job is to
create and manage a workspace (`EnterWorktree`, a `--worktree` flag, an equivalent). It owns
placement, branch creation and cleanup. Using raw git beside it produces phantom state the harness
cannot see; this is the most common mistake in this area.

Without a native tool, use git. Order of preference for the location:

1. A directory the user or instructions named — that wins over everything below.
2. An existing project-local directory: `.worktrees` if present, otherwise `worktrees`.
3. Neither exists → `.worktrees/` at the project root.

**Before creating a project-local worktree, confirm the directory is ignored.** An unignored
worktree directory means `git add .` commits an entire second checkout into the repository.

```bash
git check-ignore -q .worktrees          # exit 0 = ignored
```

If it is not ignored, add it to `.gitignore` and commit that change *before* creating the worktree.

```bash
git worktree add ".worktrees/<branch>" -b "<branch>"
cd ".worktrees/<branch>"
```

If creation fails on a permission error, the sandbox is refusing it. Say so and work in place —
do not escalate privileges or retry in a loop.

## Step 2 — Set the project up

Install what the project needs, detected from what it ships:

```bash
[ -f package.json ]    && npm install
[ -f Cargo.toml ]      && cargo build
[ -f requirements.txt ] && pip install -r requirements.txt
[ -f pyproject.toml ]  && poetry install
[ -f go.mod ]          && go mod download
```

Skip silently when none of these exist. Never invent a setup step for a language the project does
not use.

## Baseline — Run the tests before changing anything

```bash
npm test          # or: cargo test / pytest / go test ./...
```

A failure here is not your bug yet, and that is exactly why it matters: a dirty baseline makes every
later failure ambiguous. Report the failures and let the user decide whether to investigate first or
proceed. Then report the state plainly:

```
Worktree ready at <path>
Tests: <N> passed, 0 failed
Branch: <branch>
```

## Gotchas

- **Submodules fake a worktree.** The `GIT_DIR`/`GIT_COMMON` test is also true inside a submodule.
  Without the superproject guard you will "detect" isolation that does not exist and then refuse to
  create the workspace you were asked for.
- **An unignored `.worktrees/` is a data-loss shape, not a style issue.** The whole second checkout
  lands in the next commit, and the diff is unreadable.
- **`.worktrees` beats `worktrees`** when both exist. Pick one and state which.
- **A native tool and `git worktree add` do not mix.** If the harness created the workspace, git's
  view of it is partial — placement and exit are the harness's business.
- **`-b` means "create", and it will not reuse an existing branch.** `git worktree add <dir> -b feat`
  fails outright if `feat` already exists — even when nothing has it checked out. Drop `-b` to attach
  the worktree to the existing branch instead. (Both errors surface at creation, not later.)
- **A branch can only be checked out in one worktree at a time.** If another worktree — or the main
  checkout — is already on that branch, `git worktree add` refuses. Give the worktree its own new
  branch, or pick work that does not collide.
- **Do not delete a worktree you did not create.** If its path is not under `.worktrees/` or
  `worktrees/`, something else owns it and its exit is that thing's job.

## Quick reference

| Situation | Action |
|---|---|
| Already in a linked worktree | Report it, skip creation |
| Inside a submodule | Normal checkout — decide whether to isolate |
| Native worktree tool exists | Use it, do not call git |
| No native tool | `git worktree add <dir> -b <branch>` |
| `.worktrees/` exists | Use it, verify it is ignored |
| Not ignored | Add to `.gitignore`, commit, then create |
| Permission error | Report the sandbox block, work in place |
| Baseline tests fail | Report and ask before proceeding |

## Related

- Once the work is done, the `finishing-a-development-branch` skill covers the integration decision
  and who is responsible for cleaning this workspace up.
- The `verification-before-completion` skill states what counts as evidence when you claim the
  baseline or the final result is green.
