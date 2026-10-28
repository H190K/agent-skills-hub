---
name: miller
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
description: "Use when converting, filtering, joining, or summarizing column-shaped data - CSV, TSV, JSON, JSONL, DKVP, NIDX, XTAB - from a terminal: miller (mlr) is a typed streaming record processor whose RFC4180 quoting survives commas inside fields, where awk and cut do not, and whose CSV endpoints make it friendlier than jq for tabular output. Covers type-inference edges, the inverted join -f flag, schema fail-closed, and in-place edits. Measured on the v6.22.0 release, cross-checked on 6.11.0."
---

# miller — typed record processing for CSV, TSV, JSON, and friends

`mlr` ([johnkerl/miller](https://github.com/johnkerl/miller)) is a single-binary
stream processor for tabular and semi-structured data: it reads one of ten
formats, treats input as a stream of typed records, and applies *verbs* —
74 of them — chained with `then`. Where `awk` and `cut` see text, Miller sees
columns, and its CSV reader implements RFC4180 quoting: fields with embedded
commas, quotes, and spaces survive every conversion. Everything below was
measured live on the **v6.22.0 release binary** (2026-09-25) and cross-checked
on the Ubuntu 24.04 distro build `miller 6.11.0` — behavior was identical on
both except error-message punctuation. Upstream is BSD-2-Clause (John Kerl);
the skill text here is original.

## The record-stream model — read this first

- Every input is records; every verb reads records upstream and writes records
  downstream. Chaining uses `then`, not pipes, so one process does the whole
  pipeline: `mlr --icsv --ojson stats1 -a min,mean,max -f quantity then sort -f color data.csv`
- With no verb, `cat` runs — that is the format-converter use.
- **Default input and output format is DKVP.** A bare `mlr cat data.csv` on a
  real CSV parses the header row as data (`1=a,2=b`) — always pass explicit
  format flags like `--icsv --ojson`.
- `mlr --help` itself barely helps (it is ~13 lines of pointers). The real
  surfaces: `mlr help topics`, `mlr -l` (74 verbs, one per line),
  `mlr -g` (713 lines of flags), `mlr help verb <name>`,
  `mlr help type-arithmetic-info`, and `mlr help find <word>` when you can not
  remember a name.

## Install

- GitHub releases ship per-platform tarballs, for example
  `miller-6.22.0-linux-amd64.tar.gz`, which unpack to `bin/mlr` (a stripped,
  statically linked Go binary) plus `LICENSE.txt` and `README.md`. Put `mlr`
  on PATH.
- Ubuntu: `sudo apt-get install miller` — the 24.04 package measured here is
  `miller 6.11.0` (dynamically linked). Feature surface of 6.11 matched 6.22
  on everything measured for this skill; error texts differ slightly.
- Verify with `mlr --version` (prints e.g. `mlr 6.22.0`).

## Formats — always name both ends

The keystroke-saver matrix covers ten formats — CSV, TSV, JSON, JSON-lines,
DKVP, NIDX, XTAB, PPRINT, markdown, and YAML — plus DCF and GNU-recutils
round-trips. Name input and output explicitly; long forms compose
(`--icsv --ojson`), and the savers give `--c2j`, `--j2c`, and same-format
shorthands (`-c` for CSV in and out):

```bash
mlr --c2j < data.csv                 # CSV to pretty JSON
mlr --csv head -n 3 data.csv         # --csv names CSV on both ends
mlr --icsv --oxtab cat data.csv      # vertical, human-readable records
mlr --icsv --omd cat data.csv        # markdown table for a report
```

**Prefer `--ojsonl` (one record per line) when another program consumes the
output.** `--ojson` always pretty-prints *one JSON array of all records* —
even for a single record — and `--jlistwrap` does not change that (measured;
both print the same `[ {...}, {...} ]` block). jq handles the array fine, but
per-line JSONL is friendlier for line-oriented shells.

The markdown writer is a preview, not a data format: CSV quoting is dropped
(`q""q` renders as `q"q`, embedded commas sit bare in cells). XTAB likewise
reads well but is not for re-parsing.

## What CSV/TSV parsing infers — measured type table

Miller types every field on read. From a CSV row `1,2.5,true / 001,,3.0`:

- `1` - integer; `2.5` and `3.0` - floats (`3.0` keeps its `.0`)
- `001` - **string**. Leading zeroes preserve the literal; do not expect `"001"`
  to become 1.
- `true` / `false` - **strings**. Unlike jq, Miller does not infer booleans from
  CSV text — `"c": "true"` comes out with a string annotation.
- Empty field - empty string `""`, never null.
- Duplication in JSON input resolves last-wins (`{"a":1,"a":2}` reads as `a: 2`,
  rc 0).

Check types when a filter misbehaves: `put '$t = typeof($a)'` prints `int`,
`string`, and friends; `mlr help list-functions` lists `is_numeric`,
`asserting_numeric`, and the rest.

A header-only CSV produces **empty output at rc 0** — no header row is emitted
when there are no records. If your downstream expects a header, that silence
looks like a broken pipe; test your file with `head -1` first.

## JSON to CSV: flattening is automatic (and 1-based)

Moving nested JSON into a flat format flattens maps and arrays with dot
separators — `{"a":{"b":1,"deepest":2},"c":[7,8]}` becomes columns
`a.b,a.deepest,c.1,c.2`. Array indices are **1-based** (`c.1`, `c.2`).

- `--flatsep <sep>` changes the separator (measured with `::`).
- `--no-auto-flatten` keeps nested values as raw JSON embedded in one quoted
  CSV cell instead (quote-doubled per RFC4180).

## The DSL: put and filter — single-quote everything

`put` adds/rewrites fields with assignments; `filter` drops records. Quote the
expression with **single** quotes so the shell does not expand `$field` before
Miller sees it: `put "$a + $b"` dies with `parse error: unexpected equals`
because the shell substituted empty variables. Measured working forms:

```bash
mlr --icsv --ojsonl put '$sum = $a + $b; $label = $c . "-x"' data.csv
mlr --icsv --ocsv  filter 'is_numeric($a) && $a > 1' data.csv
mlr --idkvp --ojson put '$stamp = sec2gmt(1700000000)' log.dkvp
```

Type rules that bite (all measured):

- Arithmetic is typed. A string inside `+` does not raise a process error — it
  evaluates to the literal field value `(error)` **at rc 0**:
  `put '$sum = $a + $b'` over a row where `a` is `"001"` emits `{"a":"001", ...,
  "sum": (error)}` and the run still exits 0. Scan for `error` in records when
  arithmetic output looks thin.
- String literals behave the same way: `"$x = \"3\" + 4"` is `(error)`; use
  `int("3") + 4` style functions if you truly need coercion — and see
  `mlr help type-arithmetic-info` for the full in-binary truth table (empty
  string acts as an additive identity: `(empty) + 1` is `1`).
- Concatenation is `.` (dot), not `+`.

The mixed-type comparison trap: filter `$a > 1` over a column holding
`1, 001, x, 7` outputs the **string** rows and the 7 — Miller's total order
places all strings after all numbers, so any string compares greater than any
number. Gate it: `is_numeric($a) && $a > 1` keeps only the genuinely numeric
row (both halves measured on one fixture).

## Sorting and aggregation

- `sort -f c` sorts lexically, `sort -n a` numerically; suffix `-r` reverses
  (`-nr` measured). Mixed columns follow the same total order as above: numbers
  first, then strings — verify on a sample before trusting an ordering.
- `stats1 -a sum,count,mean,min,max -f val [-g group]` accumulates over the
  stream and names output fields like `a_sum` (field name underscore
  accumulator). There is **no legacy `-s`**: `stats1 -f a -s sum` hard-errors
  `mlr stats1: -a option is required` (measured).
- Group-by works on positional NIDX fields too:
  `mlr --inidx --ifs " " --onidx stats1 -a count -f 2 -g 1 access.log`.
- `uniq -f b` deduplicates (adding `-c` counts, same as `count-distinct`); note
  its help line that output fields come in the order *named*, not input order.
- Sort the emitted column by its real name: `-f amount -a sum` produces
  `amount_sum`, not `a_sum`. Sorting a field that does not exist ties every
  record and silently returns stream order — a broken pipeline looks like a
  working one with no sort applied (measured).

## join — the -f flag means the LEFT file

This is the trap that ends SQL-muscle-memory invocations:

- `mlr --icsv --ocsv join -j id -f lookup.csv main.csv` — per Miller's own help
  text, `-f {left file name}` names the **left** file (the lookup table read up
  front); the positional file is the right/stream side. Output column order is
  left-file fields first, then stream fields (measured `id,nn,nv`).
- Unpaired records of the positional file are **silently dropped** without
  `--ur`; `--ul` emits unpaired records from the `-f` file. Reversed intuition
  from "left join" is common here — reverse it.
- Emitting unpaired rows can trip the strict CSV schema check: on one fixture
  `--ur` printed the paired rows, then died rc 1 with
  `CSV schema change: first keys "id,nn,nv"; current keys "id,nv"` because the
  appended row had fewer fields. If rows differ in shape, separate them.

## Ragged rows and schema changes: fail-closed, but late

- Default reading is strict: a row with a different field count aborts with
  `CSV header/data length mismatch 3 != 2 <file> row 3` at rc 1 — **after the
  good rows have already streamed to stdout**. Scripts must gate on the exit
  code, never on "some rows appeared".
- `--allow-ragged-csv-input` (alias `--ragged`) makes short rows produce
  records with the missing fields simply *absent* (`{"a":4,"b":5}`), while an
  overlong row keeps its extra values **named by position**: the fourth value
  lands under a field literally named `"4"`. `--lazy-quotes` is the other
  reader escape valve (quotes inside unquoted fields).
- Different schemas across files is fatal with no escape flag: `cat a.csv b.csv`
  where b has different columns gives `CSV schema change: ...; exiting due to
  data error` at rc 1 (verified against the complete 713-line flag list —
  nothing relaxes this check in v6.22). Process heterogeneous files one by one.

## In-place edits: -I only

`mlr -I --icsv --ocsv put '$x2 = $a * 2' file.csv` rewrites the file in place
with the new column, same as streaming but destructive. Measured edges:

- The long form **does not exist**: `--in-place` errors
  `option "--in-place" not recognized` at rc 1. Only `-I`.
- `-I` with piped stdin hard-errors `-I option (in-place operation) requires
  input files.`
- No backup copy is made. When the transformation is unproven, write to a
  different file first and compare.

## BOM handling (v6.22.0)

The CSV reader strips a leading UTF-8 BOM. The TSV reader does **not**: the BOM
stays glued to the first field name (a record keys as `"\ufeffid": 1`), so a
spreadsheet-exported TSV gets a poisoned first column. Upstream has a master
fix for this; the released v6.22.0 still ships the behavior (measured on both
versions here).

## Exit codes, help surfaces, and error style

- rc 0 = success (including empty input and no-match `--all`-free filters).
- Every failure measured at rc 1: unknown verb (`mlr: verb "zort" not found.
  Please use "mlr -l" for a list.`), unknown flag, missing file, DSL parse
  error, data error. There is no 2-class distinct from 1 here, unlike the GNU
  families — check for nonzero, not specific values.
- Error wording itself drifts between minor versions (6.11 ends messages with
  periods and suggests `mlr --help`; 6.22 points at `mlr -l`). Match on the
  invariant prefix (`mlr:`) rather than the whole sentence.

## Config defaults: MLRRC

`$HOME/.mlrrc`, a project-local `./.mlrrc`, or an `MLRRC=<path>` environment
variable set defaults so `mlr cat data.csv` means your usual conversion.
Format (per the binary's own `mlr help mlrrc`, and measured):

```text
--icsv
--ojson
```

**One flag per line.** A single line reading `--icsv --ojson` silently applies
only the first flag (measured: input respected, output stayed DKVP). The
leading `--` is optional; `#` comments and blank lines are ignored.

## Recipes

```bash
# Peek at data as a human
mlr --icsv --oxtab cat data.csv | head -40

# One-shot JSONL for a downstream script that wants records
mlr --icsv --ojsonl cat data.csv > records.jsonl

# Top-N of a grouped sum (note the emitted column name: field + "_" + accumulator)
mlr --icsv --ojson stats1 -a sum -f amount -g country then sort -nr amount_sum then head -n 10 data.csv

# In-place column fix (rename a column in flight)
mlr --icsv --ocsv rename old_name,new_name data.csv | tee data-fixed.csv

# Whole-file rewrite in place with a new column
mlr -I --icsv --ocsv put '$total = $qty * $price' sales.csv
```

## Shipped recipe — verify a fresh install

Run this with bash after installing; it recreates the measured behaviors and
asserts each one, so a broken or aliased `mlr` shows up in seconds:

```bash
if ! command -v mlr >/dev/null 2>&1; then
  echo "mlr is not on PATH - install miller first (see Install section)"; exit 1
fi
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
printf 'a,b,c\n1,2.5,true\n001,,3.0\nx,y,"hello, world"\n7,"a, b","q""q"\n' > "$T/f.csv"
printf '{"a":{"b":1},"c":[7,8]}\n' > "$T/n.json"

# 1. type inference: leading-zero and boolean text stay strings
mlr --c2j cat "$T/f.csv" | grep -q '"a": "001"'  || { echo FAIL types-001;  exit 1; }
mlr --c2j cat "$T/f.csv" | grep -q '"c": "true"' || { echo FAIL types-bool; exit 1; }

# 2. JSONL out is one record per line; ojson is one array
test "$(mlr --icsv --ojsonl cat "$T/f.csv" | wc -l)" = 4 || { echo FAIL jsonl; exit 1; }

# 3. JSON to CSV flattens: 1-based array keys, dot map keys
mlr --ijson --ocsv cat "$T/n.json" | grep -q '^1,7,8$' || { echo FAIL flatten; exit 1; }

# 4. string arithmetic yields an in-record error value at rc 0
mlr --idkvp --ojson put '$x = "3" + 4' <<< 'k=1' | grep -q '(error)' || { echo FAIL errval; exit 1; }

# 5. mixed-type order: ungated filter leaks strings through; is_numeric gates it
mlr --icsv --ocsv filter '$a > 1' "$T/f.csv" | grep -q '^x,y,' || { echo FAIL mixed-order; exit 1; }
mlr --icsv --ocsv filter 'is_numeric($a) && $a > 1' "$T/f.csv" | grep -q '^7,' || { echo FAIL gate; exit 1; }

# 6. join: -f is the left/lookup file; unpaired stream rows drop silently
printf 'id,nn\n1,100\n' > "$T/r.csv"; printf 'id,nv\n1,10\n2,20\n' > "$T/l.csv"
test "$(mlr --icsv --ocsv join -j id -f "$T/r.csv" "$T/l.csv" | wc -l)" = 2 || { echo FAIL join; exit 1; }

# 7. cross-file schema change fails closed (rc 1)
printf 'id,nn\n3,300\n' > "$T/o.csv"
mlr --icsv --ocsv cat "$T/l.csv" "$T/o.csv" >/dev/null 2>&1 && { echo FAIL schema; exit 1; }

# 8. in-place: -I rewrites the file; the long form does not exist
printf 'a,b\n1,2\n' > "$T/ip.csv"
mlr -I --icsv --ocsv put '$x2 = $a * 2' "$T/ip.csv"
grep -q '1,2,2' "$T/ip.csv" || { echo FAIL inplace; exit 1; }
mlr --in-place --icsv --ocsv cat "$T/ip.csv" >/dev/null 2>&1 && { echo FAIL longform; exit 1; }

# 9. MLRRC: one flag per line
printf -- '--icsv\n--ojsonl\n' > "$T/rc"
test "$(MLRRC="$T/rc" mlr cat "$T/f.csv" | wc -l)" = 4 || { echo FAIL mlrrc; exit 1; }

# 10. strict reader streams partial output before the fatal
printf 'a,b,c\n1,2,3\n4,5\n' > "$T/rg.csv"
mlr --icsv --ocsv cat "$T/rg.csv" > "$T/out.txt" 2>/dev/null
grep -q '^1,2,3$' "$T/out.txt" && test $(mlr --icsv --ocsv cat "$T/rg.csv" >/dev/null 2>&1; echo $?) = 1 \
  || { echo FAIL partial-then-fatal; exit 1; }

echo "miller recipe-check: ALL PASS"
```