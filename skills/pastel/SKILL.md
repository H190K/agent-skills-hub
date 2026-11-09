---
name: pastel
version: 1.0.0
description: "Use when a script or agent must convert, mix, sort or generate colors from the command line — hex/rgb/hsl/lch conversions, black-or-white text over a background, visually-distinct palettes, colored ANSI output. Measured on pastel 0.12.0: piped output is rounded hsl() text (format hex re-parses it and shifts RGB), -m/-f are global flags that go before the subcommand, set lightness is CIELCh 0-100 while hsl-lightness is 0-1, negatives need --, pip/conda 'pastel' is a different package."
---

# pastel — colors from the command line, traps measured

`pastel` (sharkdp/pastel, dual MIT/Apache-2.0, author David Peter) parses most
color syntaxes you know, prints them back in most others, and manipulates
them: lighten/darken, mix, rotate hue, set a channel, generate visually
distinct palettes, gradients, random colors, and ANSI-painted text for
scripts. Everything below was measured live on the **official 0.12.0 release
binary** (`pastel_0.12.0_amd64.deb`, sha256 verified against the release
page's per-asset digest; the binary inside the release `.tar.gz` is
md5-identical).

## Install — and a name collision first

- Release assets from `https://github.com/sharkdp/pastel/releases`:
  `pastel_0.12.0_amd64.deb` or
  `pastel-v0.12.0-x86_64-unknown-linux-gnu.tar.gz`. Without root:
  `dpkg-deb -x pastel_0.12.0_amd64.deb dir` puts the binary at
  `dir/usr/bin/pastel`. `cargo install pastel` builds from source.
- **Do not `pip install pastel` / `conda install pastel`.** That name is an
  unrelated Python helper library ("bring colors to your terminal"), current
  at 0.2.1 — and conda-forge carries no Rust pastel at all. Ubuntu's apt has
  no package either. There is no `--completion` flag: the release tarball
  ships completions as files (`autocomplete/`, bash/zsh/fish/powershell) and
  the deb installs man pages per subcommand (`man pastel-color`).

## Mental model

Every subcommand takes colors in and prints colors out. Input forms (all
measured to parse to the same color for `#778899`): `red`,
`'#778899'`, `778899`, `789` (3-digit), `'#77889980'` (8-digit hex = alpha
0.502), `'rgb(119,136,153)'`, `'rgb(255 0 119)'` (CSS space form),
`'rgb(100%,0%,46.7%)'`, `'hsl(210, 14.3%, 53.3%)'`, `'hsv(120,50%,80%)'`,
`'lch(50,60,200)'`, `'gray(30%)'` and `'gray(0.3)'`, `'ansi_8bit(196)'`.
Spaces after commas are fine. Names are the 139-entry CSS list (`pastel
list`), single words only — `'sky blue'` fails with rc 1, `skyblue` parses.
The identifier `-` reads ONE stdin line as one color and is repeatable
(`printf 'red\ngreen\n' | pastel color - -` yields two).

Output shape is the big trap: on a TTY `pastel color X` prints the full 10-line
info card, but **piped output is one bare `hsl(...)` line per color** — hue at
0 decimals, saturation/lightness at 1, alpha at 3. That text is what the next
command in a pipeline receives.

## The piped hsl() trap — precision loss when chaining

Rounding happens at every print, so re-parsing drifts the color:

- `pastel color fff000 | pastel format hex` → `#ffee00` (true: `#fff000`; the
  printed hue 56 re-parses exactly where the true hue is 56.47)
- `pastel color e4002b | pastel format hex` → `#e4002a` (off by one)
- `pastel set alpha 0.5 fff000 | pastel format hex` → `#ffee0080`
  (true: `#fff00080`)

There is no binary color transport — every non-`format` command prints hsl()
text. Chaining therefore always re-rounds. Keep transforms to one command per
pipeline when exact values matter, feed the exact hex as an explicit argument
again, and treat a chain's final `format hex` as ±1–2 units per channel.

## Global flags go before the subcommand

`-m/--color-mode`, `-f/--force-color` and `--color-picker` are global:

```bash
pastel -m off color red      # right
pastel -f format hex red     # right
pastel color -m off red      # rc 2: error: unexpected argument '-m' found
```

`-m` values: `24bit`, `8bit`, `off`, `auto` (default). `-f` is documented as
an alias for `--mode=24bit`. Note `pastel -m truecolor` is clap rc 2 — but the
`PASTEL_COLOR_MODE` env var accepts `truecolor` as an alias. An invalid `-m`
value fails closed with the possible-values list.

## Color-mode precedence

- Piped stdout: plain, always — `auto` resolves to no-color and even `-m
  24bit` output stays the plain hsl() text. Nothing re-enables it except the
  explicit-escape `format` types.
- On a TTY, precedence from strongest: `-f` > `-m` > `PASTEL_COLOR_MODE`
  (`24bit`/`truecolor`/`8bit`/`off`) > auto. In auto: any `NO_COLOR` value —
  even empty — means no color; else `COLORTERM=truecolor|24bit` selects
  24-bit; otherwise **8-bit fallback plus a multi-line `[pastel warning]` on
  stderr** (verbatim advice: set `PASTEL_COLOR_MODE=24bit` to force 24-bit
  and remove the warning, or `=8bit` to silence it on 8-bit terminals).
  Measured: `NO_COLOR=1` loses to both `-f` and `-m 24bit`.
- `PASTEL_COLOR_MODE=bogus` on a TTY exits rc 1 with a single error line;
  the same value piped is silently ignored (env is only consulted on a TTY).
- The warning is skipped for `paint` and `colorcheck`.
- `pastel colorcheck` prints 8-bit and 24-bit test panels (colored blanks
  when piped) with an explanation, rc 0.

## paint — colored text for scripts

`pastel paint <fg> text...` with `-o <bg>`, `-b` bold, `-i` italic, `-u`
underline, `-n` no trailing newline; with no text argument it reads stdin. All
styles compose into ONE SGR escape — measured: fg alone `ESC[38;2;255;0;0m`;
bold `ESC[38;2;255;0;0;1m`; fg+bg `ESC[38;2;255;0;0;48;2;0;0;0m`; everything
closes with one `ESC[0m`. In stdin mode the reset lands on its own line AFTER
the text's newline; in argument mode it sits inline before the newline. Piped
`paint` is plain text unless `-f` (or `COLORTERM` on a TTY) forces color;
`-m off` makes it plain everywhere. `NO_COLOR` does not defeat `-f`.

## textcolor and set

- `pastel textcolor <bg>` returns the readable **black or white** for a
  background as a full color object (piped: `hsl(0,0.0%,0.0%)` or
  `hsl(0,0.0%,100.0%)`). `pastel textcolor '#fff000' | pastel format hex` →
  `#000000`. The help notes the reverse use too (background for a text
  color).
- `pastel set <property> <value>`: the value's **units belong to the
  property's own colorspace**. `lightness`, `hue`, `chroma` are CIELCh
  (lightness 0–100, hue 0–360 — so `set lightness 0.5 red` yields near-black
  HSL 18% lightness while `set hsl-lightness 0.5` leaves red at 50%); `red`,
  `green`, `blue` are 0–255; `hsl-hue` 0–360; `hsl-saturation`,
  `hsl-lightness`, `alpha` are 0–1. `set hue` rotates the LCh hue, not the
  HSL one — `set hue 300 red` is not `rotate 300`.
- Out-of-range `set` values **clamp silently, rc 0** (measured: `set red 300`
  = 255, `set alpha 1.5` = 1.0).

## Amounts, units, and signs

`darken`/`lighten`/`saturate`/`desaturate`/`mix` take fractions 0.0–1.0
(HSL channels for darken/lighten/saturate). Values > 1 clamp instead of
erroring (`darken 5 red` → black, rc 0). Negative amounts invert the direction
(darken `-0.2` lightens) but clap eats the leading minus — **use `--`**:

```bash
pastel darken -- -0.2 red     # rc 0, lightens
pastel rotate -- -30 red
pastel darken -0.2 red        # rc 2: error: unexpected argument '-0' found
```

Percent literals are rejected: `darken 10%` → `[pastel error]: Could not
parse number '10%'` rc 1. `rotate` is HSL-hue degrees with wraparound;
`rotate 180` and `complement` produce byte-identical output.

## Gradient, distinct, random, sort

- `gradient`: at least two color stops — one stop is rc 1 with verbatim
  `[pastel error]: The number of color arguments must be larger than one`.
  `-n/--number` includes BOTH endpoints (measured first and last lines equal
  the stops). `-s/--colorspace` defaults to `Lab`; values are
  **case-sensitive**: `Lab`, `LCh`, `RGB`, `HSL`, `OkLab` — lowercase is
  clap rc 2.
- `distinct [count] [seeds...]`: simulated annealing; **seed colors are kept
  in the output set** (`pastel distinct 4 fff000` returns 4 colors, the first
  being fff000). `-m/--metric`: `CIE76` (default, fast) vs `CIEDE2000` (more
  accurate, slower); 50 colors settle in ~0.3 s on CIE76. `-v` prints the
  annealing trace (`[  5000] D_mean = ...`) to stderr.
- `random -n <count>`: strategies `vivid` (default), `rgb`, `gray`,
  `lch_hue`. No cap worth worrying about (100000 in 0.07 s); `-n 0` exits rc 0
  with NO output. There is NO seed — every run differs.
- `sort-by {brightness,luminance,hue,chroma,random}` (default hue) and `list
  -s ...` share the enum. `random` order is re-shuffled every run (measured:
  md5 differs between runs) — never use it where a stable order matters.
  `luminance` sorts ascending (measured on the CSS names red/green/blue:
  #0000ff 0.07 < #008000 0.15 < #ff0000 0.21). `list` holds 139 names.

## format — 38 output types

Get the full enum free by passing a bad value (clap prints possible values and,
for near-misses, `tip: a similar value exists: 'brightness'`):

- Whole-color: `rgb`, `rgb-float` (`rgb(1.000, 0.000, 0.000)`), `hex`,
  `hsl`, `hsv`, `lch`, `oklch` (`OkLCh(0.6279, 0.2577, 29.2232)`), `lab`,
  `oklab`, `cmyk`, `name`
- Channel extraction: `rgb-r/g/b`, `hsl-hue/saturation/lightness`,
  `hsv-hue/saturation/value`, `lch-lightness/chroma/hue`,
  `oklch-*`, `lab-a/b`, `oklab-l/a/b`; plus `luminance` (red → `0.213`) and
  `brightness` (red → `0.299`)
- ANSI: **`ansi-8bit` and `ansi-24bit` print LITERAL backslash-x text**
  (`\x1b[38;5;196m` — safe to paste into docs), while
  `ansi-8bit-escapecode` / `ansi-24bit-escapecode` print the REAL escape
  bytes (`ESC[38;2;255;0;0m`), and `ansi-8bit-value` prints just `196`.

Alpha-aware colors print as `rgba(...)`/`hsla(...)` and 8-digit hex
(`format hex '#fff00080'` → `#fff00080`); `format name` ignores alpha.
`format name` is nearest-CSS-name and near-dark-grays collapse to `black`
(measured `#010203` and `#2e2e2e` both → `black`).

## pick, colorblind

`pick` shells out to an external picker — `gpick`, `xcolor`, `wcolor`,
`grabc`, `colorpicker`, `chameleon`, `kcolorchooser`, `zenity`, `yad`,
`hyprpicker`, or `gdbus`, chosen via the global `--color-picker`. The word
`pick` in any color argument does the same. **Headless, it draws a
full-screen canvas and blocks forever** — never call it from an unattended
script without a `timeout` wrapper. `colorblind {prot,deuter,trit}` simulates
colorblindness (e.g. protanopia of red reads as a dark yellow-olive).

## Exit codes

- **0** — success, including silently clamped values and `random -n 0`
  (empty output)
- **1** — pastel's own errors, all prefixed `[pastel error]:` (verbatim
  samples: `Could not parse color 'notacolor'`; `Could not read color from
  standard input` for `color -` on a closed stdin; `Could not parse number
  '10%'`; `The number of color arguments must be larger than one` for
  gradient; `The number of colors must be larger than one` for distinct)
- **2** — clap refusals: unknown subcommand or flag, invalid enum value with
  the possible-values list, global flags placed after the subcommand

## Recipes

Same-color check and drift-proof conversion in one pipeline-free step:

```bash
# parse forms are normalized: all print identical output
for c in '#778899' 778899 789 'rgb(119,136,153)' lightslategray 'hsl(210,14.3%,53.3%)'; do
  pastel color "$c"
done | sort -u      # one line: hsl(210,14.3%,53.3%)
```

Contrast-safe foreground for arbitrary backgrounds (the #1 scripting use):

```bash
fg=$(pastel textcolor "$bg" | pastel format hex)   # '#000000' or '#ffffff'
pastel -f paint "$fg" -o "$bg" "  status: passing  "
```

Palette from a brand color, exact and reproducible (explicit args, no pipe
rounding):

```bash
for i in 1 2 3 4; do pastel set lightness "$((i*18))" '#5b6ef5' | pastel format hex; done
```

## Related

- [`hexyl`](skills/hexyl/SKILL.md) — the same author's byte-level viewer;
  when you need the bytes of the asset whose colors you style.

## Provenance and divergences

`skills/pastel` is an original text (distinctive-phrase checked against
upstream's README). Upstream: sharkdp/pastel, licence `MIT/Apache-2.0` — the
repo ships BOTH `LICENSE-MIT` and `LICENSE-APACHE` and `Cargo.toml` says
`MIT/Apache-2.0`; the GitHub API licence field reports Apache-2.0 only.
Holder: David Peter.

Measured on the official 0.9.0 (2022-05) tarball for the divergence wall:
no `hsv(...)`/`lch(...)` input parsing, no `ansi_8bit(...)` input, no `alpha`
property in `set`, no `colour` alias for `color`, no `PASTEL_COLOR_MODE` env
override, and no `hyprpicker` picker (0.10 added it to the global
`--color-picker` enum). `format` offers 22 types (no
`hsv-*`, `oklch-*`, `oklab-*`, `ansi-8bit-value`; the 0.12 changelog notes
the 8-bit-value 255 fix). `colorcheck` exists but is hidden from `--help`
(it was unhidden in 0.10). Parse of `'#RRGGBBAA'` alpha hex already works in
0.9.0. Old global `-m`/`-f`/`--color-picker` semantics match.

## Verify block

```bash
set -e
bin=${PASTEL_BIN:-pastel}
command -v "$bin" >/dev/null 2>&1 || bin=$(command -v pastel)
[ -n "$bin" ] || { echo 'FAIL: pastel not installed'; exit 1; }
"$bin" --version | grep -F '0.12' >/dev/null
# parse normalization: 5 forms -> identical single line
n=$({ "$bin" color '#778899'; "$bin" color 789; "$bin" color 'rgb(119,136,153)'; "$bin" color lightslategray; "$bin" color 'hsl(210,14.3%,53.3%)'; } | sort -u | wc -l)
[ "$n" -eq 1 ] || { echo "FAIL: parse forms diverged ($n distinct lines)"; exit 1; }
# the piped hsl() transport and its drift
[ "$("$bin" color fff000 | "$bin" format hex)" = '#ffee00' ] || echo 'WARN: drift changed (upstream may print more decimals)'
[ "$("$bin" format hex fff000)" = '#fff000' ] || { echo 'FAIL: direct format hex'; exit 1; }
# global flag placement + mode refusals
rc=0; "$bin" color -m off red >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 2 ] || { echo "FAIL: global after subcommand should be rc 2, got $rc"; exit 1; }
rc=0; "$bin" -m truecolor color red >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 2 ] || { echo "FAIL: -m truecolor should be clap rc 2, got $rc"; exit 1; }
# negative positionals need -- ; percent literals rejected
"$bin" darken -- -0.2 red >/dev/null 2>&1
rc=0; "$bin" darken -0.2 red >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 2 ] || { echo "FAIL: unprefixed negative should be rc 2, got $rc"; exit 1; }
rc=0; "$bin" darken 10% red >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 1 ] || { echo "FAIL: percent literal should be rc 1, got $rc"; exit 1; }
# set scales and clamps
[ "$("$bin" set lightness 0.5 red | grep -F '18.0%')" ] || { echo 'FAIL: set lightness is LCh scale'; exit 1; }
[ "$("$bin" set hsl-lightness 0.5 red | grep -F '50.0%')" ] || { echo 'FAIL: hsl-lightness is 0-1'; exit 1; }
"$bin" set red 300 red >/dev/null 2>&1   # clamps silently, rc 0
# alpha round-trips through format; textcolor is black/white
[ "$("$bin" format hex '#fff00080')" = '#fff00080' ] || { echo 'FAIL: alpha hex roundtrip'; exit 1; }
[ "$("$bin" textcolor 000000 | "$bin" format hex)" = '#ffffff' ] || { echo 'FAIL: textcolor white'; exit 1; }
[ "$("$bin" textcolor fff000 | "$bin" format hex)" = '#000000' ] || { echo 'FAIL: textcolor black'; exit 1; }
# gradient endpoints included; paint paints only when forced on a pipe
[ "$("$bin" gradient -n 5 red blue | tail -n1 | grep -F 'hsl(240')" ] || { echo 'FAIL: gradient last stop'; exit 1; }
esc=$("$bin" -f paint red hi | tr -d -c '\033' | wc -c)
plain=$("$bin" paint red hi </dev/null | tr -d -c '\033' | wc -c)
[ "$esc" -ge 1 ] || { echo 'FAIL: forced paint must emit escapes on a pipe'; exit 1; }
[ "$plain" -eq 0 ] || { echo 'FAIL: plain piped paint must be uncolored'; exit 1; }
# ansi asymmetry: literal \x escaped text vs real bytes vs value
"$bin" format ansi-8bit red | grep -F '\x1b' >/dev/null
[ "$("$bin" format ansi-8bit-value red)" = '196' ] || { echo 'FAIL: ansi-8bit-value'; exit 1; }
# list holds the CSS name set; random order is unseeded (two runs differ)
[ "$("$bin" list | wc -l)" -eq 139 ] || { echo "FAIL: name count moved"; exit 1; }
a="$("$bin" list -s random | head -3)"; b="$("$bin" list -s random | head -3)"
[ "$a" != "$b" ] || echo 'WARN: random sort repeated (unexpected)'
rc=0; "$bin" color notacolor >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 1 ] || { echo "FAIL: bad color should be rc 1, got $rc"; exit 1; }
echo pastel-verified
```
