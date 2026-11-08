---
name: watchexec
version: 1.0.0
description: "Use when a build, test, lint, reload or sync loop should rerun on file changes — watchexec instead of hand-rolled sleep/poll loops — or when a script must react to filesystem events. Includes the default-shell join trap that silently rewrites sh -c commands, the self-trigger loop from commands writing into the watched tree, per-mode busy behavior, the ignore-discovery matrix, the measured JSON event schema and the exit taxonomy. Measured live on the official 2.8.0 binary."
---

# watchexec — run commands on file changes, with the traps measured

watchexec (watchexec/watchexec, Apache-2.0; the `watchexec-cli` crate, authors
Félix Saparelli and Matt Green) recursively watches paths and executes a
command when events pass its filters. Everything below was measured on the
**official 2.8.0 release binary** (`watchexec-2.8.0-x86_64-unknown-linux-gnu.tar.xz`,
sha256-verified against the release's `SHA256SUMS`).

## Install and verify

- Release binary: extract the `tar.xz` — the executable sits at the **root of
  the tarball**, not in `bin/`. `cargo install watchexec-cli` is the from-source
  route. conda-forge ships `watchexec` with the same version; the Ubuntu
  24.04 archives have no package.
- Cross-check that matters: the conda-forge 2.8.0 build carries a **byte-identical
  `--help` (851 lines) and `--completions bash`** (md5-equal to the release
  binary; only the embedded build commit hash differs).
- `watchexec --version` prints `watchexec 2.8.0 (<commit> <date>) +pid1` plus
  the commit-date/build-date/features lines.

## Core loop

- The command runs **once at startup** and then again on every event batch that
  survives filtering. `-p`/`--postpone` removes the startup run entirely
  (measured: no run until the first change).
- Events are debounced. The default is **50 ms**; `-d` takes span values
  (`200ms`, `2s`). Passing a bare unitless number (`-d 50`) works but emits
  `Warning: unitless non-zero time span values are deprecated and will be
  removed in an upcoming version` — note `-d 0` is exempt (only non-zero
  unitless values warn).
- Bursts coalesce: three files touched within one debounce window produce
  **one** run.
- The watcher never exits on its own. A live `watchexec` that is forgotten
  keeps running forever — always bound your probes (`timeout …`).

## The join trap — read this before writing any command

With the default shell mode (`--shell` defaults to `$SHELL`, falling back to
`sh`), the command arguments are **joined into one string and handed to
`sh -c`**. Argument boundaries silently disappear:

- `watchexec -- sh -c 'echo RAN'` becomes the string `sh -c echo RAN` — that
  runs `echo` with `$0=RAN` and prints **nothing** (measured: the marker file
  stayed empty while `[Running]` reported 26 completions).
- A compound command passed as separate words splits at the outer level:
  `watchexec -- sleep 4; echo X` measures as
  `[Running: sleep 5; echo X]` followed by `sleep: invalid time interval`
  — the `echo` becomes a separate outer-shell statement that runs every cycle,
  and the inner sleep never sleeps.

The fix is `-n` (`--shell=none`): the command is passed to `execvp` directly
(`watchexec -n -- sh -c 'sleep 4; echo done'` works exactly as written).
`-Q`/`--quote` parses but is ignored on Linux (always treated as true).

## The self-trigger trap

A command that **writes into the watched tree** re-triggers itself: the write's
event lands after the (fast) command has completed, right past the busy window,
so the runs feed themselves. Measured: `echo L >> self.txt` inside the watch
root looped **49 runs in 2.6 s** under the default do-nothing mode — do-nothing
only drops events that arrive *while* the command runs; it does not stop a
write that lands after completion. Signal mode is the worst affected: the same
self-feeding loop delivered 35+ signals (one per re-trigger, forever).

- Guard: write artifacts **outside** every watched root. The same command with
  the log moved outside the watch tree ran exactly once.
- `-i '*.log'` (etc.) also works if the artifact names are stable, but outside
  roots are the robust default.

## Busy state: what happens when events arrive mid-run

`-o`/`--on-busy-update`, all measured:

| Mode | Behavior |
| --- | --- |
| `do-nothing` (default) | Events during the run are dropped. Measured: a 1.2 s run plus a change 0.4 s in → no second run. |
| `queue` | After the current run ends, one queued rerun. Measured: startup + touch during the run → exactly 2 completions. |
| `restart` (`-r`) | The busy child is terminated (it runs in a process group) and a new run starts. Measured: startup `sleep 2` killed at 0.3 s never wrote its post-sleep marker; the restarted run did — 1 completion, 2 `[Running]` lines. |
| `signal` (implied by `-s <SIG>`) | Sends the signal to the running command's process group, once per debounced batch (measured: one touch → one delivery; three fast touches → one delivery). Useful for config reloads via `SIGHUP`/`USR1` — a trapped child kept receiving reloads while the watcher stayed up. |

Lifecycle knobs around it (defaults from the long `--help`):
`--stop-signal` (default `SIGTERM`; names, short names and numbers parse
case-insensitively), `--stop-timeout` (default 10 s, `0` force-kills at once),
`--timeout <span>` per run — a runaway `sleep` under `--timeout 400ms` prints
`[Command timed out after 400ms]` and the watcher keeps watching.

## Filtering

- `-e`/`--exts`: extension allow-list, comma-separated or repeated, with or
  without the leading dot (`-e js` and `-e .js` are equal). Measured: a `.c`
  change is invisible under `-e txt`; a `.txt` change runs.
- `-f`/`--filter` glob include, `-i`/`--ignore` glob exclude (repeats and
  `--filter-file`/`--ignore-file`, one pattern per line, `#` comments).
  Filter-program (`-j`) events pass both untouched.
- `--fs-events` picks event kinds; default is **all except `access`**.
  `--no-meta` is the shorthand for dropping metadata events and conflicts with
  `--fs-events` (clap refuses: `error: the argument '--no-meta' cannot be used
  with '--fs-events <EVENTS>'`, exit 2).
- `-w`/`--watch` adds roots (default: the current directory, recursive);
  `-W`/`--watch-non-recursive` does not descend (measured: a change in a
  subdirectory produced nothing, a change one level up ran). `-F`/`--watch-file`
  reads roots from a file, `-` for stdin — and `-` + `--stdin-quit` is refused
  at parse time (`error: stdin-quit cannot be used when --watch-file=-`, exit 2).
  The special value `-w /dev/null` watches **nothing** on purpose: the process
  stays alive on signals, stdin or interactive keys.
- Precedence per the help: internal priority (signals first) → event kind →
  explicitly watched paths → ignores → filters → filter programs.

## Ignore discovery (project files work without git)

- Built-in defaults: editor swap files, `*.pyc`, `*.pyo`, `.DS_Store`, and the
  VCS metadata dirs (`.git`, `.hg`, `.svn`, `.bzr`, `_darcs`, `.pijul`,
  `.fossil-settings`). Measured: writes to `.pyc`/`.DS_Store` trigger nothing;
  `--no-default-ignore` flips them back on.
- Project-local files are honored **even outside a git repository**:
  a `.ignore` file in a non-git directory kept its target quiet (measured); a
  project `.gitignore` did the same when git was present.
- Overrides: `--no-vcs-ignore` restarts the ignored files (measured trigger
  came through), `--no-project-ignore`, `--no-global-ignore`,
  `--ignore-nothing` (both discovery and defaults off),
  `--no-discover-ignore`. Global ignores come from git's
  `core.excludesFile`/`~/.gitignore` chain and watchexec's own
  `~/.config/watchexec/ignore` — see `--help` for the full locations list.

## Events for programs

`--emit-events-to` picks where the triggering event batch is delivered
(default `none`):

- `stdio` — text lines to the command's stdin, one per path, prefixed
  `create:`/`remove:`/`rename:`/`modify:`/`other:` (measured line:
  `create:/abs/path`, plus a directory-level `modify:` for the touched dir).
- `file` / `json-file` — a temp file; the command reads it via
  `$WATCHEXEC_EVENTS_FILE` (measured: the variable is set to a real path).
- `json-stdio` — one JSON event per line on the command's stdin.
- `environment` (legacy, deprecated by the help but silent at runtime) — sets
  `WATCHEXEC_COMMON_PATH` plus `…_CREATED_PATH`, `…_WRITTEN_PATH` (etc.).
  Measured: the paths are **relative to the common path**; a plain append set
  both `CREATED_PATH` and `WRITTEN_PATH` for the same file.
- `--only-emit-events` runs **no** command and prints the JSON stream to
  stdout (implies `json-stdio`; `--emit-events-to=stdio` downgrades to text).
  Measured event line shape:
  `{"tags":[{"kind":"source","source":"filesystem"},{"kind":"fs","simple":"create","full":"Create(File)"},{"kind":"path","absolute":"...","filetype":"file"}]}`
  — a single file append produced that create event **plus** a companion
  `modify` event for the parent directory, so expect directory events riding
  along.
- `-j`/`--filter-prog` runs custom filter programs in jaq (jq-like) syntax
  against the event JSON — the strongest tool in the box for precise triggers.
  Measured: a create-only program (`any(.tags[] | select(.kind == "fs");
  .simple == "create")`) passed the created path and filtered the modify event
  out. An invalid program fails closed at startup with exit 1 and
  `Error:   × in --filter-prog 0 / ├─▶ failed to load filter program`.
  Extra helpers beyond jaq's stdlib: `file_meta`, `file_size`, `file_read`,
  `hash`, `kv_store`/`kv_fetch`, `printout`/`log`; `@path` loads a program
  file. Programs that filter too slowly stall the stream — the help and the
  docs both warn about this.
- `--print-events` prints the batch in human form (`[EVENT n] Event
  source=Filesystem kind=Create(File) path=<abs> filetype=file`) — and it
  **requires a command**: without one, clap refuses with
  `error: the following required arguments were not provided: <COMMAND>...`
  and the usage line, exit 2.

## Shell and environments

- `--shell` selects the shell; `none` is covered above. `--shell 'zsh -x'`
  style command lines are parsed.
- `-E`/`--env KEY=VALUE` sets variables **for the command only** (measured:
  the child saw the value; the watcher side is untouched).

## Signals, exit codes, interactivity

- Sending `SIGINT` or `SIGTERM` to the watcher exits **0** in every measured
  mode (including with `--stdin-quit`) — there is no 130/143 shell convention
  here. The command's whole process group is taken down with it.
- `--stdin-quit` exits **0** when stdin closes; without a closing stdin it
  stays alive forever.
- `--map-signal TERM:INT` style pairs translate OS signals: after
  `--map-signal INT:USR1`, `SIGINT` no longer quits the watcher — the child's
  process group received `USR1` (a trapping child kept reloading) and watchexec
  kept watching. `TERM:` (empty second half) discards the signal. Mapping
  `INT`/`TERM` away removes the built-in quit path.
- `--exit-on-error` makes the watcher exit **with the command's exact status**
  (measured: exit 1 → 1, exit 7 → 7). Without it a failing command is just
  another run: failure after failure, watcher alive.
- `-I`/`--interactive` binds keys (TTY): banner
  `[Interactive] q: quit, p: pause/unpause, r: restart, s: stop`, measured
  `[Paused]`, `[Unpaused]`, and on quit
  `[Waiting 10s for processes to exit before stopping...]` then exit 0.
  Piped (no TTY) it still starts and exits 0 when stdin closes.
- Exit taxonomy, all measured:
  - **0** — clean exits: signals, `--stdin-quit` EOF, interactive `q`.
  - **1** — watchexec's own runtime errors (a missing watch path:
    `Error:   × No such file or directory (os error 2)`; a filter program that
    does not compile) — and `--exit-on-error` child failures carry the child's
    exact code.
  - **2** — clap parse errors: unknown flags, invalid enum values (the refusal
    lists `[possible values: queue, do-nothing, restart, signal]` verbatim) and
    the conflicting-flag pairs above.

## Output surface

- Lifecycle messages go to **stderr**, the child's streams stay clean:
  `[Running: <command>]` before each run, then one disposition line —
  `[Command was successful]`, `[Command exited with 1]`,
  `[Command timed out after 400ms]`, or (signal deaths) a killed variant.
  `-q`/`--quiet` silences watchexec's own lines.
- Color is **TERM-gated**: with `TERM` unset (the common state in CI and batch
  jobs) even a real TTY shows zero ANSI escapes; a pipe is always colorless by
  default; `--color=always` forces green-tinted `[Running]` lines, `NO_COLOR`
  (any value) is equivalent to `--color=never`, `CLICOLOR_FORCE`/`FORCE_COLOR`
  are ignored.
- **The `--clear` uncancellable trap**: `--clear`/`--clear=reset` writes
  `\x1b[H\x1b[2J\x1b[3J` to **stdout** even on a pipe, even with `NO_COLOR`,
  and even with `--color=never` — capture logs of clear-mode runs get raw
  cursor/erase bytes. The escapes land on stdout while the lifecycle messages
  stay on stderr.
- `--bell` appends a BEL (`\x07`) to the completion line (TTY);
  `--timings` extends the success line to
  `[Command was successful, lasted 0ms]`.
- `@argfile` as the first argument replays one-argument-per-line options
  (measured end-to-end, including `-n` and the trailing command), and
  `--completions bash|elvish|fish|nu|powershell|zsh` prints each shell's
  script; an unknown shell is a clap exit-2 refusal. `--manual` prints the
  roff manpage when piped.

## Recipes

Watch sources, rebuild once per burst, artifacts outside the watch root:

```bash
cd /path/to/project
watchexec -e rs,toml -w src -w Cargo.toml -n -- sh -c 'cargo build 2> /tmp/build.log; tail -5 /tmp/build.log'
```

Auto-reload a dev server with a graceful stop window:

```bash
watchexec -r --stop-signal INT --stop-timeout 2 -w src -- cargo run
```

React to specific events as data (no command, pure JSON consumer):

```bash
watchexec --only-emit-events -w /var/work -j 'any(.tags[] | select(.kind == "fs"); .simple == "remove")'
```

Use watchexec to gate long test loops on a quiet tree (debounce instead of
sleep-polling), and keep every watchexec invocation wrapped in `timeout` when
it runs from automation — an unbounded watcher never exits by itself.

## Related

- [`just`](skills/just/SKILL.md) — pair both: watchexec re-runs `just` recipes
  while `just` owns the recipes themselves.
- [`hyperfine`](skills/hyperfine/SKILL.md) — benchmark the command watchexec
  will run before wiring it into a loop.
- [`sd`](skills/sd/SKILL.md) — same single-binary, measure-first discipline.

## Provenance and divergences

- All behavior measured on the official 2.8.0 release binary, sha256-verified
  against the release's `SHA256SUMS`. Conda-forge's 2.8.0 build matched the
  release binary md5-for-md5 on `--help` and the bash completions, and probes
  of message shapes, both parse conflicts, `--exit-on-error` propagation, the
  `--clear` pipe trap and the unitless warning came back identical.
- Older conda builds probed for the divergence row: 2.1.1 and 2.2.0 (late
  2024) lack `-I`/`--interactive`, `--timeout`, `--socket`, `--quote` and the
  `--force-poll` alias, and both **refuse `--only-emit-events` and
  `--exit-on-error` with clap exit 2**; `--watch-file`/`-F` exists from 2.2.0.
  The `--clear` piped-trap and the join trap already exist there.
  Ubuntu 24.04's archives carry no watchexec at all, so no distro cross-check
  exists.
- Skill text is original; measured behavior only, no upstream prose adapted.

## Verify block

```bash
set -e
bin=${WATCHEXEC_BIN:-watchexec}
command -v "$bin" >/dev/null 2>&1 || bin=$(command -v watchexec)
[ -n "$bin" ] || { echo 'FAIL: watchexec not installed'; exit 1; }
"$bin" --version | head -1 | grep -F 'watchexec' >/dev/null
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
mkdir "$d/w" "$d/m"
count(){ [ -f "$d/m/$1" ] && tr -cd R < "$d/m/$1" | wc -c || true; }
# startup run + change -> exactly 2
( sleep 0.8; touch "$d/w/f1" ) &
timeout 3 "$bin" -w "$d/w" -n -- sh -c "echo R >> $d/m/a.txt" >/dev/null 2>&1 || true
[ "$(count a.txt)" -eq 2 ] || { echo "FAIL: startup+change counts, got $(count a.txt)"; exit 1; }
# postpone: no startup run, one run on change
( sleep 0.8; touch "$d/w/f2" ) &
timeout 3 "$bin" -p -w "$d/w" -n -- sh -c "echo R >> $d/m/b.txt" >/dev/null 2>&1 || true
[ "$(count b.txt)" -eq 1 ] || { echo "FAIL: postpone counts, got $(count b.txt)"; exit 1; }
# three fast touches coalesce to one run (startup + burst = 2)
( sleep 0.8; touch "$d/w/g1" "$d/w/g2" "$d/w/g3" ) &
timeout 3 "$bin" -w "$d/w" -n -- sh -c "echo R >> $d/m/c.txt" >/dev/null 2>&1 || true
[ "$(count c.txt)" -eq 2 ] || { echo "FAIL: debounce coalesce, got $(count c.txt)"; exit 1; }
# events while busy are dropped by mode do-nothing, queued by queue, and restart kills the busy child
( sleep 0.9; touch "$d/w/k1" ) &
timeout 4.5 "$bin" --on-busy-update=do-nothing -w "$d/w" -n -- sh -c "sleep 1.2; echo R >> $d/m/d.txt" >/dev/null 2>&1 || true
[ "$(count d.txt)" -eq 1 ] || { echo "FAIL: do-nothing should drop mid-run events, got $(count d.txt)"; exit 1; }
( sleep 0.9; touch "$d/w/k2" ) &
timeout 4.5 "$bin" --on-busy-update=queue -w "$d/w" -n -- sh -c "sleep 1.2; echo R >> $d/m/e.txt" >/dev/null 2>&1 || true
[ "$(count e.txt)" -eq 2 ] || { echo "FAIL: queue should rerun once, got $(count e.txt)"; exit 1; }
( sleep 0.5; touch "$d/w/k3" ) &
timeout 4.5 "$bin" -r -w "$d/w" -n -- sh -c "sleep 2; echo R >> $d/m/f.txt" >/dev/null 2>&1 || true
[ "$(count f.txt)" -eq 1 ] || { echo "FAIL: restart should kill the busy child, got $(count f.txt)"; exit 1; }
# the join trap: separate-words sh -c loses the inner argument under default shell
timeout 3 "$bin" -w /dev/null -- sh -c "echo J >> $d/m/j.txt" >/dev/null 2>&1 || true
[ "$(tr -cd J < "$d/m/j.txt" | wc -c)" -eq 0 ] || { echo 'FAIL: join trap should swallow the quoted argument'; exit 1; }
timeout 3 "$bin" -w /dev/null -n -- sh -c "echo J >> $d/m/j2.txt" >/dev/null 2>&1 || true
[ "$(tr -cd J < "$d/m/j2.txt" | wc -c)" -eq 1 ] || { echo 'FAIL: -n should pass the command intact'; exit 1; }
# --stdin-quit exits 0 on EOF; --exit-on-error carries the child code
echo x | timeout 5 "$bin" --stdin-quit -w /dev/null -q -n -- true >/dev/null 2>&1
rc=0; echo x | timeout 5 "$bin" --stdin-quit -w /dev/null -q -n -- true >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 0 ] || { echo "FAIL: stdin-quit should exit 0, got $rc"; exit 1; }
rc=0; timeout 5 "$bin" --exit-on-error -n -- sh -c 'exit 7' >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 7 ] || { echo "FAIL: exit-on-error should carry the child code 7, got $rc"; exit 1; }
# clap conflicts refuse with exit 2
rc=0; "$bin" --no-meta --fs-events modify -n -- true >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 2 ] || { echo "FAIL: --no-meta conflict rc, got $rc"; exit 1; }
rc=0; "$bin" --stdin-quit -F - -n -- true >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 2 ] || { echo "FAIL: stdin-quit + watch-file - conflict rc, got $rc"; exit 1; }
# the --clear pipe trap: escapes ride on stdout even with --color=never
esc=$(timeout 2 "$bin" -c --color=never -w /dev/null -n -- true </dev/null 2>/dev/null | tr -d -c '\033' | wc -c)
[ "$esc" -ge 1 ] || { echo 'FAIL: --clear must emit escape bytes on a pipe'; exit 1; }
# unitless debounce warns, span form is silent
(timeout 2 "$bin" -d 50 -w /dev/null -q -n -- true </dev/null 2>&1 || true) | grep -F 'deprecated' >/dev/null
(timeout 2 "$bin" -d 50ms -w /dev/null -q -n -- true </dev/null 2>&1 || true) | grep -F 'deprecated' >/dev/null && { echo 'FAIL: span debounce must be silent'; exit 1; } || true
echo watchexec-verified
```
