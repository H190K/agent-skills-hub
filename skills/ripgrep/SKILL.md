---
name: ripgrep
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
description: "Use when searching file contents in a repo or pipeline with `rg` - its ignore-file filter ladder (-u/-uu/-uuu) with the .gitignore-needs-repo vs .ignore-everywhere split, include globs that bypass ignore filters while type filters only bypass hidden, piped-vs-TTY output defaults, -c vs --count-matches, -o -r capture templates, --json/--stats machine output, fail-open config files, and rc taxonomy. Measured live on 15.2.0."
---

# ripgrep

`rg` searches file contents across a directory tree, line-oriented, with an
opinionated default filter. It is the right tool whenever you want "which files
talk about X" or "show me every line mentioning X" over a repo: it is fast (a
literal-first regex engine plus multithreaded parallel walk), and it filters the
noise you would otherwise hand-strip.

Everything below is measured live on the **ripgrep 15.2.0** official static
release build, re-run byte-identically on the official 15.2.0 .deb build and on
conda-forge's 15.2.0 build (timing fields differ, semantics do not), and
re-checked on Ubuntu 24.04 (noble)'s packaged **14.1.0-1** where the two differ.

## Install

Pick one:

- Release tarball: download `ripgrep-15.2.0-x86_64-unknown-linux-musl.tar.gz` from
  the GitHub releases page (github.com/BurntSushi/ripgrep/releases), unpack, and
  put `rg` on your PATH. The `.sha256` file publishes the tarball checksum.
- `cargo install ripgrep`
- `apt-get install ripgrep` (Ubuntu 24.04 ships 14.1.0-1 - see the divergence row)
- conda-forge `ripgrep` (15.2.0 already published there)
- an official `.deb` (`ripgrep_15.2.0-1_amd64.deb`) for dpkg-based systems

Verify with `rg --version`: the output shows the version, a `features:` line
(the 15.2.0 release builds have `+pcre2`; noble's 14.1.0-1 says
`-simd-accel,+pcre2`), and an `available` line for PCRE2 (10.45 in 15.2.0,
10.42 in 14.1.0) with a JIT mention when built with JIT support.

Upstream: BurntSushi/ripgrep, dual-licensed under **Unlicense OR MIT** per the
source tarball's `COPYING`; the `LICENSE-MIT` file's notice line is
`Copyright (c) 2015 Andrew Gallant`. This skill's text is original; behavior
claims below come from probing the binaries, not from upstream docs.

## The default filter, and the `-u` ladder

By default, from one `rg PATTERN dir` invocation you get **only** lines from:

- non-hidden files (dot files and dot directories are skipped),
- files not matching ignore rules: `.gitignore` of the surrounding **git
  repository** (a directory with a `.git`), plus `.ignore` and `.rgignore`
  files, which apply **whether or not a git repo is present**,
- text files - a file with a NUL byte is "binary" and contributes only a
  notice, not its content,
- uncompressed files (`-z/--search-zip` to descend into gzipped files),
- non-symlink traversal (symlinks are not followed without `-L/--follow`).

The escape ladder, measured on a fixture with one hidden file, one
gitignore-ignored file, and one binary file:

- `-u` - adds gitignore-ignored files. **It does not touch hidden files**:
  `-u` in a real repo surfaced the gitignored file but not the dot file.
- `-uu` - additionally searches hidden files.
- `-uuu` - additionally searches binary files - but the binary's matches
  still print as the `binary file matches` notice, not as content. To print
  binary content, add `-a/--text` on top (or use `-a` directly).

The precise single-flag equivalents in 15.2.0:

- `--hidden` (or `-.`) searches hidden files only;
- `--no-ignore` disables **all ignore files** (gitignore and .ignore alike)
  but still skips hidden files;
- `--no-ignore-vcs` disables only the gitignore class; `.ignore` rules stay;
- `--no-require-git` makes `.gitignore` apply even without a `.git` around
  (measured: in a plain directory with a `.gitignore` but no `.git`, rg
  reads the file but applies nothing; adding `--no-require-git` makes it
  filter). This is the doc-vs-intuition trap: `grep -r` in the same place
  would search everything anyway, but an agent that copies a project's
  `.gitignore`-driven expectations into a non-repo directory gets none of it
  silently. `.ignore`/`.rgignore` are the portable choices.
- `--debug` names, per skipped file, exactly which rule and ignore file did
  the skipping (`Ignoring(...): IgnoreMatch(Hidden)`, `IgnoreMatch(Gitignore)
  with from: <file>`), plus the resolved `--hyperlink-format`.

Gitignore rules from parent directories apply when you search a subdirectory
of a repository as the argument (measured on both 14.1.0 and 15.2.0: passing
`<repo>/sub` respects the root `.gitignore`, since only files in the repo's
subtree are relevant). The 15.0 series notably fixed several long-standing
bugs in applying gitignore rules across multiple search roots - behavior
that silently differed across versions before 2025's 15.0.0.

## Search model

- With no path argument: `stdin-data | rg PATTERN` searches stdin; with no
  pipe, rg searches the **current directory recursively**. One file argument
  searches that file; a directory argument recurses (plain `grep` needs `-r`
  for that). Empty stdin yields rc 1.
- Line-oriented: `.` never matches a newline, so patterns never straddle
  lines without `-U/--multiline`. With `-U`, a literal `\n` in the pattern
  joins lines (measured: `AAA\nBBB` matches a two-line block), and
  `--multiline-dotall` makes `.` cross the newline too.
- Regex engine: default is the Rust regex syntax - **no look-arounds, no
  back-references**; a look-ahead is a parse error (rc 2, stderr shows the
  caret position and suggests `-P/--pcre2`), which is present in the release
  builds (`PCRE2 ... available` in `--version`). `-F/--fixed-strings` for
  literal text, `-w/--word-regexp` (matches only word-bounded occurrences:
  `-w apple` skips the `apple` inside `pineapple`), `-x/--line-regexp`.
- Case: default case-sensitive. `-i` insensitive, `-S/--smart-case`
  insensitive only for all-lowercase patterns (any uppercase forces
  sensitivity; `-s` re-forces sensitivity even next to `-S`).
- Combining patterns: multiple `-e PATTERN` are OR'd; `-f FILE` ORs the
  file's lines. **There is no `--and` flag in 15.2.0** (the full help text
  contains no such flag) - AND two conditions by piping: `rg a file | rg b`.
- `-v/--invert-match` selects non-matching lines. `-vf PATTERNS-FILE` inverts
  a pattern file: with an **empty** pattern file, 15.x matches every line and
  14.x matched nothing (measured; this was fixed in 15.0.0).

## Output: piped and TTY output are two different tools

When stdout is **piped** (scripts, agents):

- no color, **no line numbers, no file headers**. Searching one file prints
  the matching lines exactly like grep; searching a directory prefixes each
  line with `path:LINE`. Add `-n` when you need numbers, `-N` to suppress
  them when a TTY would have added them.
- with `--pretty` (`-p`), rg prints the TTY-style result into the pipe:
  colors, line numbers, headers (measured: ANSI present with `--pretty`
  in a pipeline).
- `--vimgrep` prints `path:line:col:LINE` per match (numbers even piped) in
  a format file editors/agents can open line-by-line.

When stdout is a **terminal** (needs a real TTY and a non-`dumb` `TERM`;
`NO_COLOR` also disables color; `--color always` forces it anywhere):
colors, line numbers by default (single files too: `1:match`), file headers
with each match group (`--heading`, multi-file only), relative path display,
and `-` instead of `:` for context lines in `--context` ranges
(measured: `2:match one` followed by `3-l3`). Hyperlinks are off by
default (the resolved hyperlink format is an empty string, shown by
`--debug`); `--hyperlink-format default` emits OSC-8 `file://` links for
file paths - measured on a TTY only; a piped run stays link-free.

Context and counting:

- `-A n` / `-B n` / `-C n` context; non-contiguous groups are separated by
  a `--` line (customizable via `--context-separator`). Contiguous groups
  are merged with no separator.
- `-c/--count` prints, per file, the count of **lines that contain a match**
  (a line with two matches counts once); `--count-matches` counts every
  match (measured on a 3-line file: `one two`/`one one` - `-c` gives 2,
  `--count-matches` gives 3). With `-l` also given, `-l` wins and paths
  are printed (the two flags do not compose).
- `-l/--files-with-matches` prints just the paths (fast). Use
  `--sort path` when you need deterministic order, since the default
  parallel walk order is nondeterministic.
- `-v`'s counterpart `--files-without-match` prints paths with zero matches.
- `-m N` stops a file's search after N **matches** (not lines; a final line
  matching twice closes the cap mid-line).
- `-o/--only-matching` prints only the matched text, one per line, and is
  the base for extraction with `-r/--replace TEMPLATE`: capture groups
  substitute as `$1`/`${1}` (measured: `-o -r '$2/$1'` on
  `(\d{4})-(\d\d)-(\d\d)` turns `2024-09-01` into `09/2024`). Without `-o`,
  `-r` rewrites the matched part inside otherwise-unchanged lines.
- `-0` separates paths/matches with NUL for `xargs -0`.
- `-M N/--max-columns N` replaces match lines longer than N characters with
  the placeholder `[Omitted long matching line]`; add
  `--max-columns-preview` to print the line's head followed by
  `[... omitted end of long line]` instead. Unlimited by default.
- Binary files in a walked directory print `<path>: binary file matches
  (found "\0" byte around offset N)` and rc 0; a single explicitly-named
  binary file prints the notice without the path prefix. `-a/--text` prints
  the raw content instead. Without `-z`, compressed files (measured: a
  `.gz`) are skipped silently and count as no-matches for rc purposes
  (rc 1 with zero hits); with `-z` they are searched with their decompressed
  content.

## Machine-readable output

- `--json` emits one JSON object per line: a `begin` object per file, ONE
  `match` object per LINE containing matches (not per occurrence - a line
  with 2 occurrences stays one object), a closing `end` per file, and one
  final `summary` (measured sequence for 3 occurrences across 2 lines:
  `begin, match, match, end, summary`). Each match's `data` carries
  `path`, `line_number`, `lines.text` (the full line), `absolute_offset`,
  and `submatches` - the per-occurrence array, each entry recording
  `match.text`, `start`, `end` (measured: 2 entries on the 2-hit line).
  `-r/--replace` combines cleanly with `--json` (rc 0, no error, on both
  15.2.0 and 14.1.0) but the per-occurrence entries still record the RAW
  matched text - the JSON never substitutes the replacement, so
  extraction pipelines must not expect replaced values there (measured).
- `--stats` appends a counter block to human output: `matches`,
  `matched lines`, `files contained matches`, `files searched`,
  `bytes printed`, `bytes searched`, seconds spent; `--json` embeds the
  same under `data.stats`. On no match, rc is 1 and a zeroed block still
  prints.
- The `jq` skill's recipes compose well: `rg --json PATTERN PATH | jq -c
  'select(.type=="match") | .data.path.text'`.

## Types and globs

- `rg --type-list` lists the built-in types (224 groups in 15.2.0, one
  `name: *.ext, *.ext2` per line). `-t NAME` searches only that type,
  `-T NAME` excludes it. Define your own on the fly with
  `--type-add 'src:*.rs,*.src'`, then `-t src` (the definition itself does
  not enable the type - you still need `-t`).
- `-g GLOB` includes, `-g '!GLOB'` excludes; `--iglob` is the
  case-insensitive form. Globs and `-g` filters compose with types and with
  `--files` (below). Nested braces inside a glob, e.g. `*.{a,b{1,2}}`, work
  in 15.x; 14.1.0 rejects them with rc 2 (`nested alternate groups are not
  allowed`).
- `rg --files` lists what a search over the given paths would look at -
  the ignore-respecting replacement for `find`: compose with `-g '*.py'`.
  `--files --hidden --no-ignore` lists literally everything.

**The whitelist override asymmetry** (measured; the sharpest filtering trap):

- An **include glob** (`-g '*.txt'`) makes a matching file searchable even
  if it is hidden **or gitignored** - in search mode and in `--files`
  (measured in a real repo: ignored `skipme.txt` appeared because of the
  include glob, from `--files -g '*.txt'` and from `rg -g 'skipme.txt'`).
- A **type filter** (`-t txt`) un-hides matching files but does **not**
  defeat gitignore: in the same repo, `-t txt` searched the hidden dot file
  but never the ignored `skipme.txt`.
- Practical reading: any bare `-g '*.ext'` include silently widens your
  search into ignored and hidden files with that name. If you want ignored
  files excluded while using include globs, pair them with `-g '!<the
  ignored name>'` or add the ignore file's contents explicitly.

## Configuration file

- `RIPGREP_CONFIG_PATH` names a file whose lines are flags applied to every
  invocation (one flag per line; `# comment` lines are ignored). Measured:
  a file containing `--hidden` and `--smart-case` really did un-hide dot
  files. This is why a script's `rg` can behave differently between
  machines with no visible cause - prefer `--no-config` in any probe or
  script that must be self-consistent (measured: with the env var set and a
  valid file, `--no-config` neutralizes it).
- A missing file in `RIPGREP_CONFIG_PATH` is **fail-open**: rg prints
  `failed to read the file specified in RIPGREP_CONFIG_PATH` to stderr and
  the search proceeds normally, rc 0. Treat a warning in scripts as an
  environment smell, not a failure.

## Exit codes

- `0` - at least one match (or `--files`/`--type-list` listings).
- `1` - search ran fine, zero matches.
- `2` - error: unparsable regex (`regex parse error` on stderr with caret
  and a hint to try `-P`), a missing path (complained once on stderr in one
  of two wordings - either `rg: <path>: No such file or directory (os error
  2)` or, when a lone path argument has nothing to search,
  `IO error for operation on <path>: ...`).
- Mixed valid and missing path arguments: the existing paths are still
  searched and matches are printed, but rc is 2.
- `--no-messages` silences the error text but **keeps rc 2** - do not
  use stderr emptiness as an error check; check rc.
- `-q/--quiet` prints nothing and exits on the first match - the cheapest
  existence probe. Measured on 15.2.0: `-q --files-without-match` returns
  rc 0 when the file does NOT contain the pattern (a 15.0.0 fix; some
  older builds inverted this rc).

## Recipes

Which files mention it, deterministically, ignoring nothing by mistake:

```bash
set -e
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
printf 'TODO: rewrite parser\nuse parser\n' > "$tmp/a.rs"
printf '// clean file\n' > "$tmp/b.rs"
out=$(rg -l 'parse' "$tmp" --sort path)
test "$out" = "$tmp/a.rs"
test "$(rg --files "$tmp" | wc -l)" = 2
echo "recipe-1-ok"
```

Extract every capture group's value with -o -r (and count the difference
between lines-with-match and matches):

```bash
set -e
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
printf 'ship: 2024-09-01 gate: 2025-10-15\nnone\n' > "$tmp/dates.txt"
rg -o -r '$2/$1' '(\d{4})-(\d\d)' "$tmp/dates.txt" > "$tmp/out.txt"
test "$(cat "$tmp/out.txt")" = "09/2024
10/2025"
test "$(rg -c 'ship|gate' "$tmp/dates.txt" | rg -o '\d+$')" = 1
test "$(rg --count-matches 'ship|gate' "$tmp/dates.txt")" = 2
echo "recipe-2-ok"
```

Machine-readable hits through --json (jq from the jq sibling skill):

```bash
set -e
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
printf 'one two\none one\nx\n' > "$tmp/c.txt"
rg --json 'one' "$tmp/c.txt" \
  | jq -c 'select(.type=="match") | {line: .data.line_number, hits: (.data.submatches | length)}' \
  > "$tmp/hits.jsonl"
test "$(wc -l < "$tmp/hits.jsonl")" = 2
head -1 "$tmp/hits.jsonl" | rg -q '"hits":1'
tail -1 "$tmp/hits.jsonl" | rg -q '"hits":2'
echo "recipe-3-ok"
```

## Versions and divergences measured

- 15.2.0, official static musl build (rev `e89fff89ac`): the reference for
  every claim above.
- 15.2.0, official `.deb` build: same rev, all probes byte-identical.
- 15.2.0, conda-forge build (rev `78115297cd`): all probes identical except
  timing fields inside `--json`/`--stats`.
- 14.1.0-1 (Ubuntu 24.04 `universe`, `-simd-accel,+pcre2`, PCRE 10.42):
  differs measured in two places - nested-brace globs are rejected with
  rc 2 (`nested alternate groups are not allowed`) and `-vf empty-patterns`
  matches nothing (rc 1) instead of everything. Everything else probed
  above behaves identically on both versions, including the `-u` ladder,
  the requires-repo gitignore rule, `-M` placeholders, the count flags,
  and `-r` alongside `--json`.

## Also useful here

- `fd` - list files and filenames with the same ignore-aware filtering.
- `bat` - render single files with highlighting after a `rg -n` hit.
- `jq` - post-process `rg --json` output.