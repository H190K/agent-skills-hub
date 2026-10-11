---
name: background-coding-agents
description: Use when a task is too big or too long to sit through — multi-hour feature builds, large refactors, PR reviews, issue-to-PR loops, or several long jobs at once — and the work should happen in unattended one-shot worker sessions of separate coding-agent CLIs (Anthropic's `claude`, OpenAI's `codex`, or `opencode`) in isolated worktrees, with per-agent auth isolation, prompt files and proof receipts. Not for small edits or read-only lookups — do those inline.
version: 1.0.0
author: adapted from openclaw/openclaw (OpenClaw Foundation, MIT)
license: MIT
platforms: [linux, macos, windows]
---

# Background coding agents

## Overview

A worker is a one-shot, non-interactive run of a separate coding-agent CLI —
`claude` (Anthropic), `codex` (OpenAI) or `opencode` — spawned as a background
process, briefed once in advance, and left alone until the process reports.
Delegate to a worker only what justifies the setup: background feature builds,
PR reviews, large refactors, issue-to-PR loops. Do not delegate small edits or
read-only lookups; those are faster done inline, and an over-permissioned
autonomous session on a trivial task is pure risk.

Everything below exists to keep a broadly-empowered autonomous session from
going wrong: an isolated worktree, a per-worker auth home, a prompt file, a
completion signal someone actually watches, and a receipt to audit afterwards.

## Install and authenticate (once, in the foreground)

- `claude` — `npm install -g @anthropic-ai/claude-code`. Non-interactive form:
  `claude --print` (`-p`), prompt passed as an argument or via stdin.
  Worker-scoped identity (measured): `CLAUDE_CONFIG_DIR="$HOME/.claude-worker"`
  relocates the whole config — a fresh dir reports "Not logged in" and gets its
  own `.claude.json`; authorize it once with `claude auth login` (or
  `claude setup-token` for a long-lived token), in the foreground.
- `codex` — `npm install -g @openai/codex`; requires Node >= 24 (npm refuses
  older node with `EBADDEVENGINES`). Non-interactive form: `codex exec`, which
  reads the prompt from stdin when it is missing or a lone `-`.
  `codex exec resume --last` continues the most recent session.
- `opencode` — `curl -fsSL https://opencode.ai/install | bash` (installer drops
  the binary in `~/.opencode/bin`) or `npm install -g opencode-ai`
  (Node >= 24). Non-interactive form: `opencode run`, which reads the prompt
  from stdin; `--session <id>` / `-c` resume one. Credentials live in
  `$XDG_DATA_HOME/opencode/auth.json` (default `~/.local/share/opencode/auth.json`);
  point `XDG_DATA_HOME` at a worker-only dir to isolate them (measured:
  `opencode auth list` reads the relocated path).

Isolate every worker's identity from your own login — codex via `CODEX_HOME`,
claude via `CLAUDE_CONFIG_DIR`, opencode via `XDG_DATA_HOME`. The login is an
interactive foreground step, never backgrounded. Codex example (it scopes both
the credential file and the keyring by `CODEX_HOME`):

```bash
CODEX_WORKER_HOME="$HOME/.codex-worker"
mkdir -p "$CODEX_WORKER_HOME"
if ! env -u CODEX_API_KEY -u CODEX_ACCESS_TOKEN -u OPENAI_API_KEY \
  CODEX_HOME="$CODEX_WORKER_HOME" codex login status >/dev/null 2>&1; then
  printf 'Codex worker login required for %s\n' "$CODEX_WORKER_HOME"
  env -u CODEX_API_KEY -u CODEX_ACCESS_TOKEN -u OPENAI_API_KEY \
    CODEX_HOME="$CODEX_WORKER_HOME" codex login --device-auth
fi
```

## Hard rules for every launch

- **Background it.** Spawn behind your agent's background-process facility or
  `nohup ... &`, and record the PID and log paths. Never babysit a foreground
  worker session, never poll in a loop.
- **One prompt, one file.** A worker cannot ask you questions mid-run. Write
  the whole brief before spawning: goal, stack and layout, build/test commands,
  constraints, done-criteria, output format.
- **Isolated worktree only.** Never the primary checkout, and never the
  checkout of the shell setup or tooling the launching agent itself runs
  inside — agent state, config and your own running session live there.
- **Real completion signal.** Wire a notify-on-exit or a log line you actually
  watch. Do not rely on ambient heartbeats, system events, or the worker
  remembering to report.
- **Monitor the real process.** Poll status, read its log, write to its stdin
  only through the process interface. Kill only with cause, and record why; do
  not kill a slow-but-advancing worker before its deadline.
- **A failed or hung worker is respawned or escalated — never silently
  hand-coded.** Doing it yourself hides exactly the failure the delegation
  was supposed to surface.
- If the requester named a specific agent, use that agent.

## The prompt file

Hand the brief to the worker through a file; the worker reads it from stdin:

```bash
PROMPT=$(mktemp -t codex-brief.XXXXXX)
cat >"$PROMPT" <<'EOF'
<goal>
<stack and layout: entrypoints, tests, build commands>
<constraints: keep the public API, don't touch the migrations, ...>
<done-criteria: exact tests/checks to pass>
<report format: files changed, commands run, open questions>
EOF
printf 'prompt file: %s\n' "$PROMPT"
```

If the launching process tool spawns and writes stdin separately, substitute
the printed path at launch time.

## Git preparation — mandatory before any repo-modifying work

1. Establish the target repository, then pick its canonical remote: `upstream`
   when it exists and matches the target, else `origin`. Resolve the canonical
   default branch dynamically. Take the target base from an explicit task
   branch or authoritative PR metadata; for other shared branches prove the
   tracked base. If the repository, remote or base cannot be proven, stop.
2. Classify the source ref as trusted or untrusted before any checkout or
   worktree creation.
3. New work: `git fetch --prune <canonical>` immediately before creating an
   isolated worktree on a new branch from `<canonical>/<targetBase>`.
4. Verify the worktree's initial HEAD equals the fetched target-base SHA.
   Record: canonical remote, default branch, base branch, base SHA, worktree
   path, working branch.
5. Existing PR or shared branch: fetch the canonical target base and the
   source branch immediately before creating the worktree from the fetched
   source, record that starting SHA, report its divergence from the refreshed
   base, and do not rebase, merge, reset, force-push or otherwise rewrite
   shared history unasked.
6. Launch the worker in the isolated worktree, never the primary checkout.

Append this receipt to the worker prompt with real values:

```text
Git preparation (mandatory before edits):
- canonical remote: <canonicalRemote>
- canonical default branch: <canonicalDefaultBranch>
- target base branch: <targetBaseBranch>
- fetched target base SHA: <targetBaseSha>
- preparation mode: <new work | existing PR/shared branch>
- checkout trust: trusted
- prepared source ref: <canonicalRemote/targetBaseBranch | fetched trusted source ref>
- prepared start SHA: <preparedStartSha>
- isolated worktree: <worktreePath>
- working branch: <workingBranch>

Before editing, verify the current directory is the isolated worktree and its
initial HEAD equals <preparedStartSha>. Never edit the primary checkout.
Immediately before the final push, run `git fetch --prune <canonicalRemote>`
and `git merge-base --is-ancestor <canonicalRemote>/<targetBaseBranch> HEAD`.
If the ancestry check fails, update the branch onto the latest target base,
rerun the check, and only then push without force.
```

## Trust classification

Contributor-controlled refs — PR branches and patches from strangers — are
untrusted. Materialize them only inside the project's approved sandboxed
review workflow, and never launch a permission-bypassed worker in one. The
launch forms below are for trusted checkouts only.

## Launch forms

Measured against real binaries: `claude` 2.1.285, `codex` 0.134.0,
`opencode` 1.19.0. Run inside the isolated worktree `$WT` with the brief at
`$PROMPT`; every form writes a log next to the work and echoes the PID.

```bash
# Claude: --print is non-interactive (no PTY); prompt via stdin; worker-scoped identity
cd "$WT"
nohup env CLAUDE_CONFIG_DIR="$HOME/.claude-worker" \
  claude --permission-mode bypassPermissions --print \
  <"$PROMPT" >worker.log 2>&1 &
echo "claude worker pid: $!"
```

```bash
# Codex: exec is non-interactive; isolated auth home; approval off for
# unattended runs, sandbox scoped to the workspace
cd "$WT"
nohup env -u CODEX_API_KEY -u CODEX_ACCESS_TOKEN -u OPENAI_API_KEY \
  CODEX_HOME="$HOME/.codex-worker" codex exec - \
  --sandbox workspace-write -a never \
  <"$PROMPT" >worker.log 2>&1 &
echo "codex worker pid: $!"
```

```bash
# opencode: run is non-interactive; piped stdin starts the session (measured:
# the control run without a message errors with "You must provide a message
# or a command"); worker-scoped credentials dir
cd "$WT"
nohup env XDG_DATA_HOME="$HOME/.opencode-worker-share" \
  opencode run <"$PROMPT" >worker.log 2>&1 &
echo "opencode worker pid: $!"
```

Permission surface, as shipped:

- `claude --permission-mode` choices: `acceptEdits`, `auto`,
  `bypassPermissions`, `manual`, `dontAsk`, `plan`. `bypassPermissions` is the
  worker stance but runs unsandboxed.
- `codex -s, --sandbox` values: `read-only`, `workspace-write`,
  `danger-full-access`; `--dangerously-bypass-approvals-and-sandbox` says of
  itself that it is intended solely for environments that are externally
  sandboxed — hold it for containers you own.
- `opencode run` surfaces no permission flag; restrict its workers to projects
  you are authorized on.

These are one-shot forms. An interactive worker variant expects a real TTY —
wrap it in `script -qec "<cmd>" /dev/null` under the same `nohup` shell.

## Scratch worker (not project work)

For a throwaway experiment in an empty directory, the git preparation does not
apply — there is no canonical remote and no history worth protecting:

```bash
SCRATCH=$(mktemp -d)
git -C "$SCRATCH" init
PROMPT=$(mktemp -t codex-scratch-brief.XXXXXX)
printf 'Build X.\n<done-criteria and report format>\n' >"$PROMPT"
cd "$SCRATCH"
nohup env -u CODEX_API_KEY -u CODEX_ACCESS_TOKEN -u OPENAI_API_KEY \
  CODEX_HOME="$HOME/.codex-worker" codex exec - \
  --sandbox workspace-write <"$PROMPT" >worker.log 2>&1 &
echo "scratch codex pid: $!  scratch dir: $SCRATCH"
```

## Long issue-to-PR work

1. Create or reuse a tracker issue as the durable spec.
2. The worker brief includes: issue URL, repo, canonical remote and default
   branch, target base branch + SHA, isolated worktree, working branch, the
   expected PR, the proof expected (tests or CI), and where completion is
   reported.
3. Include the Git-preparation receipt, then direct the worker: implement,
   test, run review until no accepted actionable findings, open the PR.
4. Return the issue URL and the PID/session id immediately — the spawn itself
   is the deliverable, not the eventual result.
5. Monitor the process; escalate the failure, do not absorb it.

## Reporting and closure discipline

- On spawn: what started, where (worktree path), PID or session id.
- On milestone, worker question, error, or finish: a short status.
- On kill: the reason.
- Otherwise quiet — do not narrate every file write.
- Before reporting any worker result as done, verify it yourself in the
  worktree: run the test suite, read the diff. A worker saying "done" is a
  claim, not a result. Weigh it the way you weigh any reviewer's claim, and
  package the diff for a fresh-context review before merging.

## Related skills (in this repo)

- `using-git-worktrees` — the mechanics of the isolated worktree the receipt
  references.
- `dispatching-parallel-agents` — several short independent problems may not
  need heavyweight CLI workers; match the instrument to the job.
- `requesting-code-review` — package a worker's diff for fresh-context review
  before merge.
- `code-review-reception` — weigh reviewer and worker claims on technical
  merit.
- `finishing-a-development-branch` — the endgame of a worker's working branch.
- `verification-before-completion` — what counts as evidence before you call
  worker output done.
- `coding-development` — index of when a background worker fits the broader
  flow.