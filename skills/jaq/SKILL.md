---
name: jaq
description: >
  Use when a jq program is needed and jq itself is impractical: jq is missing,
  files must be edited in place, YAML, TOML, XML, CSV/TSV or CBOR must be
  queried or written without extra tools, you want an interactive REPL, or
  exact big-integer arithmetic matters. jaq is a Rust jq clone with the same
  filter language plus these extras; this skill maps the jq divergences, the
  streaming-fromjson and per-file-slurp traps, and the NaN/Infinity output
  that breaks downstream JSON consumers.
version: 1.0.0
---

# jaq

A jq clone in Rust. For everyday filters it *is* jq: same syntax, same
builtins, same exit-code taxonomy. It earns its place where jq falls short —
in-place editing, a built-in format system (YAML/TOML/XML/CSV/TSV/CBOR), a
REPL, exact big-integer math — and it can hurt you where it quietly changes
jq's contract. This skill is the divergence map.

Measured on jaq 3.1.2 (the official GitHub release binary), cross-checked
against jaq 2.3.0 (conda-forge build) for the version wall, and against jq
1.8.2 official release binary for the dialect. See the sibling `jq` skill for
the jq language baseline.

## Install

```bash
# GitHub release binary (static musl, no deps); sha256 of each asset is on
# the release API: api.github.com/repos/01mf02/jaq/releases/latest -> assets[].digest
curl -sLO https://github.com/01mf02/jaq/releases/download/v3.1.2/jaq-x86_64-unknown-linux-musl
sha256sum jaq-x86_64-unknown-linux-musl   # expect a469f5e6980fe2c7e73dce0a1db5176eb4a717b933b77fa32fa1da7847c12232
# or: conda-forge package named `jaq` (same version as the GitHub release), or `cargo install jaq`
# apt has no jaq package at all on Ubuntu noble — do not hunt for one
```

The release also ships `MANUAL.xhtml` and a `jaq.1` man page — the manual's
"Unsupported" sections are the authoritative jq-gap list.

## Where jaq and jq agree

Filter language: paths, `//`, `?`, try/catch, reduce/foreach, if with optional
else, update assignment (`|=`, `+=`, `//=`, including creating missing keys),
array/object destructuring (`as [$a,$b]`, `as {a:$x}`), string interpolation.
CLI: `-n -r -j -c -S -C -M`, `--tab`, `--arg/--argjson/--args/--slurpfile/--rawfile`,
`-L` modules with `include "m"; f` and `import "m" as mm; mm::f`, data modules
(`import "d" as $d` reads `d.json` as strict JSON into an array), `-e` exit
codes (0 truthy last output, 1 null/false, 4 no output, 5 runtime error,
3 compile, 2 usage/OS error). Builtins: `getpath/setpath/delpaths/pick/walk`,
`env/$ENV`, `input/inputs`, `input_filename`, `debug/stderr/halt/halt_error/now`,
`tojson/fromjson`, `@base64/@base64d/@csv/@tsv/@sh/@html/@json/@uri/@text`,
regex family `test/match/capture/splits/scan/sub/gsub` (first-match `sub`,
global `gsub`, same `g` flag), date family `todate/fromdate/strftime/mktime/
gmtime/localtime`, arrays `sort/group_by/unique/flatten/bsearch/combinations/
transpose/reverse`, `limit/first/last/skip/nth/range`,
`utf8bytelength`, `abs`, `trim/split/join`, `keys/keys_unsorted`, `type/tostring/tonumber`.
Colors: TTY-gated only (empty `TERM` still colors), `-C` forces in a pipe,
`-M` suppresses, `NO_COLOR` honored in auto mode, `JQ_COLORS` recolors —
with one trap: `NO_COLOR` does *not* beat an explicit `-C`.

## The traps — where jaq diverges from jq

**Exact integers.** Integer literals outside f64 still compute exactly:
`9223372036854775807 + 1` → `9223372036854775808`, `2^128 + 1` → exact
(jq silently rounds past 2^53: `9007199254740993 + 2` → jaq `…995`,
jq `…994`). Decimal calculation is still plain f64: `0.1 + 0.2` →
`0.30000000000000004`.

**XJON output.** Default output is a JSON *superset*: `nan` prints `NaN`,
`1/0` prints `Infinity` and exits 0 (jq errors rc 5 on division by zero and
prints NaN as null). `nan | tojson` → `"NaN"`. Crucially `--to json` does
**not** sanitize — NaN/Infinity survive every format target. Anything feeding
a strict JSON consumer breaks. Convert before emitting:

```bash
jaq -n '[1/0, 0/0] | walk(if type == "number" and (isnan or isinfinite) then null else . end)'
# [null, null] — safe JSON; jq needs no such guard
```

**`-s` is per file.** `jaq -s . a.json b.json` emits one array per file (two
outputs); jq combines all inputs into a single array. Two generations of jaq
(2.3.0 and 3.1.2) both behave this way.

**`fromjson`/`tonumber` stream.** `'"1 2" | fromjson'` yields `1` and `2` and
exits 0 — trailing junk is parsed as more values, not an error (jq: rc 5,
no output). Worse, failures come *after* partial output: `'"1 x" | fromjson'`
prints `1` then errors rc 5 (`"0x10" | tonumber` prints `0` first). A
"validate this JSON string" check built on jaq's fromjson passes dirty input.

**Regex is the Rust regex crate**, not Oniguruma. No look-around
(`test("a(?=b)")` → rc 5 `look-around is not supported`), no back-references,
no `\p{L}` Unicode classes (named error `Unicode character classes are not
supported`). Accepted flags: `i x n s m g` (`p`/`l` accepted but `U` fails
closed). Flag meanings are the Rust crate's, not jq's: `s` means *dotall* —
`"a\nb" | test("a.b"; "s")` is `true` in jaq, `false` in jq, whose `s` pins
anchors to the whole string. The `g` in `gsub(...; ""; "n")`-style flag sets
also streams differently from jq — measure before relying on it.

**Bare negative-number filters are flags.** `jaq -n '-0'` → rc 2
`unknown flag: -0`. Use `jaq -n -- -0` or write `-(0)` / `0 - .`.

**Absent from jaq** (compile-error `undefined filter` / `undefined variable`):
`$__loc__`, `input_line_number`, `builtins`, `modulemeta`,
`have_literal_numbers`, `$JQ_BUILD_CONFIGURATION`, the SQL-style `INDEX/JOIN/
IN`, and everything stream-related (`--stream`, `tostream`, `fromstream`,
`truncate_stream`). CLI: no `-a/--ascii-output`, `--unbuffered`, `--seq`,
`--stream-errors`, `--jsonargs` (plain `--args` works). `halt_error` with a
null input prints `null` to stderr; jq prints nothing. `--indent` is capped
only by memory (10+ accepted; jq caps at 7). `input_filename` names the
stream `"<stdin>"` where jq gives null.

**jaq-only extras.** Byte strings (`"a" | tobytes` → `b"a"`; indexable in
constant time, `isstring`-true, equal to the equivalent text string, only
writable in input literals as `b"..."`); `-i/--in-place` overwrites each file
argument with its output, concatenating multiple outputs with newlines, and
falls back to stdout with no file args (jq 1.8.2 has no `-i` at all); a
REPL when run with no filter on a terminal (jq 1.8.2 prints usage); `-f
PROG.jq` runs a module-style file — any `def`s plus exactly one trailing
filter — while `-f -` (stdin) misbehaves in 3.1.2 and should be avoided;
`--raw-input0`/`--raw-output0` NUL-split inputs/outputs (final unterminated
chunk still becomes a value).

## The format system

`--from F/--to F` (or the filter spellings `fromyaml`, `toyaml`, `fromtoml`,
`totoml`, `fromxml`, `toxml`, `fromcsv`, `tocsv`, `fromtsv`, `totsv`, which
jaq has and jq — beyond json — does not). Formats: `raw raw0 json cbor yaml
toml xml csv tsv`.

- CSV/TSV: each row reads as an array of fields (no header logic); `tocsv`
  expects each *input value* to be one row of scalars — a single `[[1,2],[3,4]]`
  value errors (`expected table field (null, bool, number, or string)`), the
  same two rows streamed separately write `1,2` and `3,4`.
- YAML: writes `---` before and `...` after **every** output value; anchors
  and aliases read fine (`"[&a 1, &b 2, *a, *b]" | fromyaml` → `[1,2,1,2]`),
  self-referential aliases fail; scalar tags are validated (`!!bool true` →
  true, `!!int true` → error) while tags on arrays/objects are ignored; byte
  strings become Base64 `!!binary`; `.inf`/`.nan` for the special floats.
- TOML: root must be an object, `null`/byte strings/non-string keys and
  date-times fail (named errors, e.g. `could not encode null as TOML value`);
  output shuffles tables after scalars; big integers round-trip *out* but not
  back *in*.
- XML: an information-preserving mapping, not a friendly one — a `<a
  x="1"><b>2</b>tail</a>` element becomes `{"t":"a","a":{"x":"1"},"c":
  [{"t":"b","c":["2"]},"tail"]}`: tag under `t`, attributes (as strings) under
  a key named after the tag, children under `c`. That exact shape feeds back
  into `toxml` for a lossless round trip. XHTML only — hand real HTML to a
  converter first.
- CBOR: `--to cbor` concatenates values with no separator (≡ joined output);
  date-time/undefined/bigfloat CBOR values fail on read; invalid UTF-8 text
  becomes U+FFFD.

## Modules and search paths

`-L` directories are the *only* implicit search sources and are interpreted
relative to the CWD — there is no default `~/.jq` lookup, so scripts using
`include` on another machine need explicit `-L` or per-module metadata:
`include "m" {search: ["lib"]};`. `~` expands to `$HOME` and `$ORIGIN` to the
binary's directory. Data modules (`import "d" as $d`) read `d.json` with
strict JSON — unquoted keys fail at load.

## Error surfaces

Compile errors print a boxed, caret-marked diagnostic with the source line to
**stderr** (rc 3); runtime errors are single-line `Error: …` on stderr (rc 5).
Because output streams as it is produced, stdout may hold partial results
before a later-input failure — never assume stdout is empty when the exit
code is non-zero.

## Version wall

v3.x added the XJON specials (`nan` → literal `NaN`, byte strings, the
`--from/--to` system and its filters) and turned `fromjson` into a streaming
parser. jaq 2.3.0 still prints `nan` as `null`, lacks `tobytes`/`tocsv`/
`--from`, and rejects trailing junk in `fromjson` — jq-like. In-place `-i`,
exact big integers and the per-file `-s` already exist in 2.x. Pin ≥ 3.1 when
formats or byte strings matter; the flags above are re-verify-on-touch.

## Verify this skill

```bash
set -u
BIN="${JAQ_BIN:-$(command -v jaq || echo /dev/null)}"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
if [ "$BIN" = /dev/null ]; then
  BIN="$WORK/jaq"
  curl -sLo "$BIN" https://github.com/01mf02/jaq/releases/download/v3.1.2/jaq-x86_64-unknown-linux-musl
  chmod +x "$BIN"
fi
F=0; chk() { local d="$1" got="$2" want="$3"; if [ "$got" != "$want" ]; then
  echo "FAIL: $d (got '$got', want '$want')"; F=$((F+1)); fi; }

chk version "$("$BIN" --version)" "jaq 3.1.2"
chk bigint "$("$BIN" -n '9223372036854775807 + 1' 2>/dev/null)" "9223372036854775808"
chk nan    "$("$BIN" -n 'nan' 2>/dev/null)" "NaN"
chk tojson-nan "$("$BIN" -n 'nan | tojson' 2>/dev/null)" '"NaN"'
chk strict "$("$BIN" -n '[1/0] | walk(if type == "number" and (isnan or isinfinite) then null else . end)' 2>/dev/null)" '[null]'

printf '{"a":1}\n' > "$WORK/a.json"; printf '{"a":2}\n' > "$WORK/b.json"
chk slurp-per-file "$("$BIN" -c -s . "$WORK/a.json" "$WORK/b.json" | wc -l)" "2"
chk fromjson-multi "$("$BIN" -n '"1 2" | fromjson' 2>/dev/null | tr '\n' ' ')" "1 2 "
"$BIN" -n '"0x10" | tonumber' > "$WORK/p.out" 2>/dev/null; chk partial-stdout "$(cat "$WORK/p.out")" "0"
"$BIN" -n '"0x10" | tonumber' >/dev/null 2>&1; chk tonumber-rc "$?" "5"
"$BIN" -n '"ab" | test("a(?=b)")' >/dev/null 2>&1; chk no-lookaround-rc "$?" "5"
chk s-dotall "$("$BIN" -n '"a\nb" | test("a.b"; "s")' 2>/dev/null)" "true"

chk tocsv "$("$BIN" -n '[1,2], [3,4] | tocsv' -r 2>/dev/null | tr '\n' ' ')" "1,2 3,4 "
printf '<a x="1"><b>2</b>tail</a>' | "$BIN" --from xml -c --to xml > "$WORK/x.out" 2>/dev/null
chk xml-roundtrip "$(cat "$WORK/x.out")" '<a x="1"><b>2</b>tail</a>'
"$BIN" -n '"a: 1" | toyaml' -r > "$WORK/y.out" 2>/dev/null; chk toyaml "$(cat "$WORK/y.out")" 'a: 1'
"$BIN" -n -- '-0' > "$WORK/d.out" 2>/dev/null; chk dashdash-neg "$(cat "$WORK/d.out")" "0"
"$BIN" -n '-0' >/dev/null 2>&1; chk bare-neg-rc "$?" "2"
chk tobytes "$("$BIN" -n '"x" | tobytes' 2>/dev/null)" 'b"x"'
exit "$F"
```

If any check fails, the version above this skill's claims does not hold —
re-measure before trusting it.
