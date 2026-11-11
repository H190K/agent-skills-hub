---
name: dasel
version: 1.0.0
description: "Use when a JSON, YAML, TOML, XML, CSV, INI, HCL, or KDL file must be queried, converted, or modified with one selector language: dasel. Covers the v3 stdin-only file model (no -f flag), dot-prefix selectors as hard parse errors, end-inclusive slices, JSON-quoted output and the yaml-writer unquote trick, camelCase-only functions absent from help, removed put and delete commands vs assignment expressions with --root, rc 1-vs-80 taxonomy, and the auto-loaded ~/dasel.yaml config. Measured on official 3.11.2; apt/noble ships divergent 2.6.0."
---

# dasel — one selector language over eight config formats, with the v2-to-v3 traps measured

dasel (TomWright/dasel, MIT, © 2020 Tom Wright per the source-tarball
LICENSE) queries, converts and modifies structured data with a single
selector/expression language — the tool to reach for when a task spans more
than one of JSON, YAML, TOML, XML, CSV, INI, HCL and KDL and format-specific
tools would each bring their own syntax. Every claim below was measured live
on the **official v3.11.2 release binary**
(`dasel_linux_amd64`, sha256-verified against the per-asset digest on the
release page).

## Install and verify

- Release binaries from `github.com/TomWright/dasel/releases` ship with
  **per-asset sha256 digests** — verify before use. `brew install dasel` and
  `go install github.com/tomwright/dasel/v3/cmd/dasel@master` are the other
  official routes (note the `/v3` module path).
- conda-forge's `dasel` package **is** the same tool: the 3.11.2 build
  produced an md5-identical `--help` and an identical probe set against the
  release binary.
- **Debian/Ubuntu apt is v2, not v3.** noble ships `dasel 2.6.0`, whose CLI
  is a different tool surface (see the migration table at the end). Do not
  learn v3 on apt-dasel and expect the flags to exist.
- `dasel version` prints `3.11.2`. The `--version` flag does **not** exist in
  v3 — it fails with the rc-80 usage error — the inverse of v2, where
  `dasel --version` works and `dasel version` is treated as a data query.

```bash
bin=$(command -v "${DASEL_BIN:-dasel}") || { echo "FAIL: dasel not on PATH"; exit 1; }
"$bin" version
```

## The v3 file model: stdin in, stdout out, no file flag

v3 has **no `-f` flag at all**. `dasel -f file` fails with
`unknown flag -f, did you mean one of "-h", "-i", "-o", "-c"?` at **rc 80**.
Data reaches dasel through three channels:

1. **Stdin** — the main one: `cat f.yml | dasel -i yaml 'query'` or
   `dasel -i yaml 'query' < f.yml`.
2. **A variable bound to a file** — `--var d=json:file:./x.json` then use
   `$d.users[0].name`. The scheme is `<format>:file:<path>`.
3. **`readFile("./x.json")` inside a query** — returns the **raw file bytes
   as a string**, not parsed data. Parse it explicitly (format first,
   content second): `parse("json", readFile("./x.json")).name`.

In-place edits do not happen: v3 **never writes files**. `dasel … > new.yml`
then move the file yourself — this is the exact opposite of v2, whose
`put`/`delete` subcommands rewrote the target file in place.

Two silent-config facts:

- `~/dasel.yaml` is **auto-loaded when the file exists**; missing is silently
  ignored. Its one key, `default_format: yaml`, becomes the implicit in/out
  format for every dasel call (JSON otherwise). A stray config changes default
  parsing for your whole account — check it when `dasel` suddenly parses
  wrong. Measured end-to-end: with `default_format: yaml`,
  `printf 'x: 1' | dasel -c <path> 'x'` parses YAML with no `-i` flag.
- The `~/` expansion ignores `$HOME`, so point `-c` at an explicit path to
  test a config deterministically.

## Reader and writer switches

- `-i`/`-o` take one of eight formats: `json yaml toml xml csv ini hcl kdl`.
- **JSON is the only implicit format.** Feed YAML to a bare `dasel` and it
  dies inside the JSON parser: `error reading input: json: invalid character
  x as token`. Always pass `-i yaml` (and friends) for non-JSON stdin.
- The **yaml writer prints scalars unquoted** — for a string value, `-o yaml`
  yields `str` where the json writer yields `"str"`. When a shell script needs
  a bare value, convert through `-o yaml`.
- ini output requires the document root to be a map (`ini can only represent
  map values`); the **xml writer rejects non-string leaves**
  (`xml writer does not support value type: int`).
- csv uses `--read-flag`/`--write-flag` (or `--rw-flag`) style knobs:
  `--write-flag 'csv-delimiter=;'`.
- `--compact` removes indentation/newlines; there is no `--pretty`, `--indent`
  or color flag in v3.

## Selectors: dot is a separator, not a prefix

- Properties chain bare: `users[0].name`. A **leading dot is a hard parse
  error** — `.name` dies at position 0 with `unexpected token "."`. Every v2
  path that starts with `.` must drop the dot.
- Indexing is `users[0]`; negative indexes **error**
  (`slice index out of range: -1`) — this is not Python.
- **Slices are end-inclusive.** On `[1,2,3]`: `u[0:2]` → `[1,2,3]`,
  `u[0:1]` → `[1,2]`, `u[1:]` → `[2,3]`, and `u[1:3]` errors because the
  inclusive end 3 is past the array. The Python habit of exclusive ends
  selects one element too many here.
- **The v2 trap: dot-indexing is gone.** `users.[0]` does not navigate — it
  evaluates to a synthetic array containing the index number, silently and at
  rc 0. Real navigation is `users[0]`.
- Recursive descent searches everything: `..key` returns an array of all
  matches at any depth.
- `search(cond)` finds all values matching a condition anywhere in the tree.

## Expressions inside calls are bare

Inside `filter`/`map`/`each` etc., write expressions over **bare property
names and `$this`** — no dots, no quotes around properties:

```bash
echo '{"u":[{"n":"a","age":10},{"n":"b","age":40}]}' | dasel -i json 'u.filter(age > 25)'
echo '[1,2]' | dasel -i json --compact 'map($this * 10)'        # [10,20]
echo '[1,2,3]' | dasel -i json --compact 'each($this = $this*2)' # [2,4,6]
```

Variables come from `--var name=value` (with the `json:file:` scheme for
files) and are referenced as `$name`. Comments are allowed inside queries.

## Modification is assignment, not a subcommand

v3 removed the `put` and `delete` commands (changelog, v3.0.0). Modify inside
the query and add `--root` to emit the whole document:

```bash
echo '{"foo":{"bar":"baz"}}' | dasel -i json --root 'foo.bar = "bong"'
# without --root, only the assigned value is printed
```

- `k = null` **sets null but keeps the key** — it does not delete.
- **v3.11.2 ships no delete** — calling `delete(...)` or `append(...)`
  fails at runtime with `unknown function: "delete"`. Deleting a key means
  rebuilding (filter/entries-style) or falling back to a v2 binary.
- The error for `append(3)` is `error evaluating expression ast.CallExpr:
  unknown function: "append"` — with the internal-AST wrapper text that
  precedes every execution error.

## Functions: camelCase only, and help never lists them

`--help` lists no functions anywhere. Wrong names fail at runtime with
`unknown function: "<name>"`. The registered default set in v3.11.2 is
**camelCase-exact**

`len, add, toString, toInt, toFloat, merge, reverse, typeOf, max, min,
ignore, base64Encode, base64Decode, parse, readFile, has, get, contains, sum,
join, replace, keys, split, toLower, toUpper, trim, trimPrefix, trimSuffix,
startsWith, endsWith, indexOf, abs, floor, ceil, round, avg, flatten, unique,
first, last, values, entries, fromEntries, toBool, stringify`

— so `to_string(123)` fails while `toString(123)` works. `parse` takes
exactly two arguments (format, content string). `ignore` is the one function
gated behind `--unstable`; everything else needs no flag.

## Exit taxonomy: 0, 1, 80

- **rc 0** — success (including traps like the synthetic-array dot-index).
- **rc 1** — every runtime class: selector parse errors, execution errors,
  unsupported format names, unreadable input, empty stdin
  (`expected map, got null`), missing keys (`map key not found: "x"`).
- **rc 80** — Kong usage errors only: unknown flag (with a did-you-mean
  suggestion), unexpected argument, and a missing file inside
  `--var f=json:file:./nope.json` (usage page reprinted).

Never branch on rc 1 alone — it covers six different classes; assert the
message after `dasel: error:` instead. Error text carries the failing
position (`unexpected token "." at position 0`) which makes silent-trap
diagnosis cheap.

## Migration table — v2.6.0 (apt/noble) vs v3.11.2, measured

| v2.6.0 | v3.11.2 |
| --- | --- |
| `-f file` reads a file | stdin only; `--var x=json:file:` or `readFile`+`parse` |
| `put -t type -v val`, `delete` rewrite the file **in place** | removed; assignment `path = value` + `--root`, output to stdout |
| `validate <file…>` prints `pass <file>` per file | gone |
| `-r/-w` parsers, 5 formats (json,yaml,toml,xml,csv) | `-i/-o`, 8 formats (+hcl, ini, kdl) |
| dot-index `users.[0].name` is valid navigation | hard parse error; `[n]` directly after the name |
| `--version` flag works; `dasel version` is a query (rc 1) | `dasel version` subcommand; `--version` is an unknown flag (rc 80) |
| `-s selector`, `--pretty`, `--indent`, `--colour`, `--escape-html`, `--csv-comma` | none of these; positional query, `-c` config, `--compact`, `--rw-flag csv-delimiter` |
| all errors rc 1 (unknown flag, missing file, bad selector) | rc 1 runtime vs rc 80 usage split |
| strings print quoted (`"frank"`) | strings still print quoted under the json writer; `-o yaml` unquotes |

## Related

- `jq` — JSON-only extraction and transformation with a larger language.
- `gron` — flatten JSON into grep-able assignment lines.
- `miller` — CSV/TSV/JSON-row oriented transformations.

## Provenance and divergences

- Behaviour measured live on the official `dasel_linux_amd64` v3.11.2 release
  binary, sha256-verified against the GitHub release asset digest; conda-forge
  3.11.2 cross-checked (identical `--help`, identical probe results).
- v2.6.0 divergence row measured on the actual `dasel 2.6.0-1ubuntu0.3`
  binary from Ubuntu noble (`apt-get download dasel`).
- Function inventory taken from the v3.11.2 source-tarball `execution/func.go`
  registration list; the two XML/ini writer limitations and all error strings
  are verbatim captured messages from the measured binary.
- Upstream docs live at daseldocs.tomwright.me for newer releases; re-probe
  any hidden/unstable surface before shipping version-specific claims about
  it.

## Verify block

```bash
set -e
bin=${DASEL_BIN:-$(command -v dasel)} || { echo "FAIL: dasel missing"; exit 1; }
[ -x "$bin" ] || { echo "FAIL: dasel not executable"; exit 1; }
[ "$("$bin" version)" = "3.11.2" ] || { echo "FAIL: version drifted"; exit 1; }
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
printf '{"users":[{"name":"alpha"},{"name":"beta"}]}' > "$tmp/t.json"

# stdin + selector, no -f; the json writer quotes strings
[ "$("$bin" -i json 'users[0].name' < "$tmp/t.json")" = '"alpha"' ] || { echo "FAIL: sel"; exit 1; }

# dots are separators, not prefixes
if echo '{}' | "$bin" -i json '.name' > "$tmp/err" 2>&1; then echo "FAIL: dot-prefix should error"; exit 1; fi
grep -q 'unexpected token' "$tmp/err" || { echo "FAIL: dot prefix"; exit 1; }

# yaml writer unquotes scalars; json quotes them
[ "$("$bin" -i json -o yaml 'users[0].name' < "$tmp/t.json")" = "alpha" ] || { echo "FAIL: yaml unquote"; exit 1; }

# slices are end-inclusive
[ "$("$bin" -i json --compact 'u[0:1]' <<< '{"u":[1,2,3]}')" = "[1,2]" ] || { echo "FAIL: slice"; exit 1; }

# assignment with --root; no delete function exists
out=$("$bin" -i json --compact --root 'users[1].name = "B"' < "$tmp/t.json")
[ "$out" = '{"users":[{"name":"alpha"},{"name":"B"}]}' ] || { echo "FAIL: assign"; exit 1; }
if echo '{}' | "$bin" -i json 'delete(foo)' > "$tmp/err2" 2>&1; then echo "FAIL: delete should error"; exit 1; fi
grep -q 'unknown function' "$tmp/err2" || { echo "FAIL: delete"; exit 1; }

# rc taxonomy: runtime errors exit 1, Kong usage errors exit 80
rc=0; { echo '{}' | "$bin" -i json 'foo[' > /dev/null 2>&1; } || rc=$?
[ "$rc" -eq 1 ] || { echo "FAIL: rc1"; exit 1; }
rc=0; { "$bin" -z < /dev/null > /dev/null 2>&1; } || rc=$?
[ "$rc" -eq 80 ] || { echo "FAIL: rc80"; exit 1; }

# format conversion across the matrix
[ "$("$bin" -i json -o toml <<< '{"a":1,"s":"t"}' | tr -d '\n')" = "a = 1s = 't'" ] || { echo "FAIL: toml"; exit 1; }
echo "PASS"
```
