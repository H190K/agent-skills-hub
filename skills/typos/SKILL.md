---
name: typos
description: Use when spell-checking a codebase before commit or in CI — typos in identifiers, strings, comments, filenames or docs; configuring per-word or pattern-based ignore rules; a spelling gate exiting unexpectedly; or auto-fixing misspellings across a repo. Covers typos-cli 1.51.1 — install, exit codes 0/2/64/78, -w renames files, config keys, output formats. All behaviors measured live.
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
---

# typos — source-code spell checker (typos-cli)

`typos` ([crate-ci/typos](https://github.com/crate-ci/typos), MIT OR Apache-2.0, distributed as
the `typos-cli` package) is a single static Rust binary that spell-checks identifiers, strings,
comments, doc text and even **file names** against a dictionary of common misspellings, proposes
case-matched corrections, and can rewrite files in place. Every behavior below was measured live
against typos-cli 1.51.1 on Linux; flag names are quoted from `typos --help`. This skill is
original text written from the binary; the dictionary and checks belong to upstream.

## Install

Pin a release tarball. Known asset scheme for the prebuilt binaries — note there is **no**
`x86_64-unknown-linux-gnu` build; Linux x86_64 ships as **musl** (a request for the gnu asset
returns `Not Found`):

```bash
curl -sSfL -o typos.tgz \
  https://github.com/crate-ci/typos/releases/download/v1.51.1/typos-v1.51.1-x86_64-unknown-linux-musl.tar.gz
tar xzf typos.tgz && ./typos --version   # typos-cli 1.51.1
```

Other verified package sources, all at 1.51.1 at the time of writing:

```bash
cargo install typos-cli        # crates.io package is typos-cli (the binary is `typos`)
brew install typos-cli         # Homebrew formula name, homebrew-core
```

aarch64 linux / macOS / windows assets follow the same `typos-v<ver>-<target>` scheme
(`.zip` for windows), visible via the GitHub release page.

## First run, and what gets scanned

Running bare scans the current directory. Measured output for a file containing
`recieve`/`teh`:

```text
error: `recieve` should be `receive`
  ╭▸ ./README.md:1:19
  │
1 │ This project will recieve data and handle teh timeout.
  ╰╴                  ━━━━━━━
```

What the default walk includes, as measured:

- **Any text file, regardless of extension** — `.md`, obviously, but a plain `.xyz` file, a
  `.json`, even `lib.min.js` were all checked. There is no whitelist of extensions; the
  `--type-list` output only tells you which built-in *type* sections exist for per-type
  overrides. Files whose content is binary are skipped (a file containing NUL bytes was
  reported only as a `binary_file` event, never scanned), and **hidden files/directories are
  skipped** — a `.hidden.txt` and `.github/` file were invisible to a default scan of the same
  directory.
- **File names** are spell-checked too. A file named `recieve_app.py` produces an error with
  the rendered "line" being the path itself. `--no-check-filenames` skips this, and
  `--no-check-files` checks names only.
- **Identifiers and words**. The tokenizer splits snake_case, camelCase and PascalCase:
  `recieveData` reports an error at the `recieve` slice, and corrections re-assemble the casing
  of the original (`recieve`→`receive`, `Recieve`→`Receive`, `RECIEVE`→`RECEIVE`).
- **Symlinks** are not re-reported: a `link.md -> real.md` pair produced one finding, for the
  real file.

What it is **not**: a grammar checker. Valid English words are never flagged regardless of
context — measured: `their going home` scanned clean. Only tokens that fail the bundled
misspelling dictionary report.

## Exit codes — measured taxonomy

```text
0   clean (no typos)
2   typos found          ← not 1! measured with long, brief, json and silent formats
64  usage / runtime error  (bad flag: "error: unexpected argument '--no-such-flag' found";
                          missing path: "argument '/path/to/nope.md' is not found")
78  configuration error    (unknown config key; TOML parse error — see below)
```

Scripts that branch on `1` (the conventional "diagnostics found" exit in many linters) must
check `2` for typos. The usage path is clap's `EX_USAGE`; config failures are a distinct,
fail-closed code.

## Reading findings programmatically

- `--format brief` — one grep-able line per finding,
  `./path:line:col: error: `X` should be `Y``. Filename findings are the one exception:
  they print **without** the `path:line:col:` prefix.
- `--format json` — one JSON object per line: `type` (`typo` / `binary_file`),
  `path`, `byte_offset`, `typo`, `corrections` (an array), and `line_num` when known.
  Filename findings carry `byte_offset: 0` and no `line_num`. Suitable for line-buffered
  processing (`| while read -r line; do ...`).
- `--format sarif` — full SARIF 2.1.0 with `fixes` (deleted region + inserted content), for
  CI code-scanning ingestion.
- `--format silent` — no output; the exit code still reports findings.
- Default `long` format adds the boxed context shown above. `--color auto|always|never`,
  `--sort` orders results, `-j` sets threads.

## Fixing: --diff and -w

```bash
typos --diff .    # print unified diffs; touches nothing
typos -w .        # --write-changes: rewrite fixed files
```

Two `-w` behaviors that matter, both measured:

- **It renames files whose names contain typos.** `recieve_app.py` was renamed to
  `receive_app.py` by `-w` (no output, exit 0). It renames files, **not directories** — a
  `recieve_data/` directory was left alone. The rename is a filesystem operation only: imports,
  build files and URLs that referenced the old name are not updated. Review `--diff` first —
  its header already shows the proposed rename (`+++ ./receive_app.py  fixed`).
- **`-w` exits 0 even when it rewrote files.** A directory with typo fixes applied exited 0,
  and re-running on the now-clean tree also exits 0. Never use `-w` as a CI gate — for gating
  run without `-w` and treat exit `2` as findings.

## Configuration

Config is TOML, discovered per directory in a **fixed order — first match wins** (each pair
verified by mapping the same typo to a different correction and reading the winner):

```text
typos.toml  >  _typos.toml  >  .typos.toml  >  .github/typos.toml
```

Discovery walks up: a config in a repo's root applied while scanning from a subdirectory cwd.
`-c custom.toml` points at an explicit file; `--isolated` ignores implicit config files
entirely. `typos --dump-config -` prints the *effective* configuration (merged defaults + CLI +
config, `-` for stdout) — run this after upgrading: the key surface has been renamed across
typos versions over time, so an old `.typos.toml` can drift against a new binary.

Core keys (all from the measured dump):

```toml
[files]
extend-exclude = ["drafts/"]      # like --exclude; explicit path args still bypass it

[default]
check-filename = true
check-file = true
locale = "en"                     # en, en-us, en-gb, en-ca, en-au

[default.extend-words]            # typo -> correction, whole words
"seperated" = "separated"

[default.extend-identifiers]      # exact-identifier allowlist
"recieve_data" = "recieve_data"   # allowed to exist; bare `recieve` still flagged

[default.extend-ignore-re]        # REMOVE matched spans from file text before checking
```

Rules that trip people up, all measured:

- **`extend-words` corrections are case-preserving.** One lowercase line
  (`seperated = "separated"`) corrects `Seperated`, `SEPERATED` and `seperated` correctly in
  the same file.
- **`extend-ignore-re` removes spans, not lines.** A pattern that covers the typo token
  (e.g. `recieve with`) silenced both files across the repo whose files contained it; text
  *before* the match on the same line was still flagged; `^`/`$` anchors matched nothing
  without `(?m)` (the regex runs on whole-file text, default non-multiline; use
  `(?m)^...$` to scope to lines). Corollary: an over-broad pattern hides matching occurrences
  everywhere — keep ignore regexes narrow and re-check with a clean run.
- **Per-type sections.** `[type.py]` / `[type.md]` / … carry the same
  `extend-ignore-identifiers-re` / `extend-ignore-words-re` / `extend-ignore-re` /
  `extend-identifiers` keys plus `extend-glob` for files that don't match the type's builtin
  patterns. Type-scoped regexes measured scoped: a `[type.py]` allowlist cleaned the `.py`
  while the same typo in `.md` still reported. Some built-in types skip content checks —
  `[type.cert]` appears in the dump with `check-file = false` (certificates are never
  spell-checked) — and built-in types ship their own identifier allowlists (`[type.py]`
  already knows `NDArray`, `arange`, …).
- **Backslashes in regexes need TOML literal strings** — `"recieve on\S+"` inside
  double quotes fails to load with `TOML parse error … missing escaped value`; write
  `extend-ignore-re = ['recieve on\S+']` (single quotes, a TOML literal string).

Configuration is **fail-closed**: an unknown key or a parse error refuses the run rather than
continuing with a partial config — measured `unknown key `default.ignore-words`` and the
parse error above, both exit 78. If your config silently "does nothing", check stderr; it is
either not being discovered (wrong name, order collision) or rejected.

## Files that are skipped, and why

From the [files] defaults (each flip verified live):

- **VCS ignore files (`.gitignore`) are honored only inside a git repository.** The same
  directory with a `.gitignore`d `gen_out/` reported those files before `git init` and
  skipped them after. Build outputs in a non-repo checkout (a CI export, a tarball) get
  checked. `--no-ignore-vcs` re-includes them inside a repo.
- **`.ignore` files are honored without git** — the `ignore`-crate dotfile works in a plain
  folder, unlike `.gitignore`. `--no-ignore-dot` turns it off.
- Hidden files: default off, `--hidden` includes them.
- Binary files: default off, `--binary` scans them.
- Explicit path arguments **bypass** `--exclude` / `[files] extend-exclude`; pass
  `--force-exclude` to make the exclusion stick even for explicitly requested files
  (measured both ways with a `drafts/` exclude).
- `--file-list PATH` checks exactly the newline-separated paths provided (a file path, or a
  bare value of `-` to read the list from stdin).
- `typos -` reads stdin: findings render with path `-`, and JSON output works, which pipes
  into scripts nicely.

## Locales

`typos --locale en-gb .` (or `locale = "en-gb"` in config) switches the correction dictionary:
US spellings become findings — measured `color` should be `colour` in both a docstring and
regular code. The default `en` is locale-neutral. Options: `en`, `en-us`, `en-gb`, `en-ca`,
`en-au`.

Hex-identifier checking exists in the config surface (`ignore-hex = true` default; flipping to
`false` admitted tokens like `BADF00D` into the `--identifiers` stream), but probes across
`0xBAADF00D`, `BADF00D`, `DEADBABE` comment/declaration forms produced **no** finding — tokens
prefixed with a digit (`0x…`) are excluded from identifier tokenization outright. Treat hex
typo detection as dictionary-dependent, not guaranteed.

## Continuous integration

Upstream ships an official GitHub Action at the same repo (`crate-ci/typos`, tagged
`v1.51.1`), reading `files`, `extend_identifiers`, `extend_words`, `isolated`,
`write_changes` inputs. For any CI runner, the minimal gate is:

```bash
typos --format brief .   # exit 0 = clean, 2 = findings; failures use 64/78
```

Bare CI runners should run with `--isolated` or pin a config — otherwise a repo subdirectory's
own config file participates in the run.

## Debug and dry-run surface

All measured: `--files` prints each file that would be checked, `--identifiers` /
`--words` print the token stream (identifiers keep `uint32_t` whole; words split it into
`uint`/`32`/`t`), `--highlight-identifiers` / `--highlight-words` re-print files with the
checked spans marked, `--file-types` prints the type decision per file, `--type-list` prints
every built-in type with its file patterns. Use `--files` + `--identifiers` first when
diagnosing "why isn't my typo reported" — the answer is usually hidden/ignored/binary, or the
token split differently than you assumed.

## Limits

Dictionary-based only: no grammar, no context, no language detection. Corrections are
proposals — always read them; `extend-words` entries for domain jargon (API names, product
names) are the normal way to keep a repo green. Dictionary and type allowlists evolve with
each release: re-run `typos --dump-config -` and re-check `--help` after upgrading before
trusting old expectations.