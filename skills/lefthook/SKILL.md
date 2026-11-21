---
name: lefthook
version: 1.0.0
author: H190K
license: MIT
description: "Use when setting up or debugging git hooks with lefthook - install/uninstall/skip mechanics, file templates in run strings, piped vs parallel execution, stage_fixed, core.hooksPath conflicts, or migrating v1 configs whose json templates and dict-style skip conditions no longer behave; measured on the official 2.2.2 release binary."
---

# lefthook — git hooks manager, measured on 2.2.2

`lefthook` ([evilmartians/lefthook](https://github.com/evilmartians/lefthook), licence MIT — the LICENSE file says "Copyright (c) 2019 Arkweid") is a fast single-binary git hooks manager. Everything here is original text measured live on **v2.2.2** (the official `Linux_x86_64` `.gz` release asset, sha256-verified against the release's `lefthook_checksums.txt`) and cross-checked on the conda-forge 2.2.2 build — `--help` byte-identical (same md5). 2.2.2 was the newest release at the time of writing; no older line was measured, so treat exact strings as version-specific. The v2 line introduced a `jobs` config vocabulary; the legacy `commands` vocabulary still executes on 2.2.2 (measured).

## Install and verify

```bash
cd "$(mktemp -d)" &&
curl -f -sL -o lh.gz "https://github.com/evilmartians/lefthook/releases/download/v2.2.2/lefthook_2.2.2_Linux_x86_64.gz" &&
curl -f -sL -o lefthook_checksums.txt "https://github.com/evilmartians/lefthook/releases/download/v2.2.2/lefthook_checksums.txt" &&
grep -F "lefthook_2.2.2_Linux_x86_64.gz" lefthook_checksums.txt | sha256sum -c - &&
gunzip -kf lh.gz &&
mkdir -p "$HOME/.local/bin" &&
install -m 755 lefthook_2.2.2_Linux_x86_64 "$HOME/.local/bin/lefthook" &&
"$HOME/.local/bin/lefthook" version
```

The release carries per-arch `.gz` payloads plus `.deb`/`.rpm`/`.apk` and a `lefthook_checksums.txt` sidecar; sha256 of the 2.2.2 x86_64 payload starts `2b8d7fd5`. Other measured/documented sources: `conda install -c conda-forge lefthook` (2.2.2 there too — cross-checked byte-identical `--help`), npm `@evilmartians/lefthook` (the hook wrapper probes several `node_modules` layouts itself), `go install`, brew. Invoke the binary by installed path in scripts; nothing here assumes PATH membership.

## How hooks resolve the binary — read before deleting it

`lefthook install` writes a POSIX-sh wrapper into `.git/hooks/<hook>`. Measured resolution order, first hit wins, else "Can't find lefthook in PATH":

1. `$LEFTHOOK_BIN` if set
2. `lefthook` on **PATH** (`lefthook -h` probe)
3. the **absolute binary path baked in at install time** — if you install from a throwaway location, that path rots with it
4. `node_modules/lefthook-${osArch}-${cpuArch}/bin/lefthook`, `@evilmartians/lefthook`, `lefthook-installer`, legacy `lefthook/bin/index.js`
5. `go tool lefthook`, `bundle exec`, `yarn`, `pnpm`, `swift package`, `mint`, `uv run`, `composer exec`, `mise exec`, `devbox run`

Consequence measured live: a repo whose wrapper baked a 2.2.2 path still answered a `git commit` with a *different* lefthook because PATH hit first (2.2.1 banner). If hook behavior mismatches the version you installed, check PATH before blaming config. The wrapper itself honors `LEFTHOOK=0` (exit 0) and `LEFTHOOK_VERBOSE=1` (`set -x`) before ever calling the binary.

## Install mechanics

- In a repo with **no config**, `lefthook install` prints `Config not found, creating...`, scaffolds a fully commented example `lefthook.yml` (v2 vocabulary: `jobs`, `tags`, `parallel`) and syncs hooks — measured hook set on an empty config: `pre-commit` **and** `prepare-commit-msg`.
- With a config, one wrapper per hook section present (`pre-commit:` → `.git/hooks/pre-commit`).
- Plain install does **not** overwrite a foreign (non-lefthook) hook in the way: a manually written `.git/hooks/pre-commit` survived `install` with rc 0 and no backup — lefthook skips it, and `check-install` then correctly reports rc 1. Only `lefthook add` documents renaming an existing hook to `<hook>.old`.
- `lefthook uninstall` removes only lefthook-owned wrappers; a foreign hook survived it (measured).
- `lefthook add pre-commit --create-dirs` (or `--dirs`) creates `.lefthook/pre-commit/` and `.lefthook-local/pre-commit/` script dirs (`.lefthook-local` is the personal one — gitignore it) and installs the hook.
- `core.hooksPath` set → plain install **fails rc 1** with an actionable box offering `lefthook install --reset-hooks-path`, a manual `git config --unset-all --local core.hooksPath`, or `lefthook install --force` (which installs into the custom path, measured).
- In a repo with **zero commits**, runs can fail rc 1 with `Failed to save unstaged changes` + `Error: failed to run the hook` (its internal `git stash create` has no base commit). Init-repo probes need one commit first.

## Manual runs and exit codes

`lefthook run <hook>` executes a group by name and re-syncs hooks every call (the `sync hooks: ✔️(...)` line). Measured contract, all exit codes read unpiped:

- unknown group → `Error: hook <name> doesn't exist in the config`, rc 1; no name at all → `Error: hook name missing`, rc 1.
- commands that reference no file templates are **skipped when nothing is staged** — `(skip) no files for inspection`, rc 0. Nothing to debug here: an empty stage is a silent skip, not an error.
- a command failing (any exit) → the run summary shows `✗ name`, prints `exit status N`, and **lefthook always returns rc 1** — the child's exit code (3, 4 measured) never propagates. Gate scripts can't distinguish failure kinds by rc, only by output.
- empty stage with `--force` → commands run anyway (rc 0); `--all-files` replaces file templates with `{all_files}` regardless of staging.
- `lefthook run --no-auto-install` disables the implicit hook sync.

## File templates — the v2 trap section

In `run:` strings, measured on 2.2.2:

- `{staged_files}` and `{all_files}` expand to a **brace-wrapped, space-joined** list — `{a.txt new.txt}`. Both `{...}` and the doubled `{{...}}` spelling expand (measured); the docs spell them single-brace.
- `{staged_files_json}` and `{all_files_json}` (v1-era names) **do not expand** — they pass through *literally* into the command line with no warning. Scripts relying on them get curly braces in argv.
- A bare `{files}` (v1 alias for all files) now behaves as a file template matching nothing: the whole command **silently skips** with `(skip) no files for inspection`, rc 0. Migrate every `{files}` to `{all_files}`.
- `templates:` top-level keys define custom placeholders (`{dip:` etc.); a `lefthook-local.yml` (companion config for personal overrides) filling them measured working.

Example of the working pair (one base commit first — zero-commit repos fail some run paths):

```bash
cd "$(mktemp -d)" && git init -q -b main . && git config user.email t@t && git config user.name T &&
echo base > b.txt && git add b.txt && git commit -qm base &&
printf 'pre-commit:\n  commands:\n    t1:\n      run: echo T1={staged_files}\n    t2:\n      run: echo T2={staged_files_json}\n' > lefthook.yml &&
lefthook install && echo x > f.txt && git add f.txt &&
out="$("$HOME/.local/bin/lefthook" run pre-commit --colors off)" &&
printf '%s' "$out" | grep -q 'T1={f.txt}' &&
printf '%s' "$out" | grep -q 'T2={staged_files_json}' &&
echo "ok template-matrix"
```

(`t2` *runs* — literal passthrough is not an error — which is why the silent-skip `{files}` and the literal `_json` variants are easy to ship without noticing.)

## Skipping — documented forms that work, and one that doesn't

Measured at hook level and command level, against the current upstream `docs/configuration/skip.md`:

- `skip: true` (boolean) works: hook → `pre-commit (skip) hook setting` + `summary: (skip) empty`, rc 0; command → `t (skip) by condition`.
- Bare string `skip: merge` works at both levels (measured during a real `git merge --no-ff --no-commit`). Other documented values: `rebase`, `merge-commit`.
- List form `skip: [- ref: main]` works; values accept **globs** (`ref: "dev/*"` correctly did not match `main`). Hook-level skip means the whole group is skipped.
- Command-level `skip: [- run: 'test ${SKIP_ME} -eq 1']` works: the command runs while `test` fails and shows `(skip) by condition` when it succeeds (measured both ways).
- The **v1-era dict form** `skip: {ref: main}` or `skip: {merge: true}` at hook level is **silently inert** on 2.2.2: the command runs, rc 0, no warning — measured through both a manual `lefthook run` and a real `git commit`. If old configs "stopped skipping", rewrite to the list/string forms above.

The skip reasons echo distinct strings — `hook setting`, `by condition`, `no matching staged files` (templates/glob matched nothing), `broken pipe` (see below) — usable for asserting behavior in tests.

## piped vs parallel

- Default: commands run in parallel; all still run when one fails, summary collects `✗` lines, rc 1.
- `piped: true` runs groups/commands **sequentially in config order** and on failure aborts the rest: measured `third (skip) broken pipe` after `second` exited 3. The phrase reads like an OS error; it is lefthook's abort marker, ignore no pipes.
- rc is 1 in both modes; only the summary distinguishes.

## stage_fixed

`stage_fixed: true` on a command (pre-commit only) re-stages files lefthook can attribute: a *tracked, staged* file whose contents the command modified came back fully staged (`M  a.txt`, nothing unstaged, measured). A **brand-new file the command creates is not staged** — it stayed `??` (measured). Formatters that reformat staged files compose; generators that emit new files still need an explicit `git add` (e.g. chain `git add {staged_files}` yourself or rely on `stage_fixed` only for in-place edits).

## Output control — measured

- Color boxes (truecolor frame lines like `│ 🥊 lefthook  v2.2.2 … │`) are emitted **even when stdout is piped** — verified with `od -c`. In scripts/CI use `lefthook run <hook> --colors off` (or `--no-tty`); `--colors` takes `on|off|auto`, default auto.
- `LEFTHOOK_OUTPUT` restricts printed sections, measured: `meta` → banner only; `execution`/`success` → nothing when everything skipped; `summary` → just `summary: (done in ...)` + result rows.
- `LEFTHOOK=0` (or the wrapper pre-check) = complete silent skip, rc 0, even on a direct binary call. `LEFTHOOK_VERBOSE=1` adds debug logs.

## validate / dump / check-install / uninstall

- `lefthook validate` → `All good` rc 0 on a parseable config; a real YAML error (`tab` char) → rc 1 `Error: yaml: ...`; **no config at all** → rc 1 with the search-name list `["lefthook" ".lefthook" ".config/lefthook"]` — that is the config-discovery truth, plus extensions.
- `lefthook dump` prints the merged config; `--format yaml|json|toml` all measured, unknown format fails closed rc 1 naming the supported set.
- `lefthook check-install` → rc 0 iff lefthook's own wrappers are installed; rc 1 when the hook name is taken by a foreign script or hooks were uninstalled.
- `lefthook uninstall` → rc 0, deletes owned wrappers (foreign hooks untouched).

## Recipes

All recipes are self-contained and use the installed path from the first recipe.

Install the release binary with checksum verification:

```bash
cd "$(mktemp -d)" &&
curl -f -sL -o lh.gz "https://github.com/evilmartians/lefthook/releases/download/v2.2.2/lefthook_2.2.2_Linux_x86_64.gz" &&
curl -f -sL -o lefthook_checksums.txt "https://github.com/evilmartians/lefthook/releases/download/v2.2.2/lefthook_checksums.txt" &&
grep -F "lefthook_2.2.2_Linux_x86_64.gz" lefthook_checksums.txt | sha256sum -c - &&
gunzip -kf lh.gz &&
mkdir -p "$HOME/.local/bin" &&
install -m 755 lefthook_2.2.2_Linux_x86_64 "$HOME/.local/bin/lefthook" &&
"$HOME/.local/bin/lefthook" version &&
echo "ok install"
```

Smoke-test hook install → manual run → uninstall round-trip:

```bash
cd "$(mktemp -d)" && git init -q -b main . &&
git config user.email t@t && git config user.name T &&
echo base > b.txt && git add b.txt && git commit -qm base &&
printf 'pre-commit:\n  commands:\n    hello:\n      run: echo HOOK_RAN\n' > lefthook.yml &&
"$HOME/.local/bin/lefthook" install &&
echo x > f.txt && git add f.txt &&
out="$("$HOME/.local/bin/lefthook" run pre-commit --colors off)" &&
printf '%s' "$out" | grep -q HOOK_RAN &&
"$HOME/.local/bin/lefthook" check-install &&
"$HOME/.local/bin/lefthook" uninstall &&
[ ! -f .git/hooks/pre-commit ] &&
echo "ok round-trip"
```

Validate + dump-format matrix (including the expected-failure arm):

```bash
cd "$(mktemp -d)" && git init -q -b main . &&
git config user.email t@t && git config user.name T &&
echo base > b.txt && git add b.txt && git commit -qm base &&
printf 'pre-commit:\n  commands:\n    t:\n      run: echo ok\n' > lefthook.yml &&
"$HOME/.local/bin/lefthook" validate &&
"$HOME/.local/bin/lefthook" dump --format json | grep -q pre-commit &&
"$HOME/.local/bin/lefthook" dump --format toml | grep -q 'run = ' &&
printf 'pre-commit:\n\tbroken: [\n' > lefthook.yml &&
if "$HOME/.local/bin/lefthook" validate; then echo "unexpected pass"; exit 1; fi &&
echo "ok validate-matrix"
```

Skip and kill-switch matrix (boolean skip, env kill, unknown-hook error):

```bash
cd "$(mktemp -d)" && git init -q -b main . &&
git config user.email t@t && git config user.name T &&
echo base > a.txt && git add a.txt && git commit -qm base &&
echo x >> a.txt && git add a.txt &&
LH="$HOME/.local/bin/lefthook" &&
printf 'pre-commit:\n  skip: true\n  commands:\n    t:\n      run: echo NEVER\n' > lefthook.yml &&
out="$($LH run pre-commit --colors off)" &&
printf '%s' "$out" | grep -q '(skip) hook setting' &&
[ -z "$(LEFTHOOK=0 $LH run pre-commit --colors off)" ] &&
printf 'pre-commit:\n  commands:\n    t:\n      run: echo NEVER\n' > lefthook.yml &&
if $LH run no-such-hook >/dev/null 2>&1; then echo "unexpected pass"; exit 1; fi &&
echo "ok skip-matrix"
```

piped abort semantics (second fails, third never runs, rc 1 overall):

```bash
cd "$(mktemp -d)" && git init -q -b main . &&
git config user.email t@t && git config user.name T &&
echo base > a.txt && git add a.txt && git commit -qm base &&
echo x >> a.txt && git add a.txt &&
LH="$HOME/.local/bin/lefthook" &&
printf 'pre-commit:\n  piped: true\n  commands:\n    first:\n      run: echo ONE\n    second:\n      run: exit 3\n    third:\n      run: echo THREE\n' > lefthook.yml &&
out="$($LH run pre-commit --colors off)" ; rc=$? &&
printf '%s' "$out" | grep -q '(skip) broken pipe' &&
printf '%s' "$out" | grep -q 'exit status 3' &&
[ "$rc" -eq 1 ] &&
echo "ok piped-abort"
```

## Version honesty

Everything above was measured only on **v2.2.2** (official release binary, sha256 `2b8d7fd5...` vs the release `lefthook_checksums.txt`; conda-forge 2.2.2 build `--help`-identical). lefthook moves fast (v1→v2 renamed semantics that still silently run), so before quoting a specific flag, banner or skip-reason string to a stranger, re-measure against the newest release with `lefthook version` and `lefthook run <hook> --colors off` on a scratch repo.
