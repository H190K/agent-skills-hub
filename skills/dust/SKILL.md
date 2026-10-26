---
name: dust
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
description: "Use when a per-directory disk-usage view is needed — hunting space hogs, cleaning a tree, or reading disk state faster than du. Covers the biggest-at-bottom default ordering, the 20-row piped display cap with uncapped totals, filter semantics (-X path prune vs -v/-e regex on node paths, display-only -z, hidden-file -i), size modes (blocks, apparent-size, filecount, filetime), the per-extension view, JSON output shape, and version walls back to 0.8.6. Measured live."
---

# dust — readable disk usage in one bar-chart tree

`dust` (the upstream crate is `du-dust`, [bootandy/dust](https://github.com/bootandy/dust))
walks a directory tree and prints every entry as a bar-and-percent row over a tree glyph,
sorted by size — `du` with the aggregation and sort already done for you.

Everything below was measured live on **dust 1.2.6** (the x86_64 musl release binary) and
cross-checked on **1.1.2** and **0.8.6**; version lines call out where the surface changes.

## Install

- Static build, no root needed: take the release tarball for your platform from GitHub releases
  (x86_64 Linux musl ships as `dust-v1.2.6-x86_64-unknown-linux-musl.tar.gz`), extract the `dust`
  binary, put it on PATH. The tarball carries only the binary, a LICENSE and a README.
- Debian-style root install: each release also ships a `.deb` named `du-dust_<version>-1_amd64.deb`.
- With a Rust toolchain: `cargo install du-dust` (crate name `du-dust`, binary `dust`).
- Do not rely on distro packages: on an Ubuntu 24.04 box checked in October 2026,
  `apt-get download du-dust` found nothing in the configured sources. Use the release assets.

## Read the output — three rules first

1. **Biggest is at the bottom.** Rows sort ascending and the scanned root prints last as the
   100%-total row. `-r` flips the tree so the largest rows print first (pair with `head`).
2. **Piped output is capped at 20 rows** (the "terminal height" default becomes 20 when stdout
   is not a tty) plus the root row. The smallest rows vanish silently, while totals and every
   aggregate are still computed over the full tree — so a script that reads the rows can miss
   entries the numbers already include. Measured: a 41-directory tree printed exactly 21 lines.
   Use `-n <N>` when scripting (`-n 0` prints only the total row).
3. **Sizes are disk-block usage, not file length.** A 7-byte file displays as 4.0Ki on this
   probe. `-s` switches to apparent size (actual file bytes: that same file shows 7B); `-o b`
   prints exact allocated bytes (no Ki/Mi rounding); `-o si` uses powers of 1000.

Ties at equal size print in alphabetical name order and the output is byte-identical across
runs (three identical md5 sums on the same tree).

## Filters that recompute totals — and the one that does not

| flag | matches | totals move? | measured notes |
|---|---|---|---|
| `-X <path>` | a path or path component (`sub`, `p/sub`) | yes | subtree pruned from rows and totals; nonexistent value silently ignored rc 0; repeat the flag for several |
| `-v <regex>` | node paths, `./`-prefixed relative (`./zzz` matches) | yes | matched files drop entirely; an unanchored pattern matching a directory drops the whole subtree |
| `-e <regex>` | same as `-v`, include-only | yes | `-v` and `-e` conflict → rc 2 |
| `-I <file>` | one regex per line in FILE, added to `-v` | yes | |
| `-i` | hidden entries (leading dot) | yes | hidden files are excluded from the aggregate, not just hidden from the display |
| `-z <min>` | files smaller than MIN bytes | **no** | display-only culling; the total row keeps the full tree size |

The `-v`/`-e` regexes are plain Rust regexes tested against the relative node path
(`dust -p` shows exactly which strings those are). Two sharp edges, both measured:

- Anchoring with `$` is asymmetric. A `$`-anchored pattern matches a directory's own entry but
  does not prune the walk: the directory row stays with its children and only the directory's
  own 4 KiB block is subtracted from its aggregate. Measured twice: `-v 'sub$'` took a 12Ki
  directory to 8.0Ki instead of removing it, and `-v 'zzz$'` removed just two directory blocks
  (8192B) from a 172032B subtree whose rows all stayed. When you mean "prune this subtree",
  use `-X`; when you mean "drop these files", use an unanchored regex like `-v '\.png$'`.
- A nonexistent `-X` value is a silent no-op at rc 0 — check the total row moved.

## Size and time modes

- `-f` (filecount): the size column becomes the number of descendant files. Empty directories
  show 0, and `(total)` counts files only — on the probe tree a 40-directory flat tree read 40
  and the root read 55.
- `-m m|a|c` (filetime): the size column becomes ISO timestamps (`2026-10-26T10:05:23`); the
  bar and percent columns disappear entirely and rows sort by time. A directory shows the most
  recent child file. Pair with time filters `-M/-A/-y +/-n` (present since 1.1.2: `+n` =
  modified in the last n days minus one window).
- bare `-t` (file-types): an aggregate view grouped by extension — one row per extension plus
  `(no extension)` and `(total)` rows. `-t <file>` restricts the view to the extension(s) of
  the given file(s): `dust -t big.bin` prints only the `.bin` row. The value must be an
  existing path (`dust -t txt` exits rc 1 with `No such file or directory: txt`), and the
  `--file-types=txt` value form errors rc 2 (`no more were expected`). On 1.1.2, `-t` also
  conflicts with `-d` (rc 2).

## Display flags that actually matter for scripting

- `-n <N>` row cap (`-n 0` = total only; `-n 5` keeps the five largest entries). Default cap:
  terminal height, 20 when piped.
- `-p` full paths (`./` prefixes on every row — makes `-R` and `-v` debugging legible).
- `-R` screen-reader mode: flat `name depth size percent` table, no bars; names repeat, so add
  `-p`.
- `-L` dereference symlinks: the link row renders under the link's own path with the target's
  subtree and the target's own row disappears; the duplicate is not double-counted.
- `--collapse <path>` keeps that directory as a single leaf row even above the depth cut.
- `--skip-total` drops the root/total row; `-b` drops bars and percents; `-B` moves bars right;
  `-w <N>` fixes the width; `--dim` dims the bars; `-c`/`-C` disable/force colors (colored rows
  survive a pipe with `-C`).
- `-x` stays on one filesystem (parsed, rc 0; no second filesystem was available to probe
  cross-device behavior); `-T <n>` caps the walker threads; output stayed deterministic.

Multiple input paths render as several trees under a single `(total)` row. `--files-from -`
(newline-separated) and `--files0-from -` (NUL-separated) read input paths from stdin; empty
stdin falls back to scanning the current directory.

## Errors, exit codes

- Unknown flag, invalid `-o` value, conflicting flags → **rc 2** with a clap error.
- Nonexistent input path → **rc 1** on 1.2.6, stderr `No such file or directory: <paths>`
  (all missing paths are listed together). On **1.1.2 the same error still exited rc 0** — do
  not chain `&& dust` across versions without checking.
- Unreadable directories → rc stays **0**; stderr carries a one-line hint, and `--print-errors`
  names the exact directories (`Did not have permissions for directories: ./<dir>`). Totals
  silently shrink past unreadable subtrees — look at the hint when you need exact numbers.
- `--config <missing>` only warns and continues at rc 0.
- `-o` values: si, b, k, m, g, t, kb, mb, gb, tb. `-o` does not exist at 0.8.6 (rejected rc 2);
  it exists from 1.0/1.1 on.
- `-S/--stack-size`: accepted but deprecated on 1.2.6 (help says the walker no longer recurses
  and the value is ignored); on 1.1.2 it takes a value with documented defaults.

## JSON output

`-j/--output-json` prints the whole tree as JSON **to stdout** (the help's "to the current
directory" means paths are rooted at the scan directory, not that a file is written):

```json
{"size": "1.0Mi", "name": "./flat", "children": [...]}
```

Two traps when parsing: entries sort biggest-first (opposite of the text tree), and every
`size` is a human-readable string rounded like the display — not byte-exact. For byte-exact
scripts use `-o b` text output or `du`.

## Reproduce the sharpest traps on your build

```bash
mkdir -p /tmp/dusttrap/sub && head -c 5000 /dev/urandom > /tmp/dusttrap/sub/f.bin
head -c 100000 /dev/urandom > /tmp/dusttrap/big.bin
cd /tmp/dusttrap && dust -n 100 -o b        # 7 rules: cap, bottom ordering
dust -v 'sub$'                              # row stays, only own block drops
dust -v sub                                 # subtree pruned, totals move
dust -X sub                                 # clean subtree prune
dust -z 50000                               # rows cull, total unchanged
```

## Related

- `fd` — locate exactly the files you then want to size with dust.
- `tokei` — per-language code sizing once dust shows where the tree is heavy.
- `gron` / `jq` — flatten or query the `-j` JSON if you script against it.