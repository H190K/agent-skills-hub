---
name: hexyl
version: 1.0.0
description: "Use when raw bytes need reading — carving file structure, checking magic bytes or padding, decoding a blob — whenever xxd or od squints. Measured on hexyl 0.17.0 (conda-forge cross-check, byte-identical): piped output stays colored by default (NO_COLOR beats --color=always, only --color=force beats NO_COLOR), = -syntax for negative --skip, --display-offset math and its help-text lie, squeeze semantics, kB/KiB/0x/block units, panels/width mapping, exit codes, Ubuntu 0.8.0 divergence wall."
---

# hexyl — color-coded hex dumps

`hexyl` renders binary input as a bordered hex dump with a character side:
position panel on the left, hex bytes in the middle, readable glyph panel on
the right, and a default color scheme that classes every byte (NULL, ASCII
whitespace, ASCII control, printable ASCII, non-ASCII) in its own color. It
reads one file argument or stdin, and everything below was measured live on
**hexyl 0.17.0**.

## Install

Any one of these provides `hexyl` on PATH:

```bash
cargo install hexyl
```

or a release binary from `https://github.com/sharkdp/hexyl/releases` (e.g.
`hexyl-v0.17.0-x86_64-unknown-linux-gnu.tar.gz`; the `hexyl_0.17.0_amd64.deb`
ships a byte-identical binary — sha256 checked against the tarball build), or
`conda install -c conda-forge hexyl` (conda-forge 0.17.0 gave **byte-identical
output** on every probe run against the release build). Ubuntu's apt package
is a trap: noble ships **hexyl 0.8.0-2** (2020) — see the version wall for
everything that is missing.

## Anatomy of the output

```bash
hexyl f1.bin
```

renders five bordered panels — position | hex (8 bytes) | hex (8 bytes) |
characters | characters, with a `┊` separator between the two halves. That is
16 bytes per row by default. `--border=ascii` swaps to `+---+` rules,
`--border=none` drops the frame entirely.

The character panel maps each byte: printable ASCII as-is, a space for the
space byte, `_` for ASCII whitespace (`\t\n\r`, 0x0B, 0x0C), `⋄` for NULL,
`•` for other ASCII control bytes, `×` for non-ASCII bytes. `--no-characters`
drops the panel (and `-C`/`--characters` restores it); `--no-position` drops
the offset panel. `--print-color-table` prints the glyph/color legend with
colors and stays rc 0.

## The pipe trap: colored output is the default

`--color` defaults to `always`, so **hexyl emits ANSI color codes even when
piped** — the opposite of most tools. Measured matrix:

- default (no flags, piped): colored.
- `--color=auto`: colored only when stdout is a TTY — the choice for scripts.
- `NO_COLOR` set (even to an **empty string**): plain, and it wins over
  `--color=always`.
- `--color=force`: the only way to re-enable color after `NO_COLOR`.
- `--color=never`: always plain.
- `CLICOLOR_FORCE=1` under `NO_COLOR`: ignored (still plain).

`-p`/`--plain` bundles `--no-characters --no-position --border=none
--color=never` (verified md5-identical to passing all four), which is the
compact form for logs or further processing. Colored `--help`/`-h` is a TTY
only feature — piped help is plain.

## Slicing input

- `-n N` / `--length N`: read only N bytes. N accepts decimal prefixes
  (`64`, `4kB`, `32MB`), binary prefixes (`4KiB`), and hex (`0xff`). Aliases:
  `-l`, `-c`, `--bytes`.
- `-s N` / `--skip N`: skip the first N bytes (same unit syntax). A negative
  value seeks **from the end of the file**: `--skip=-32 --length=16` prints
  the 16 bytes starting 32-from-end (on a 4096-byte file the position panel
  still shows the absolute offset `00000fe0`). Negative numbers typed with a
  space (`-s -32`) parse as flags and fail with a clap error rc 2 — the
  `=` form (`--skip=-32`) is required.
- Skipping past EOF, `-n 0`, or an empty file produce the bordered
  **`No content`** row and rc 0 — not an error.
- `--block-size=1024` changes the meaning of an extra `block` unit (used as
  `--skip=2block`; default block is 512 bytes).
- `-o N` / `--display-offset N`: add N to every position printed. The data is
  unchanged; the shown offset = real stream position + N (e.g. after stripping
  a container header: `--skip 4 --display-offset 100` shows position `0x68`
  for stream byte 4). **The help text claims negative values are valid ("relative
  to the end of the file") — every negative value is in fact refused** with
  rc 1: `negative offset specified, but only positive offsets (counts) are
  accepted in this context`.

## Squeezing

Default behavior compresses runs: rows whose *bytes* are identical to the
preceding row become a single `*` marker row (positions are not compared —
every row differs there). `-v`/`--no-squeezing` prints every row.

The shape matters at boundaries:

- A partial last row (1–15 bytes) is never squeezed even when the full rows
  before it were identical.
- When the swallowed sequence includes the final data row, hexyl still shows
  where the data ends: an end-of-data row with the final position and empty
  data is printed (in `--plain` mode that trailing row renders as a bare `*`).

## Grouping and bases

- `-g N` / `--group-size N` groups 1, 2, 4, or 8 bytes into one number (2
  hex digits per byte, so `-g 8` prints `00204161…`); `--groupsize` is an
  xxd-compat alias.
- `--endianness=big` (default) or `--endianness=little` (`-e`): only affects
  the grouping display, never the character panel.
- `-b BASE` accepts names (`binary`, `octal`, `decimal`, `hexadecimal`) or
  digits (`2`, `8`, `10`, `16`) — anything else fails with rc 1 listing the
  four valid bases. Digit widths follow the base (2 hex digits, 3 octal or
  decimal, 8 binary).

## Character tables

`--character-table` picks the right-panel alphabet, keeping NULL as `⋄`
except where noted (measured on a mixed 14-byte fixture):

- `default` (above).
- `ascii`: printable ASCII as-is, ` ` for space, everything else `.`.
- `codepage-437`: maps 0x80–0xFF through IBM codepage 437 (measured glyphs:
  `⌂` for 0x7F, `Ç á ﬀ Θ ╚` for 0x80 a0 ff e9 c8; CR/LF render as `♪`/`◙`).
- `codepage-1047`: EBCDIC map for mainframe data — printable ASCII is no
  longer printable there (measured: 0x41 renders `.`, 0x61 renders `/`),
  and NULL drops its `⋄` glyph.
- `braille`: renders high bytes as braille dot patterns (`⢀`, `⢠`, `⣱`, `⣐`,
  `⣿` for 0x80 a0 e9 c8 ff; control bytes as arrows `↵ ← →`).

`--color-scheme=gradient` repaints with 24-bit truecolor (`38;2;R;G;B`
escapes, zero-padded channels): nulls stay dark, printable ASCII cyan, a
pink-to-violet ramp for non-printable ASCII and a red-yellow-white heat ramp
for non-ASCII. The default scheme uses plain 16-color codes instead.

## C include mode

`-i` / `--include` emits C source instead of a hex dump (needs a filename,
not stdin):

```bash
hexyl -i payload.bin
```

produces an `unsigned char` array named after the **basename** with
non-alphanumerics folded to `_` (`sub/a.b-c.d` → `a_b_c_d`), 12 hex values
per row, plus a matching `unsigned int name_len = N;`. With **stdin**, `-i`
emits only the value lines — no wrapper, no array name, no length symbol.

## Panels and terminal width

Two hex panels (16 bytes/row) are the default; narrow terminals shrink to one
panel (below ~78 columns). The panel count is the maximum that fits the
width: measured switch points are 78 → 2 panels, 112 → 3, 146 → 4, 209 → 5
(~34 columns per 8-byte panel). Wide TTYs
do **not** auto-grow — 2 panels is still the cap at 130 columns; pass
`--panels=auto` to take the maximum that fits (`--panels=1..4` forces an
exact count). `--terminal-width=N` substitutes a width without a TTY, and
**conflicts with `--panels`** — combining them is rc 2
(`cannot be used with`).

## Exit codes and error surface

| situation | rc | measured message |
| --- | --- | --- |
| happy path, incl empty input / `No content` | 0 | — |
| missing file | 1 | `Error: No such file or directory (os error 2)` |
| file argument is a directory | 1 | `Error: '/tmp' is a directory.` |
| bad unit in `-n/-s/-o` | 1 | `invalid unit "qi"` under `failed to parse … as byte count` |
| bad `-b` base (not 2/8/10/16) | 1 | `The number provided is not a valid base. Valid bases are 2, 8, 10, and 16.` |
| negative `--display-offset` / negative `--length` with `=` | 1 | `negative offset specified, but only positive offsets (counts) are accepted in this context` |
| negative `--skip` beyond the file, or on a pipe (stdin) | 1 | `Error: Failed to jump to the desired input position. This could be caused by a negative offset that is too large or by an input that is not seek-able (e.g. if the input comes from a pipe).` |
| unknown/extra args, bad enum value (with a `possible values` list), `--panels` + `--terminal-width` together | 2 | clap-style errors |

So: rc 1 = hexyl's own argument/IO errors, rc 2 = the CLI parser. The
`Failed to jump` message means negative skip is **impossible on stdin** —
pipes are not seekable; use a file (or `tail -c` on the input).

Two never-happens behaviors worth knowing: hexyl **never pages** — 8 KiB
poured through a 24-row TTY streams in full at rc 0 with no pager — and
`hexyl -n 16 /dev/zero` works fine (infinite devices are safe once a length
is set; without one it runs until killed).

## Version wall

- conda-forge 0.17.0 vs the official release 0.17.0 binary: identical — all
  12 probe outputs (rendering, plain, squeeze, include, gradient, grouping,
  base-10, negative skip, completions, version) md5-equal with rc parity.
- Ubuntu noble's apt `hexyl 0.8.0-2` (2020) diverges hard: it lacks `--base`,
  `-g/--group-size`, `--endianness`, `--panels`, `--terminal-width`,
  `--character-table` (all five tables), `--color-scheme`, `-i`, `-p`,
  `--no-characters`, `-P`, `--print-color-table`, `--completion`, and the
  `force` value of `--color`. Rendering differences: NULL shows as `0` (not
  `⋄`), empty input prints bare borders (no `No content` row), negative
  `--skip` is silently ignored instead of erroring or seeking, a directory
  argument gives a generic `Is a directory (os error 21)`, and CLI parse
  errors exit rc 1 (clap 2.x era) rather than rc 2.

## Verify the install (run this after setup)

Measured to exit 0 on clean scratch state (needs only `hexyl` and `python3`
on PATH; every call is stdin-safe via explicit redirections):

```bash
set -eu
command -v hexyl >/dev/null || { echo "hexyl not installed"; exit 1; }
T=$(mktemp -d)
HX=$(command -v hexyl)
python3 -c "open('$T/mix.bin','wb').write(b'Hello world\n\x00\x01\x02\xff')"
python3 -c "open('$T/rep.bin','wb').write(b'A'*48+b'B'*32)"

out=$("$HX" --color=never "$T/mix.bin")
case "$out" in *'Hello wo┊rld_⋄••×'*) : ;;
  *) echo "FAIL: rendering/char panel"; exit 1;; esac

# exit-code taxonomy: 0 happy / 1 own error / 2 parser
set +e
"$HX" --color=never "$T/mix.bin" >/dev/null 2>&1; rch=$?
"$HX" --color=never "$T/missing.bin" >/dev/null 2>&1; rcm=$?
"$HX" --color=never --bogus < /dev/null >/dev/null 2>&1; rcb=$?
"$HX" --color=never --display-offset=-1 "$T/mix.bin" >/dev/null 2>&1; rcd=$?
"$HX" --color=never "$T/mix.bin" "$T/rep.bin" >/dev/null 2>&1; rcx=$?
set -e
[ "$rch" -eq 0 ] || { echo "FAIL: happy rc $rch"; exit 1; }
[ "$rcm" -eq 1 ] || { echo "FAIL: missing-file rc $rcm"; exit 1; }
[ "$rcb" -eq 2 ] || { echo "FAIL: unknown-flag rc $rcb"; exit 1; }
[ "$rcd" -eq 1 ] || { echo "FAIL: negative display-offset rc $rcd"; exit 1; }
[ "$rcx" -eq 2 ] || { echo "FAIL: multi-file rc $rcx"; exit 1; }

# empty input -> 'No content' box, rc 0
nocont=$("$HX" --color=never < /dev/null)
case "$nocont" in *'No content'*) : ;;
  *) echo "FAIL: empty-input rendering"; exit 1;; esac
set +e
"$HX" --color=never < /dev/null >/dev/null 2>&1; rce=$?
set -e
[ "$rce" -eq 0 ] || { echo "FAIL: empty-input rc $rce"; exit 1; }

# squeezing: * marker rows, and -v disables them
sq=$("$HX" --color=never "$T/rep.bin")
case "$sq" in *'│*       │'*) : ;; *) echo "FAIL: squeeze marker"; exit 1;; esac
plain=$("$HX" -p -v "$T/rep.bin")
case "$plain" in *"41 41"*"42 42"*) : ;; *) echo "FAIL: -v rows"; exit 1;; esac

# color: piped default is colored; NO_COLOR (even empty) wins; force beats it
n_defaults=$(env -u NO_COLOR "$HX" "$T/mix.bin" | od -An -c | tr ' ' '\n' | grep -c 033 || true)
n_nocolor=$(NO_COLOR=0 "$HX" "$T/mix.bin" | od -An -c | tr ' ' '\n' | grep -c 033 || true)
n_force=$(NO_COLOR=0 "$HX" --color=force "$T/mix.bin" | od -An -c | tr ' ' '\n' | grep -c 033 || true)
[ "$n_defaults" -gt 0 ] || { echo "FAIL: piped output should stay colored by default"; exit 1; }
[ "$n_nocolor" -eq 0 ] || { echo "FAIL: NO_COLOR not honored"; exit 1; }
[ "$n_force" -gt 0 ] || { echo "FAIL: --color=force did not beat NO_COLOR"; exit 1; }

# slicing: = -syntax negative skip reads the true tail, absolute position kept
python3 -c "open('$T/seq.bin','wb').write(bytes([i%250 for i in range(4096)]))"
last=$("$HX" --color=never --skip=-8 --length=8 "$T/seq.bin" | sed -n '2p')
case "$last" in *'00000ff8│ 58 59 5a 5b 5c 5d 5e 5f'*) : ;;
  *) echo "FAIL: negative skip tail"; exit 1;; esac

# -p is exactly the 4-option bundle
cmp <("$HX" -p "$T/mix.bin") \
    <("$HX" --no-characters --no-position --border=none --color=never "$T/mix.bin") \
    || { echo "FAIL: -p bundle equality"; exit 1; }

# include mode: symbol from basename + _len
inc=$("$HX" -i "$T/mix.bin")
case "$inc" in *'unsigned char mix_bin[]'*'unsigned int mix_bin_len = 16'*) : ;;
  *) echo "FAIL: include mode shape"; exit 1;; esac

# completions exist
for sh in bash zsh fish elvish powershell; do
  "$HX" --completion "$sh" > /dev/null || { echo "FAIL: completion $sh"; exit 1; }
done

# terminal-width panel mapping without a TTY (row 2 of data = line 3)
wide=$("$HX" --color=never --terminal-width=120 -n 96 "$T/seq.bin" | sed -n '3p')
case "$wide" in *'00000018'*) : ;; *) echo "FAIL: width→panels"; exit 1;; esac

rm -rf "$T"
echo hexyl-verified
```

## Notes for pipelines

Scripts and CI should reach for `hexyl -p` (or `--color=auto --border=none`)
explicitly: the default colored output will otherwise poison anything the
dump is piped into. For machine-readable bytes prefer `xxd -p` anyway — hexyl
is a *viewer*: its rendering is layout-first, and the character panel's
glyphs are presentation choices, not data.

Related in this library: `delta` for colored diff viewing, `difftastic` for
syntax-aware diffs, `bat` for colored text with line numbers, and `gron`
when the bytes turn out to be JSON.
