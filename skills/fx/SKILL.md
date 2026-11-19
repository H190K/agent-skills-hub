---
name: fx
description: Use when a terminal session or script must view, query, convert, edit or validate JSON — exploring large files in the TUI, extracting or filtering fields, sorting or grouping, converting YAML/TOML/XML/HTML/EDN/MAML input, editing a file in place, or when jq-style pipelines hit undefined results, BigInt values or lexicographic sorting traps. Covers the viewer-without-TTY panic, the JavaScript expression language, save() and viewer tree editing, env knobs, and the version wall. Behaviors measured live.
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
---

# fx — terminal JSON viewer & processor

`fx` ([antonmedv/fx](https://github.com/antonmedv/fx), MIT) is two tools in one binary: an
interactive JSON viewer (collapsible tree, search, queries, yank/delete with write-back) and a
JSON processor whose expression language is **JavaScript** running on a Go JS engine. This skill is
original text from live behavior, pinned to **40.0.1** (the current release as of writing,
sha256-verified against the per-asset digest on the release API) with a
conda-forge build whose `--help` is byte-identical, and a version wall measured on conda-forge
builds of 38.0.0 and 39.1.0. Unlike jq, fx preserves every numeric literal in the input and
accepts comments and trailing commas — and its `undefined`-result behavior is a scripting trap.

## Install

Prefer the official Go release binary ([ Releases](https://github.com/antonmedv/fx/releases),
e.g. `fx_linux_amd64`); `brew install fx` and conda-forge also package it. Verify the download
against the per-asset digest from the GitHub release API:

```bash
curl -sL https://api.github.com/repos/antonmedv/fx/releases/latest \
  | python3 -c 'import json,sys; print([a["digest"] for a in json.load(sys.stdin)["assets"] if a["name"]=="fx_linux_amd64"][0])'
# expect: sha256:9f0cc5a29d2940dd28fdc7df7b5e19bf16856d388e60d1c9f1116890967c604a (40.0.1)
```

Install trap: `npm i -g fx` ships a **reduced JavaScript reimplementation**, not the Go binary —
its wrapper knows only `--help/--raw/--slurp/--yaml/--maml`; everything else in this skill
(the viewer, `--toml/--xml/--edn/--html`, `save()`) is Go-binary-only. Install from the release,
Homebrew, or conda-forge.

## The golden rule — viewer vs script mode

Without an expression argument fx opens the TUI. In an environment with no TTY (cron, subprocess
piping without a pty, most agent harnesses) that is a hard **panic, exit code 2**:

```text
panic: bubbletea: error opening TTY: bubbletea: could not open TTY: open /dev/tty: no such device or address
exit code 2
```

Scripting rules that follow from it:

- **Always end the command with an expression** (`.name`, `x => ...`, a reducer) or pass
  `--no-tui` / set `FX_NO_TUI=1`.
- `--no-tui` with no expression is equivalent to `.` — it pretty-prints each input value.
- No flags, no file, empty redirected stdin → fx prints usage to stdout with **exit code 0**.
- Empty stdin *with* an expression → `Empty input: expected JSON value.` on stderr, rc 1.
- The viewer draws on **stderr**, not stdout. `P` inside the viewer prints the current node to
  stdout when the viewer quits.

## Expression language

Arguments are a **pipeline**: each argument transforms the result of the previous one
(`fx data.json '.items' 'filter(x => x > 1)'`). One transformation happens per input JSON
value, so a stream like `1 2 3` feeds the expression three times.

Three styles of argument, all measured:

```bash
fx data.json '.items[0].a'          # dot path (no TTY, prints result headlessly)
fx data.json 'x => x.items.map(i => i.a)'   # lambda over the whole input
fx data.json 'sortBy(y => y.n)'     # curried reducer applied to the input
```

- Dot paths: `.a.b`, `.[0]`, `.items[0].a`; `.a[]` iterates arrays via flatMap. A bare `.`,
  `this`, or `x` is the fast pretty-print path.
- A bare identifier that takes the value directly (`sort`, `reverse`, `keys`, `uniq`,
  `flatten`, `len`, `sortKeys`) works bare. **Curried** reducers (`map`, `filter`, `sortBy`,
  `groupBy`, `chunk`, `del`, `walk`) must be *called* — `del` bare returns a function that the
  engine cannot stringify (`internal error: Unsupported value type: func`, rc 1).
- `@expr` maps over the input array (`@x => x.n`), `?expr` filters — on a non-array object
  `?` is a keep-or-drop match that silently prints nothing, rc 0, when it fails.
- `return skip` (or passing `skip` through) suppresses that value's output entirely.
- `exit(n)` sets the exit code; `console.log(...)`/`println(...)` print side lines to stdout
  before the result.
- A typo'd **flag** is not rejected: `fx --zzz` becomes an expression and fails
  `ReferenceError: zzz is not defined`, rc 1 (same on 38–40). Unknown flags never parse as flags.

### Stdlib functions (all measured live)

- Direct reducers (usable bare): `sort`, `reverse`, `uniq`, `flatten` (one level only),
  `keys`, `values`, `len`, `sortKeys`, `list` (each element as a line).
- Curried: `map(fn)`, `filter(fn)`, `sortBy(fn)` (comparator by key fn — numeric-correct),
  `groupBy(keyFn)` (function or key name), `chunk(size)`, `zip(...)`, `del(key)`,
  `walk(fn)` (like jq's walk).
- IO helpers: `save(x)` writes x back to the input file (below); `exit(code)`;
  `toBase64(x)` / `fromBase64(x)`; `YAML.stringify(x)` / `YAML.parse(str)`;
  `MAML.stringify` / `MAML.parse` (no TOML serializer).

### The sort trap — JS ordering, not jq ordering

`sort` is JavaScript's default `Array.sort()` — **lexicographic** even for numbers:

```bash
echo '[10,9,2]' | fx 'sort'    # [10, 2, 9]
echo '[10,9,2]' | fx 'sortBy(x => x)'   # [2, 9, 10]
```

jq's `sort` is numeric. When porting a jq pipeline to fx, replace `sort` with a `sortBy`.

## Numbers — exact output, JS arithmetic

fx's own JSON parser preserves **the literal text of every number** — `100.0`, `0.100`,
`1e10`, `1e999`, `9007199254740993` and 30-digit integers all round-trip byte-exact
(jq 1.7/1.8 does this too; jaq normalizes `1e999` differently). BUT runtime values get JS
types:

- Integers beyond ±2^53 parse as **BigInt**. Mixing with Number throws:
  `this.x + 1` → `TypeError: Cannot mix BigInt and other types, use explicit conversions` (rc 1).
  Fix: `this.x + 1n` for exact BigInt arithmetic (`9007199254740993 + 1n` → `9007199254740994`),
  or `Number(this.x)` to knowingly degrade.
- Small ints and floats are Number (exact float64 arithmetic, no error).
- `1e999` compares `> 1e308` as true — usable as an infinity in tests, though it is not a float.

## Output — what breaks strict JSON consumers

- Result is a **string** → printed *unquoted* (jq's `-r` is always on):
  `echo '{"n":"x"}' | fx '.n'` → `x`. jq prints `"x"`.
- Missing path → the literal `undefined` printed **on stderr with exit code 0** — no output on
  stdout, the exit code says success. Check both when gating on fx.
- Computed `NaN` and `Infinity` print literally (`{ "v": Infinity }`, top-level `Infinity`),
  rc 0. Input `NaN` is accepted non-strict and preserved.
- `{"u": x.missing}` embeds as `null` inside objects, but a bare undefined top-level result is
  the `undefined`-on-stderr case above.
- Pretty-print inlines small objects/arrays on one line (`{ "a": 1 }`); `--no-inline` disables.
- Default indent 2; `FX_INDENT=0` compacts (`"b": [ 1, 2 ]` retains inner spaces), any other
  value sets the width. `save()` always uses 2-space indent with a trailing newline.
- All fx errors (input parse, expression, save) go to stderr with a caret snippet, rc 1.

## Input formats

Six parsers convert input to JSON; the flag or the file's **extension** selects (`.yaml`,
`.yml`, `.toml`, `.edn`, `.xml`, `.svg`, `.html`, `.htm`, `.maml`):

```bash
fx config.yaml --no-tui        # extension auto-detect, prints JSON
cat doc.xml | fx --xml --no-tui
```

Measured shapes (all print JSON):

- XML: attributes become `"@name"`, element text becomes `"#text"`, and **all values are
  strings** (`<a>1</a>` → `"a": "1"`).
- HTML: wraps everything as `{ "html": { "head": ..., "body": ... } }`.
- MAML (maml.dev config syntax): `{zebra: 1, alpha: 2}`, newline-separated properties; YAML
  syntax is rejected (`maml: Unexpected character`).
- EDN: `{:a 1 :b "x"}` → `{"a": 1, "b": "x"}`.
- JSON non-strict (default) additionally accepts **`//` comments** and **trailing commas**.
- `--strict` = RFC 8259 mode: comments refused (`Comments are not allowed in strict mode`),
  trailing commas refused, `NaN`/`Infinity` literals refused. Duplicate keys are preserved as-is
  in both modes.
- `--raw` (`-r`) treats input (including a text file) as a plain string:
  `printf 'hello' | fx -r 'this.toUpperCase()'` → `HELLO JSON`. `--raw` wins over the extension.
- `--slurp` (`-s`) reads every input value into one array (`printf '1 2 {"a":3}' | fx -s` →
  `[1, 2, {"a": 3}]`; empty input still gives `[]`). `-rs`/`-sr` combine both.
- Several formats at once is an error (`can't use --yaml and --toml flags together`, rc 1).

## Editing files in place — save() and the viewer

Scripted edit, atomic rewrite (single JSON value only, always 2-space):

```bash
cp data.json data.json.bak
fx data.json 'x => { x.n = 42; return x }' 'save'    # file rewritten without .bak
```

Measured refusals (all rc 1, stderr): no file argument (`specify a file as the first
argument to be able to save`); a file holding multiple JSON values (`save supports a single
JSON value, but x.json contains several`); a non-JSON file (`save writes JSON, but x.yaml is
YAML: it can't replace it`).

The viewer is also an editor: move the cursor to a node and **`dd`** deletes it (the first
`d` alone is only a pending key), `y` yanks (subkeys `y` value, `k` key, `p` path, `b`
key+value), then `:w[rite]` writes the *displayed* result — the file or a given path, asking
`Overwrite ...?` without `!` (`:w!` skips confirmation), `:w !cmd` pipes it to a shell
command, `:wq` writes and quits. Measured end-to-end: delete a key with `dd`, `:w!`, and the
file on disk no longer contains the key.

## The viewer

Quit `q`/`ctrl+c`; nav `j/k/h/l`, `enter`/`backspace`; expand/collapse recursive `L`/`H`,
all `e`/`E`, level by digit `1`–`9`; siblings `J`/`K`; matching bracket `%`; strings wrap
toggle `z`; regexp search `/` with `n`/`N` (status `found: [k/k]`); query input `.` with tab
completion and live preview; goto symbol `@`, goto `$ref` `ctrl+g`; preview pinned node `p`;
print node at exit `P`; reload file `r`; history `[` / `]`; mouse enabled by default
(`FX_NO_MOUSE=1` disables). Command line `:`: `:<n>` goto line, `:w[!] [file|!cmd]`, `:wq`,
`:q[uit]`. Suspend `ctrl+z`; paging `f`/`b`/space/`pgup`/`pgdown`, half-page `ctrl+d`/`ctrl+u`.

Environment knobs (no flags for these; all measured):

- `FX_NO_TUI=1` — force headless output even with no expression.
- `FX_COLLAPSED` — start collapsed; `FX_LINE_NUMBERS=1` shows a gutter;
  `FX_SHOW_SIZE=true|yes|on|1` appends `(4 keys)`/`(2 items)` annotations.
- `FX_THEME` — theme by name: `0 1 2 3 4 5 6 7 8 9 🔥 🔵 🟣 🥝` (default `1`; ASCII terminals
  fall back to `0`). Unknown theme → stderr warning listing all names, exit 1.
- `FX_INDENT` — pretty-print width (`0` = compact).
- `FX_PPROF` — internal diagnostics; drops `cpu.prof`/`mem.prof` into the current directory.
- Over SSH (`SSH_CONNECTION` or `SSH_TTY` present), yank/copy uses OSC52 instead of a local tool.

`--themes` renders a swatch sampler (`export FX_THEME="..."` lines); `--export-themes` prints
the ANSI code matrix as JSON to stdout; `--comp bash|zsh|fish` prints a completion script
(`eval "$(fx --comp bash)"`; unknown shell prints `unknown shell type` at rc 0). `--dungeon`
opens a small roguelike (`Find the Golden Brace { on depth 8`).

## Version wall (measured on conda-forge builds)

| Feature | 38.0.0 | 39.1.0 | 40.0.1 |
| --- | --- | --- | --- |
| `--yaml` | yes | yes | yes |
| `--toml` | no | yes | yes |
| `--edn --xml --html --maml` | no | no | yes |
| `--themes`, `--comp` | yes | yes | yes |
| `--dungeon`, `--no-tui` | no | no | yes |
| Unknown flags | become junk expressions (silent rc 0 or ReferenceError) | same | same |

The TTY panic and `FX_*` knob set above are the 40.x contract; older builds lack them and
stay silent instead of failing loudly.

## jq → fx migration cheatsheet

| jq | fx | Note |
| --- | --- | --- |
| `.n` → `null` on missing key | `.n` → `undefined` on stderr, rc 0 | Gate on both the stream and the code |
| `"x"` quoted string results | `x` unquoted | jq's `-r` is fx's default |
| `sort` numeric on numbers | `sort` lexicographic; use `sortBy(x => x)` | Classic porting bug |
| Arithmetic stays exact past 2^53 | BigInt/Number mixing throws; rewrite with `1n` | fx output is still literal-exact |
| Input must be strict JSON | comments and trailing commas accepted; `--strict` restores RFC mode | fx is the lax side |
| `nan` → `null` (tojson) | `NaN`/`Infinity` print literally | Non-JSON output, rc 0 |
| `-s` slurp stream | `-s` identical behavior | |
| `walk(...)` | `walk(fn)` identical idea | |

## Recipes (all executed live against 40.0.1)

```bash
# Explore an API response interactively (terminal only)
curl -s https://example.com/data.json | fx

# Headless pretty-print (script-safe, no TTY)
fx big.json --no-tui

# Extract every user's name from a nested array
fx users.json 'x => x.users.map(u => u.name)'

# Filter numbers above 10 and print the kept values
printf '%s' '[5,11,20]' | fx '?x => x > 10' --no-tui

# Sort by a key, top of the list
fx data.json 'x => x.items' 'sortBy(i => -i.score)' --no-tui

# JSON -> YAML without leaving the pipeline
printf '%s' '{"a":1,"b":[2,3]}' | fx 'YAML.stringify(this)' --no-tui

# Validate strict JSON with a caret pointing at the error
fx --strict --no-tui api.json

# Drop a key everywhere, write the file back
fx cfg.json 'walk(obj => { delete obj.debug; return obj })' 'save'
```

One gotcha in the filter recipe: `?` is a filter operator, but a ternary that *mentions*
`skip` inside a `@` map does not drop values — it embeds the placeholder string `"skip"` in
the output (measured: `@x => x > 10 ? x : skip` prints `["skip", 11, 20]`). Filter with `?`,
and reserve `skip` for whole-value suppression returned by a lambda.
