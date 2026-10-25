---
name: tokei
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
description: "Use when a project's per-language code size is needed fast — repo sizing, migration audits, or finding how much script hides inside Markdown docs. Covers the sort-direction trap (-s descending, -r ascending), Markdown prose-as-comments with fenced code as embedded rows, .gitignore honored only inside git while .ignore/.tokeignore apply everywhere, the silent-empty --types miss, per-build serialization support, the head-pipe panic and the broken -i in 13.0.0 builds. Measured live."
---

# tokei — count code by language, instantly

`tokei` ([XAMPPRocky/tokei](https://github.com/XAMPPRocky/tokei)) walks a tree and prints a
per-language table of files, lines, code, comments and blanks in milliseconds — with surprises:
Markdown prose counts as *comments*, fenced code blocks surface as *embedded languages*, and a
mistyped `--types` filter silently reports zero. This skill is **original text written from live
binary behavior**, pinned to tokei **15.0.0**. Upstream is **dual-licensed MIT OR Apache-2.0** (the
source tarball ships both `LICENCE-MIT` and `LICENCE-APACHE`); the GitHub API license field reads
just `NOASSERTION` — take the files, not the field. No tokei code is quoted here, only measured
behavior. Cross-checked on **14.0.0** and **13.0.0** conda-forge builds; their `--help` surfaces
are byte-for-byte identical to 15.0.0.

## Install — and the binaries fact

GitHub releases for tokei ship **no binary assets** (checked all releases back through v13: zero
attached files — do not hunt there). Real routes, from upstream's own README:

```bash
cargo install tokei        # build from crates.io (needs rustc)
brew install tokei         # macOS
# conda-forge payload extracts with plain tools, no conda needed:
curl -sLO https://conda.anaconda.org/conda-forge/linux-64/tokei-15.0.0-hf19af3b_0.conda
unzip -o tokei-15.0.0-hf19af3b_0.conda && tar -I zstd -xf pkg-tokei-15.0.0-hf19af3b_0.tar.zst
./bin/tokei --version      # -> tokei 15.0.0 compiled with serialization support: json, cbor, yaml
```

Ubuntu/Debian apt has **no tokei package** (measured absent from the distro index); Arch
(`pacman -S tokei`), Fedora (`dnf install tokei`), Nix and Void do.

The `--version` line is authoritative per build: `compiled with serialization support: ...` lists
the output formats the binary actually carries. Conda-forge 13/14/15 builds all ship only
**json, cbor, yaml** — no toml — and the fail-closed error confirms it:

```text
$ tokei -o toml
error: invalid value 'toml' for '--output <output>': "toml" is not a supported serialization format
# exit 2
```

## The default model

- Running `tokei` in a directory counts it via a table: `Language | Files | Lines | Code | Comments
  | Blanks`, languages in **alphabetical order** by default. You can pass paths instead: one or
  more dirs/files; multiple dirs merge into **one combined table** (no per-directory breakdown).
- Hidden entries (dot-names, incl. whole dot-directories like `.github/`) are **excluded by
  default**; `--hidden` includes them. Measured: two Python files appear only with `--hidden` —
  one inside a dot-directory (`.hidden/h.py`) and one dot-named in the tree (`.dot-file.py`) —
  at rc 0.
- **Ignore semantics split by file class** (all measured):
  - `.gitignore`, `.hgignore` — VCS ignores — are honored **only inside a git repository**. Same
    tree, same `.gitignore` excluding `node_modules/`: the JavaScript files are counted without a
    `.git/` directory and vanish the moment `git init` runs. (Same wall as `fd`.)
  - `.ignore` and `.tokeignore` are honored **everywhere, git or not**: a `.ignore` containing
    `sub/` removed `sub/` from the count in a tree with no git repo, and `.tokeignore` naming
    `a.py` removed exactly that file.
  - `--no-ignore-vcs` (git/hg ignores), `--no-ignore-dot` (`.ignore`/`.tokeignore`), and
    `--no-ignore-parent` (parent-directory ignores) each disable one class; `--no-ignore` disables
    all three at once.
- Extensions tokei doesn't know are **silently skipped** from the table. `-v` (just one `-v`) turns
  on level-1 logging, which prints one WARN line per unknown extension, e.g.
  `WARN ... Unknown extension: zzz`. `-vvv` is a noisy per-file trace.

## Markdown — prose is comments, fences are code

The classifier treats Markdown as a text language, which produces the least-obvious numbers in the
tool and also its most useful party trick.

- Every non-blank Markdown line that is not fenced code counts as a **comment**; `# Title` and
  ordinary prose alike. A plain `.md` file measures `Files 1, Lines 3, Code 0, Comments 2,
  Blanks 1`. In a markdown-heavy documentation repo the language row reads code=0 with thousands
  of "comments" — that is prose, an audit artifact, not a bug.
- A fenced ```` ```bash ```` / ```` ```rust ```` block inside the file is counted as an **embedded
  language**: the table shows a section under a thin divider, like

  ```text
  Markdown                1            7            0            4            3
  |- Rust                 1            1            1            0            0
  (Total)                              8            1            4            3
  ```

  The Markdown row's own numbers exclude the fenced lines; the `(Total)` row and the grand `Total`
  below **do include** the embedded counts.
- Embedded children are named by the **fence token**, not the internal language: a ```` ```bash ````
  fence reports as `|- BASH` while a `.sh` file reports as `Shell`; other measured children
  include HTML, JSON, Just, Python, SVG, TOML, YAML and even nested `|- Markdown`.
- The whole holding language is **pulled out of the main alphabetical list** into that divider
  section, regardless of any `-s` sort. A Markdown file with *no* fenced code prints as a normal
  in-place row.
- `-C`/`--compact` removes the embedded section (and the children rows) but the grand Total keeps
  including embedded numbers.

Measured on a real 44-file markdown skill library: 7,685 counted lines, `Code 0`, `Comments 5,996`
— and embedded below: 30 bash scripts (432 code lines), PHP-era HTML, JSON, a justfile, Python,
SVG, TOML and YAML. That is the fastest answer to "how much script is actually in these docs?"

## Sorting — the direction trap

- `-s <column>` sorts **descending** — the opposite of common convention. Measured `-s code`:
  Python(4) before JSON(3) before Rust(3) before Shell(1). `-r`/`--rsort <column>` reverses to
  ascending. Possible columns: `files`, `lines`, `blanks`, `code`, `comments`. Ties keep
  alphabetical order.
- `-r` **takes a value**: bare `tokei -r` swallows the next token as its value and fails
  (`invalid value 'sort' for '--rsort'` when you write `-rsort code`, parsed as `-r sort`). Use
  `-r code` or `-r=code`.
- Languages with embedded content never join the sort (see above).

## Filtering — and the silent-empty trap

- `-t`/`--types` filters by language, comma-separated; both `-t Rust` and `-t=Rust,Markdown` (the
  documented form) work. A trailing comma is harmless (`-t Python,` still counts Python — measured
  rc 0 with the full Python row).
- **An unmatched type is not an error.** `-t Nope` prints the full table shell — headers plus a
  zero Total — and **exits 0**; the same happens in machine output (`-o json` emits just an empty
  `{"Total": ...}`) and for any typo (a space-separated mistake like `-t 'Python Rust'` printed
  no error either — same fail-silent class). There is no stderr hint to rely on: eyeball the
  Total row, or diff against a second run; exit codes cannot detect this miss.
- `-e`/`--exclude` takes **glob patterns** matched against path components and relative paths:
  bare `dep` removed `node_modules/dep/`, `index.js` removed by file name, `*.py` removed both
  `a.py` and `sub/d.py`, and a path form `sub/` / `sub/d.py` also worked. A non-matching pattern
  (e.g. `-e nope_pattern`) changes nothing and exits 0.
- The language-name authority is `-l`/`--languages`: a wide name→extensions box (338 lines here)
  listing every accepted `-t` name and mapped extension.

## Files, streaming and output formats

- `--files` (-f) prints per-file rows grouped under each language, with `./`-prefixed paths;
  per-file columns are `Lines Code Comments Blanks` (no Files column). Files whose path was
  excluded simply don't appear.
- `--streaming simple` prints a batch-friendly header plus fixed-width per-file records;
  `--streaming json` prints one JSON object per file (`{"language":"Python","stats":{"name":
  "./a.py","stats":{...}}}`). **Record order is the walk order — non-deterministic run-to-run and
  different from the table's order** (two identical runs ordered files differently; a Shell record
  landed before Python while the table prints differently) — sort yourself, don't rely on it.
- **Piping streaming output into an early-closing reader panics.** `tokei --streaming json
  | head -3` prints `failed printing to stdout: Broken pipe (os error 32)` and tokei itself dies
  at **rc 134** (same for `--streaming simple`). The aggregate table survived short pipes in
  measurements (rc 0), since its output is written in one lump. When scripting streaming output,
  redirect to a file or pipe through a full consumer (`wc`, `jq`), not `head`.
- `-o`/`--output` json/yaml/cbor emits the whole report; a `Total` key plus a `children` map per
  language, per-file `reports` lists. The recomposition flag `-i`/`--input` re-renders or extends a
  saved run: `tokei -o json | tokei -i stdin` and `tokei -i prev.json` both render the normal
  table (measured, and tokei 15 reads a JSON dump produced by tokei 13).
- `-n`/`--num-format` styles numbers (plain default, commas, dots, underscores) and **cannot be
  combined with `-o`** — clap rejects the pair ("cannot be used with", rc 2).

## Version walls found

- **13.0.0 conda-forge build: `-i` and `--streaming` are broken — any use panics** with
  `Mismatch between definition and access of \`file_input\`` / `\`streaming\`` (clap_builder
  4.5.15 downcast bug), aborting at rc 134 even when fed its own previous output. Fixed by
  14.0.0's changelog entry ("Fix downcast type mismatches in clap_builder"); 14 and 15 measured
  clean. If a tokei script dies this way, the binary is built on that clap version — upgrade.
- Help text and table shape are identical across 13.0.0, 14.0.0 and 15.0.0; the 14/15 changelogs
  only add languages (C++20 modules, Koka, Ark TS; C3, Blade, Djot, Godot scenes) — no flag walls
  found between them.

## Quick recipes (all verified by running them)

```bash
tokei                                  # aggregate table for cwd
tokei -t Python,Markdown -s code       # two languages, code-heavy first (descending is fine here)
tokei --files -t Markdown              # per-file sizes across docs
tokei -o json | jq -r '."Total".code'  # 12 — machine totals
tokei -o json | jq -r 'to_entries | map(select(.key != "Total")) | sort_by(.value.code)
  | reverse | .[0:3] | .[] | "\(.key) \(.value.code)"'
tokei --streaming json > stats.jsonl   # per-file records to file (head would panic)
```

## Version pin

- Primary: tokei **15.0.0** (upstream 2026-09-06, conda-forge x86_64 build).
- Cross-checked: **14.0.0**, **13.0.0** (conda-forge builds) — identical CLI surface; 13.0.0 as
  noted above panics on `-i`/`--streaming`.
- Upstream GitHub releases ship no binaries; licence files verified inside the source tarball.