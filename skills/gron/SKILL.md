---
name: gron
description: Use when JSON needs grep/diff/sed treatment instead of a query language — flattening an API response into one line per leaf so a subtree can be grepped out, a key deleted, two documents diffed statement by statement, or a file edited and rebuilt with gron -u. Covers gron 0.7.x — exit codes, NDJSON streaming, ungron's unforgiving input contract, -v's stdin-only quirk. Behaviors measured live.
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
---

# gron — make JSON greppable

`gron` ([tomnomnom/gron](https://github.com/tomnomnom/gron), MIT) turns JSON into discrete
assignment statements — one line per leaf, each a full path with its value:

```bash
printf '{"b":2,"a":{"x":[1,2]},"c":null}' | gron
# json = {};
# json.a = {};
# json.a.x = [];
# json.a.x[0] = 1;
# json.a.x[1] = 2;
# json.b = 2;
# json.c = null;
```

This makes JSON workable with plain `grep`, `diff`, `sed` and `awk` — no query language needed.

**Pairing with jq:** `jq` (see the `jq` skill) answers *query* questions (`jq -r '.a[0].b'`);
gron answers *text-tool* questions — grep a pattern across paths, diff two files, hand a subtree
to `sed` and put the JSON back. They are complementary, not competing.

This skill is **original text written from live binary behavior**, pinned to the **v0.7.1**
release tarball (the current release as of writing) and cross-checked on the distro build
(Ubuntu's `gron 0.7.1-2ubuntu0.24.04.3`) — both binaries produced identical output on every
probe below.

## Install

No runtime dependencies (per upstream README), three routes:

```bash
# 1. Release tarball — one file, "gron":
curl -sL https://github.com/tomnomnom/gron/releases/download/v0.7.1/gron-linux-amd64-0.7.1.tgz \
  | tar xz
# 2. Go:
go install github.com/tomnomnom/gron@latest
# 3. Homebrew (macOS): brew install gron — Debian/Ubuntu ships it: apt-get install gron
```

Version note measured on the v0.7.1 tarball: the release binary prints `gron version dev`
(the release build skipped the version stamp); the distro 0.7.1 build prints
`gron version 0.7.1`. Upstream's `master` is ahead of the tag and its `CHANGELOG.mkd` stops at
0.6.0 — trust binaries, not the changelog, for the 0.7.x surface (`--no-sort` is in the binary
but not in that changelog).

## The shape of the output

Measured on nested input, each rule explicit:

- The root is always `json` — even for top-level arrays (`json[0] = ...`) and scalars
  (`json = 123;`, `json = "txt";`, `json = null;` all work; `json = -1.5;` too).
- **Empty containers get their own lines**: `json.d = {};` and `json.e = [];` — they never
  vanish, so an `ungron` rebuild keeps empty shells exactly as they were.
- Strings are double-quoted with escapes embedded: `\"` for quotes, `\\` for backslashes,
  `\t` for tabs. Non-ASCII is left **raw** (`json.snäck = 1;`, `json.s = "a\"b\\cé";`) — no
  `\uXXXX` escaping.
- **Numbers print verbatim as written** — jq-style precision loss does not happen:
  `12345678901234567890` keeps all digits, `1.0` and `2.50` keep their trailing zeros (gron
  parses with `json.Number` and `ungron` emits the token as-is).
- Keys that are valid identifiers print as dot paths (unicode included). Everything else is
  bracket-quoted: `json["a.b"]`, `json["a b"]`, `json[""]` (empty key), `json["quote\"k"]`
  (escapes preserved inside the quotes), `json["2"]` (numeric-looking keys are quoted).
- **Duplicate keys in one document: last wins** (`{"a":1,"a":2}` → `json.a = 2;`, exit 0).

## Sorting

Output is **sorted** by default, not document-ordered. The measured order is by printed path:

- Keys that need no quoting sort as bare names **before** all bracket-quoted keys
  (`A`, `_k`, `a`, `b`, `z`, then `["2"]`, `["x y"]`) — ASCII order within each group.
- Array indices compare **numerically**: `[0]...[9]`, then `[10]`, `[11]` — never
  `[0],[10],[1]`.
- `--no-sort` emits document order and skips the sort pass (faster on large documents).
- Sorting is cosmetic and rebuild-safe: `ungron` re-sorts keys itself (below), so a
  `--no-sort` pipeline loses nothing except visual document order.

## Exit codes — all seven, with the triggers that actually fire

From `--help`, 0–6. Measured triggers (errors go to **stderr**; stdout stays clean, and `$?`
should be taken unpiped):

| Code | Measured trigger | Sample stderr |
| --- | --- | --- |
| 0 | any successful gron/`-u`/`-v` run | |
| 1 | file arg that can't be opened | `open /tmp/no.json: no such file or directory` |
| 2 | **unknown/flag usage error** — with the full `--help` text reprinted | `flag provided but not defined: -nope` |
| 3 | **every JSON decode failure**: bad JSON (`{`), garbage bytes, **empty input**, trailing data, reading a directory, a UTF-8 BOM (`ï`), a 404 page's HTML | `failed to form statements: EOF` |
| 4 | URL fetch failure | `Get "http://...": dial tcp ...: connection refused` |
| 5 | `ungron` statement errors (see its contract) | `no statements were parsed` |
| 6 | `failed to encode JSON` per `--help` — no trigger reproduced in 0.7.1 | |

Two traps inside the taxonomy:

- **Bare JSON-decode errors are 3, not 1/2** — a script branching on `exit 1` for "bad JSON"
  gets nothing; branch on 3.
- **The 2 collision**: `--help` documents 2 as *failed to read input*, but the observed 2 is
  the flag parser's usage error. Treat `2` as "invocation error, check your flags".

## `-s` — one JSON doc per line (NDJSON)

```bash
printf '{"a":1}\n{"a":2}\n' | gron -s
# json = [];
# json[0] = {};
# json[0].a = 1;
# json[1] = {};
# json[1].a = 2;
```

- Each **input line** is one document; output is wrapped in a `json = [];` root with per-line
  indices. `gron -s ... | gron -u` prints that stream back as one pretty JSON array.
- **The loudest trap in the tool**: NDJSON fed WITHOUT `-s` is **silently truncated to its
  first value — exit 0**. `{"a":"FIRST"}` + `{"a":"SECOND"}` → `json.a = "FIRST";`, nothing
  else, no warning. Never assume an error will save you; add `-s` whenever input may hold
  more than one document.
- `-s` is line-oriented: **pretty-printed JSON breaks under `-s`** (the `{` line alone is a
  broken document — you get a partial `json = [];` on stdout, then rc 3). Documents must be
  single-line under `-s`.

## `--ungron` — the reason this works as a pipeline

`gron -u` runs the reverse: assignment statements in, JSON out. Rebuild is forgiving about
what you removed — **containers are inferred from the leaves**:

```bash
# Extract a subtree: prefix-grep survives with neither root nor parent lines
gron api.json | grep 'json\.sub\.' | gron -u

# Delete a key or subtree: grep -v
gron config.json | grep -v 'json\.debug' | gron -u

# Hand-edit values with sed, then rebuild
gron config.json | sed 's/^json\.port = 3000/json.port = 8080/' | gron -u

# Diff two JSON files at path granularity (the classic recipe)
diff <(gron a.json) <(gron b.json)
```

Measured rebuild rules:

- Leaf-only input fully reconstructs parents: `json.a.b = 1;` + `json.a.c = 2;` (no root, no
  container) → `{"a": {"b": 1, "c": 2}}`. Indices rebuild arrays; a lone `json.a = {};` line
  yields `{"a": {}}`; a scalar root `json = 42;` yields `42`.
- Deleting only the **leaves** leaves an **empty shell**: drop the child lines but keep
  `json.a.x = {};` and the rebuild contains `"x": {}`. To remove a subtree entirely, drop its
  container line too (a `grep -v 'json\.sub\.'` prefix match takes container + children
  together).
- Output is pretty-printed (2 spaces) with keys **sorted** regardless of input statement
  order — `gron -u` is also a JSON pretty-printer/normalizer; number tokens keep their
  written form across the roundtrip (`1.0` → `1.0`, `2.50` → `2.50`).

**The ungron input contract is strict — these all fail** (rc 5, stderr):

| Input shape | Error | Verbatim tail message |
| --- | --- | --- |
| a statement not ending in `;` | `statement has no value` | |
| a duplicate path | merge failure | `failed to merge statements: unexpected data type for merge` |
| scalar + object on one key (either order) | type conflict | `failed to merge statements: cannot merge object with non-object` |
| blank line or `# comment` between statements | unparsable line | `invalid statement` |
| plain prose / JSON fed in | no statements | `no statements were parsed` |

The failure line names the offending statement — the semicolon case reads, verbatim:
`` ungron failed for `json[2] = {}`: statement has no value ``

And one **silent data-loss trap** with rc 0: `ungron` reads **one statement per line** —
`json.a = 1; json.b = 2;` on a single line rebuilds `{"a": 1}` only; the rest of the line is
dropped without any warning. If a hand-edited pipeline output is missing keys, suspect
two-statement lines before suspecting your gron.

## `-j` — the JSON-pairs stream

`gron -j` ("Represent gron data as JSON stream") emits one `[path, value]` pair per line,
paths as arrays, root as `[]`:

```bash
printf '{"a":1,"b":{"x":2}}' | gron -j
# [[],{}]
# [["a"],1]
# [["b"],{}]
# [["b","x"],2]
```

One-way by design: `gron -j | gron -u` fails (`ungron failed for `[`: invalid statement`,
rc 5) and `gron -u -j` on statements fails too. Use `-j` when a script wants to consume pairs
line-orientedly (e.g. with `while read`), not `-u`'s output.

## `-v` — values only, stdin only

`-v` reads assignment statements and prints just the scalar values, one per line — strings
**unquoted**, numbers/booleans/null raw, containers skipped:

```bash
printf 'json.a = 5;\njson.b = "x";\njson.c = [1,2];\njson.d = null;\n' | gron -v
# 5
# x
# null
```

**Measured quirk (source-confirmed in 0.7.1)**: `-v` scans **stdin only** — a file argument is
ignored silently (`gron -v vfile.txt` outputs nothing, rc 0). Feed it through the pipe.
Escaped-string values whose escapes fail to decode are skipped silently, not errored.

## URL mode — and why you still want curl in front

gron accepts a URL directly (`gron https://host/data.json`) with two measured costs:

- **No HTTP status check**: a 404's HTML body is fetched and then fails to parse as JSON —
  gron exits 3 with `failed to form statements: invalid character '<' ...` rather than
  flagging the HTTP error. You see a decode error for what is really a routing/response
  problem.
- Connection failures are rc 4 with the Go HTTP error verbatim (`Get "...": dial tcp ...`).
- `-k` / `--insecure` skips TLS certificate validation — measured against a local
  self-signed server: without it rc 4 (x509 error), with it rc 0 and clean output.

The robust pattern is curl's status checking feeding gron:

```bash
curl -sf https://host/data.json | gron        # -f turns HTTP errors into rc 22 before gron sees bytes
```

## The `ungron` alias

Any invocation whose binary name ends in `ungron` flips `--ungron` on implicitly (it's in the
flag logic, not the shell): `ln -s "$(command -v gron)" .../ungron && gron x.json | ungron`.
Neither the release tarball nor the distro package ships such a binary — make the symlink if
you want the alias; upstream's README also recommends it.

## Flag quick reference

| Flag | Behavior (measured) |
| --- | --- |
| `-u`, `--ungron` | statements → JSON; strict contract above; output pretty + key-sorted |
| `-s`, `--stream` | one JSON doc per input line (NDJSON); output wrapped in `json = []`; single-line docs only |
| `-j`, `--json` | output as `[path, value]` JSONL pairs; not feedable back to `-u` |
| `-v`, `--values` | RHS scalar values of statement input; **stdin only**; strings unquoted |
| `--no-sort` | skip the sort pass — document order, faster; irrelevant to rebuilds |
| `-c`, `--colorize` | force color even piped (default is TTY-only: piped default and `-m` emit zero ANSI lines; `-c` adds them) |
| `-m`, `--monochrome` | strip color |
| `-k`, `--insecure` | skip TLS cert validation for URL mode |
| `--version` | print stamp — reads `dev` on the 0.7.1 release tarball, `0.7.1` on the distro build |