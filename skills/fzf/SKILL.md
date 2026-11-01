---
name: fzf
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, bsd, windows]
description: "Use when picking items from a list in a script or a shell - fuzzy-match files, git branches, log lines, or command output with fzf. Covers headless --filter mode for scripts (exit-code taxonomy, field/index expressions, the accept-nth raw-span output quirk, smart-case and quoted-term semantics), what changes on a real terminal (multi output order, --expect key lines, signals), FZF_DEFAULT_* env vars, the built-in file walker, and shell integration. Measured live on fzf 0.74.5."
---

# fzf — fuzzy picker for scripts and terminals

fzf reads a list on stdin, matches a query against it with a fuzzy scorer, and prints the
selection. Two faces matter and they behave differently: the interactive terminal UI, and the
headless `--filter` mode that scripts exist on. Everything below was measured on the **fzf
0.74.5** release binary (static Go build; upstream
[junegunn/fzf](https://github.com/junegunn/fzf), **MIT**, Copyright (c) 2013-2026 Junegunn Choi),
with a divergence pass on the Ubuntu 24.04 distro build **0.44.1-1ubuntu0.3**. The self-documenting
sources: `fzf --man` (~2200 lines), `fzf --help`, and the CHANGELOG.

Install from GitHub releases — per-platform tarballs (`fzf-0.74.5-linux_amd64.tar.gz`), a
`.deb` (`fzf_0.74.5_amd64.deb`), and a checksums file are published per release; distro packages
lag behind (Ubuntu noble ships 0.44.1). The repo tree also carries `bin/fzf-tmux`, a tmux-popup
wrapper that `./install --bin` / `make install` puts next to `fzf`.

## Terminal or `--filter` — the first fork

- With **no terminal at all** (stdin and stdout both pipes): `fzf` prints
  `inappropriate ioctl for device` and exits **2**. It does not fall back to anything.
- Piped stdin + a real terminal on stdout: the UI runs full-screen, items stream from stdin,
  keys come from the terminal. The classic `seq 100 | fzf`.
- A **terminal stdin** and no piped items: fzf runs `$FZF_DEFAULT_COMMAND` (via `$SHELL -c`,
  POSIX only), or, when that variable is unset, its **built-in walker** — files, following
  symlinks, including hidden ones, skipping `node_modules` and `.git` (see `--walker`,
  `--walker-skip`). Measured: in a directory with a marker file, typing part of its name and
  Enter returned the path; querying content that only exists inside `node_modules/` found
  nothing.
- `--filter=QUERY` (or `-f QUERY`) is the scripted face: rank, print all matches, exit — no
  terminal needed.

## Exit-code taxonomy (all measured)

| Code | Meaning | Measured triggers |
| --- | --- | --- |
| 0 | accepted a match | `--filter` with at least one match; UI Enter on a match |
| 1 | no match | `--filter` no match; empty input; `--exit-0` with a no-match initial query; UI Enter on an **empty list**; `--filter` with `--print-query` still prints the query first and exits 1 |
| 2 | error | `inappropriate ioctl for device` with no TTY; `unknown option: --bogus`; `fzf -f` with no value → `query string required` |
| 126 / 127 | permission / invalid command from a `become` action | documented in `fzf --man` |
| 130 | interrupted | **CTRL-C and ESC both** exit 130 in the UI (measured) |

Sharp edges for scripts: fzf takes **no positional arguments** — a bare word is rejected as
`unknown option: <word>` (rc 2). `--query` is ignored in `--filter` mode. A `--history` file is
created (empty) even under `--filter`, but filter runs record nothing.

## Search semantics (0.74.5, all measured)

**Smart case** is the default: an all-lowercase query matches case-insensitively, any uppercase
character forces case-sensitive matching — and this governs quoted terms too:

- `-f ap` matched `apple`, `Apple`, `aPple`; `-f Ap` matched only `Apple`.
- `-i` forces insensitivity; `+i` forces sensitivity (fuzzy `ap` with `+i` still finds `aPple`
  via `a…p` at positions 0 and 2 — case rules apply per character, not per item).
- `-f 'Pp` (uppercase inside a quoted term) matched only `aPple`.

**Term syntax** in extended-search mode (the default):

- Plain terms are fuzzy and AND-ed together: `main go` matched `main.go`, rejected `main.py`.
- `'term` (leading quote) = **exact substring** — it matches mid-word occurrences and ranks
  them last: `'foo` matched `xxfooyy` (ranked after `foo`, `foobar`, `afoo`); `'pp` matched
  `Apple` *and* `aPple` (the latter case-insensitively, through smart case).
- `'term'` (quoted on **both ends**) = word-boundary match, and here boundaries are enforced:
  `'pp'` over `Apple/aPple/apple` matched **nothing** (rc 1) because every `pp` sits inside a
  word; `'apple'` over `xx apple yy/apple pie/myapple` matched the first two and rejected
  `myapple`. With a leading quote only, boundary quality only affects ranking: one-word
  occurrence > word start > word end > mid-word — the man page's four-rank table reproduced
  verbatim on equal-length lines (`xxx foo xxx` > `xxx foo_xxx` > `xxx_foo xxx` >
  `xxx_foo_xxx`).
- `!term` excludes (exact by default): `main !test` dropped `test/main.go`; `!^src` anchored;
  `!'ain` fuzzy-negation. In `--exact` mode the `'` prefix unquotes (documented; both forms
  then behave as exact-substring).
- `|` is a single-character OR term: `^core go$ | rb$ | py$` matched `core.go`, `core.rb`,
  `core.py` (tied candidates keep input order).
- `--exact` (`-e`) turns all terms into exact substrings; `--literal` disables latin-script
  normalization; `\ ` escapes a literal space inside a term.

## Fields: `-d`, `--nth`, `--with-nth`, `--accept-nth`

`-d` is a **regex** (default: AWK-style whitespace runs). `-d -`, `-d [,:]`, `-d [-,:]` all
work; the pattern must actually match the separators — `-d '[,:]-?'` requires a comma or colon
first, so `a-b-c` fell into one field and an accept-nth of field 2 printed nothing.

The matching pipeline composes as **split → `--with-nth` transform → `--nth` scope → match**,
proven by:

- query `c` + `--with-nth 2 -d ,` on `a,bb,c` → **rc 1**: `c` exists in the original line but
  not in the transformed field; matching runs on the transformed text.
- `--with-nth 3 --nth 1 -d ,` on `a,c,bb` → match (transform = 1-field line `bb`; `--nth 1` of
  *that* is `bb`). `--with-nth 2 --nth 2` on 3-field data → rc 1 (single-field transform has no
  field 2 to scope to). Argument order between the two flags does not matter.
- Despite all this, `--filter` **prints the original input line** — transforms affect only what
  is matched (and what `--accept-nth` prints).

`--accept-nth` reshapes the printed output — and it does **not** join with the delimiter. It
concatenates the raw field spans (each keeping its trailing delimiter), then strips the final
trailing delimiter of the whole output; missing fields contribute nothing. Measured on `a,bb,c`:

- `--accept-nth 2,1` → `bb,a`; `2,3` → `bb,c`; `1,3` → `a,c`
- `3,2,1` → **`cbb,a`** (field 3 has no trailing comma, so the reorder glues 3 to 2)
- `1,3,2` → `a,cbb` for the same reason
- On the 2-field line `x,bb`: `1,3` → `x` (nothing emitted for the missing field, no trailing
  separator survives)

For exact control use the **template** form: `--accept-nth '1st={1} n={n}'` printed
`1st=a n=0` — `{n}` is the zero-based line ordinal, and template expressions strip their own
trailing delimiters. The template form also works in `--filter` runs, and `--multi` accepts
honor it in the UI too (measured: `-d , --accept-nth 2` printed `1` from `a,1`).

Also measured in filter mode: `--header-lines=N` removes the first N lines from matching *and*
output (`NAME,VAL\na,1` with `--header-lines=1` returned only `a,1`); `--ansi` strips color
codes from printed items (without it the raw escape bytes pass through); `--read0` /
`--print0` switch the NUL delimiters independently, and NUL bytes without `--read0` pass
through as item content.

## Ranking knobs (all measured)

- Default `--tiebreak=length`: among equal scores, shorter lines win first (`-f ain` on
  `main.py/a main.cpp...`-style fixtures ordered by line length).
- `--tiebreak=pathname` compares path components from the end backwards; `end`, `begin`,
  `chunk` and `index` each produced a different measured order — `index` is plain input order.
- `+s` (`--no-sort`) keeps the input order of matches; `--tac` reverses the input stream
  *before* ranking (ties then break in reversed input order: `FZF_DEFAULT_OPTS=+s` +
  `--tac` on `aa/ab/ac` printed `ac ab aa`).
- `--scheme` re-weights scoring: `default` == unset; `path` prioritizes basename matches
  (`-f ain` pulled `lib/x/main.c` above `a/main.cpp`); `history` boosted the `src/`-prefixed
  item in the same fixture.

## Terminal behaviors (measured under a real pty on 0.74.5)

- **`--multi` output is input order, not selection order.** Marking `ccc` first, then `aaa`,
  printed `aaa` then `ccc`. Parse the lines; never assume selection order.
- Default Tab = mark the current item and move down (source `defaultKeymap` maps Tab to
  `toggle-down`, Shift-Tab to `toggle-up`); at the edge the cursor clamps — add `--cycle` to
  wrap. Multi count renders as `n/m (selected)`.
- `--expect=ctrl-t,...` prints the pressed key's name as the first output line (`ctrl-t`), the
  selection after; with `--print-query` the query comes first, then the key, then the item.
  Listing `enter` *in* `--expect` makes plain Enter print the literal name `enter`; completing
  with an unlisted Enter prints an empty first line (per `fzf --man`).
- `--select-1` auto-accepts only the **initial, pre-filled** query's unique match
  (`--select-1 -q bb` accepted instantly); typing a query during the run never triggers it.
- `--exit-0` exits immediately — rc **1**, no output — when the initial query has no match.
- Accepting with an **empty item list** exits 1 with no output.
- The preview command gets `{}` (current item) substituted, plus `FZF_PREVIEW_LINES`,
  `FZF_PREVIEW_COLUMNS`, `FZF_CURRENT_ITEM` and ~40 other `FZF_*` exports; with `--listen` the
  child also gets `FZF_PORT`. The `FZF_DEFAULT_COMMAND/OPS/OPS_FILE` **nulling** lives only on
  the tmux-popup path (it defeats tmux-injected defaults); plain preview children inherit
  `FZF_DEFAULT_OPTS` normally.
- `--listen` (HTTP or Unix socket) also doubles as an introspection API: `GET /` returns the
  live state as JSON — `query`, `position`, `totalCount`, `matchCount`, `current`,
  `matches[]`, `selected[]` — which is the honest way to test key-driven behavior in
  automation instead of scraping the redrawn screen. `FZF_API_KEY` protects a remote listener;
  `--listen-unsafe` additionally allows remote process execution.
- Default key chords worth knowing (source `defaultKeymap`, 0.74.5): Tab/Shift-Tab toggle
  down/up, Ctrl-N/Ctrl-P jump matches in raw mode, Enter accepts, Ctrl-C/Ctrl-G/Ctrl-Q/ESC
  abort, Ctrl-D deletes or EOF-exits, Ctrl-L clears the query line.

## Environment variables

- `FZF_DEFAULT_OPTS_FILE` (read first), then `FZF_DEFAULT_OPTS`, then argv — later flags win
  per the option order in the source. The env string is parsed shell-words style (quotes and
  backslashes honored, newline-separated flags work: `--exact\n--tac` parsed as two flags);
  the file is parsed line by line. Bad content fails rc 2 with the source-named prefix
  (`$FZF_DEFAULT_OPTS: unknown option: …` / `<path>: unknown option: …`).
- `FZF_DEFAULT_COMMAND` fires only when stdin is a TTY; it runs through `$SHELL -c` (or
  `sh -c`), so it must be POSIX — unquoted backslashes are eaten by that shell before the
  command ever runs.
- `--history=FILE` / `--history-size=N` (default 1000) store the *search* history, not shell
  history.

## Shell integration and fzf-tmux

`fzf --bash` / `--zsh` / `--fish` / `--nushell` print their integration scripts to stdout for
`eval "$(fzf --bash)"`-style use (939 / 684 / 394 / 684 lines at 0.74.5). The bash script binds
CTRL-T to the file widget (`__fzf_select__`), CTRL-R to history search (`__fzf_history__`) and
ALT-C to cd (`__fzf_cd__`); the zsh script defines `fzf-file-widget`, `fzf-history-widget`,
`fzf-cd-widget` plus the `_fzf_complete` TAB-completion hook (`**` trigger). `fzf-tmux` opens
the finder in a tmux pane or popup (popup needs tmux 3.2+; the wrapper parses `tmux -V`
numerically with an awk compare and a `bc` fallback) — and 0.74.5 carries security fixes for it:
attached layout sizes are no longer evaluated through bash arithmetic (GHSA-w6x2-f5m4-xw82) and
zsh completion moved its FIFO into a private `mktemp -d` directory (GHSA-7rj6-7pqx-v7rm).

## Version caveats (Ubuntu noble 0.44.1 cross-check)

Absent in 0.44.1: `--accept-nth` (and templates), `fzf --bash/--zsh/--fish/--nushell`, the
built-in `--walker` (TTY-stdin runs need `FZF_DEFAULT_COMMAND` there), `--popup`, `--id-nth`,
`--tail`. Present and unchanged: `--scheme`, `--track`, the whole search core — boundary-quoted
`'pp'` rc 1, the `'foo` mid-word match with the same four-rank order, smart case on quoted
terms. Distro builds print `0.44.1 (debian)` — no commit hash — where releases print
`0.74.5 (c0a193e0)`. Any claim above that depends on these surfaces gets stale on distro
builds; probe `fzf --help` before scripting against them.

## Recipes

Field scoping and span semantics, exit codes, and the `FZF_DEFAULT_OPTS` contract, all in
headless filter mode:

```bash
set -eu
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
printf 'apple\nApple\naPple\nbanana\ncherry\n' > "$d/fruits.txt"

# --filter prints ranked matches; rc 0 with a match
printf 'apple\nbanana\n' \
  | fzf --filter=an | tail -n 1 | grep -qx banana

# no match: rc 1 and empty output
if printf 'apple\nbanana\n' | fzf --filter=zzz >/dev/null 2>&1; then
  echo 'no-match must exit 1'; exit 1
fi

# smart case: uppercase anywhere in the query forces case sensitivity
r=$(fzf -f Ap < "$d/fruits.txt"); [ "$r" = Apple ]

# quoted term = exact substring, hits mid-word; both-ends = boundary enforced
r=$(printf 'xxfooyy\nfoo\n' | fzf -f "'foo"); printf '%s\n' "$r" | grep -q xxfooyy
printf 'Apple\naPple\napple\n' | fzf -f "'pp'" > "$d/none" 2>&1 \
  && { echo 'boundary term must fail'; exit 1; }

# no positional arguments, ever
if fzf apple > "$d/err" 2>&1; then echo 'positional must fail'; exit 1; fi
grep -q 'unknown option: apple' "$d/err"
echo 'ok: search + exit codes'
```

```bash
set -eu
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
printf 'a,bb,c\nx,bb\nqq,zz\n' > "$d/i.csv"

# --nth scopes matching to one field of the original line
r=$(fzf -f bb --nth 2 -d , < "$d/i.csv")
[ "$r" = "$(printf 'x,bb\na,bb,c')" ]

# accept-nth joins raw field spans, then strips the final trailing delimiter
[ "$(printf 'a,bb,c\n' | fzf -f bb -d , --accept-nth 2,1)" = bb,a ]
[ "$(printf 'a,bb,c\n' | fzf -f bb -d , --accept-nth 3,2,1)" = cbb,a ]
[ "$(printf 'x,bb\n'    | fzf -f bb -d , --accept-nth 1,3)" = x ]
r=$(printf 'a,b\n' | fzf -f b -d , --accept-nth '1st={1} n={n}')
[ "$r" = '1st=a n=0' ]

# header-lines are excluded from matching and output; NUL delimiters round-trip
r=$(printf 'NAME,VAL\na,1\n' | fzf -f a --header-lines=1); [ "$r" = a,1 ]
printf 'p\0q\0' | fzf -f q --read0 --print0 > "$d/out"
printf 'q\0' | cmp - "$d/out"
echo 'ok: fields, accept-nth, headers, NULs'
```

```bash
set -eu
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
printf 'ab\naxb\n' > "$d/exact.txt"
printf 'aa\nab\nac\n' > "$d/sort.txt"

# FZF_DEFAULT_OPTS: newline-separated flags parse; --exact changes what matches
r=$(FZF_DEFAULT_OPTS=$'--exact\n--tac' fzf -f ab < "$d/exact.txt")
[ "$r" = ab ]

# env opts compose with argv flags: +s (input order) + --tac reverses ties
r=$(FZF_DEFAULT_OPTS=+s fzf -f a --tac < "$d/sort.txt")
[ "$r" = "$(printf 'ac\nab\naa')" ]

# FZF_DEFAULT_OPTS_FILE is parsed line by line; bad content fails rc 2, path-prefixed
printf -- '--exact\n' > "$d/opts"
r=$(FZF_DEFAULT_OPTS_FILE="$d/opts" fzf -f ab < "$d/exact.txt"); [ "$r" = ab ]
printf -- '--bogus\n' > "$d/bad"
if FZF_DEFAULT_OPTS_FILE="$d/bad" fzf -f a < "$d/sort.txt" > "$d/err" 2>&1; then
  echo 'bad opts file must fail'; exit 1
fi
grep -q "$d/bad: unknown option: --bogus" "$d/err"
grep -q 'unknown option: --bogus' "$d/err"
echo 'ok: FZF_DEFAULT_OPTS contract'
```