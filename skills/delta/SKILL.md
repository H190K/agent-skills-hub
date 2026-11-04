---
name: delta
version: 1.0.0
description: "Use when rendering a git diff, patch or two-file diff for a human: install delta (release binary byte-identical to the official .deb), the stdin-only input model with silent positional two-file mode, why color persists in pipes while the auto pager withholds TTY output past one screen, light/dark and TERM-driven color depth, side-by-side and navigate layouts, the gitconfig feature system, config resolution traps, and exit codes. Use when a diff renders monochrome or a pager stalls a script."
---

# delta (0.20.1)

A pager for diffs: feed it diff text on stdin and it renders the changes with
syntax highlighting, line pairing, box-drawn headers and optional side-by-side
columns. The binary does not run `git` for you until you use two-file mode;
everything else arrives on stdin. Everything below was measured live on the
official **0.20.1** release binary (x86_64-unknown-linux-gnu tarball, whose
`.deb`-shipped binary is byte-identical, sha256 `1324960d…`), with the v0.20.1
source tree pinned alongside, and cross-checked on the Ubuntu noble
**git-delta 0.16.5-5** build (see the divergence entry). Upstream is MIT,
holder `Copyright 2020 Dan Davison` per the source-tarball LICENSE.

## Install

1. Get the binary: the official release tarball / `.deb` (their extracted
   binaries are byte-identical, sha256 `1324960d…`), or
   `conda install -c conda-forge git-delta`. Distro builds lag heavily
   (noble ships 0.16.5).
2. Verify: `delta --version` → `delta 0.20.1`.
3. Distro builds need shared libs at runtime; if you see
   `error while loading shared libraries: libgit2.so.1.7`, the noble build
   wants `libgit2.so.1.7`, `libhttp_parser.so.2.9` and `libssh2.so.1` —
   install the packages or point `LD_LIBRARY_PATH` at extracted copies
   (resolve the symlink: copying the `libgit2.so.1.7.2` file under its
   `.so.1.7` name is what works).
4. `delta --help` is 114 options long and every flag has a config-side twin
   (`--tabs` ↔ `tabs = N` under `[delta]`). Treat the help as the contract.

## Input model: stdin only

- The diff always comes from stdin: `git diff | delta`,
  `git show | delta`, `diff -u a b | delta`. Positional arguments are
  something else — see below.
- **Positional args are `[MINUS_FILE] [PLUS_FILE]`**: `delta old.txt new.txt`
  makes delta compute the comparison itself (0.16.5 help: equivalent to
  piping the output of a two-file `diff -u` in). It shells out to git's
  no-index diff internally, with git semantics for exit codes: **1 when the
  files differ** (measured; 0 and silent when identical), and on a missing
  path it prints git's own stderr — `git diff: error: Could not access
  '<path>'` — rc 1. A single positional arg is *silently ignored* alongside
  whatever stdin says: `delta something` with empty stdin rc 0's and prints
  nothing.
- Non-diff stdin passes through **verbatim, unstyled, rc 0** (measured
  byte-identical) — delta only rewrites the sections it recognizes as diff
  structure. An empty stdin is equally happy: empty output, rc 0. So a
  script that pipes the wrong thing into delta fails open, silently.
- Unknown flag: **rc 2** with clap's error text (plus a
  `tip: to pass '--x' as a value…` hint). Bad enum values are rc 2 too and
  the error lists the possible values — e.g. `--detect-dark-light=bogus`
  prints `[possible values: auto, always, never]`.

## Piped vs TTY: the half that bites automation

- **Piping does not de-style.** `git diff | delta | cat` still carries the
  full stylesheet: on a 634-byte diff fixture the output held 107 escape
  sequences — blue file header, a full-width rule, box-drawn hunk markers,
  per-line 256-color backgrounds. The identical fixture produced the
  identical 107-segment count on the 0.16.5 build. delta is a pager *stage*
  by design: it renders for a downstream `less -R`, and there is no
  monochrome switch short of stripping ANSI afterwards (`--raw` still
  colors minus/plus lines red/green, see the styling-modes table).
- **Layout decisions use 80 columns when piped** (`--width=N` overrides;
  on a TTY the real width applies): plain inline lines pass through in full
  — no truncation until the `max-line-length` wall (default 3000; set 0 to
  lift it, per help) — but side-by-side columns wrap and truncate at the
  piped width.
- **TTY stdout: the pager engages.** The `paging` default is `auto`
  (per the resolved config dump): delta hands the rendered diff to a pager —
  `--pager CMD`, else the `DELTA_PAGER` env var, else `PAGER`, else `less`
  (help text; measured that each layer wins in that order) — **when the
  output is taller than one screen**. Measured at a 10-row terminal: the
  tail was withheld and the process held until keys arrived; a one-screen
  diff rendered whole. `--paging=always` forces the pager (measured alt-screen
  entry under a 256-color TERM), `--paging=never` never does.
- For scripts and agent harnesses that run on a TTY, the deterministic
  choice is `--paging=never` (or `--pager cat`): full output, the process
  exits, no keystrokes needed. `PAGER=cat` also neutralizes it.
- **With `TERM` unset on a TTY, the first thing you see is less:**
  `WARNING: terminal is not fully functional` plus a `Press RETURN` prompt
  that stalls rendering entirely (measured: a 68-byte capture and nothing
  else). That is the classic signature of a harness that forgot `TERM`.
- Color depth tracks the terminal: `TERM` unset → primitive 16-color codes;
  `TERM=xterm-256color` → `38;5;N` sequences; `--true-color=always` → 24-bit
  `38;2;R;G;B` everywhere (piped too). `--true-color auto` (the default)
  means 24-bit only when `COLORTERM` is `truecolor` or `24bit`. `--24-bit-color`
  still parses but is a deprecated alias.
- Theme selection: the default palette assumes a **dark** background;
  `--light` renders measurably differently. On a TTY the 0.20 line
  auto-detects the terminal background (source: the theme module consults a
  terminal color query, active when stdout is a TTY or with `--color-only`);
  `--detect-dark-light=always|never` forces the behavior and piped runs are
  identical under all three values (measured 107/107/107 escapes).
- `--hyperlinks` emits OSC-8 sequences for file names and line numbers even
  when piped (12 on the fixture); the commit-line hyperlink pass is gated on
  a TTY stdout (source).

## Readability controls (all measured)

- The `+`/`-` line markers are **stripped by default**; restore with
  `--keep-plus-minus-markers`.
- Tabs expand to 8 spaces without asking (`--tabs=N` to change, `--tabs=0`
  to pass tabs through raw — widths are then computed as if a tab were 1
  column, so avoid it with proportional fonts).
- `--side-by-side` (two columns): column widths follow the terminal when
  attached, 80 when piped. Long lines wrap into at most `--wrap-max-lines`
  continuation rows (default 2) and then truncate; `0` means never wrap
  (overflow truncates), `unlimited` keeps wrapping. Side-by-side shows
  **line numbers by default**; inline shows none unless you pass
  `--line-numbers` (whose left/right label templates are
  `--line-numbers-left-format` / `--line-numbers-right-format`, default
  shapes like `{nm:^4}⋮`).
- `--navigate` labels files with a `Δ` prefix and numbers hunks so the
  pager's `n`/`N` keys jump between them; set it in config, not per run.
  (Its help notes a tmux caveat about mouse-key interpretation.)
- Within-line diff pairing is governed by `--max-line-distance` (default
  0.6; higher = more aggressive pairing of similar minus/plus lines).
- Emulation presets exist as real flags: `--diff-so-fancy` and
  `--diff-highlight` toggle whole preset bundles in one go.
- Per-element styles are strings (`file-style`, `file-decoration-style`,
  `hunk-header-style`, `commit-style`, …) accepting named styles plus the
  `omit` / `none` / `box` / `plain` / `underline` attribute words; e.g.
  `file-style = omit` drops the file header entirely (measured).

## Styling modes

| mode | structure | styling (same 634-byte fixture) |
| --- | --- | --- |
| default | rewritten: headers, box drawings, paired lines | 107 escape seq, 256-color |
| `--color-only` | untouched — use it as the interactive diff-filter | 65 escape seq |
| `--raw` | byte-identical apart from red/green `+`/`-` line colors | 20 escape seq |

`--raw`'s help calls it mainly for testing delta; it still colors the changed
lines, so it is not a plain-text mode either.

Theme/syntax inspection:

- `--show-syntax-themes` renders a sample per built-in syntax theme: 532
  lines of demo by default, and if a diff waits on stdin it becomes the
  sample instead (fixture: 1092 lines). **It reads stdin to EOF** — a probe
  that leaves an open, empty pipe attached blocks it forever; redirect from
  `/dev/null` or supply the diff.
- `--list-syntax-themes`: 28 rows, `dark<TAB>Name` or `light<TAB>Name`;
  pick with `--syntax-theme=Name`.
- `--list-languages`: 198 rows of language + extensions (only matters with
  custom languages; syntax is highlighted via a vendored highlighter).
- `--show-themes` lists *named user themes* (your `[delta.mystyle]` config
  blocks). A fresh install has none: **rc 2** with `No themes found. Please
  see https://dandavison.github.io/delta/custom-themes.html.` — exit code 2
  for an empty result, worth knowing before scripting against it.

## Config resolution — and its traps

delta reads gitconfig-style files **directly**, in two layers that merge:

1. User layer: `~/.gitconfig`, then `$XDG_CONFIG_HOME/git/config`
   (default `~/.config/git/config`).
2. Repo layer: `.git/config` of the current repository.

All three honored (measured one by one):

```ini
[delta]
    side-by-side = true
    navigate = true

[delta "my-commit-style"]
    commit-style = omit
```

- **The git(1) redirection environment variables do not affect delta.**
  Measured both directions: `GIT_CONFIG_GLOBAL=<file-with-side-by-side=true>`
  changes nothing outside a repo, while the *same file* placed as
  `$XDG_CONFIG_HOME/git/config` applies immediately. Relocating delta's
  config for a scratch session means `HOME` / `XDG_CONFIG_HOME` relocation
  or `--config` — not the git env vars.
- `--no-gitconfig` **bypasses all three sources** (measured: repo
  `side-by-side = true` neutralized), restoring built-in defaults — handy
  precisely when you need a hermetic run: `delta --no-gitconfig`.
- `--config PATH` **replaces the whole resolution**: with it, neither the
  user layer nor the repo config applies (measured: settings from the file
  active, repo-side settings ignored). A missing file is **silently
  ignored, rc 0** — a typo'd path fails open.
- Features are named blocks (`[delta "my-commit-style"]` above), activated
  with `--features my-commit-style`, or via `DELTA_FEATURES`. With the env
  var, a bare name and a `+name` prefix both worked identically (measured
  on `file-style = omit`). An unknown feature name is **silently ignored,
  rc 0**.
- `delta --show-config` dumps every resolved `key = value` line — run
  `env -u XDG_CONFIG_HOME ... --show-config` in a clean shell when you want
  pure defaults; otherwise it prints whatever your user/repo config
  contributed too. Defaults worth knowing: `tabs = 8`, `max-line-length =
  3000`, `true-color = false`, `paging = auto`, `max-line-distance = 0.6`,
  `navigate = false`, `hyperlinks = false`, `file-style = blue`,
  `hunk-header-style = syntax`.
- Flags override config values; config keys mirror the long flag names
  (no `--` prefix) as shown by `--show-config`.

## Wiring into git

```bash
git config --global core.pager delta
git config --global interactive.diffFilter 'delta --color-only'
git config --global delta.navigate true
```

`core.pager` runs delta with a TTY stdout, so the auto pager applies its
one-screen logic for you; `--color-only` under `interactive.diffFilter`
is exactly the mode built for that slot — structure untouched, styling only,
so `git add -p`'s internal diff keeps its own layout. Prefer config keys
(`delta.navigate = true`) over flags in the pager string: they stay editable.

## Exit codes

- **0** — rendered, passed through, or empty input; also the silent-failure
  cases above (unknown feature, missing `--config` file).
- **1** — two-file mode found differences (git diff semantics); missing
  positional file (git's own message on stderr).
- **2** — usage errors: unknown flag, invalid enum value, and the
  `--show-themes`-with-no-themes case.

## Divergence — Ubuntu noble ships git-delta 0.16.5

Measured on noble's 0.16.5-5 against the 0.20.1 release binary:

- Runtime needs `libgit2.so.1.7`, `libhttp_parser.so.2.9`, `libssh2.so.1`
  (fails rc 127 with a loader message until they are present — extract and
  point `LD_LIBRARY_PATH`).
- `--detect-dark-light` is a 0.20-era flag: absent on 0.16.5. Everything
  else in this skill probed identical, including the styling-mode table
  (`--raw`/`--color-only`), `--show-config`, `--show-syntax-themes`,
  `--config`, and the byte-count of the piped stylesheet (107 escapes on
  the same fixture on both builds).
- Prefer the release binary; the distro build is a 2022-era wall.

## Verify the install (run this after setup)

Measured to exit 0 on clean scratch state (needs only the binary on PATH;
deliberately stdin-safe — every delta call gets `--paging=never` and either
a redirected pipe or `/dev/null`):

```bash
set -eu
T=$(mktemp -d)
export HOME="$T/home" XDG_CONFIG_HOME="$T/xdg"
mkdir -p "$HOME" "$T/xdg/git"
printf '%s\n' '[delta]' '    side-by-side = true' > "$T/xdg/git/config"
D=$(command -v delta)
printf '%s\n' '--- a/f.txt' '+++ b/f.txt' '@@ -1,2 +1,3 @@' \
    ' alpha' '-beta' '+BETA2' '+gamma' > "$T/p.patch"
plain=$("$D" --paging=never --no-gitconfig < "$T/p.patch")
sbs=$("$D" --paging=never < "$T/p.patch")
case "$plain" in *beta*) : ;; *) echo "FAIL: content lost"; exit 1 ;; esac
case "$plain" in *"-beta"*) echo "FAIL: markers not stripped by default"; exit 1 ;; esac
case "$sbs" in *"│"*"│"*) : ;; *) echo "FAIL: config not applied"; exit 1 ;; esac
test "$plain" != "$sbs"
test "$(printf '' | "$D" --paging=never)" = ""
printf '%s\n' 'just some text' | "$D" --paging=never > "$T/passthrough"
test "$(cat "$T/passthrough")" = 'just some text'
set +e; "$D" --no-such-flag </dev/null >/dev/null 2>&1; rc=$?; set -e
test "$rc" -eq 2
rm -rf "$T"
echo delta-verified
```