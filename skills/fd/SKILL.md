---
name: fd
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
description: "Use when finding files or directories in a shell pipeline: `fd` filters by regex or glob with hidden/ignore handling, runs commands over results, and replaces `find` one-liners. Covers the 9/10 breaking wall (.git/ under --hidden), the path-separator pattern rejection, exec vs exec-batch modes, --batch-size placement and the no-match exit-0 trap; also the fdfind rename on Debian/Ubuntu. Behaviors measured live."
---

# fd — find files without `find`'s flags

`fd` ([sharkdp/fd](https://github.com/sharkdp/fd)) finds filesystem entries by regex or glob, with
gitignore filtering, hidden-file skipping and smart case built in. This skill is **original text
written from live binary behavior**, pinned to fd **10.5.0** (the current release as of writing).
Upstream is **dual-licensed MIT OR Apache-2.0**: the release tarball ships both `LICENSE-MIT` and
`LICENSE-APACHE`, while the GitHub API license field reports only Apache — take the files, not the
field. No fd code is quoted here, only measured behavior. The major-version walls below were
re-measured on fd 8.7.1, 9.0.0 and the Ubuntu distro build (`fd-find` 9.0.0).

## Install

```bash
# static binary from the release page (x86_64 linux ships gnu and musl tarballs)
curl -sL -o fd.tar.gz https://github.com/sharkdp/fd/releases/download/v10.5.0/fd-v10.5.0-x86_64-unknown-linux-musl.tar.gz
tar xzf fd.tar.gz && ./fd-v10.5.0-x86_64-unknown-linux-musl/fd --version   # fd 10.5.0
# or: cargo install fd-find   /   brew install fd
```

Debian/Ubuntu gotcha: `apt-get install fd-find` installs a binary named **`fdfind`**, not `fd`
(the name was chosen to avoid colliding with a Unix tool). The distro package measured here
(Ubuntu `fd-find` 9.0.0) actually ships **two binaries**: `/usr/bin/fdfind` and an unrenamed
`/usr/lib/cargo/bin/fd` — only the first is on the normal PATH. Check which one you get with
`command -v fd` and `fd --version` before scripting version-sensitive flags.

## The default model

- The pattern is a regex **matched against the entry name only** (not its path). With no pattern,
  every entry matches: `fd` lists like `ls -R` but shallow-sorted and filtered.
- **Smart case**: a lowercased pattern is case-insensitive; an uppercase character anywhere makes
  the search case-sensitive. Measured: `fd src` finds `sub/SRC/`, `fd SRC` misses `src`.
- Hidden entries (dot-names) are **excluded by default** (`-H/--hidden` includes; `--no-hidden`
  restores). Ignore-listed entries (`.gitignore`, `.ignore`, `.fdignore`, global ignore) are
  excluded by default (`-I/--no-ignore` includes; `-u/--unrestricted` = `-H -I`). `-E <glob>`
  (`--exclude`) adds exclusions that override ignore logic; `--prune` stops descending into
  matching directories.
- **gitignore filters only apply inside a git repository** (git detection is on by default).
  Measured on 10.5.0: a `.gitignore` filter that works inside the repo silently disappears once
  `.git/` is absent — `fd` then lists ignore-listed entries. `--no-require-git` restores
  gitignore honoring outside a repo (added in fd 8.7.0).
- Symlinked entries are listed as themselves but not followed into (`-L/--follow` follows;
  `-t l` filters for them). Directories print with a trailing `/` (e.g. `sub/`).
- Exit codes: **exit 0 with matches — and exit 0 with NO matches too.** Measured: `fd zzz`,
  `fd REPORT-` (case-sensitive miss) and `fd -g 'sub/*.log'` on fd 8/9 all print nothing and exit
  0. `[fd error]` diagnostics exit **1** (bad regex, path-separator pattern, no valid search
  path); option parse errors exit **2** ("unexpected argument", "Only one placeholder allowed for
  batch commands"). A non-zero exit from any `-x`/`-X` child command also propagates as 1.
  The **only** way to detect a no-match by exit code is `-q/--quiet` (alias `--has-results`):
  prints nothing, exit 0 if at least one match, else 1.
- Output paths: plain stdout prints relative paths without a `./` prefix **when the search root is
  the implicit CWD**; an explicitly passed root is kept verbatim (search path `.` prints
  `./sub/SRC/`). Paths handed to `-0`, `-l` and to `-x`/`-X` commands **always carry the `./`
  prefix** — string-comparing plain output against exec paths mismatches (all measured). Add
  `-a` for absolute paths.

## The version wall — measure before scripting against older fd

- **`.git/` handling under `-H` flips across majors** (measured by counting `.git` entries in a
  real repo tree with `-H`):
  - fd 8.7.1: `.git/` contents LISTED (29 entries).
  - fd 9.0.0: `.git/` silently ignored even with `-H` (1 entry — only `.gitignore`); introduced as
    a breaking change in 9.0.0.
  - fd 10.5.0: listed again (29 entries); 10.0.0 reverted the 9.0.0 behavior, recommending a
    global fdignore instead.
  A script counting or iterating `.git` entries under `-H` returns a different world on 9.x.
- **Patterns containing a path separator**: fd 10.5.0 **fails closed** with a diagnostic before
  searching, exit 1:

```text
$ fd sub/report-v1
[fd error]: The search pattern 'sub/report-v1' contains a path-separation character and will
not lead to any search results.

If you want to search for all files inside the 'sub/report-v1' directory, use a match-all
pattern:

  fd . 'sub/report-v1'

Instead, if you want your pattern to match the full file path, use:

  fd --full-path 'sub/report-v1'
```

  On fd 8.7.1 and 9.0.0 the **same command prints nothing and exits 0** — a silent miss. Older fd
  will also swallow glob patterns like `sub/*.log` the same way. Scripts that must run on pre-10
  fd need to pre-filter for `/` in the pattern themselves. The 10.5.0 changelog notes the
  diagnostic previously fired only when the pattern also named an existing directory, and that
  slash patterns inside `--and` patterns now get it too.
- Feature boundaries (from fd's own CHANGELOG, all in-tree): `--format` arrived in 10.1.0;
  `--exact` in 10.5.0; `--no-require-git` in 8.7.0. Anything newer than the distro binary you
  test on may silently not be there.

## Pattern semantics (measured on 10.5.0)

- Regex by default: `fd report.v1` matches `report-v1.log` (`.` is any character);
  `-F/--fixed-strings` makes it literal; `--exact` requires the pattern to match the **entire
  filename** — `fd --exact report2.log` finds `sub/report2.log`, `fd --exact report` misses.
  A malformed regex prints the parse error plus advice pointing at `--fixed-strings`/`--glob`
  and exits 1.
- `--glob` matches the filename: `-g '*.log'` finds nested logs too. A glob with a `/` hits the
  same path-separator diagnostic as above.
- `--full-path` (`-p`) matches against the **full path** (the option help says the full absolute
  path, and that is what the probes show): `fd -p SRC/rep` matched
  `sub/SRC/rep3.LOG` because it is a substring of the absolute path; `fd -p '^sub/'` matched
  nothing even in a directory whose entries all sat under `sub/`. `--exact -p` therefore needs
  the entire **absolute** path, measured: `--exact -p sub/report2.log` and its `./`-prefixed
  form both missed, while `--exact -p "$PWD/sub/report2.log"` matched. For the common case,
  "search inside a directory" is simply a second positional: `fd <pattern> <search-path>`
  (`fd . sub` lists everything under `sub`).
- A dot-anchored pattern under `-p` (`fd -p '^\.'`) triggers a different diagnostic — "the
  pattern(s) seems to only match files with a leading dot, but hidden files are filtered by
  default" — exit 1; add `-H` or re-anchor the pattern.
- `--and <pattern>` adds additional required regexes, chainable
  (`fd report -e log --and report2 --and '2$'`).
- `--format <fmt>` (10.1.0+) prints each result through a template using the same placeholders as
  `--exec`: `fd --format '{/.}' -e log` prints extensionless basenames.

## Filters

```bash
fd -H                     # include hidden (dot) entries
fd -I                     # include ignore-listed entries
fd -u                     # both at once (measured: identical counts to -HI)
fd -e log                 # extension filter — case-insensitive (matched .LOG too)
fd -tf -e LOG             # smartcase applies to extensions as well
fd -t f                   # regular files (d dir, l symlink, x executable, e empty)
fd -d 1                   # depth limit (--min-depth/--exact-depth also exist)
fd -S +1k                 # size filter: + at-least, - at-most, no sign = exactly
fd --changed-within 2weeks --changed-before 2026-01-01
fd -q some-pattern        # presence check by exit code (rc 0 only if matched)
fd -1 -e log              # first match only (--max-results=1)
```

`-e` is case-insensitive and, per the option help, also matches directories whose name ends in
the extension — add `-t f` to keep it files-only. `--changed-within`/`--changed-before` take
durations (`1d`, `10h`, `35min`) or dates and carry aliases
(`--changed-after`/`--newer`, `--older`).

## Running commands over results: `-x` vs `-X`

```bash
fd -e jpg -x convert {} {.}.png     # once per result, PARALLEL; order not guaranteed
fd -e log --threads 1 -x wc -l      # sequential (ordered) per-result mode
fd report -X wc -l                  # ONE invocation over all results
```

The trap pair here is heavier than `find -exec`:

- **`-x`/`--exec` runs the command once per result in parallel** — output interleaves and runs in
  arbitrary order (measured: same `wc`-style command listed results in a different order between
  two runs; `--threads 1` restores sequential execution). Placeholders: `{}` the path, `{/}` the
  basename, `{//}` the parent, `{.}` the path without extension, `{/.}` the basename without
  extension; `{{` and `}}` produce literal braces. With **no placeholder, an implicit `{}` is
  appended to the command** (measured both with and without one). Repeating `{}` is allowed in
  per-result mode — every occurrence gets the same result path. A trailing terminator `;` is
  only needed when fd flags should continue after the command; **everything after `-x` belongs
  to the command**: a trailing `-a` was consumed as a command argument (measured), so place
  `-x` last.
- **`-X/--exec-batch` runs the command exactly once with all results as arguments** (the arg
  order is non-deterministic — measured across runs). At most **one** placeholder is allowed;
  more than one errors with rc 2 ("Only one placeholder allowed for batch commands"). Two
  orderings measured in 10.5.0:
  - `--batch-size <n>` (splits oversized batches) must be placed **before** `-X`: after `-X`
    every following argument belongs to the command — `fd -e log -X --batch-size 2 ech {}` failed
    with `[fd error]: Command not found: --batch-size`, exit 1.
  - the search pattern must come **before** `-X` too: a positional after the command template is
    appended to that command, not used as the pattern (measured `fd -X ech {} zzz` passed `zzz`
    into the command and searched with no pattern at all).
- **With zero results, `-X` silently never executes the command** and fd exits 0 (measured on
  10.5.0) — a batch step that must run even on empty input needs its own fallback.
- A child command that exits non-zero makes fd itself exit 1 (measured with `/bin/false` under
  both `-x` and `-X`).

## Recipes

```bash
fd -0 -e log | xargs -0 some-command     # NUL-separated handoff (paths arrive ./-prefixed)
fd -e jpg -x convert {} {.}.png          # parallel per-file conversion
fd -g 'test_*.py' -X vim                 # open all matches in one editor invocation
fd -e log -q && echo has-logs            # presence check for a CI-style gate
fd --changed-within 2weeks -e py         # recently touched python files
```

## Gotchas, condensed

- no-match **exit 0** — use `-q` when the exit code is the point.
- old fd (8.x, 9.x) returns **silently empty** for slash patterns (`sub/file.log`,
  `sub/*.log`); 10.5.0 rejects them rc 1 — check this before debugging "no results".
- the `.git/`-under-`-H` behavior differs across 8/9/10.
- exec paths (`-x`, `-X`, `-0`, `-l`) carry a leading `./`; plain stdout may not.
- `-X`: one placeholder max, pattern before, flags (`--batch-size`) before, zero results = silent
  no-op with rc 0.
- `-x`: parallel by default, `--threads 1` for order; trailing args are the command's.
- Debian/Ubuntu: the package is `fd-find` and the binary is `fdfind`.
- `-e` matches directories too unless `-t f` is added.