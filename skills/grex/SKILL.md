---
name: grex
version: 1.0.0
description: "Use when test cases — log samples, filenames, field formats — must become a regex by example: grex. Covers the flag-placement trap (flags after the first test case silently become test cases at rc 0), always-on anchors, opt-in repetition detection with its min-repetitions/min-substring-length knobs, the (?i)/(?x)/\u{...} portability matrix across Python/JavaScript, `-f -` reading the filename from stdin, the rc-101 panic on empty input, and the pre-1.4.2 rc-0-on-error divergence."
---

# grex — generate regular expressions from test cases, with the traps measured

grex (pemistahl/grex, Apache-2.0, © Peter M. Stahl per its own `--help` banner)
turns concrete test cases into a regex that matches exactly those cases — the
fast way to build a matcher from real log lines, IDs or field values. Every
claim below was measured on the **official 1.4.6 release binary**
(`grex-v1.4.6-x86_64-unknown-linux-musl.tar.gz`).

## Install and verify

- Extract the release tarball — the executable sits at the **root of the
  tarball**, not in `bin/`. `cargo install grex` is the from-source route.
- The release page ships **no checksum assets**, so cross-check behaviorally:
  conda-forge's 1.4.6 build (`conda install -c conda-forge grex`) produced an
  md5-identical `--help` **and** an identical probe set against the release
  binary.
- **Name collision: `pip install grex` is NOT the CLI.** The PyPI package
  (`grex` 1.0.2, from the same repo) is the **Python bindings** for the Rust
  library — import it with `import grex`, do not expect a `grex` command.
  conda-forge's `grex` **is** the CLI binary. Pick intentionally.
- `grex --version` prints a plain `grex 1.4.6` line (no commit suffix).

## The core model

- Output is a **single line on stdout** (multi-line only in `-x` verbose mode)
  and is **anchored `^…$` by default** — the generated regex matches exactly
  the given cases and nothing else.
- Structural merging needs **no flag**: common prefixes, suffixes and
  char-classes are detected automatically. `grex a b c` → `^[a-c]$`, and the
  shared tail of `midway beta / zeta alpha` is extracted:
  `^(?:midway bet|zeta alph)a$`.
- Case differences become a **case-insensitive character class**, not a flag:
  `grex foo Foo` → `^[Ff]oo$`.
- Regex metacharacters in the input are escaped automatically: `a.b / a?b` →
  `^a[.?]b$`; `^A / $B` → `^(?:\$B|\^A)$`; `a\b` → `^a\\b$`;
  `a[1] / b[1]` → `^[ab]\[1\]$`.
- Same input set always yields the **same regex**: alternatives and classes
  come out sorted (`9x 8x 10x` → `^(?:10|[89])x$`). Output is safe to
  snapshot-test.

## Read this first: flags die after the first test case

Options must come **before the first positional test case**. Everything
hyphen-leading that follows a test case — even a *known* flag — is swallowed
as just another test case, and the exit code stays **0**:

- `grex a1b -d` → `^(?:a1b|\-d)$` (rc 0) — `-d` is *inside the regex*, the
  digit class was never applied; the long form `--digits` behaves the same.
- Unknown flags never fail anywhere: `grex -q a` → `^(?:\-q|a)$` (rc 0).
- Even a bare `--` after the first positional becomes a test case:
  `grex a -- d` → `^(?:\-\-|[ad])$`.

Two corollaries worth committing to habit:

- **Never trust rc 0** from grex — assert the produced regex (run it against
  the original cases) instead of the exit code.
- Hyphen-leading test cases need **no `--` escape at all**:
  `grex -foo -bar` → `^\-(?:bar|foo)$`. It simply works.

## Anchors, case, capture groups

- Anchors are always added. `--no-start-anchor`, `--no-end-anchor` and
  `--no-anchors` remove them (`grex --no-anchors a b` → `[ab]`). Use
  `--no-anchors` whenever the result is spliced into a larger expression.
- `-i`/`--ignore-case` prepends the **inline flag** `(?i)` instead of folding
  chars: `grex -i foo Foo` → `(?i)^foo$`.
- `-g`/`--capture-groups` turns non-capturing groups into capturing ones:
  `grex -i -g one1 two2 three3` → `(?i)^(t(hree3|wo2)|one1)$`.

## Portability matrix — measure the engine before shipping the regex

| syntax in grex output | Python `re` | JavaScript |
| --- | --- | --- |
| `(?i)` prefix | works (measured `fullmatch`) | SyntaxError — use the `/i` flag |
| `(?x)` verbose prefix | works | no such thing |
| `\u{f6}` (`-e` spelling) | compile error | matches **only with the `u` flag** |
| `\u{d83d}\u{de00}` surrogate pair | compile error | matches with and without `u` |

Both portability columns were measured. For Python, rewrite `\u{hhhh}` to
`\uhhhh` (or `\xhhhh`); grex's escaping is Rust-regex spelling.

## Repetition detection is opt-in

- By default repetitions stay literal: `grex ABCABCABC` → `^ABCABCABC$`.
  With `-r`/`--repetitions`: `^(?:ABC){3}$`.
- Two knobs bound the conversion, both **default 1**: `--min-repetitions`
  and `--min-substring-length`. Measured on `aaabaabx`: default `-r` →
  `^a(?:a{2}b){2}x$`, but `--min-repetitions 2` suppresses that conversion →
  `^a{3}baabx$`; `--min-substring-length 4` suppresses short-substring
  conversions on `fofoobarfoobaz`.

## Shorthand class flags and precedence

`-d`/`--digits` and `-D`/`--non-digits`, `-s`/`--spaces` and `-S`/`--non-spaces`,
`-w`/`--words` and `-W`/`--non-words`. The help's precedence chains are real —
measured on `one1 two2` with `-d -w` (both set): `^\w\w\w\d$` — digits become
`\d`, everything else `\w`. With `-s -d` on `a b1c / x y2z`:
`^(?:a\sb\dc|x\sy\dz)$` — spaces `\s`, digits `\d`, others literal.

## Three input modes, one trap

- Positional test cases, separated by blank space.
- A single `-` reads **test cases from stdin** (newline-separated works:
  `printf 'foo bar\nbaz qux\n' | grex -` → `^(?:baz qux|foo bar)$`).
- `-f FILE` reads **one test case per line** (`abc\nabd` → `^ab[cd]$`).
- **`-f -` reads the *filename* from stdin** — a different object from
  input mode `-`! `echo ./samples.txt | grex -f -` opens `samples.txt` and
  reads its lines as test cases. Mixing the two `-` meanings up silently
  builds a regex out of the wrong text.

## Empty input panics (rc 101), not errors

Any zero-test-case run **panics** and exits `101`:

```
thread 'main' (…) panicked at …/src/builder.rs:48:13:
No test cases have been provided for regular expression generation
```

Measured both ways: `printf '' | grex -`, and `-f` on an empty file. In
pipelines, pre-check that the sample list is non-empty before invoking grex.

## Exit taxonomy (1.4.x, since the 1.4.2 fix)

- **0** — success, *including* the silent flag-as-test-case traps above and
  missing-`--no-*`-flag typos.
- **1** — runtime errors, e.g. a missing file path prints
  `error: the specified file could not be found`.
- **2** — clap usage errors: `grex` with no arguments lists the required
  `--file <FILE>` / `<INPUT>...` plus the usage line and exits 2.
- **101** — the empty-input panic described above.

## Colorize is not TTY-gated

`-c`/`--colorize` emits ANSI escapes **even when piped** (`grex -c … | cat -v`
shows the bytes; opposite of the common TTY-gated family). Without `-c`,
output is plain on both a TTY and a pipe. `-c` colors only the skeleton
(anchors, groups, quantifiers) — the literal text stays plain — so capture
logs of `-c` runs carry escape bytes into whatever parses them next.

## Verbose mode and recipes

`-x`/`--verbose` produces a multi-line free-spacing regex with a `(?x)`
prefix (Python `re` compiles it as-is; verified against the real output):

```
(?x)
^
  (?:
    ABC
  ){3}
$
```

Derive a matcher from real samples and validate the round-trip before using
it anywhere:

```bash
grep -oE '[a-z]{3}-[0-9]{3}' app.log | sort -u > samples.txt
rex=$(grex -f samples.txt)
python3 -c "
import re
raw = open('samples.txt').read().split()
bad = [s for s in raw if not re.fullmatch(rex, s)]
print('unmatched:', bad[:5] or 'none')
"
```

Splice into a bigger expression without anchors:

```bash
id=$(grex --no-anchors AB-123 AB-999)
grep -n "$id" events.log
```

## Related

- [`sd`](skills/sd/SKILL.md) — derive the pattern with grex, apply it in bulk
  with sd; both benefit from the same measure-first discipline.
- [`jq`](skills/jq/SKILL.md) — when the target engine differs, check its
  regex dialect against the portability matrix above.

## Provenance and divergences

- All behavior measured on the official
  `grex-v1.4.6-x86_64-unknown-linux-musl.tar.gz` binary. Conda-forge's 1.4.6
  linux-64 build matched the release binary md5-for-md5 on `--help` and on a
  probe set (structural merging, case class, `-d`, `-r`, `-x`, stdin mode).
- The release page carries no per-asset checksums; the behavioral parity
  check above is the substitute.
- Divergences probed on older official musl builds: **1.2.0** (2021) has no
  stdin/pipeline mode — `-` arrived in 1.3.0 — and no anchor flags:
  `--no-anchors` was silently swallowed as a test case even back then, so the
  flag trap is old. **1.4.1** (2022) printed the same
  `error: the specified file could not be found` for a missing `-f` path but
  exited **0** — the rc-1 runtime error class arrived in 1.4.2. The
  empty-input panic exists on both (only the source line differs).
- 1.4.3 (2023) introduced the Python bindings; 1.4.5 added type stubs; 1.4.6
  supports Unicode 16.0 and Python 3.14 for the bindings.
- Skill text is original; measured behavior only, no upstream prose adapted.

## Verify block

```bash
set -e
bin=$(command -v "${GREX_BIN:-grex}") || { echo 'FAIL: grex not installed'; exit 1; }
"$bin" --version </dev/null | grep -F 'grex' >/dev/null
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
out=$("$bin" a b c); [ "$out" = '^[a-c]$' ] || { echo "FAIL: basic, got $out"; exit 1; }
out=$("$bin" foo Foo); [ "$out" = '^[Ff]oo$' ] || { echo "FAIL: case class, got $out"; exit 1; }
out=$("$bin" 'a.b' 'a?b'); [ "$out" = '^a[.?]b$' ] || { echo "FAIL: escaping, got $out"; exit 1; }
out=$("$bin" -r ABCABCABC); [ "$out" = '^(?:ABC){3}$' ] || { echo "FAIL: -r, got $out"; exit 1; }
out=$("$bin" -d one1 two2); [ "$out" = '^(?:one|two)\d$' ] || { echo "FAIL: -d, got $out"; exit 1; }
out=$("$bin" -i foo Foo); [ "$out" = '(?i)^foo$' ] || { echo "FAIL: -i, got $out"; exit 1; }
out=$(printf 'foo bar\nbaz qux\n' | "$bin" -)
[ "$out" = '^(?:baz qux|foo bar)$' ] || { echo "FAIL: stdin, got $out"; exit 1; }
# the flag-placement trap: -d after a positional is a silent test case, rc 0
out=$("$bin" a1b -d); [ "$out" = '^(?:a1b|\-d)$' ] || { echo "FAIL: trap, got $out"; exit 1; }
out=$("$bin" -q a); [ "$out" = '^(?:\-q|a)$' ] || { echo "FAIL: unknown flag, got $out"; exit 1; }
out=$("$bin" -foo -bar); [ "$out" = '^\-(?:bar|foo)$' ] || { echo "FAIL: hyphen cases, got $out"; exit 1; }
# -c carries ANSI bytes even piped; without -c a pipe stays plain
esc=$("$bin" -c -r ABCABCABC </dev/null | tr -d -c '\033' | wc -c)
[ "$esc" -ge 1 ] || { echo "FAIL: -c must emit escapes on a pipe"; exit 1; }
esc=$("$bin" -r ABCABCABC </dev/null | tr -d -c '\033' | wc -c)
[ "$esc" -eq 0 ] || { echo "FAIL: plain pipe must be escape-free"; exit 1; }
# exit taxonomy: empty input panics 101, missing file 1, no args 2
: > "$d/empty"
rc=0; "$bin" -f "$d/empty" >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 101 ] || { echo "FAIL: empty panic rc, got $rc"; exit 1; }
rc=0; "$bin" -f "$d/nope" >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 1 ] || { echo "FAIL: missing file rc, got $rc"; exit 1; }
rc=0; "$bin" >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 2 ] || { echo "FAIL: no-args rc, got $rc"; exit 1; }
# python round-trips of the (?i) and (?x) dialects
if command -v python3 >/dev/null 2>&1; then
  "$bin" -i foo Foo > "$d/i.re"
  "$bin" -x -r ABCABCABC > "$d/x.re"
  python3 - "$d/i.re" "$d/x.re" <<'PY'
import re, sys
i_pat = open(sys.argv[1]).read().strip()
x_pat = open(sys.argv[2]).read().strip()
assert re.fullmatch(i_pat, 'Foo') and re.fullmatch(i_pat, 'FOO')
assert re.fullmatch(x_pat, 'ABCABCABC') and not re.fullmatch(x_pat, 'ABC')
print('python round-trips OK')
PY
fi
echo grex-verified
```
