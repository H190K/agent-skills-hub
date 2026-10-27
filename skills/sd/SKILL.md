---
name: sd
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
description: "Use when replacing text in files or piped streams by regex — the sd find-replace CLI as the low-drama sed alternative. Covers in-place edits with no -i flag and no prompt, the 1.1 line-by-line default vs -A whole-file mode, cross-line patterns, capture-group adjacency errors, the v1.1.0 release that still reports version 1.0.0, batch fail-closed vs 1.0 fail-open, and preview-then-apply review. Measured live."
---

# sd — find and replace without sed's ceremony

`sd` ([chmln/sd](https://github.com/chmln/sd)) is a single-binary find-and-replace
tool: one regex, one replacement, optional file paths. No `s///` delimiters, no
`-e` scripts, no `-i` dance. Everything below was measured live on the **v1.1.0
x86_64 musl release binary** and cross-checked on the **v1.0.0 release** and the
**Ubuntu 24.04 distro build (`sd 1.0.0-2`, probe-identical to the v1.0.0
release on every probe)**; lines marked *v1.0 only* call out the wall.

Upstream licence is **MIT** (the source tarball's LICENSE reads
`MIT License / Copyright (c) 2018 Gregory`; `Cargo.toml` carries
`license = "MIT"`). This skill is an original write-up of measured behavior.

## Install

- Release tarball, no toolchain needed: GitHub releases ship per-target archives
  (e.g. `sd-v1.1.0-x86_64-unknown-linux-musl.tar.gz`). Extract the `sd` binary
  and put it on PATH; the archive also carries `LICENSE`, `README.md`, a `sd.1`
  man page and shell completions under `completions/`.
- Distro package: Ubuntu 24.04 ships `sd 1.0.0-2` via apt — that is the 2023
  v1.0.0 surface (**whole-file default, no `-A`**), so scripts written against
  it are not wrong but are written for a different tool behavior. `apt install sd`
  is fine as long as the default-mode wall below is respected.
- The other package routes are stale. The crates.io `sd` crate is still at 1.0.0
  (the workspace split moved the binary into an unpublished `sd-cli` crate), so
  `cargo install sd` installs the old whole-file build.

## The version that lies

Every one of the three probed binaries prints `sd 1.0.0` for `--version` —
including the 1.1.0 release assets. The v1.1.0 tag's `Cargo.toml` still carries
`version = "1.0.0"` and its changelog ends at 1.0.0; the binaries are not
byte-identical to v1.0.0's (the builds differ), the version string just was
never bumped. Two consequences:

- Never feature-detect by `--version`; use `sd --help | grep -q -- --across`
  (`--across` exists only on the 1.1+ surface).
- A bug report that says "sd 1.0.0" does not say which behavior you have.

## Two default modes — the wall that matters most

**1.1 processes line-by-line by default.** Patterns cannot span newlines, which
makes streaming possible: fed a pipe, partial output arrives before EOF, and
memory stays flat. Whole-file mode returns behind `-A`/`--across`.
Measured on a 34.8 MB file (2M lines): default ≈ 9.0 MiB peak RSS at 0.6 s;
`-A` ≈ 66.6 MiB at 0.3 s. Same result, opposite trades: `-A` is quicker,
line-by-line is bounded.

**v1.0 (and the Ubuntu distro build) is whole-file always**, and `-A` does not
exist — it fails with `unexpected argument '-A' found` at rc 2. A replacement
script moved across this wall changes behavior silently on everything except
cross-line patterns, which hard-fail instead.

What actually changes at the wall, all measured:

- Cross-line patterns fail closed on 1.1 unless `-A` is given. `-f s 'fo.*bar'`
  over `fo\nbar` is a rc-0 no-op on 1.1 and a clean match on 1.0. On 1.1 the
  same pattern works only with `-A` (`-f s -A`), and an explicit `\n` in FIND
  with `-A` also crosses.
- `-f e` (disable multi-line anchoring) is inert on 1.1 (each line is its own
  input, so `^` is always line-true) but real on 1.0 whole-file (`-f e '^foo'`
  stops matching a non-first line).
- `-f s` (dot matches newline) alone is enough to cross lines on 1.0; on 1.1 it
  needs `-A` too, because per-line processing has no newline to match.
- Streaming: 1.1's default emitted its first line while the producer was still
  writing; `-A` produced nothing until stdin closed. 1.0 always buffers. If you
  glue `sd -A` into a two-way pipeline with a producer that waits for output,
  expect the deadlock — the fix is the streaming default.

## In-place by default, no confirmation, no `-i`

The classic trap for sed users inverted: `sd` edits the named files **in place
by default**. There is no `-i` flag at all (passing nothing is the in-place
mode), and rc 0 on success. Given several file paths, all of them are edited:

```bash
sd 'old-name' 'new-name' src/main.rs README.md
```

- A directory in FILES is not recursed: 1.1 errors `Is a directory (os error 21)`
  at rc 1; **v1.0 only** silently ignores it at rc 0. Batch replacements go
  through `find`/`grep -rl` feeding explicit paths (see recipes).
- When both a pipe and FILES are given, FILES win and stdin is silently dropped
  (measured: a fresh file got the edit, the piped text vanished).
- Edits are atomic renames — the inode changes on every affected file, which
  file watchers will notice as a fresh file rather than an in-place write.
- No backup files are left behind.

## Preview — the only safe first step

`-p`/`--preview` processes the input but writes nothing (rc 0). The output is
the would-be **result text**, not a diff. Two measured shapes:

- Piped, 1.1's preview is plain text — **indistinguishable from the real
  edit**, so the diff review below is the review, not eyeballing the output.
  v1.0 only hardcodes ANSI markers on the changed span even when piped.
- With several FILES, 1.1 prints `----- FILE <path> -----` headers for every
  file; v1.0 prints headers only for files that actually changed.

The review recipe, then apply:

```bash
diff fruit.txt <(sd -p 'banana' 'cherry' fruit.txt)   # the review
sd 'banana' 'cherry' fruit.txt                         # the edit
```

## Flags that matter

| flag | measured semantics |
|---|---|
| `-p`, `--preview` | process only; result text to stdout, files untouched |
| `-F`, `--fixed-strings` | both args are literals (`a.x` stops matching `a-x`) |
| `-n <N>` | max replacements **per input unit** — per line on 1.1's default, per file on 1.0 and under `-A`; the help's "per file" wording means the input unit (measured: `-n 1` over a two-line file with one hit on each line replaced both on 1.1's default, once under `-A` and on 1.0; a cap larger than the match count is harmless) |
| `-f <flags>` | regex flags, combinable: `i` insensitive, `c` sensitive default, `w` whole word, `m` multi-line anchors default, `s` dot-newline, `e` disables multi-line anchors; **unknown flag chars are silently ignored** (`-f Q` still replaces, rc 0) |
| `-A`, `--across` | whole-file mode (1.1+; unknown argument at rc 2 on 1.0) |

The default regex mode behaves like a per-line Rust regex: `$1` captures work,
adjacent capture references without braces abort.

## Captures and escapes

- `$1`–`$N` reference groups in the replacement; `$1$2` composes fine.
- Adjacency is the hard error: `$1foo` aborts rc 1 with
  `` ``The numbered capture group `$1` in the replacement text is ambiguous.`` ``
  and a hint to write `${1}foo`. Braced form replaces cleanly.
- A group reference out of range renders **empty** at rc 0 (no error, no output
  hint) — `$2$1` against a one-group pattern quietly dropped the `$2`.
- Replacement escapes are real: `\t` and `\n` embed tab/newline. Stray
  backslashes survive as literals (measured `\z`-shaped leftovers pass
  through) rather than erroring.

## Exit codes and error shapes

- **0** — success, including **no matches** (`zzz` pattern rc 0, file untouched)
  and an **empty pattern** (`'' ''` rc 0). `sd` is never a presence check;
  check with `grep` first or review with `-p`.
- **1** — fail-closed inputs and syntax: bad regex (`error: invalid regex regex
  parse error:`), missing file (`error: invalid path: <f>`), unreadable file
  (`Permission denied (os error 13)`), dangling symlink, a directory argument
  (1.1), ambiguous capture.
- **2** — argument parsing: unknown flag, and on v1.0 also `-A`.

Error text moved between releases: v1.0 (and the distro build) dumps a
multi-line `failed processing files:` report with **hardcoded ANSI colors even
when piped**; 1.1 prints one plain `error: ...` line. Scripts matching error
text against 1.0 should strip ANSI spans or match the `error:` prefix only.

## Batch semantics — one wall, two kinds of damage

The same command over `[good, missing]` behaves differently:

- **1.1 is fail-closed for the whole invocation**: any invalid path aborts
  before processing, and the good files are left untouched (measured).
- **v1.0 is fail-open**: the good files are edited, the failures are reported,
  rc 1.

For 1.0-driven batches, validate the path list first (`ls <files> >/dev/null`
or a `find` that exists by construction). On 1.1, a failed batch is simply
re-runnable. Feed a bounded set per invocation (`xargs -0 -n 100`) so one bad
path cannot undo a large batch's progress.

## Reproduce the sharpest traps on your build

```bash
set -e
W="$(mktemp -d)"; cd "$W"
printf 'alpha banana gamma\nbeta banana\ndelta\n' > fruit.txt

# review then apply: preview prints the result, diff shows the change
sd -p 'banana' 'cherry' fruit.txt > preview.txt
diff fruit.txt preview.txt || true   # rc 1 just means the change exists
sd 'banana' 'cherry' fruit.txt
diff fruit.txt preview.txt           # rc 0: the edit matches the reviewed preview
grep -q 'alpha cherry gamma' fruit.txt

# whole-word matches only one run per input unit; the -n cap counts per unit
printf 'aaaa\n' > w.txt
sd -n 1 'a' 'Z' w.txt
grep -q '^Zaaa$' w.txt

# cross-line pattern needs -A on the 1.1 surface; feature-detect by help, never --version
if sd --help | grep -q -- --across; then
  printf 'fo\nbar\n' > x.txt
  sd -A -f s 'fo.*bar' 'X' x.txt
  grep -q '^X$' x.txt
fi
```

The last probe intentionally names a project-wide-replace pipeline (`grep -rl
--exclude-dir=.git -l PATTERN . | tr '\n' '\0' | xargs -0 sd FIXED REPLACEMENT`)
without running it: feed only the file list you audited, because on v1.0 a
mid-pipeline error means partial damage across batches.

## Version notes

- All behavior above measured on the **v1.1.0** musl release binary (tagged
  2026-02, which still prints version 1.0.0), cross-probed on the **v1.0.0**
  release and the Ubuntu 24.04 distro build (both match the whole-file v1.0.0
  surface exactly).
- Per the v1.1.0 release notes (labeled as upstream notes, not separately
  measured on this box): line-by-line default with `-A` restored, a more
  lenient escape implementation, ownership retention on the atomic write, and
  extra Windows targets. The measured items above are the surface an agent
  touches; the notes line up with the probes everywhere they overlap.
- The 0.x → 1.0.0 rename (`-s/--string-mode` → `-f/--fixed-strings`, changelog
  documented) left both spellings working — measured: `-s` and the long form
  `--string-mode` still parse as fixed-strings on 1.1.

## Related

- `fd` — produce the file list that feeds a batch `sd` (respecting gitignore).
- `typos` — find the misspellings before you bulk-replace with sd.
- `gron` / `jq` — round-trip JSON through those, never through regex replacement.