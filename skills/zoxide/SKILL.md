---
name: zoxide
version: 1.0.0
description: "Directory-frecency jumps: install and init zoxide, the z/zi decision flow, the exact keyword-matching rule (last keyword must occur inside the final path component), score tiers and the SUM-OF-RANKS MAXAGE prune, exclude globs, bincode DB internals with 0.9-to-0.10 cross-compat, scripting zoxide non-interactively (query/add/remove/import), and the fzf-driven edit TUI. Use when a jump misses or ranks oddly, when migrating z/autojump/atuin histories, or scripting zoxide."
---

# zoxide (0.10.0)

A smarter `cd`: zoxide records every directory you visit and lets `z`/`zi` (shell
hooks) jump to a recorded path by keywords, ranked by a frecency score. The binary
never changes directory itself — it only prints paths; the shell hook does the
`cd`. Everything below was measured live on the official **0.10.0** release
(x86_64-unknown-linux-musl tarball + the official `.deb`, whose extracted binaries
are **byte-identical**, sha256 `0959b169…`) and re-run behavior-identically on the
conda-forge 0.10.0 build; Linux-specific notes cross-checked against the pinned
v0.10.0 source tree. Divergences measured on Ubuntu noble's **0.9.3** build are in
their own section. For the fuzzy-finder semantics zoxide embeds, see the `fzf`
skill.

## Install and init

1. Get the binary: the official release tarball or `.deb` (both sha256-identical),
   or `conda install -c conda-forge zoxide`. Distro builds lag (noble: 0.9.3).
2. Verify: `zoxide --version` → `zoxide 0.10.0`.
3. Wire the shell: `eval "$(zoxide init bash)"` at the **end** of `~/.bashrc`.
   Supported shells (from `zoxide init --help`): `bash`, `elvish`, `fish`,
   `nushell`, `posix`, `powershell`, `tcsh`, `xonsh`, `zsh`.
4. Every subcommand's `--help` carries the full env-var contract — the binary
   self-documents; trust it over blog posts.

Init flags:
- `--cmd j` — the two commands become `j`/`jj` (hook still records visits).
- `--no-cmd` — no commands defined; alias `__zoxide_z`/`__zoxide_zi` yourself.
- `--hook pwd|prompt|none` (default `pwd`): `pwd` adds the current directory when
  it **changed since the last prompt**; `prompt` adds the current directory at
  **every** prompt (re-visit = rank growth every prompt); `none` records nothing.

### The hook's mechanics (bash flavor, read from `zoxide init bash` output)

- The hook is appended to `PROMPT_COMMAND` at init time and adds the current
  directory only when it differs from the last added one, calling
  `command zoxide add -- "<dir>"`.
- **The add is gated on `[[ -o history ]]`** — a shell with history disabled
  (`set +o history`) records *nothing*, silently, while `z` still works on stale
  data. Diagnose a never-growing database by checking history first.
- Adds happen when a **prompt is rendered**, not per command. Commands that run
  entirely during startup (`.bashrc` itself, `bash -i --rcfile` scripts that end
  in `exit`) never hit a prompt, so those directories are never added — measured:
  an rcfile that `cd`s twice and exits yields an empty database.
- Do not wrap the init `eval` — the un-`eval`ed output of `zoxide init bash`
  defines the hook and the `z`/`zi` functions; sourcing its raw text also works.

## The `z`/`zi` decision flow (read from the bash hook)

1. `z` with **no arguments** → `cd ~` literally (no DB, no query).
2. `z -` → `cd $OLDPWD`.
3. `z <dir>` where a plain `cd -- <dir>` would succeed → **literal `cd`**. The
   database is never consulted: `z /usr/lib`, `z .` and `z ~/existing` do not add
   rank or offer alternatives. Only if the literal `cd` fails does it fall
   through to the query path.
4. `z -- <path>` → forces the literal-`cd` branch even if that path is only a
   keyword in your DB.
5. `z <words>...` → `zoxide query --exclude "$(__zoxide_pwd)" -- <words>` and
   `cd` into the printed result. Queries that match only the current directory
   fail with `zoxide: you are already in the only match` (rc 1) instead of a
   pointless same-dir `cd`; other failures print `zoxide: no match found`
   (stderr) and leave the cwd unchanged — there is no fallback prompt.
6. `zi <words>...` → `zoxide query --interactive -- <words>` and `cd`s into the
   picked result.
7. Completions (bash ≥4.4 with readline and `TERM != dumb`): `z <TAB>` completes
   directories with `compgen -A directory`; a trailing **space** then `<TAB>`
   runs the interactive query and splices the result through a `z#`-prefixed
   protocol. On non-interactive shells the whole block is inert.

Because `z <dir>` cds literally whenever `cd` would, keyword matching is only
exercised for names that are *not* directly reachable from where you are — that
is the reason `z` results from your `$CDPATH` also work (`z` inherits `cd`'s
`CDPATH` handling on the literal path).

## Keyword matching rules (measured + source test vectors)

Keywords are **case-folded** on both sides (`case`, `CASE` both match
`Alpha2/Case`). For `zoxide query k1 k2 ... kn`:

1. **The last keyword `kn` must occur inside the final path component** — the
   text after its match position may not contain a `/`. `query fo` on
   `/foo/bar` fails (`fo` matches but the remainder `o/bar` has a separator);
   `query ba` on `/foo/bar` matches.
2. **Each earlier keyword must occur, right-to-left, before the previous
   keyword's match** — keyword **order matters**, and matches may not overlap:
   `query alpha lph beta` on `/alpha/beta` **fails** (the `lph` match overlaps
   `alpha`'s).
3. A keyword ending in `/` (`alpha2/`) requires a component *after* that
   position: `alpha2/` matches `/alpha2/Case` but not `/alpha2` itself
   (trailing-slash "children only" intent); a bare `/` keyword acts as an
   explicit component boundary.
4. A keyword spanning exactly one component boundary (`oo/ba`) is a single
   in-order match.

Practical shapes (all measured against a fixture tree):
- `query dir` → matches `/other/dir` (final component) but **not** `/dir/echo`.
- `query dir echo` → matches `/dir/echo` (dir first, echo in the final piece).
- `query alpha gamma` → matches `/alpha/gamma`; `query gamma alpha` → nothing.
- `query t` substring-matches mid-component (`alpha/beta`).

Output shapes: bare `query` prints exactly the best match (+ newline); `-l`
lists every match one per line; `-s` prefixes a score column
(`{score:>6.1}` + a space, e.g. ``  24.0 /path``); no-match is rc 1,
`zoxide: no match found`. `query --exclude <path>` skips one exact path from
results; `--base-dir <path>` restricts results to that subtree's children
(a plain `Path::starts_with` prefix — the base dir itself is not checked for
existence).

## Scores, ages and pruning

- Each entry has a float `rank`. `add` bumps it by the score value (`--score K`
  **increments** an existing entry by K and *sets* it for a new one; default 1.0;
  rank never goes below 0 — negative imports clamp to display 0.0).
- The displayed score is `rank × time-tier`, where the tier depends on how long
  ago the entry was last touched: **×4** under 1 hour, **×2** under 24 hours,
  **×0.5** under 7 days, **×0.25** beyond a week (measured: rank 8 at 30 min →
  `32.0`; rank 2 at 60 days → `0.5`; rank 3 at 120 days → `0.8` after rounding;
  rank 5 at 100 days → `1.25` → `  1.2`-style display). Display only: the column
  is clamped to 9999.0 (an imported rank of 50000 shows as `9999.0`), the sort
  still knows the real value.
- **`_ZO_MAXAGE` is a ceiling on the SUM of all ranks, not an age in days.** On
  every write operation (add/import; *remove does not age*), if
  `sum(ranks) > _ZO_MAXAGE` (default 10000), every rank is scaled by
  `0.9 × maxage / sum`, and any entry whose scaled rank drops below 1.0 is
  **deleted**. Measured: ranks 2+2+8+1 (sum 13) under `_ZO_MAXAGE=5` → factor
  0.346 → the rank-8 entry survives at 2.77, everything else is deleted; with
  maxage 3 → factor 0.2077 → only the rank-8 entry survives at ~1.66. Re-adds
  after an aging pass grow the rank again from the small base.
- Deleted directories: the default query filters entries whose path no longer
  exists; `-a/--all` shows them again — **but only until they are pruned**. Any
  entry whose directory is gone *and* whose `last_accessed` is older than a
  90-day TTL (3 × 30-day months) is **lazily removed during the next default
  query**, which then silently rewrites db.zo (sorted, pruned). Measured: a
  directory touched `<90d` ago vanishes from results but reappears via `-a`; a
  one touched `>90d` ago disappears permanently on the first default query even
  from `-a`. Consequences: a `query` is not read-only (it can mutate the file);
  to inspect stale data before pruning, use `-a` and never run a default query
  against that database again.

## Database internals

- Location: `$XDG_DATA_HOME/zoxide/db.zo` (falling back to
  `$HOME/.local/share/zoxide/db.zo`), or exactly `$ZO_DATA_DIR` when set.
  `_ZO_DATA_DIR` replaces the whole directory path and **must be absolute**
  (relative value → rc 1 `zoxide: _ZO_DATA_DIR must be an absolute path`). The
  directory is created on demand; `db.zo` appears on the first *write*.
- Format: **bincode-serialized, not text** — a leading version `u32`
  (little-endian `03 00 00 00` on both 0.9.3 and 0.10.0) followed by the entry
  vector, capped at 32 MiB. You cannot read (or hand-edit) it; use `query`,
  `edit` or an import to fix data.
- Version wall: a database with an unknown leading version — including a
  corrupted one — fails **rc 1** with
  `zoxide: unsupported version (got N, supports 3)` for *any* query/add/remove,
  and the file is left untouched (measured with a doctored header). There is no
  auto-migrate or salvage path.
- Cross-version compat: **0.9.3 ↔ 0.10.0 interoperate** — measured round-trip
  writes, reads and adds by both binaries on the same `db.zo` (both embed
  version 3). Unlike some tools' caches, mixing these two zoxide builds is safe.
- Writes are atomic (`tmp_XXXX` file in the data dir + rename, owner preserved).

## `zoxide edit` — an fzf TUI, not an editor

`zoxide edit` does **not** read `$EDITOR`. It spawns its own fzf UI listing the
database as `score<tab>path` lines with header/label (`zoxide-edit`,
`ctrl-r:reload`, `ctrl-d:delete`, `ctrl-w:increment`, `ctrl-s:decrement`,
`enter:abort`) and a directory-preview window (`command -p ls -Cp
--color=always --group-directories-first {2..}`). The key bindings call hidden
subcommands — `zoxide edit reload|delete|increment|decrement {2..}` — which
print the (re-sorted) database back to fzf as NUL-terminated lines. Measured:
TUI boots, `Enter` aborts, ESC exits **130 silently**. Requires fzf on PATH;
without it → rc 1 `zoxide: could not find fzf, is it installed?` (same for
`query --interactive`; `$EDITOR` is irrelevant in every case).

## remove — and the discard trap

- `zoxide remove <PATH>...` matches the **exact stored string** first, then
  retries with the resolved-absolute form, so relative args work (`remove
  alpha/beta` from `/parent`). Nothing exists-on-disk is special: a path present
  on disk but absent from the DB fails rc 1 `path not found in database: X`
  (distinct from add's `not a directory: X`).
- **Multiple paths are not transactional-safe for partial results**: the database
  is saved once at the end, so when path #N fails, *all* removals from that
  invocation (including earlier, successful ones) are discarded. Measured: `remove
  x missing` → rc 1 and `x` still in the database. In scripts, remove one path
  per invocation or pre-check membership with `query`.
- The same end-gated save governs `add` with multiple paths: a bad path aborts
  the whole call after earlier adds were applied in memory (source-verified —
  same save discipline).

## add

- `zoxide add [PATHS]...` — multiple positional paths; relative ones resolve
  against the cwd and are stored absolute; `.` and `x/.` normalize.
- Nonexistent path → rc 1 `not a directory: X` (aborts the call; see above).
- Paths containing `\n`/`\r` are silently skipped (unprintable-on-one-line
  guard).
- `--score K` — the rank to **increment** by (existing) or initialize with
  (new).
- **There is no stdin mode**: `zoxide add -` treats `-` as a literal relative
  path and fails `not a directory: <cwd>/-` (measured — scripts from older
  zoxide write-ups that pipe into `add -` break both here and on 0.9.3).
- `_ZO_EXCLUDE_DIRS` entries are skipped *silently* (rc stays 0).

## import (migration from other jump tools)

0.10.0 rewrote the interface to **per-source subcommands**; there is no file
argument — each subcommand reads its own default path (override where the
variable exists):

| subcommand | reads (default, measured where marked) | row format |
| --- | --- | --- |
| `z` | `$Z_DATA` or `~/.z` | `path\|rank\|last_accessed` |
| `fasd` | `$FASD_DATA` or `~/.fasd` (source-pinned) | same as `z` |
| `zsh-z` | `~/.z` (measured — same default as `z`) | same as `z` |
| `z.lua` | `~/.zlua` (measured) | same as `z` |
| `autojump` | `$XDG_DATA_HOME/autojump/autojump.txt` (measured) | `rank\t path`, sigmoid-normalized (source-pinned) |
| `atuin` | runs `atuin history list --format={time}\t{directory} --print0` | missing atuin → rc 1 `failed to run \`atuin\`; is it installed and on PATH?` |

- `z`/`fasd`/`zsh-z`/`z.lua` rows are **pipe-delimited path|rank|epoch**
  (split from the right, so paths containing `|` survive); epoch is seconds.
- Bad rows do **not** abort: each prints `<file>:<line>: invalid entry: <line>`
  to stderr and the rest of the file still imports (measured rc 0 with mixed
  good/bad rows). Future-dated epochs import fine (age math saturates at the
  recent tier — measured).
- **Refusal guard**: importing into a *non-empty* database without `--merge`
  does nothing and exits rc 1 `current database is not empty, specify --merge
  to continue anyway` — checked before the source is even read (a missing
  source file reports that same line instead of a file error when the target
  DB is non-empty). On an empty DB the import proceeds without `--merge`.
- `--merge` adds rows *on top of* existing data, then deduplicates (sums ranks
  of same-path entries, keeps the newest `last_accessed`) and ages the result —
  measured: rank 1 now + imported 0.5 old → one entry, rank 1.5.
- `_ZO_EXCLUDE_DIRS` globs filter import rows too.

## Environment variables (all measured)

| var | value contract |
| --- | --- |
| `_ZO_DATA_DIR` | full data directory, **absolute** required; overrides `$XDG_DATA_HOME` |
| `_ZO_MAXAGE` | integer (u32); invalid value → rc 1 `unable to parse _ZO_MAXAGE as integer: abc` with a `Caused by: invalid digit found in string` chain; ceiling on the **sum of ranks** |
| `_ZO_EXCLUDE_DIRS` | **colon-separated** list of glob patterns matched against full stored paths (glob crate syntax: `*` stays within a component, `**` crosses); bad glob fails **every** add/query rc 1 `invalid glob in _ZO_EXCLUDE_DIRS: ...` — fail-closed, nothing is stored while it is set |
| `_ZO_RESOLVE_SYMLINKS` | `1` only (the string `true` does nothing — measured); `=1` → `add` stores the canonicalized target, default stores the symlink path itself |
| `_ZO_ECHO` | `1` only — **vestigial in 0.10.0**: the help text advertises printing the matched directory before navigation, but no shell flavor's init script reads it beyond a comment; setting it changes nothing (measured with `z` jumps) |
| `_ZO_FZF_OPTS` | replaces zoxide's default fzf argument set, passed as `FZF_DEFAULT_OPTS`; the universal fzf args (`--read0`, `--nth=2`, `--delimiter=\t`) always remain — measured an added `--select-1` auto-accepting the sole match |
| `_ZO_DOCTOR` | shell-side only (bash init); `0` silences the hook-configuration warning |

## fzf interactivity (needs the `fzf` binary)

- `query -s`-style scoring lines are formatted `score\tpath` with `--read0` so
  NUL-delimited rows feed fzf; `--nth=2` makes the search examine only the path
  column.
- No-TTY + empty input: rc 1 `zoxide: no match found` (fzf treats the empty
  pipe as zero candidates). Missing fzf: rc 1 `could not find fzf, is it
  installed?`. On a real TTY: the interactive UI; **ESC exits 130 silently**
  (fzf's 130 passes straight through); a selection prints the bare path.
- Exit-code taxonomy to script against: **0** ok, **1** no-match / fzf absent /
  fzf-no-match / refusals, **2** usage errors (unknown flag/subcommand — the
  parser also emits suggestions like `tip: a similar argument exists:
  '--score'`), **130** user-abort passthrough.

## Divergence row — Ubuntu noble ships 0.9.3

Measured on `noble/universe` zoxide **0.9.3-1** against 0.10.0:

- `query`: `--score`/`-s`, `--exclude` and `--base-dir` are 0.10.0 additions
  (0.9.3 refuses them with an rc 2 clap error, sometimes with a
  `tip: a similar argument exists: '--score'` hint); `-a/-i/-l` behave
  the same on both.
- `add`: no `--score` in 0.9.3 (help lists only `-h/-V`).
- `import`: old syntax — `zoxide import --from <TYPE> <PATH>` (measured:
  `--from z <file>` works and shares the same pipe row format; per-source
  env-var routing is a 0.10.0 feature).
- `edit`: exists in 0.9.3 with the same fzf-driven shape (help identical).
- Database: same version-3 bincode format — no cache break between these two.
- What stayed true on both: `add` has no stdin `-` mode; `query -l/-r`-style
  flags from older tutorials don't exist (`-r`/`-f` were never these flags in
  either build — don't trust old blog posts).

## Verify the install (run this after setup)

Measured to exit 0 on clean scratch state (needs only the binary on PATH and a
writable temp dir; deliberately stdin-safe — no pipe is read):

```bash
set -eu
Z="$(mktemp -d)"
export _ZO_DATA_DIR="$Z/db" HOME="$Z/home" XDG_DATA_HOME="$Z/x"
mkdir -p "$_ZO_DATA_DIR" "$HOME" "$XDG_DATA_HOME"
mkdir -p /tmp/zv-probe/one /tmp/zv-probe/one/two /tmp/zv-probe/other/tree
cd /tmp/zv-probe
zoxide add one/two other/tree
[ -f "$Z/db/db.zo" ]                          # db materialized under _ZO_DATA_DIR
test "$(zoxide query two)"     = /tmp/zv-probe/one/two   # last keyword = final component
test "$(zoxide query one two)" = /tmp/zv-probe/one/two   # ordered two-keyword rule
zoxide query two one >/dev/null 2>&1 && { echo "FAIL: keyword order ignored"; exit 1; }
zoxide remove /tmp/zv-probe/one/two
test "$(zoxide query -l two)" = ""           # -l on no-match: rc 0, empty output
rm -rf "$Z" /tmp/zv-probe
echo zoxide-verified
```