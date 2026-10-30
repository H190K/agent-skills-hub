---
name: bat
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
description: "Use when an agent must view or review files with syntax highlighting from scripts or pipelines - cat-compatible when piped, forced colors on demand, line numbers, line-range extraction, git-diff gutters, per-glob syntax mapping, themes and cache management. Every flag was measured live on the 0.26.1 release binary; the piped-default scripting traps are the sharpest content."
---

# bat — cat(1) clone with syntax highlighting, git markers and a pager

`bat` prints files with syntax highlighting, line numbers and git-aware
decorations; it also carries git-diff gutters, per-glob syntax mapping and a
cache for extra syntaxes/themes. This skill documents the behavior of the
**0.26.1 release binary** (sharkdp/bat, x86_64-unknown-linux-musl asset
`bat-v0.26.1-x86_64-unknown-linux-musl.tar.gz`), every fact measured live on
that binary plus a real TTY via a pty, and cross-checked against the Ubuntu
24.04 distro build `batcat 0.24.0-1build1` (divergences flagged inline).

## Install (no repo copy of anything here — install the tool, then run it)

```
curl -sSL https://github.com/sharkdp/bat/releases/download/v0.26.1/bat-v0.26.1-x86_64-unknown-linux-musl.tar.gz \
  | tar xzf - -C "$TMPDIR" ; "$TMPDIR"/bat-v0.26.1-x86_64-unknown-linux-musl/bat --version
# distro route: `apt install bat` on Ubuntu noble gives you 0.24.0 named `batcat`,
# dynamically linked (libgit2) and missing the 0.25/0.26 options - see divergence row
```

Upstream is `github.com/sharkdp/bat`, dual-licensed under **MIT and Apache-2.0
at your option** (both `LICENSE-MIT` and `LICENSE-APACHE` ship in the release
and source tarballs; the MIT file credits *bat-developers*; `--acknowledgements`
states the same). `--version` prints `bat 0.26.1 (979ba22)` — it embeds the
release commit hash. Shell completions for bash/fish/zsh/ps1:
`bat --completion bash`.

## The piped default is byte-exact `cat` (the scripting rule)

When stdout is **not** a terminal, plain `bat file` behaves like `cat` by
design (v0.26.1 hardens this). Measured consequences:

- No ANSI codes, no styles, no headers: a piped `bat` never decorates.
- Raw tabs pass through **even with `--tabs=4`**; tab expansion only happens
  where output is rendered/wrapped.
- UTF-8 BOM, CRLF endings, a **missing final newline** (no newline is added)
  and **invalid UTF-8 bytes** pass through raw, rc 0.
- An **unknown `-l` name is silently tolerated** (rc 0, un-highlighted):
  language validation only runs when highlighting actually runs.

To get highlighting/decorations out of a pipeline, re-enable rendering:

```
bat -f file                 # --force-colorization = --color=always + --decorations=always
bat --color=always file     # colors AND the default decorations come back together
bat --decorations=always    # decorations WITHOUT colors (plain grid/numbers rendered)
bat --color=always --decorations=never file
                            # token colors only, no grid/header/numbers
```

- `NO_COLOR` cannot defeat `-f` (measured: `-f` still colors with `NO_COLOR=1`).
- `CLICOLOR_FORCE` is ignored: `CLICOLOR_FORCE=1` piped stays colorless.
- The exceptions that DO render when piped: `-n`/`--number`, `-A`/`--show-all`,
  `-s`/`--squeeze-blank`, `--terminal-width` (its presence forces `wrap=auto`
  wrapping), anything under `--decorations=always`, and `-f`.
- **`-n` piped still numbers lines, but `--style=numbers` piped does not.**
  The carve-out is wired to the literal alias: `--decorations=never -n` kills
  the numbers again. So a "strip decorations but keep numbers" pipe is
  `bat -n file`, never `bat --style=numbers file`.
- Styles that come from the **config file or `BAT_STYLE` env do not leak into
  pipes either** (measured: a config with `--style=numbers,header-filename`
  piped shows nothing extra; adding `--decorations=always` to that config or
  the command line makes them render).
- `--strip-ansi=always` **does not strip in piped passthrough** — with or
  without `--color=never`. It strips the *input's* own ANSI only when bat
  renders the file (forced colors). The `auto` mode additionally skips
  plain-text languages.

`bat` with a `-` argument or **no argument at all** reads stdin; a bare piped
`echo hi | bat` behaves like `cat` (equivalent to piping it through `bat -`).

Plain mode shortcuts: `-p` = `--style=plain`; **`-pp` additionally disables
paging**; `-P` = `--paging=never`; a hidden `--no-pager` parses too.

## Style system

Default components: `changes, grid, header-filename, numbers, snip`.

- Components: `changes` (git markers), `header` (= `header-filename`),
  `header-filesize` (renders human sizes like `Size: 6 B`), `grid`, `rule`
  (horizontal separator between files), `numbers`, `snip`.
- Predefined styles: `default`, `auto` (equals `default` unless the output is
  piped — then plain), `full`, `plain`.
- A set made only of `+`/`-`-prefixed components **modifies** the previous set
  instead of replacing it (e.g. `-p` then `--style=+numbers`; measured:
  `-f --style=-numbers,header-filename` = header shown, numbers gone).
- Precedence: command line > `BAT_STYLE` env > config file ("nearest wins").

## Line-range extraction

`-r, --line-range` accepts (all measured):

```
bat -r 30:40 file    # lines 30-40          bat -r 40       # only line 40
bat -r :40 file      # 1-40                 bat -r 40:      # 40-end
bat -r -10: file     # last 10 lines        bat -r 30:+10   # 30-40
bat -r 35::5 file    # line 35 with 5 lines of context
bat -r 30:40:2 file  # lines 28-42: the 30:40 range with 2 lines of context
```

Traps (measured):

- `-r -5:-2` fails with rc 1 `[bat error]: invalid digit found in string`
  (negative *end* values are not a feature).
- A reversed (`-r 5:2`) or beyond-EOF (`-r 90:99`) range prints **nothing,
  rc 0** — silent empty, not an error. Gate on rc, not on output.
- The range applies **per file** when several files are given.
- On the Ubuntu 0.24 build, `-r -10:` is a clap usage error (rc 2, the
  `=`-separated form `-r='-10:'` parses but then also fails on `invalid
  digit`); negative *start* ranges are a 0.26.0 feature.

`-H, --highlight-line` (N / 30:40 / :40 / 40: / 30:+10) only shows when bat
renders (TTY or forced) — piped it is silently a no-op.

## Syntax picking and mapping

- `-l` accepts names or extensions (`C++`, `py`, `md`, `Snakefile`); names are
  case-insensitive (measured `-l PyThOn`). Unknown name while rendering:
  rc 1 `[bat error]: unknown syntax: 'nosuchlang'`.
- `--list-languages` lists one `Name:ext1,ext2,...` line per syntax:
  **183 syntaxes in 0.26.1** (173 in 0.24). Practical entries:
  `Diff:diff,patch,*.debdiff`, `JSON:...ipynb...Pipfile.lock...`,
  `YAML:...CITATION.cff...`.
- Extension-based detection: an unknown extension renders as plain text; an
  **extensionless file with a shebang is detected by the shebang line**
  (measured: `#!/bin/sh` file gets shell token colors).
- `--map-syntax 'GLOB:SYNTAX'` (short `-m`): the glob is matched against the
  **full path and the filename** (measured: both `-m '*.myconf:INI'` and the
  absolute-prefix form work). The right-hand side is the *syntax name*, not an
  extension. An unknown syntax name on the right **silently falls back to
  plain text, rc 0, no warning**; a missing colon is an honest error:
  `[bat error]: Invalid syntax mapping. The format of the -m/--map-syntax
  option is '<glob-pattern>:<syntax-name>'.`
- `--ignored-suffix '.dev'` strips a trailing suffix from detection
  (`f.py.dev` → Python; its header shows `Size: 6 B`).
- For stdin, `--file-name=foo.py` sets the displayed name **and** drives
  syntax detection; the forced-render header for piped input is `STDIN`.

## Themes

- `--list-themes` = 28 themes in 0.26.1 (24 in 0.24). An unknown theme name is
  a **stderr warning, rc 0, falls back to the default theme**:
  `[bat warning]: Unknown theme 'badname', using default.`
- `--theme` default is `auto`, which picks dark/light from the terminal's own
  colors; variants `auto:always` (detect even when redirected),
  `auto:system` (macOS only). `--theme-dark` / `--theme-light` choose the two
  branch themes. `BAT_THEME` environment variable sets a default.

## Git integration

Default style includes `changes` markers; the dedicated mode:

- `-d, --diff` shows only lines that **differ between the worktree and the
  index**; `--diff-context N` adds context around the changed lines — the
  default is exactly **2**: on a 30-line file with hunks at lines 2 and 25,
  default prints lines 1-4 plus 23-27 (9 lines); `--diff-context=0` prints
  only the changed lines; `=1` trims one line around each hunk. The removed
  versions of modified lines are **not shown** — deletions are dropped, only
  new/new-replaced lines print.
- **Untracked file → empty output rc 0.** Staged-but-clean worktree (worktree
  == index) → empty rc 0. **Outside a git repo → empty rc 0, no warning**; the
  same holds for stdin (`--diff -` on a pipe = empty rc 0). Every one of these
  silently empties: if you expected a diff, verify the file is tracked and the
  worktree actually differs from the index.

## Binary files, notations and encoding

- On a **TTY**, binary content is suppressed and labelled:
  the header becomes `File: blob.bin   <BINARY>` (rc 0, no content).
  `--binary=as-text` makes it print the bytes anyway (tag still shown).
- **Piped**, binary content passes through raw, rc 0, in every mode —
  `cat` compatibility again (measured raw `PK..` bytes with rc 0 both by
  default and with `--binary=as-text`).
- `-A, --show-all` renders non-printables (works piped; Unicode notation by
  default): space→`·`, tab→`├──┤` wide placeholder, newline→`␊`, CR→`␍`,
  BOM→`\u{feff}`, NUL→`␀`. `--nonprintable-notation` accepts only
  `unicode|caret` (anything else: clap usage error rc 2).
- A file that is *not* valid UTF-8 passes through raw when piped, but when bat
  **renders** it the invalid byte is replaced with U+FFFD (both rc 0, measured
  on a latin-1 `caf<0xE9>` file).
- `--tabs=0` passes tabs through raw, but under `-A` the tab placeholder is
  still rendered (measured: `-A --tabs=0` shows `├──┤`, not a raw tab).

## Tabs and wrapping

- `--tabs N` sets tab width (0 = pass tabs through); expansion happens only
  where bat renders — piped output keeps the raw tab even with `--tabs=4`.
- `--wrap` modes: `auto` (default; wraps only when the width is known — a TTY,
  or an explicit `--terminal-width`), `never` (alias `-S --chop-long-lines`),
  `character`. An unknown mode is a clap error rc 2 listing the three values.
- `--terminal-width` accepts `+N`/`-N` offsets against the real width.

## Pager

- Default paging mode is `auto`: the pager runs **only when stdout is a TTY**
  (measured: piped runs never spawn a pager; TTY runs invoke `less`, which
  quits immediately on short output). `--help` itself **pages on a TTY** since
  0.26.1 (truecolor-rendered) but prints straight to a pipe.
- Disable: `--paging=never`, `-P`, the env `BAT_PAGING=never`, or the hidden
  `--no-pager`.
- `--pager CMD` overrides `PAGER`/`BAT_PAGER`; `Example: --pager "less -RF"`.
- **`--pager=builtin`** selects the built-in `minus` pager (0.26.0+): on a TTY
  it switches to the **alternate screen** (`\x1b[?1049h`); **when piped it
  swallows ALL output — rc 0, zero bytes** (measured: `--pager=builtin
  --paging=always file` piped produces nothing. On 0.24, which lacks the
  builtin, the same call prints the content normally).

## Configuration file

- `--config-file` prints the resolved path (default `~/.config/bat/config`;
  `XDG_CONFIG_HOME` is respected; `BAT_CONFIG_PATH` replaces the whole path).
- `--generate-config-file` writes a fully commented template there (rc 0,
  measured), including `--theme`, `--paging=never`, `--pager
  "less --RAW-CONTROL-CHARS --quit-if-one-screen --mouse"` and `--map-syntax`
  examples. Each line is one command-line option; unknown flags inside a
  config are clap usage errors rc 2 (tip line suggests `--no-pager`).
- Config-sourced styles are subject to the same piped suppression as env
  styles (see the scripting rule above).

## The `cache` subcommand

- Grammar: exactly one of `--build` / `--clear` (bare `bat cache` = rc 2
  `required arguments were not provided: <--build|--clear>`; both flags
  together = rc 2 conflict error). **`bat cache --help` is itself rc 2**
  (`unexpected argument '--help'`) — use full `bat --help` instead.
- Its *sources* are subdirectories of the **config dir**:
  `~/.config/bat/syntaxes` and `~/.config/bat/themes` (the build message names
  them verbatim when missing). Its *outputs* land under the cache dir:
  `$XDG_CACHE_HOME/bat/{syntaxes.bin,themes.bin,metadata.yaml}` (measured);
  `BAT_CACHE_PATH` relocates it.
- **Caches are version-coupled.** A cache built by a newer bat makes an older
  binary fail on *every* call, rc 1:
  `The binary caches for the user-customized syntaxes and themes in
  '~/.cache/bat' are not compatible with this version of bat (0.24.0). To
  solve this, either rebuild the cache (bat cache --build) or remove the
  custom syntaxes/themes (bat cache --clear).` If two bat versions share one
  machine, `bat cache --clear` before switching.

## Exit codes

- **0** — success, including theme warnings and the silent-empty cases above.
- **1** — runtime failure: missing file (`'nope.py': No such file or directory
  (os error 2)`), unreadable file (`Permission denied (os error 13)`),
  directory given (`'.' is a directory.`), unknown syntax while rendering,
  invalid line-range digits.
- **2** — usage: unknown flags/options, invalid enum values (`--wrap`,
  `--nonprintable-notation`, negative `--squeeze-limit`), flags in the config
  file, and any `cache` misuse.
- The `--style` predef `full`/`default` and the **`+`/`-` merge sets** are how
  you recover a specific decoration set without re-specifying everything.

## Squeezing blank lines

`-s/--squeeze-blank` collapses runs of empty lines to one blank line **when
piped too** (measured `a\n\n\n\n\n\nb` → `a\n\nb`). `--squeeze-limit=N` sets
the maximum number of consecutive blank lines kept — `--squeeze-limit=0`
removes them all; the flag does nothing without `-s`; a negative value is a
clap error rc 2 (`Requires a non-negative number`).

## Recipes (executable as one bash block; everything self-created)

```
# 0. One-time tool fetch (the only install the recipe needs); stay inside $d
d=$(mktemp -d)
curl -sSL https://github.com/sharkdp/bat/releases/download/v0.26.1/\
bat-v0.26.1-x86_64-unknown-linux-musl.tar.gz | tar xzf - -C "$d"
cd "$d/bat-v0.26.1-x86_64-unknown-linux-musl" || exit 1

# 1. Colorize a unified diff inside any pipeline (the diff syntax is a real one)
printf 'int old() { return 1; }\n' > old.c
printf 'int old() { return 2; }\n' > new.c
diff -u old.c new.c | ./bat --paging=never -f -l diff > colored.diff
grep -q 'int old()' colored.diff && echo "diff colorized"

# 2. Numbered extraction around a suspicion (note: -n, never --style=numbers
#    piped; a range past EOF is silently empty, so keep it inside the file)
printf 'one\ntwo\nthree\nfour\nfive\n' > f.txt
./bat -n -r 2:4 f.txt | grep -q '   4 four' || { echo "range/numbers wrong"; exit 1; }

# 3. Verify the piped default really is cat (byte-equal, no ANSI)
printf 'x\t\ty\n' | ./bat > pass.out
cmp <(printf 'x\t\ty\n') pass.out && echo "piped bat == cat"

# 4. Config styles stay out of a pipe unless --decorations=always is set too
printf -- '--style=numbers,header-filename\n' > bat-cfg
BAT_CONFIG_PATH="$PWD/bat-cfg" ./bat -P f.txt \
  | grep -q -e '   1 ' -e 'File: ' && { echo "config leaked"; exit 1; }
printf -- '--style=numbers,header-filename\n--decorations=always\n' > bat-cfg
BAT_CONFIG_PATH="$PWD/bat-cfg" ./bat -P f.txt \
  | grep -q 'File: ' || { echo "always-render missing"; exit 1; }

# 5. Review only what git sees changed (tracked file, unstaged work)
git init -q -b main . && printf 'line1\nline2\nline3\n' > w.py
git add w.py && git -c user.name=t -c user.email=t@t commit -qm w1
printf 'line1\nCHANGED\nline3\n' > w.py
./bat -f --diff --diff-context=0 --style=plain w.py \
  | grep -q 'CHANGED' || { echo "diff empty for a modified file"; exit 1; }

# 6. Log with earlier ANSI: strip while re-colorizing (strips only when rendering)
printf '\x1b[31mred\x1b[0m plain\n' > build.log
./bat -f --strip-ansi=always -l Python --style=plain build.log \
  | grep -qF $'\x1b[31m' && { echo "source ANSI survived"; exit 1; }
./bat -f --strip-ansi=always -l Python --style=plain build.log \
  | grep -qF $'\x1b[38;5;231m' || { echo "re-colorization missing"; exit 1; }
echo "all bat recipe asserts passed"
```

Exit-code discipline for scripts: bat exits 1 on runtime errors but still
writes the good part of multi-file output first — assert on `rc`, never only
on received rows.

## Checklist when output looks wrong

- Empty with rc 0: reversed/beyond-EOF range, `--diff` on untracked/staged/
  non-repo/stdin content, or `--pager=builtin` under a pipe.
- Numbers/headers missing: piped run (`-n`, `-f`, or `--decorations=always`).
- Colors missing: `NO_COLOR` + no `-f`, or styles only in config/env.
- Everything rc 1 instantly: another bat version poisoned `~/.cache/bat`
  (`bat cache --clear`).

## Version divergences (measured, Ubuntu noble batcat 0.24.0-1build1)

Lacks: `--strip-ansi`, `--binary`, `--squeeze-blank`/`--squeeze-limit`
(`-s` is an unknown option there), `--theme-dark`/`--theme-light`,
`--set-terminal-title`, `--completion`; negative line-ranges fail; builtin
pager not present; 173 languages / 24 themes. Same: piped suppression rules,
rc classes, unknown-language piped tolerance, raw binary passthrough.

Related skills in this repository: `fd` (finding the files to run bat on),
`hyperfine` (benchmarking the pager decision), `gron` (JSON inspection),
`sd` (stream edits before display), `tokei`/`dust` (repo/disk context).