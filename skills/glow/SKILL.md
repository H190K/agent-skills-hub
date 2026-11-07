---
name: glow
version: 1.0.0
description: "Use when previewing, reading or converting markdown in the terminal — files, READMEs, piped stdin, a fetched repo readme, or the folder-notes TUI — and when scripting against glow's output. Includes the piped notty trap (raw markers plus OSC-8 bytes unless -s), the dead tokyonight style, inert --config, the 80-col wrap terminal width cannot change, frontmatter stripping and the TUI keys. Measured live on the official 3.0.0 binary."
---

# glow — markdown on the terminal, with measured sharp edges

glow (charmbracelet/glow, MIT, © Charmbracelet, Inc — single MIT LICENSE in the
source tarball) renders markdown in the terminal and browses local markdown
folders with a TUI. Everything below was measured on the **official glow 3.0.0
release binary** (amd64 .deb, sha256 verified against the release's
`checksums.txt`; the packaged completions match `glow completion bash`
byte-for-byte and the packaged man page matches `glow man` except the build
date). v3.0.0 is a from-scratch rewrite on Bubble Tea 2; the last v2 release
was 2.1.2.

## Install and verify

- With Go: `go install charm.land/glow/v3@latest` (module path is
  `charm.land/glow/v3`, Go 1.21+). Distros: none of the usual fallbacks help —
  Ubuntu's archives have no glow package, and the conda-forge package named
  `glow` is an unrelated Python library. Download the release `.deb`/tarball
  and check it against `checksums.txt` from the same release.
- Verify: `glow --version` prints `glow version <x.y.z> (<7-char commit>)` —
  the version template embeds the build commit.

## What it reads (one positional argument, maximum)

- **File**: `.md`, `.mdown`, `.mkdn`, `.mkd`, `.markdown` (case-insensitive).
  Any other extension — the file is presented as a fenced code block with the
  extension as its language, so `glow script.py` gets syntax highlighting.
- **Stdin**: if stdin is a pipe it wins over any argument, no `-` needed; a
  bare `-` reads stdin explicitly. Stdin content is always treated as
  markdown, even when it looks like code — it is never code-wrapped.
- **Directory**: starts the TUI rooted there (see below). Non-TTY contexts
  fail: `glow .` on a service or in a pipeline exits 1 with
  `Error: unable to run tui program: bubbletea: error opening TTY: bubbletea: could not open TTY: open /dev/tty: no such device or address`.
- **URLs**: `github://owner/repo` and `gitlab://owner/repo` fetch the repo
  README; an argument whose first path component is `github.com` or
  `gitlab.com` (e.g. `glow github.com/charmbracelet/glow`) also resolves the
  README, and a plain `https://…` URL is fetched and rendered. Measured
  fail-closed paths: **bare `owner/repo` does not work** —
  `glow charmbracelet/glow` → `Error: unable to open file: open charmbracelet/glow: no such file or directory`
  exit 1 (other hostnames take the same fall-through); `ftp://…` →
  `Error: ftp is not a supported protocol` exit 1; any non-200 fetch →
  `Error: HTTP status 404` exit 1. Documents fetched from a URL get their
  relative links/images resolved against the URL's directory.
- Two positional arguments never parse as input:
  `Error: accepts at most 1 arg(s), received 2`, exit 1. Empty stdin renders
  happily with exit 0.

## The piped trap — the single sharpest behavior

When stdout is **not** a TTY, glow forces its `notty` style (plausible from the
flag default `auto`, but the force wins over the environment and the config
file). The matrix, all measured:

- `glow file.md | cat` → zero ANSI coloring: headings keep their `#`, emphasis
  keeps `*emphasis*` and `**bold**` verbatim, bullets become `•`, inline-code
  backticks are stripped, and **links carry OSC-8 hyperlink escapes** — so a
  naive pipe is not clean text: invisible bytes ride along on link lines.
- `glow -s auto file.md | cat` → colored. The notty force only applies when
  `--style` is completely absent; explicitly passing `-s auto`, `-s dark`,
  `-s notty` (etc.) always takes precedence, in a pipe or not.
- `GLOW_STYLE=dark` (or a config `style: dark`) **without** an explicit `-s`
  → still notty on a pipe. Environment and config style are silently ignored
  whenever stdout is not a terminal.

Byte-stable extraction for scripts that want markdown-as-text with no padding:

```bash
glow -s notty -w 0 doc.md
```

Colors on a pipe, deliberately:

```bash
glow -s auto doc.md | sed 's/\x1b\[[0-9;]*m//g'
```

## Width — 80 everywhere, terminal size ignored

The word-wrap default is **80 columns in every context**: piped, a 60-column
TTY, or a 200-column TTY all render at 80 (`glow` reads the terminal size in
code, but the CLI output does not use it — measured directly at 60/100/200
columns). Only `-w` changes it:

- `-w 120` wraps at 118 visible columns (width minus the two-column margin).
- `-w 0` disables wrapping entirely — long lines stay single lines.
- Piped output is space-padded with trailing spaces up to the width; `-w 0` is
  also the honest choice for hashing or diffing rendered bytes.

## Styles

- Built-in style names that validate: `auto`, `dark`, `light`, `pink`,
  `notty`, `dracula`. `auto` picks dark styling on dark terminals.
- **`-s tokyonight` is a trap**: the tool's own source has a `tokyonight`
  branch, but style validation rejects it before the renderer sees it —
  `Error: specified style does not exist: tokyonight`, exit 1. The measured
  built-in set is the six names above.
- Custom styles are JSON files: `glow -s /path/to/style.json` (a
  glamour-style JSON). A missing file fails closed with the same
  `Error: specified style does not exist: <path>` message, exit 1.

## Frontmatter

YAML frontmatter between leading `---` fences is stripped before rendering,
including at most one blank line after the closing fence. Two blank lines
after the fence leave one blank line in the output; there is no flag to
preserve frontmatter.

## Config file and environment

- Search order for `glow.yml`: `GLOW_CONFIG_HOME` first, then
  `XDG_CONFIG_HOME/glow`, then the platform user-config directory
  (`~/.config/glow`). First match wins.
- **Every run that finds no config auto-creates one** — the default
  (`style: auto`, `width: 80`, `mouse: false`, `pager: false`, `all: false`)
  is written into the first search directory. A failing location surfaces as a
  log line in `~/.cache/glow/glow.log`, where glow always writes debug-level
  logs silently (`GLAMOUR_STYLE` and `GLOW_ENABLE_GLAMOUR` also exist).
- The `--config` flag is **inert for rendering** — measured: a `--config`-named
  file's `style`/`width` settings never reach a render; the flag only selects
  the file that `glow config` edits. Never pass `--config` expecting behavior
  changes.
- `glow config` opens the config in your editor and prints
  `Wrote config file to: <path>`; it refuses other extensions with
  `Error: '.json' is not a supported configuration type: use '.yaml' or '.yml'`,
  exit 1.
- Environment mirrors the flags: `GLOW_STYLE`, `GLOW_WIDTH`, `GLOW_PAGER`,
  `GLOW_TUI`, `GLOW_ALL`, `GLOW_MOUSE`, `GLOW_PRESERVENEWLINES`,
  `GLOW_SHOWLINENUMBERS`. Precedence: flag > env > config file > built-in
  default; the piped notty force sits on top of all of it (only the presence
  of an explicit `-s` prevents the force).

## Pager and the TUI

- `-p` pages through `$PAGER` parsed as shell words (default `less -r`);
  `GLOW_PAGER=cat` works as an override. `-t` shows any file or URL in the TUI;
  the combination fails closed: `Error: cannot use both pager and tui`, exit 1.
- `-a` (show all files), `-l` (line numbers) and the hidden `-m` (mouse) are
  TUI-only: silently accepted, with no effect on plain renders.
- Bare `glow` or `glow <dir>` opens the TUI listing: documents sorted by
  relative path, dotfiles/node_modules excluded. `-a` flips this on — it shows
  hidden and ignored files *and* bypasses gitignore rules (measured: a hidden
  dotfile appears first in the ordering).
- Listing keys: `j`/`k` or arrows to move, `g`/`G` top/bottom, `enter` opens,
  `/` filters (matches the document title, diacritics normalized), `F`
  rediscovers files, `e` opens the selected file in your editor, `?` toggles
  full help, `esc` clears an active filter, `tab`/`L` and `shift+tab`/`H`
  switch sections, `q` quits with exit 0. The document view shares the keys
  plus `esc`/`left` to go back and `r` to refresh; `-l` adds line numbers
  there.
- Headless hosts cannot run the TUI at all — any directory argument, `-t`, or
  `GLOW_TUI=true` on a machine without a controlling terminal exits 1 with the
  bubbletea error quoted above.

## Completions and man

- `glow completion bash|zsh|fish|powershell` emits the script. Unknown shells
  print the completion help and exit 0 (measured) — check the output kind,
  not the exit code.
- `glow man` (undocumented in the help) prints a roff manpage; the deb's
  bundled `/usr/share/man/man1/glow.1.gz` matches it byte-for-byte apart from
  the build date and the host-specific config default path.

## Exit codes

- **0** — every successful render (including empty stdin), TUI quits, and the
  unknown-shell completion help.
- **1** — everything else: argument parse errors (`accepts at most 1 arg(s),
  received 2`), open failures, style validation failures, the pager/tui
  conflict, unsupported protocols, HTTP failure statuses, and any TUI start on
  a TTY-less host. There is no separate "2" tier: cobra parse errors and glow's
  own errors share exit 1.

## Provenance and divergences

- All behavior above measured on the 3.0.0 release `.deb` (sha256 in the
  release's `checksums.txt`). Cross-build checks are impossible for glow: no
  apt package, and conda-forge's `glow` is a different program entirely.
- v2.1.2 (last v2 release) was also probed: the CLI flag surface and the
  measured notty/coloring/width behaviors match 3.0.0; the TUI error wording
  differs (`could not open a new TTY` vs the newer
  `bubbletea: error opening TTY`) and the TML query/protocol layer changed
  with the rewrite. The `-s tokyonight` rejection exists in both.
- Upstream commits after v3.0.0 (checked before publishing) add an unreleased
  text-sizing protocol for headers — expect future 3.x to change document
  view rendering.

## Verify block

```bash
set -e
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
bin=$(command -v glow || true)
[ -n "$bin" ] || { echo 'FAIL: glow not installed'; exit 1; }
printf '%s\n' '---
title: x
---

body line one' > "$d/doc.md"
printf '%s\n' '[link](https://example.com) and body line' > "$d/link.md"
rc=0
# frontmatter is stripped on a pipe (notty keeps markers, so a leaked
# frontmatter would still show)
fm=$("$bin" "$d/doc.md" 2>/dev/null | grep -cF 'title:' || true)
[ "$fm" -eq 0 ] || { echo 'FAIL: frontmatter must be stripped'; exit 1; }
# piped default: no SGR coloring at all
esc=$("$bin" "$d/doc.md" 2>/dev/null | tr -d -c '\033' | wc -c)
[ "$esc" -eq 0 ] || { echo 'FAIL: piped default must not be colored'; exit 1; }
# ...but links still carry invisible OSC-8 bytes on a pipe (raw bracket
# syntax never survives: the label and URL each become hyperlink text)
osc=$("$bin" "$d/link.md" 2>/dev/null | grep -cF $'\033]8;' || true)
[ "$osc" -ge 1 ] || { echo 'FAIL: OSC-8 must survive the pipe'; exit 1; }
# an explicit -s colors the pipe even for auto
esc2=$("$bin" -s dark "$d/doc.md" </dev/null 2>/dev/null | tr -d -c '\033' | wc -c)
[ "$esc2" -gt 0 ] || { echo 'FAIL: -s dark must color a pipe'; exit 1; }
# tokyonight is rejected exit 1 (dead style name)
rc=0; "$bin" -s tokyonight "$d/doc.md" >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 1 ] || { echo 'FAIL: tokyonight must be rejected'; exit 1; }
# width: piped default pads to 78; -w 0 disables padding entirely
w80=$("$bin" "$d/doc.md" 2>/dev/null | awk 'BEGIN{m=0}{if(length($0)>m)m=length($0)}END{print m+0}')
[ "$w80" -eq 78 ] || { echo "FAIL: expected 78-wide padding, got $w80"; exit 1; }
last=$("$bin" -w 0 "$d/doc.md" 2>/dev/null | grep -v '^$' | tail -1)
[ "$last" = '  [link](https://example.com) and body line' ] || { echo "FAIL: -w 0 padding: '$last'"; exit 1; }
# two positional arguments never render
rc=0; "$bin" "$d/doc.md" "$d/doc.md" >/dev/null 2>&1 && rc=1
[ "$rc" -eq 0 ] || { echo 'FAIL: two args must error'; exit 1; }
# the --config flag is inert for rendering: width 20 in the config, output still 78 wide
printf '%s\n' 'width: 20' > "$d/c.yml"
wc=$("$bin" --config "$d/c.yml" "$d/doc.md" 2>/dev/null | awk 'BEGIN{m=0}{if(length($0)>m)m=length($0)}END{print m+0}')
[ "$wc" -ge 77 ] || { echo "FAIL: --config leaked into the render: $wc"; exit 1; }
# a missing config file is auto-created in the first search dir
rm -rf "$d/conf" && mkdir "$d/conf"
GLOW_CONFIG_HOME="$d/conf" "$bin" "$d/doc.md" >/dev/null 2>&1
[ -f "$d/conf/glow.yml" ] || { echo 'FAIL: default config must be auto-created'; exit 1; }
# unknown completion shells print help with exit 0
"$bin" completion nothereshell </dev/null >/dev/null 2>&1 || { echo 'FAIL: unknown shell exits 0'; exit 1; }
echo glow-verified
```
