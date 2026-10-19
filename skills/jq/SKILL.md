---
name: jq
description: Use when a shell command or agent script must extract, filter, reshape or validate JSON — pulling fields out of API responses, filtering a stream of objects, grouping, deep-merging, converting to CSV/TSV/URI, building payloads from script arguments, or debugging a jq one-liner that printed nothing. Covers jq 1.8.x — the stream model, exit codes 0/2/3/5, the // alternative, -e gates and argument passing. Behaviors measured live.
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
---

# jq — JSON on the command line

`jq` ([jqlang/jq](https://github.com/jqlang/jq)) is the standard filter language for JSON: read a
stream of JSON values, apply a filter to each value, print the results. This skill is **original
text written from live binary behavior**, pinned to jq **1.8.2** (the current release as of
writing); upstream's license is not a plain SPDX-MIT (the GitHub API reports `NOASSERTION`, its
COPYING bundles terms for embedded components) — irrelevant here, because no jq code is quoted,
only measured behavior. The exit taxonomy and `//` semantics below were re-measured identical on
a distro `jq-1.7` build.

## The stream model — read this first

jq runs the filter once **per JSON value on the input stream**, not once per invocation:

```bash
printf '{"a":1}\n{"a":2}\n' | jq '.a'   # prints 1, then 2
```

Consequences, all measured:

- A `select` that matches nothing emits **no output at all** — not `null`, not `[]`; the exit
  code stays 0. Collect results with `-s`, or wrap the filter in `[...]`.
- **Empty input is not an error**: no bytes on stdin → no output, exit 0. With `-s` the same
  empty input yields `[]`, still exit 0. A script can therefore "succeed" while printing nothing.
- Inside a filter, `,` means "produce both", `|` feeds onward. A `;` between filters is a
  **compile error** (`;` only separates function arguments).

## Install

Pin the static binary — one file, no dependencies:

```bash
curl -sL -o jq https://github.com/jqlang/jq/releases/download/jq-1.8.2/jq-linux-amd64
chmod +x jq && ./jq --version   # jq-1.8.2
```

Release tags are `jq-<version>`; per-platform assets are listed on the release page (the Linux
x86_64 asset used above was verified). Homebrew installs `jq`; distro packages exist but lag —
the Ubuntu box measured here ships `jq-1.7` while the pinned release is 1.8.2.

## Exit codes — measured taxonomy

```text
0   ok (even when input was empty or selects matched nothing)
2   usage error — unknown option ("jq: Unknown option --bogus"), or a bad
    --argjson value ("jq: invalid JSON text passed to --argjson")
3   compile error — filter syntax; stderr ends with a "jq: 1 compile error" line
5   input parse error OR runtime error (both use 5)
```

With `-e`, the exit code describes the output:

```text
0   last output was neither null nor false
1   last output was null or false
4   no output at all (nothing matched, `empty`, a `?`-suppressed miss)
```

Two things to notice:

- **A parse error on the input is 5, not 2.** Truncated JSON (`echo '{' | jq .`) dies with
  `jq: parse error: Unfinished JSON term at EOF at line 2, column 0`; plaintext piped in
  (`hello`) also dies at parse — `jq: parse error: Invalid numeric literal at line 2, column 0`.
- Runtime errors carry the input position: `jq: error (at <stdin>:1): Cannot index number with
  string ("b")`.

## `//` — the alternative operator (truthiness is jq's, not the shell's)

`A // B` evaluates A and falls through to B only when A yields **no output, false, or null**.
Everything else — including `0` and `""` — does *not* fall through:

```bash
echo '{"z":0,"e":""}' | jq -c '.z // "d"'   # 0   — zero is truthy
echo '{"z":0,"e":""}' | jq -c '.e // "d"'   # ""  — empty string is truthy
echo '{"m":1}'        | jq -c '.m // "d"'  # 1
echo '{}'             | jq -c '.m // "d"'  # "d" — missing key is null
echo '{}'             | jq -c 'empty // "d"'   # "d" — an empty stream falls through
```

But `//` **does not catch errors** — `error("boink") // "d"` still aborts with exit 5. Suppress
the error yourself first (`(.x?.b?) // "d"`).

## `-e`: the "is it there" gate

`-e` turns output shapes into shell decision points:

```bash
jq -e '.token' f.json >/dev/null        # 0 = field present and non-null
jq -e '.[0]'   f.json >/dev/null        # null on an empty array → 1
jq -e 'select(.state=="open")' f.json >/dev/null   # 4 = nothing matched
```

## Nulls, missing keys, `?`, and updates

- Reading a **missing key is quiet**: `{}` → `.b` → `null`, exit 0. Indexing `null` also yields
  `null` without error.
- Indexing the **wrong type** is exit 5: `.b` on an array (`Cannot index array with string
  ("b")`), `.b` on a string, `.[0]` on an object (`Cannot index object with number (0)`).
  Number-index an array, string-index an object — never the reverse.
- `.b?` removes the error and yields **no output** (not null): `echo '[1]' | jq '.b?'` prints
  nothing, exit 0 (and `4` with `-e`).
- `has("k")` answers for objects only — on a string it errors with `Cannot check whether string
  has a string key` (exit 5).
- `del(.a)` removes a key. **`.b |= 9` creates the key when missing** (measured on an object
  and on null input); `.b //= 9` writes only when the value is missing, null or false.

## Passing arguments in

```bash
jq -n --arg s 100 '$s | type'       # "string"  — --arg values are strings
jq -n --argjson s 100 '$s | type'   # "number"  — --argjson must be valid JSON
jq -n '$ARGS.positional' --args a b            # ["a","b"]
jq -n '$ARGS.positional' --jsonargs '{"x":1}'  # [{"x":1}]
jq -n -c '$d' --slurpfile d f.json  # array of every JSON value in the file
jq -n -r '$r' --rawfile r f.txt     # the file as one string
```

Bad `--argjson` values are rejected up front, exit 2:

```text
jq: invalid JSON text passed to --argjson
```

Build request payloads from args with the object shorthand — `{ ... , $s }` means `s: ($s)`:

```bash
jq -n --arg s hi '{msg: "x", $s}'    # {"msg":"x","s":"hi"}
```

## Input and output modes

```text
-c  compact output; -S sort keys; --tab; --indent n (max 7 spaces)
-r  print strings raw (non-strings still render as JSON)
-j  -r without the trailing newline (multiple outputs glue together)
--raw-output0  -r with a NUL after each output ('a\0b\0' measured) — pairs with xargs -0
-R  read each LINE as a string; -Rs slurps the whole file as one string
-n  no input — build from constants or iterate `inputs`
-s  slurp every input value into one array
```

Line-to-array recipe (measured): `jq -Rs 'split("\n")[:-1]' f.txt` → `["a","b"]`; for an
already-JSON-values stream, `jq -n '[inputs]'` does the same.

## Recipes

All single-line and measured on 1.8.2:

```bash
jq '[.[] | select(.state=="open")]' issues.json    # filter a list, keep as array
jq -r '.[] | .name' list.json                      # one value per line
jq -c 'group_by(.k) | map({t: .[0].k, n: length})' # counts per key (group_by sorts first)
jq 'to_entries'                                    # {"a":1} → [{"key":"a","value":1}]
jq -c 'with_entries(.value += 1)'                  # transform entries in place
jq -n -c '{"a":{"x":1}} * {"a":{"y":2}}'           # deep merge: {"a":{"x":1,"y":2}}
jq -c '[paths]'                                    # path to every leaf: [["a"],["a","b"]]
jq -n -c '{"a":{"b":1}} | fromstream(tostream)'    # exact roundtrip
jq -c '["x",1,true,null] | @csv'                   # "x",1,true,  — null becomes an EMPTY field
jq -c '["a b",123] | @tsv'                         # "a b\t123"  — numbers coerced
jq -rn '"a=b,c" | @uri'                            # a%3Db%2Cc
jq -rn '"a b" | @sh'                               # 'a b'
jq -rn '"hi" | @base64'                            # aGk=
echo '"{\"a\":1}"' | jq 'fromjson'                 # double-decoded {"a":1}
printf 'id=42\n' | jq -R 'capture("(?<id>\\d+)")'  # {"id":"42"}
jq -n '"1" | tonumber'                             # 1 — arithmetic needs this
jq -n '[limit(2; 1,2,3)]'                          # [1,2] — limit yields a stream; collect it
jq -n 'env.HOME | type'                            # "string" ($ENV works; "$env" is a compile error)
```

String `tostring` vs `tojson`/`@json` differ for strings: `tostring("a")` → `a`,
`tojson("a")` → `"\"a\""` (adds the quotes back).

## Numbers

- JSON **literals print verbatim**: `1.0` stays `1.0`; `12345678901234567890` keeps every digit
  (no precision loss on input literals); exponent input prints normalized (`1e3` → `1E+3`).
- **Computed values are IEEE doubles**: `0.1+0.2` → `0.30000000000000004`. And `"1" + 0` is an
  error — `string ("1") and number (0) cannot be added` — use `tonumber`.
- `length` on a number is its absolute value (−3 → 3); on null → 0; strings → characters;
  arrays/objects → element/key count.

## Builtins worth knowing

- `keys` returns keys **sorted**; `keys_unsorted` keeps insertion order (measured `[a,b]` vs
  `[b,a]` on `{"b":1,"a":2}`).
- `..` yields the value plus every descendant (`[..]` on `{"a":{"b":1}}` → itself, `{"b":1}`, 1).
- `first`/`last` take streams; `add` sums arrays; `any`/`all`; `test("b")` regex-tests strings;
  `if ... then ... else ... end`; `and`/`or`/`not`.
- `ltrimstr` and friends are conditional: no match leaves the string unchanged.

## Debugging a one-liner that printed nothing

1. **Was the input valid?** Plaintext and truncated JSON die at parse (exit 5, message on
   stderr). Empty input prints nothing with exit 0.
2. **Did nothing match?** Re-run with `-e`: exit 4 = no output; 1 = last output was
   null/false; 0 = a real value.
3. **Did a `?` swallow the path?** Rewrite the chain without `?`s — `.b?` on the wrong type
   yields nothing instead of an error.
4. Wrong-type indexing (`.[0]` on objects, `.key` on arrays) is exit 5 — fix the index type or
   add the matching `?`.

## Limits

Everything above is the measured surface of jq 1.8.2 (flags quoted from `jq --help`). Not
covered: module loading (`-L`, imports), `--stream`/`--seq` input modes, and jq the scripting
language beyond one-liners — see `man jq` and [jqlang.org](https://jqlang.org). Flag behavior is
version-specific: re-run `jq --version` and `--help` before trusting older-version assumptions.