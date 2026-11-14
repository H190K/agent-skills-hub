---
name: yq
description: "Use when scripting mikefarah/yq or when its output surprises you — querying, editing, merging and converting YAML, JSON, XML, CSV/TSV, TOML, INI, properties. Measured traps: default output re-types quoted numbers (-r=false fixes), double-quoted expression strings only, gsub/splits/getpath don't exist, sub is global, RE2 forbids lookaround, -i pushes every evaluated doc into the first file, the merge-anchor spec-flag divergence, and the apt/conda python-yq name collision."
version: 1.0.0
---

# yq

Measured on the official Mike Farah `yq` **v4.54.3** release binary (linux_amd64, sha256
verified against the GitHub per-asset digest and the release `checksums` file), cross-checked
against conda-forge `go-yq` 4.54.3 whose `--version` and `--help` output are md5-identical to
the release binary, with divergence rows measured on Ubuntu noble's apt `yq` build. Upstream
MIT (LICENSE holder: "Copyright (c) 2017 Mike Farah"). The gitbook docs describe intent; this
file records what the binary actually does.

## First: is your yq the right yq?

**Two unrelated tools share this name.** Mike Farah's yq is a Go one-binary processor with a
custom expression language. The other is Kislyuk's python yq — a jq wrapper that transcodes
YAML to JSON and pipes it into jq (it also ships `xq` and `tomlq` binaries).

- `apt install yq` on Ubuntu noble gets the **python jq wrapper** (measured: `yq 3.1.0-3`,
  package description "Command-line YAML processor - jq wrapper for YAML documents", installs
  `yq`, `xq`, `tomlq`). None of this file applies to it.
- `conda install yq` also installs the python wrapper (conda-forge `yq` 4.4.5 measured).
- The conda-forge package for Mike Farah's tool is **`go-yq`** (`go-yq` 4.54.3; same-name
  parity: its binary printed `--version` and `--help` md5-identical to the official release).
- Fingerprint test — Mike Farah's yq prints exactly:
  `yq (https://github.com/mikefarah/yq/) version <semver>`

Scripts that need a guaranteed build should download the release binary (below), never rely on
the package name.

## Install and verify

Download the static binary from the GitHub releases page, then verify. The release publishes a
`checksums` sidecar whose final whitespace-separated column is sha256 (an older line in that
file documents the column order), plus a per-asset `sha256:` digest on the API object:

```bash
curl -sL -o yq https://github.com/mikefarah/yq/releases/download/v4.54.3/yq_linux_amd64
chmod +x yq
grep 'yq_linux_amd64 ' checksums | awk '{print $NF}'   # last column = sha256
sha256sum yq
./yq --version
```

## Invocation model

- Bare `yq '.a.b' file.yml` runs `eval` (per document). Subcommands: `eval`/`e`,
  `eval-all`/`ea`. An expression is optional: `yq file.yml` prints the document.
- Files come after the expression; `-` is a stdin file usable anywhere in the list
  (`yq '.a' f1.yml - f3.yml`).
- `-n` (`--null-input`) evaluates without input — the way to construct documents:
  `yq -n '.a.b = "cat"'`.
- The expression language accepts **double-quoted strings only**. Single quotes are a lexer
  error: `yq -n ".a.b.c = 'cat'"` fails with `1:10: lexer: invalid input text "'cat'"`.
- A bare word expression is also a lexer error (`yq x.yml file` →
  `lexer: invalid input text "x.yml"`), and an expression that looks like a path to an existing
  file can be mistaken for one — `--expression '.a'` and `--from-file expr.txt` force clarity.
- When `-p` sets an explicit input format but `-o` is omitted, yq **warns on stderr** and falls
  back to yaml: `yq default output is now 'auto' (based on the filename extension). Normally yq
  would output 'csv', but for backwards compatibility 'yaml' has been set. Please use -oy to
  specify yaml, or drop the -p flag.` Setting both (`-p csv -o csv`) silences it.
- Exit codes are coarse: parse errors, lexer errors, missing files and unknown flags all exit
  **1** (only `--help` prints usage and exits 0). `yq -e` (`--exit-status`) makes no-match,
  `null` and `false` results exit 1 with `Error: no matches found` on stderr — while stdout
  still carries the per-document `null` lines. For shell logic: capture rc AND parse stdout.

## The default-output type trap (unwrapScalar)

`-r` / `--unwrapScalar` defaults to true for yaml output: scalars print bare — quotes, colors
and comments stripped. A quoted numeric string therefore re-types on the next parse:

```bash
yq '.b' f.yml            # prints: 5        (f.yml has b: "5")
yq '.b' f.yml | yq tag   # measured: !!int  — the "5" silently became a number
yq -r=false '.b' f.yml   # prints: "5"
yq -r=false '.b' f.yml | yq tag  # measured: !!str
```

Strings that only look special (bool-like, date-like: `"true"`, `"2024-01-01"`) unwrap the same
way. Any downstream `yaml`/`json` consumer re-types these. **When the value matters beyond
printing, run with `-r=false`** (or `--unwrapScalar=false`). The same stripping also removes
line comments from scalar output.

## Formats

Input auto-detects from the file extension (unknown or stdin defaults to yaml); output auto
follows the input extension (so `yq '.a.b' file.json` prints json). Both accept the flags:
`-p/--input-format` and `-o/--output-format` over
`yaml|kyaml|json|props|csv|tsv|xml|toml|hcl|ini|lua|shell|base64|base64url|uri`.

Per-format behaviors measured on 4.54.3:

- **YAML is round-trip honest**: comments (header, line, foot) and anchors/aliases survive a
  read-print unchanged; `-I` sets indent (default 2), `-c` uses compact sequence indent, `-P`
  idiomatic style.
- **JSON output drops comments silently** — no warning; json also always quotes strings.
- **XML**: attributes become `+@name` keys, element text `+content`, empty elements parse to
  null; the reverse direction renders repeated map keys as repeated sibling elements. Namespaced
  attributes surface as `+@xmlns:n` with the default `--xml-keep-namespace` on. Prefixes are
  configurable (`--xml-attribute-prefix`, `--xml-content-name`, `--xml-proc-inst-prefix`...) and
  `--xml-strict-mode` fails closed on malformed input.
- **CSV/TSV**: input maps each row over a header; values auto-parse by default (`30`, `"42"` both
  become numbers — `--csv-auto-parse=false` `--tsv-auto-parse=false` keep strings). Output
  expects an array of scalar records; nested arrays/objects as cells are refused
  (`csv encoding only works for arrays of scalars (string/numbers/booleans), child[1] is a
  !!seq`). A null cell prints the literal text `null`. `--csv-separator` changes the delimiter.
- **Properties**: on input every value is a **string** (`server.port=8080` parses as
  `"8080"`), comments survive, and dotted keys nest — but array syntax `list[0]=x` stays a
  literal flat key, it does not build a list. Output flattens back to `server.port = 8080`,
  array indexes as `list.0 = x`, and numeric-looking strings lose their quotes
  (`b = 5` from `"5"`) — a props round trip re-types numbers. `--properties-array-brackets`
  switches output to `a[0] = x` style.
- **TOML/HCL/INI**: input works (`-p toml`/`-p ini`; INI needs `[section]` headers, keys may be
  split by `=` or `:` per `--ini-key-value-delimiters`). Table-style outputs (toml, hcl) render
  nested maps as `[table]` blocks **after** the top-level scalars — key order is reshuffled, not
  source order. HCL prints string values unquoted. INI output needs sections (`-o ini` with
  `.sec = {..}`).
- **shell** output emits `KEY=VALUE` lines with underscore-joined paths (`a.b` → `a_b`, array
  item → `arr_0`); a top-level scalar becomes a variable named `value`. Values are single-quoted
  and escaped by default (measured: `"a b; rm -rf x | cat"` → `value='a b; rm -rf x | cat'`),
  eval-safe. `--security-force-never-escape-shell-output` is the explicit unsafe opt-out.
- **lua/base64/url**: `-o lua` wraps in `return {...};`; `-o base64` / `-o uri` operate on
  string scalars (uri uses `+` for spaces).

## Merging and the merge-anchor flag

`*` deep-merges maps (RHS values win, nested maps merge); `+` is a shallow merge that replaces
whole values; `*= rhs` is the compound form (`yq '. *= load("file2.yml")' f1.yml` — note
`load()` parses **YAML-format** files; loading a toml/csv file yields raw text and
`cannot multiply !!str with !!str`).

Modifier flags appended to `*` change the behavior (each measured):

- `*d` — deeply merge **arrays element-wise** (`... *d {"a": [2, {"y": 2}]}` merged the matching
  `{x: 1}` into `{x: 1, y: 2}`)
- `*+` — append arrays
- `*?` — merge only fields that already exist (`{"a": 1} *? {"b": 2, "a": 9}` → `{"a": 9}`: b
  dropped)
- `*n` — merge only new fields (`{"a": 1, "b": 2}`)
- `*c` — clobber custom tags

A null value in the RHS **sets** the key to null — it does not delete it. Use `del(.key)`.

`<<` merge anchors are **not** resolved by ordinary paths (`.item` leaves `<<: *D` visible);
`explode(.item)` resolves them. Exploding diverges from the YAML spec when the merge source and
the local map both define a key: the legacy default lets the **merge source override the local
value**. Measured on the upstream example
(`foobarList: {b: foobarList_b, <<: [*foo, *bar], c: foobarList_c}` exploding to):

```
default: b: bar_b            # local foobarList_b LOST to the anchor, a appended last
--yaml-fix-merge-anchor-to-spec: b: foobarList_b   # spec-correct, local preserved
```

The fix flag also fixes exploded key order and enables inline-map merging. Upstream's own help
text still promises the default flip "in late 2025"; v4.54.3 still ships it false and logs
`--yaml-fix-merge-anchor-to-spec is false; causing merge anchors to override the existing values
which isn't to the yaml spec` on stderr for every explode. Scripts that read merge-anchored
config should set the flag explicitly so a future default flip cannot change results.

## Expression language: what exists and what does not

jq vocabulary is *mostly* there, but measured unknowns (each fails as
`lexer: invalid input text "<name>(`...) on 4.54.3:

- **Absent**: `gsub`, `splits`, `ltrimstr`, `rtrimstr`, `inside`, `getpath`, `getStyle`,
  `setStyle`, `datepart`, `dateformat`, `name` (use `key` for keys and array indexes alike),
  the `ascii_upcase`/`ascii_downcase` spellings (use `upcase`/`downcase`), `//=` (write
  `.k = (.k // 42)`), `-S` key-sorting shorthand (use `sort_keys(.)`).
- **`sub` is global**: `"banana" | sub("a", "X")` measures `bXnXnX` — it replaces every match,
  jq's gsub, not jq's first-only sub. Accepts `,` or `;` argument separators.
- Regex is Go's RE2: `test`, `match`, `capture` (named groups) work, but **lookahead and
  lookbehind are rejected** — `capture("(?=a)")` errors `invalid or unsupported Perl syntax`,
  `capture("(?<=a)b")` errors `invalid named capture`. jq's Oniguruma patterns do not port.
- `contains(str)` and `split(",")` (returns an array) work; `has("k")` distinguishes an
  existing-null key (true) from a missing one (false) — handy because
  `.k == null` is true for both.
- `setpath(["a","b"]; val)` works; the `getpath` spelling does not — read nested paths
  positionally (`.a.b`) instead.
- String multiplication repeats: `"ab" * 3` measures `ababab`.
- Style/comments: `| style` reads the print style, `.s style = "double"` re-styles a node;
  `-P` is shorthand for setting `style = ""` everywhere.
- Number handling: int64 is exact past jq's 2^53 wall (`9007199254740993 + 1` measures
  `9007199254740994`), and untouched literals keep their source formatting (`1.10` prints
  `1.10` until an arithmetic op normalizes it to `1.1`).
- Env: `env(NAME)` fails closed on an unset variable (`value for env variable 'NAME' not
  provided in env()`), but **`strenv(NAME)` fails open** — an unset variable yields the empty
  string, silently. `--security-disable-env-ops` turns both off (`env operations have been
  disabled`).
- Comments: read them with the pipe postfix — `.b | lineComment` (a `.b.lineComment` path
  probe measures null). Write with `.b lineComment="text"` — on a key that does not exist this
  **creates the key** (`b: null # text` measured). `headComment`/`footComment` analogous. They
  only survive yaml-family output.
- Datetime: `now`, `now | tz("UTC")`, `now | format_datetime("2006-01-02")` (Go layout), and
  `with_dtf(layout; "2024-01-01")` for parsing. The datepart/dateformat spellings do not exist.

## eval, eval-all, split, front matter

- `eval` visits each document in each file and prints results — **including `null` results** —
  separated by `---` lines. `-N` drops the separators; `-0` separates values with NUL bytes.
- `eval-all` (alias `ea`) loads every document first and runs the expression once over the
  whole set; that is the tool for cross-document aggregation. Note measured quirk: a bare
  `yq eval-all 'length' f.yml` still produces per-document results (`3` twice for a two-doc
  file) while the explicit aggregate `[.] | length` measures the doc count (2) once. For
  folding documents into one map use the idiom
  `yq eval-all '. as $item ireduce ({}; . * $item )' *.yml`.
- `-s/--split-exp "expr"` writes each result into files named by the expression (double-quoted,
  `$index` is the result counter, directories are created automatically). A null filename
  expression lands as `null.yml`; output goes to the files, not stdout. Paths are refused
  outside the working directory: `split-exp output path "../esc.yml" was rejected: path must
  stay within the current directory; use --security-allow-write-any-path to override` (a WARN
  line plus an Error line, both on stderr).
- `-f front-matter` reads a leading YAML front-matter block: `-f extract` prints the block with
  its `---` delimiters; `-f process` runs the expression against the block and then prints the
  rest of the file unchanged. An **invalid mode string silently degrades to plain evaluation of
  the front matter** only — `yq -f bogus '.title' page.md` printed `My Post` alone, with no
  warning; misspellings go unnoticed.
- In-place `-i` evaluates the **whole argument list and overwrites the FIRST file with every
  evaluated document** — not a per-file edit. Measured: two single-doc files
  (`yq -i '.a = 99' i1.yml i2.yml`) ended with i1 containing BOTH documents, both updated to
  `a: 99`, while i2 on disk was untouched — with exit 0 and no warning. Never pass `-i` more
  than one file unless that overwrite is intended. A single file behaves as expected. With no
  file argument it refuses (`write in place flag only applicable when giving an expression and
  at least one file`), and on an empty file it is a silent no-op despite exit 0 ("editing an
  empty file does not work"). `-i -o json` rewrites a .yml file as JSON in place.

## File ops and the system operator

- `load("path")` reads a file at eval time and parses it **as YAML**; JSON is fine (it is valid
  yaml), other formats come back as raw text. A multi-document yaml file loads as a list
  (`. | length` counts docs), and its `type` prints an empty string. Missing files fail closed:
  `failed to load fx/zzz: open fx/zzz: no such file or directory`;
  `--security-disable-file-ops` blocks the op (`file operations have been disabled`).
- `system(...)` is disabled by default (fails with `system operations are disabled, use
  --security-enable-system-operator to enable`). Even with the flag, on 4.54.3 **arguments are
  not forwarded**: `system("touch", ["/tmp/f"])` measured `touch: missing file operand` and
  `system("/bin/echo", "hi")` printed nothing. It executes the command name, captures its
  stdout as the result string (`system("id")` returned the full uid/gid line), and does not
  return exit codes (`system("sh", ["-c", "exit 3"])` results in an empty string, rc 0). Do not
  reach for it expecting a generic shell escape.

## Colors

Colorizing is **TERM-gated, not just TTY-gated**: a pty without a real TERM prints plain; with
`TERM=xterm-256color` colors appear automatically (comments gray, keys cyan, numbers magenta,
strings green), and `-C`/`--colors` forces them even into a pipe while `-M`/`--no-colors`
suppresses. Scripts differ in color behavior between terminals — parse with `-M`, or capture
and strip.

## Verification recipe

Run after installing the binary; every assert is self-checking:

```bash
#!/usr/bin/env bash
# Self-checking battery for mikefarah/yq v4.54.3. Point YQ_BIN at the installed binary.
set -u
YQ_BIN="${YQ_BIN:-yq}"
fail=0
assert_out() { # label, expected-stdout, yq arguments... — empty expected for absent/error probes
  got=$("$YQ_BIN" "${@:3}" 2>/dev/null)
  if [[ "$got" == "$2" ]]; then echo "ok: $1"; else echo "FAIL: $1: got $(printf '%q' "$got") want $(printf '%q' "$2")"; fail=1; fi
}
assert_rc() { # label, expected-rc, arguments...
  "$YQ_BIN" "${@:3}" >/dev/null 2>&1; rc=$?
  if [[ "$rc" == "$2" ]]; then echo "ok: $1"; else echo "FAIL: $1: rc $rc want $2"; fail=1; fi
}

tmp=$(mktemp -d) || exit 1
trap 'rm -rf "$tmp"' EXIT
cd "$tmp"
printf '# head\nb: "5"  # line\nlist:\n  - x\n  - y\n---\nsecond: doc\n' > f.yml

assert_rc  "double-quote ok"             0 -n '.a.b = "cat"'
assert_rc  "single-quote refused"        1 -n ".a.b = 'cat'"
assert_rc  "bare word refused"           1 -n 'item'
assert_rc  "-e no-match rc 1"            1 -e '.zzz' f.yml
assert_rc  "-e found rc 0"               0 -e '.b' f.yml
assert_out "unwrap prints bare 5"        "5
---
null" '.b' f.yml
assert_out "gsub absent (empty out, rc lost)"  "" -n '"ab" | gsub("a", "X")'
assert_out "getpath absent"               "" -n 'getpath(["a","b"])'
assert_out "splits absent"                "" -n '"a,b" | splits(",")'
assert_out "sub is global"                "bXnXnX" -n '"banana" | sub("a", "X")'
assert_out "no lookbehind"                "" -n '"ab" | capture("(?<=a)b")'
assert_out "int64 exact"                  "9007199254740994" -n '9007199254740993 + 1'
assert_out "upcase works"                 "AB" -n '"ab" | upcase'
assert_out "merge flag *? keeps existing" "a: 9" -n '{"a": 1} *? {"b": 2, "a": 9}'
assert_out "json out quotes the string"   '"5"
null' -o json '.b' f.yml
assert_out "yaml out drops the comment"   "5
---
null" -o yaml '.b' f.yml
assert_rc  "system disabled"              1 -n 'system("id")'
assert_out "strenv fail-open"             "x=" -n '"x=" + strenv(NO_SUCH_VAR_XYZ)'
assert_rc  "env fail-closed"              1 -n 'env(NO_SUCH_VAR_XYZ)'

# unwrap type trap: default output re-types quoted numbers.
printf 'b: "5"\n' > q.yml
t1=$("$YQ_BIN" '.b' q.yml | "$YQ_BIN" tag)
t2=$("$YQ_BIN" -r=false '.b' q.yml | "$YQ_BIN" tag)
if [[ "$t1" == "!!int" && "$t2" == "!!str" ]]; then echo "ok: unwrap re-types, -r=false preserves"
else echo "FAIL: unwrap trap: $t1 / $t2"; fail=1; fi

# -i overwrites the FIRST file with every evaluated document; other files untouched on disk
printf 'a: 1\n' > i1.yml; printf 'a: 1\n' > i2.yml
"$YQ_BIN" -i '.a = 99' i1.yml i2.yml >/dev/null 2>&1
if [[ "$(printf '%s\n---\n%s\n' 'a: 99' 'a: 99')" == "$(cat i1.yml)" \
   && "$(printf 'a: 1\n')" == "$(cat i2.yml)" ]]; then echo "ok: -i first-file overwrite semantics"
else echo "FAIL: -i semantics: $(cat i1.yml) | $(cat i2.yml)"; fail=1; fi

if [[ $fail -eq 0 ]]; then echo "ALL PASS"; else echo "FAILURES PRESENT"; exit 1; fi
```

Every quoted yq expression here uses double quotes only — the quoting rule the language itself
enforces. Expression-only probes pass -n because yq reads stdin otherwise; scripts that run this
battery or probe files should redirect stdin explicitly (</dev/null) wherever no input file is
given.

## Related skills

- [`jq`](skills/jq/SKILL.md) — the JSON sibling; yq can read JSON natively, and this file lists
  which jq functions yq lacks.
- [`miller`](skills/miller/SKILL.md) — CSV/TSV-shaped data processing.
- [`gron`](skills/gron/SKILL.md) — line-grained grep-able JSON views.
