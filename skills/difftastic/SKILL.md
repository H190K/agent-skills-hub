---
name: difftastic
version: 1.0.0
description: "Use when a line diff buries the real change under moved code or reformatting, or when a machine-readable diff is needed: install difftastic (`difft`), route git through it (diff.external / GIT_EXTERNAL_DIFF), the exit-code contract (0 by default even with differences, --check-only --exit-code as a silent CI gate), the fallback headers that flip to text diff (parse-error / byte / graph limits), the DFT_UNSTABLE=yes-gated JSON mode, and directory / conflict-marker / binary / override handling."
---

# difftastic — a structural diff that understands syntax

`difft` compares files by their syntax trees, not by lines. Tokens that
relocate but keep their meaning still match; real changes get highlighted
per token. Where a normal diff says "everything moved", difftastic says
"what actually changed". It supports 62 languages via bundled tree-sitter
parsers (v0.72.0; F#, Verilog and Smali were removed in that release).

## Install

Any one of these provides the `difft` binary on PATH:

```bash
cargo install difftastic          # from source (the crate name)
```

or grab a release binary from
`https://github.com/Wilfred/difftastic/releases` (e.g.
`difft-0.72.0-x86_64-unknown-linux-gnu.tar.gz`), or install via
`conda install -c conda-forge difftastic`. There is **no pip package**
(pypi.org/pypi/difftastic 404s). The full manual lives at
`https://difftastic.wilfred.me.uk/`.

## Invocations (all of these are real)

```bash
difft old.py new.py        # two files, side-by-side tree diff
difft old-dir/ new-dir/    # two directories (see "Directory mode" below)
difft conflicted.py        # one file containing conflict markers
git -c diff.external=difft diff        # git integration, see "Git integration"
```

The single-argument conflict mode diffs the two conflicting states; the
header explains the direction: `Showing the result of replacing every
conflict in 'HEAD' with 'branch'.` (new state = the LAST marker block
side). `--display side-by-side-show-both` forces two columns even for a
pure-addition diff, which plain `side-by-side` collapses to one.

## The exit-code contract

Measured on 0.72.0 (conda-forge and release binaries agree):

- **Default: rc 0 even when the files differ.** Only a missing path (rc 2,
  stderr `No such file: <path>`) and the JSON-mode refusal (rc 2) exit
  nonzero by default.
- `--exit-code`: rc 1 when there are *syntactic changes*. Comments count
  as changes (a comment-only diff gives rc 1) unless `--ignore-comments`
  is passed (then rc 0). Files with no parsed language count *byte*
  changes — a changed binary gives rc 1.
- `--check-only`: prints one report line per file (`<path> --- <Lang>`
  then `Has syntactic changes.` / `No changes.` on stdout; no actual diff)
  and stays fast. Combine with `--exit-code` for a CI guard: rc 0 =
  identical, rc 1 = changed. Files with no parsed language report
  `Has changes.` instead (byte comparison).

```bash
difft --check-only --exit-code old.py new.py && echo no-changes || echo changed
```

## Fallback headers: when the "structural" diff becomes a text diff

When tree diffing is impossible or too expensive, difftastic falls back to
a line-oriented diff and *says so inside the header line* — never miss
these:

- Garbage content in a parsed extension (default `--parse-error-limit 0`):
  `probes/g2.py --- Text (5 Python parse errors, exceeded DFT_PARSE_ERROR_LIMIT, first at 1:0)`
- Input over `--byte-limit` (default 1000000 bytes):
  `big2.py --- Text (1.2 MiB exceeded DFT_BYTE_LIMIT)`
- Alignment graph over `--graph-limit` (default 3000000):
  `big2.py --- Text (exceeded DFT_GRAPH_LIMIT)`

(In directory mode the parse-error header additionally ends with
`in initial file`.) A fallback header means the per-token alignment you
came for did not happen — either fix the input/limits or accept the
line-oriented result.

## The two different "nothing changed" messages

- `No changes.` — the inputs are equal after comparison.
- `No syntactic changes.` — a structural pass found nothing syntactic:
  e.g. differences limited to comments under `--ignore-comments`, or
  line-ending-only differences under `--strip-cr off`.

`--strip-cr` (default `on`) removes `\r` before diffing. Turn it `off` and
line-ending differences inside multiline text (HTML bodies, triple-quoted
string literals) surface as real changes; identical code with different
line endings still reports `No syntactic changes.`

## Piped vs TTY output

- **Piped output is plain text**: zero ANSI escapes on the same fixture
  that a TTY colors (measured 0 vs 106 escapes at 80 columns). Force with
  `--color always` (works in pipelines), `--color never` always suppresses.
- Width: piped output defaults to 80 columns — two 39-character content
  columns plus the gutter. `--width 40` wraps at 19/19. On a TTY the width
  is detected from the terminal (a 40-column pty produces the same 19/19
  wrap). Wrapped continuation lines are marked with `.` in the number gutters.
- **There is no pager.** Long output pours straight through a TTY and every
  byte lands (a 24 KB diff streamed through a 24-row pty, rc 0, immediate
  exit). Never wait on "q to quit" from difftastic.
- `--background dark` (default) and `--background light` pick different
  palettes (byte-different color output measured); `--syntax-highlight off`
  skips token coloring.

## JSON mode — gated behind DFT_UNSTABLE

```bash
difft --display json old.py new.py          # refused
# stderr: JSON output is an unstable feature and its format may change in
# future. To enable JSON output, set the environment variable DFT_UNSTABLE=yes.
# (exit code 2, empty stdout)

DFT_UNSTABLE=yes difft --display json old.py new.py
```

Measured shape (one compact single-line JSON object per invocation for a
two-file diff):

- Top keys: `path` (the NEW argument), `language`, `status`,
  `aligned_lines`, `chunks`.
- `status` ∈ changed / created / deleted / unchanged. An unchanged file is
  just `{...,"status":"unchanged"}` — no `chunks`/`aligned_lines` keys.
- `chunks[]` carry the changed lines with intra-line detail:
  `{"lhs":{"line_number":4,"changes":[{"start":15,"end":19,"content":"True","highlight":"keyword"}]},"rhs":{...}}`
  (0-indexed byte offsets, one change per moved token).
- `aligned_lines` pairs every displayed row as `[lhs, rhs]` line numbers,
  0-indexed integers; an unpaired side is `null` (`[[0,0],[null,1]]`).
  Additions-only input yields `aligned_lines: null` with `status:created`.
- In directory mode the top level is a **JSON array** of these objects, in
  walk order (use `--sort-paths` for sorted).

## Languages, overrides and binaries

`--list-languages` prints 62 language names (one per line) each followed by
a line of recognized extensions. Detection is by file extension; an
unknown extension diffs as plain text. To force or re-route a language:

```bash
difft --override='*.c:C++' old.c new.c      # names are case-insensitive
difft --override='*.conf:text' a.conf b.conf  # the "text" pseudo-language
```

Multiple `--override` flags are allowed (first match wins); env mirrors
`DFT_OVERRIDE_1` … `DFT_OVERRIDE_9` exist. Note difftastic does **not**
refuse "binary-looking" input: two small binary blobs with an unknown
extension diff as raw text. Force binary treatment with
`--override-binary='*.gz' a.gz b.gz`, which emits a one-liner instead:
`Binary file modified (old: 9 B, new: 10 B).`

## Context, tabs and debug dumps

- `-c/--context LINES` (default 3) controls unchanged context shown.
- `--tab-width 4` is the default tab expansion.
- `--dump-syntax PATH` (difftastic's own node/position tree),
  `--dump-ts PATH` (raw tree-sitter tree) and `--dump-syntax-dot`
  debug a single file's parse — invaluable when a diff surprises you: a
  parse you disagree with is visible here, and parse errors are the
  fallback story above.
- Every flag has a `DFT_*` env mirror (`DFT_WIDTH`, `DFT_DISPLAY`,
  `DFT_CONTEXT`, `DFT_TAB_WIDTH`, ...) for shell defaults.

## Git integration

All three forms measured working on git 2.4x with an unstaged or staged
change:

```bash
git -c diff.external=difft diff            # worktree vs index
git -c diff.external=difft show --ext-diff # needs --ext-diff for show/log
GIT_EXTERNAL_DIFF=difft git diff           # env-variable equivalent
```

The upstream manual recommends aliases (one logical setup):

```ini
[alias]
    dlog = -c diff.external=difft log --ext-diff
    dshow = -c diff.external=difft show --ext-diff
    ddiff = -c diff.external=difft diff
```

If `difft` is not on git's PATH the whole diff dies with git's own
`error: cannot run difft: No such file or directory` /
`fatal: external diff died, stopping at <file>` (exit code 128) — install
first. In GIT_EXTERNAL_DIFF mode difftastic accepts git's
7-argument `<path old-file old-hex old-mode new-file new-hex new-mode>` and
9-argument calling conventions (documented in `--help`). Prefer the
`diff.external` route over wrapping `git diff` output in difftastic: piping
a unified patch into `difft` is not an input mode — it diffs the two
arguments or, with one argument, conflict markers.

## Verify the install (run this after setup)

Measured to exit 0 on clean scratch state (needs only `difft` + `python3`
on PATH; every call is stdin-safe):

```bash
set -eu
T=$(mktemp -d)
D=$(command -v difft)
printf '%s\n' 'def f(path):'    '    return path[0]' \
              'def g():'        '    print("done")' > "$T/a.py"
printf '%s\n' 'def f(path):'    '    return path[-1]' \
              'def g():'        '    print("finished")' > "$T/b.py"
printf 'def h(( broken @@@\n' > "$T/bad1.py"
printf 'def i())) garbage\n'  > "$T/bad2.py"

out=$("$D" "$T/a.py" "$T/b.py")
case "$out" in *'--- Python'*) : ;; *) echo "FAIL: no language header"; exit 1 ;; esac
set +e
"$D" "$T/a.py" "$T/b.py" >/dev/null 2>&1; rcdef=$?
set -e
test "$rcdef" -eq 0 || { echo "FAIL: default rc $rcdef, expected 0"; exit 1; }
set +e
"$D" --exit-code "$T/a.py" "$T/b.py" >/dev/null; rcx=$?
set -e
test "$rcx" -eq 1 || { echo "FAIL: --exit-code rc $rcx"; exit 1; }
set +e
"$D" --check-only --exit-code "$T/a.py" "$T/b.py" > "$T/co.out" 2> "$T/co.err"; rcc=$?
set -e
test "$rcc" -eq 1 || { echo "FAIL: check-only rc $rcc"; exit 1; }
grep -q 'Has syntactic changes.' "$T/co.out" \
    || { echo "FAIL: check-only message (out: $(cat "$T/co.out"))"; exit 1; }
cmp -s /dev/null "$T/co.err" || { echo "FAIL: check-only stderr"; exit 1; }
set +e
"$D" --check-only "$T/a.py" "$T/a.py" > "$T/cu.out" 2>/dev/null; rcu=$?
set -e
test "$rcu" -eq 0 || { echo "FAIL: check-only unchanged rc $rcu"; exit 1; }
grep -q 'No changes.' "$T/cu.out" || { echo "FAIL: unchanged message"; exit 1; }
set +e
"$D" "$T/a.py" "$T/no-such.py" > /dev/null 2> "$T/miss.err"; rcm=$?
set -e
test "$rcm" -eq 2 || { echo "FAIL: missing-file rc $rcm"; exit 1; }
grep -q 'No such file' "$T/miss.err" || { echo "FAIL: missing-file message"; exit 1; }
set +e
"$D" "$T/bad1.py" "$T/bad2.py" > "$T/fb.out" 2>/dev/null; rcf=$?
set -e
test "$rcf" -eq 0 || { echo "FAIL: fallback rc $rcf"; exit 1; }
grep -q 'exceeded DFT_PARSE_ERROR_LIMIT' "$T/fb.out" \
    || { echo "FAIL: parse fallback header"; exit 1; }
set +e
"$D" --display json "$T/a.py" "$T/b.py" > /dev/null 2> "$T/j.err"; rcj=$?
set -e
test "$rcj" -eq 2 || { echo "FAIL: json gate rc $rcj"; exit 1; }
grep -q 'DFT_UNSTABLE=yes' "$T/j.err" || { echo "FAIL: json gate message"; exit 1; }
DFT_UNSTABLE=yes "$D" --display json "$T/a.py" "$T/b.py" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d["status"] == "changed" and d["language"] == "Python"
assert set(d["aligned_lines"][0]) == set([0])
'
rm -rf "$T"
echo difftastic-verified
```

Related in this library: `delta` renders the same diffs as a
syntax-highlighted pager (line diffing, opposite trade-off), `jq` for
further slicing of the JSON display, and `tokei` for plain line counts.
