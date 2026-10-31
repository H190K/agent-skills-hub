---
name: procs
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
description: "Use when an agent must inspect, filter, sort, or monitor processes from scripts or terminals - a ps replacement whose default search hits Pid (exact) plus User and Command only, with AND/OR/NAND/NOR keyword logic, regex modes whose anchors never match, smart-case, tree and thread views, JSON that goes invalid under --only, TOML configs that reshape the search domain, a pager that ignores $PAGER, and watch mode that clear-screens into pipes. Measured live on v0.14.12."
---

# procs — ps with colored, sorted, tree, JSON and watch views

`procs` lists processes with adaptive columns, keyword filtering, sorting,
tree/thread views and JSON output. It is read-only — it offers **no kill/
signal flags** (pair it with `kill`/`pkill` for that). This skill documents
the behavior of the **v0.14.12 release binary** (dalance/procs, asset
`procs-v0.14.12-x86_64-linux.zip`, a static-pie musl build), every fact
measured live on that binary plus a real TTY via a pty, and cross-checked on
the conda-forge `procs 0.14.12` build (dynamic) — identical kind list,
`--gen-config` output, default header and probe results.

## Install (nothing is vendored here — install the tool, then run it)

```
curl -sSL https://github.com/dalance/procs/releases/download/v0.14.12/procs-v0.14.12-x86_64-linux.zip \
  -o "$TMPDIR/procs.zip" && unzip -o "$TMPDIR/procs.zip" -d "$TMPDIR/procs-bin"
"$TMPDIR/procs-bin/procs" --version        # procs "0.14.12 ( rev: 8ad5da5, ... )"
# other routes: `cargo install procs`, snap, per-platform release zips
# (macos arm/x64, windows x64) and an rpm; NOT in Ubuntu apt on noble
```

`--gen-completion bash` writes **`./procs.bash` into the current directory**
(and prints `completion file is generated: ./procs.bash`); use
`--gen-completion-out <shell>` to get completion straight on stdout. Supported
shells: bash, elvish, fish, powershell, zsh.

## The default view

`procs` with no arguments prints, in this order: `PID:▲  User │ TTY  CPU  MEM
CPU Time │ Command` plus a unit row (`[%]` under CPU/MEM). Measured rules:

- The leading marker is the active sort: **column 0, ascending** by default —
  so `PID:▲`; `--sortd cpu` flips it to `CPU:▼` on the sorted column.
- The `│` between User and TTY and before Command is a rendered **Separator
  column**, configurable in `[display] separator`.
- Kernel threads render as `[kthreadd]` **in the Command column** (their
  cmdline is empty — the bracketed *name* is what the substring search sees).
- Column widths adapt to content: a filtered list with no rows shows a much
  narrower header (header-only output, rc 0).
- **procs hides itself** (`show_self = false` in the config template): it
  never appears in its own list.
- **Width cutting depends on the sink.** Through a pipe the output is never
  truncated (a 2,000-char command line ships whole); on a real terminal rows
  are cut to the terminal width (60-col pty measured).
- `procs -l` lists **78 column kinds** with one-line descriptions.

## Search — the domain is narrower than the display (the #1 trap)

The default searchable set is **exactly three columns**: numeric keywords hit
`Pid`, text keywords hit `User` and `Command`. Measured consequences:

- `procs 1234` matches **pid exactly 1234** — numeric search is
  *"Exact"* (`[search] numeric_search = "Exact"`), not substring:
  pid `2` matches only pid 2, nonexistent `292` matches nothing.
- `procs h190k` returns that user's processes — **User is searched** (a kw
  matching only user values returned exactly the same pid set as `ps -u`).
- `procs kthreadd` matches pid 2 because the *Command column value* is
  `[kthreadd]` — the FileName/name column is **not** searched by default.
- `procs 'pts/2'` matches nothing — **Tty is not searched by default**.
- Searching an inserted column does not work either: `-i Tty 'pts/2'` still
  matches 0 rows. Search scope changes **only** through a config file.
- No keyword at all = full list; a keyword matching nothing = header-only
  output, rc 0 (never an error).

### Keyword logic and case

- Multiple keywords are **AND** by default (`[search] logic = "And"`).
  `-o/--or` ORs them; `-d/--nand` = NOT-all (rows matching only one keyword
  **are included**); `-r/--nor` = NOT-any (any matching row is excluded).
- **Smart case**: any uppercase letter in the keyword makes matching
  case-sensitive; an all-lowercase keyword is insensitive. Measured on the
  same machine: lower-case kw → 3 rows, `Crafty`/`CRAFTY` → 0 rows.

### The three search modes

- `--text` (default): byte-substring, regex metacharacters are **literal** —
  `sl.e` matches nothing (dot is a real dot), `.` matches rows containing a
  literal period.
- `--regex`: one single regex per invocation — passing two keywords errors
  with *error: --regex accepts a single PATTERN argument* (rc 1); an
  unbalanced pattern errors with *Parsing error at position 1: Opening
  parenthesis without closing parenthesis* (rc 1).
- **Anchors never match, even in regex mode**: `--regex '^sleep'` and
  `--regex 'sleep$'` both return **0 rows** while `--regex sleep` and
  `--regex '^.*sleep.*$'` return 3. Wrap patterns as `^.*x.*$` when you need
  explicit anchoring.
- `--smart`: auto-detects regex only when explicit syntax characters appear
  (`[s]le+` matches like the regex), while a lone `.` or `sl.e` stays a
  literal search (measured: same counts as text mode).
- Case sensitivity applies in every mode (smart-case, as above).

## Columns, only, sort, tree, threads

- `-i/--insert <kind>` appends a column. Kind names are case-insensitive
  (`-i pid` == `-i Pid`); inserting an **already present kind duplicates it**
  (two User columns); an unknown kind warns *Can't find column kind: X* on
  stderr but **continues rc 0 without the column** — check stderr, not the
  exit code.
- `--only <kind>` takes **a single kind** — any further positional argument
  silently becomes a *keyword*: `--only Pid Command` shows a PID-only table
  filtered by the literal text "Command". An unknown kind again warns rc 0;
  repeating `--only` is a clap usage error (rc 2).
- Sort: `--sorta <kind>` ascending, `--sortd <kind>` descending — **only one
  sort flag is allowed**; `--sorta user --sortd cpu` = *error: the argument
  '--sorta <kind>' cannot be used with '--sortd <kind>'* and repeating the
  same flag errors *cannot be used multiple times* (both rc 2). Kind names
  are case-insensitive, and **loose aliases resolve to nearby columns and
  append a duplicate sorted column**: `--sorta mem` appends a second `MEM`
  column and sorts it `MEM:▲`; `--sortd cpu` marks `CPU:▼` and appends a
  duplicate `CPU Time` column. A **bogus kind warns rc 0 and does not sort at
  all** — a silent no-op, the worst failure mode here.
- `-t/--tree` renders parent-child branches (`├┬───────`) instead of the flat
  list; a config `kind = "Tree"` column renders branch glyphs inline in a
  normal view, while plain `-i Tree` (a hidden kind — see below) leaves
  blank slots on non-tree rows.
- `--thread` lists per-thread rows with the **TID bracketed in the PID
  column** (`[2190]`), one row per thread.
- `--use-config large` (the only built-in alternative) expands the default
  column set: adds State, Nice, VmSize, VmRSS, TCP, UDP, Read, Write, Start...
- `--no-header` drops the header; it is ignored by `--json`.

## JSON output — with a validity trap

`--json` emits an array, **one object per line**, whose keys are the header
labels:

```
procs --json sleep
# [{"PID": 3643, "User": "h190k", "TTY": "pts/2", "CPU": 0, "MEM": 11,
#   "CPU Time": 0, "Command": "bash -c localtonet & sleep 999999"}, ...]
```

- `CPU`/`MEM` arrive as integers (tenths of a percent — `MEM: 11` = 1.1 %);
  `CPU Time` is an integer (seconds), not the `00:05:36` clock string.
- Default output **parses as valid JSON** — but `--json --only Pid` produces
  each object as `{"PID": 3643, }` with a **trailing comma: invalid JSON**
  (confirmed with `json.load` → *Illegal trailing comma*). If a config or
  `--only` trims columns, re-validate before parsing.
- `-i User` duplicating a column duplicates the JSON **key** (`"User"`
  appears twice; a parser keeps the last value).
- On a terminal `--json` bypasses both the pager and colors.

## Config files — they rebuild columns AND the search domain

`procs --gen-config` prints the complete default template (a TOML "proconf",
140 lines); piping it into `--load-config` reproduces the stock header — so
it doubles as the documentation of every knob:

- `[[columns]]` entries with `kind`, `style`, `numeric_search`,
  `nonnumeric_search`, `align`. Both search flags **default to false when
  omitted** — a one-column `Pid` config makes *every* text keyword silently
  match nothing (empty output, rc 0; likewise empty JSON). Extend search by
  setting the flag per column: a config with
  `kind = "Tty"` / `nonnumeric_search = true` makes `procs 'pts/2'` work.
- `[search]`: `numeric_search = "Exact"`, `nonnumeric_search = "Partial"`,
  `logic = "And"`, `case = "Smart"`.
- `[display]`: `cut_to_terminal = true` vs `cut_to_pipe = false` /
  `cut_to_pager = false` (the width rules above), `separator = "│"`,
  `ascending = "▲"` / `descending = "▼"`, `show_self = false`,
  `show_kthreads = true`, `tree_symbols = [...]`.
- `[style]`: header/unit/tree styles plus `by_percentage`, `by_state` and
  `by_unit` palettes (the coloring logic of CPU/MEM/State/size cells).
- `[sort]`: `column = 0`, `order = "Ascending"` (the `PID:▲` default).
- `[pager]`: `mode = "Auto"`, `use_builtin = false` — the pager is an
  external `less`, not an embedded one.
- `[docker]`: `path = "unix:///var/run/docker.sock"` for the Docker column.

Load paths, measured:

- The **auto-loaded file is `$XDG_CONFIG_HOME/procs/config.toml`**
  (default `~/.config/procs/config.toml`) — verified: relocation changed the
  header the next run.
- `~/.procs` is **NOT auto-loaded**: a valid config placed at a relocated
  `$HOME/.procs` changed nothing (the README-era path is dead in 0.14.12).
- `--load-config <path>`: missing file → rc 1 *error: failed to open file
  (...)* ; unknown kind → rc 1 with the **complete fail-closed enum list**.
  This error text is also the only place that reveals **two hidden kinds** —
  `Tree` and `Username` — which `procs -l` does not list (78 visible kinds vs
  80 enum variants). `-i Username` is rejected (*Can't find column kind*) —
  the insert validator differs from the config validator.

## Colors, theme, pager, watch

- Through a **pipe there are no ANSI codes** by default (verified byte
  counting od output): `--color auto` (the default) stays colorless when
  piped, `NO_COLOR=1` and `FORCE_COLOR=1` match that.
- Escape hatches: `-c always` forces ANSI through pipes; and uniquely
  **`CLICOLOR_FORCE=1` forces color too** (61 escape sequences measured in a
  piped run). `-c disable` removes color even on a TTY.
- `--theme dark` and `--theme light` are different palettes, measured down to
  the escape codes: dark uses 256-color sequences (`38;5;11`), light the base
  set (`33`/`32`/...).
- The pager: on a terminal, output longer than the screen pages into an
  external **`less`** (`-p auto` default; `-p always` forces even short
  output; `use_builtin = false`). **`$PAGER` is ignored everywhere** — a
  `PAGER=marker` run on a TTY showed no marker. Through a pipe the pager
  never engages for any `-p` value, and `--json` bypasses it on a TTY.
- `--watch` / `-w` (1 s) and `-W <seconds>` overlay watch mode; the status
  line reads `Interval: 2000ms, Last Updated: ... ( Next: n, Prev: p, ...)`.
  Every frame starts with **clear-screen sequences (`\033[2J`)** — emitted
  **even when piped**, so piping watch output yields escape-code soup. Watch
  runs until the process is killed (no self-exit; `timeout` returns 124).

## procfs

`--procfs <path>` re-reads processes from an alternate procfs (container /
foreign-host mounts). A **nonexistent path fails silently**: header-only
output, **0 rows, rc 0, empty stderr**. Verify the row count, not just the
exit code, when using this flag.

## Exit-code taxonomy (0 / 1 / 2 only)

- **rc 0** — normal runs, empty results, warnings on stderr (unknown kind),
  bad `--procfs`, watch frames.
- **rc 1** — runtime failures: invalid regex pattern, `--load-config` with a
  missing file or bad TOML, `--regex` given two keywords.
- **rc 2** — usage errors (clap): unknown flag, `-a` with `-o`, duplicate or
  mixed `--only` / `--sorta` / `--sortd`, bad `-W` value.

## Recipes

```
# whose process is eating CPU (user search is built in)
procs --sortd cpu | head -5            # CPU:▼ with the dup CPU Time col
procs h190k                            # everything owned by h190k
procs 1234                             # pid-exact: only pid 1234

# safe JSON pipelines (default shape is parser-clean)
procs --json --no-header | jq '[.[] | {pid:.PID, mem:.MEM, cmd:.Command}]'

# watch one process, no clear-screen junk in a log
procs -w --thread --sortd cpu sleep 2>&1 | head -3   # first frame only

# search by TTY column (config route — insert alone cannot do this)
cat > /tmp/procs-tty.toml <<'EOF'
[[columns]]
kind = "Pid"
style = "BrightYellow|Yellow"
numeric_search = true
nonnumeric_search = false
align = "Left"

[[columns]]
kind = "Tty"
style = "BrightGreen|Green"
numeric_search = false
nonnumeric_search = true
align = "Left"
EOF
procs --load-config /tmp/procs-tty.toml 'pts/2'      # now TTY search works
```

## Version notes

All behavior above was measured on **v0.14.12** (2026-06 release; upstream
master carries only dependency bumps since). The `~/.procs` path silently
absent here, the `--only` trailing-comma JSON, the anchor-breaking regex
mode, and the ignored `$PAGER` are exactly the kind of details that shift
between releases — re-probe them on any version bump.