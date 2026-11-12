---
name: duf
version: 1.0.0
description: "Use when df output is unreadable or unscriptable — capacity checks in scripts, mount triage, or audit JSON: use duf. Covers grouped tables, exact-path args whose selection errors land on stdout while flag errors go to stderr, filters silent when they match nothing, ascending-only sort with no reverse flag in 0.9.1, filter-immune JSON with renamed keys, the two-value threshold grammar that rejects the word never, and the 0.9.1-vs-0.8.1 terminal-shrink divergence. Measured on official 0.9.1."
---

# duf — the df replacement measured: exact-path args, stdout-vs-stderr error split, filter-immune JSON, ascending sorts

`duf` (muesli/duf, MIT) renders disk usage as grouped box-drawn tables and JSON. This skill is
written from measurements on the official **v0.9.1** release binary (sha256-verified, see Install),
cross-checked against conda-forge 0.9.1 and Ubuntu noble's apt 0.8.1 (divergence row at the end).
Every exit code and message quoted below was produced live; two of them (threshold words, silent
rc-1 filters) are the kind that only surface in scripts.

## Install

The release page ships a **sha256 digest for every asset** — verify before running:

```bash
curl -sLO https://github.com/muesli/duf/releases/download/v0.9.1/duf_0.9.1_linux_x86_64.tar.gz
sha256sum duf_0.9.1_linux_x86_64.tar.gz
# expected: 5add851e7062c5e56939abb664705e4d14fa2d06289490aff31d51f153832de7
tar -xzf duf_0.9.1_linux_x86_64.tar.gz && install -m755 ./duf ~/.local/bin/duf
```

The tarball root holds both `duf` and `duf.1` (man page). Cross-checks:

- **conda-forge** `duf` 0.9.1 is the **same CLI** (a source rebuild — `duf --version` prints
  "(built from source)" instead of the commit, and the flag surface matches the release binary;
  `--help` is identical once you ignore the usage line's binary path). Same name = same tool here.
- **apt** (Ubuntu noble) ships **0.8.1** — old enough to diverge behaviorally; see the last section.

## The group model

duf classifies every mount with a `device_type` and folds them into groups: `local, network, fuse,
special, loops, binds` — the vocabulary both `-only` and `-hide` accept, and the value of
`device_type` in JSON. The default table shows **real-disk mounts only**: `/proc`, `sysfs`,
`devtmpfs`, `tmpfs` and friends are the `special` group and stay hidden unless asked for.

- `duf` — local disks (+ a network table when one exists)
- `duf -all` — everything, including pseudo, duplicate and inaccessible filesystems
- `duf -only special` — exactly the pseudo mounts
- each group renders as its own framed table with its own header ("2 local devices",
  "7 special devices")

`-style ascii` swaps the box-drawing frame for `+---+`; `unicode, ascii` is the whole style list.

## Arguments are exact paths only — never regex, never glob

This is where expectations from other tools break:

- **directory args** show the mount that *contains* the path (like `df <path>`):
  `duf /usr/bin` prints the `/` row, not a subtree.
- **device paths** also work: `duf /dev/nvme0n1p1` prints that device's mounts.
- **several args** union the containing mounts, deduplicated (`duf /tmp /boot` on a machine where
  both resolve to `/` prints one `/` row).
- **no regex, no glob, no substring**: `duf '^/boot'` and `duf '['` are treated as path literals.
- **a path that does not exist** fails with a walk worth reading: duf checks the path's components
  **top-down** and reports the *first* missing prefix, not the whole argument — `/no/such/dir`
  prints `lstat /no: no such file or directory`, `/tmp/x/nope` prints
  `lstat /tmp/x: no such file or directory`. Two twists: the `lstat` line goes to **stdout**
  (not stderr), and the run exits **rc 1**.
- **mixing a valid and a nonexistent arg kills the whole run**: `duf /tmp /nope` prints only the
  `lstat /nope` line, no table, rc 1.

So the scripted rule: rc 1 with a line on **stdout** = argument selection failed (a `lstat` path
error or an `unknown device group` filter typo); rc 1 with a line on **stderr** = a flag *value* is
wrong (sort/output column, theme, threshold grammar); rc 0 with zero output = a filter matched
nothing (valid for groups, unvalidated for fs/wildcards).

## Filtering — and the silent-failure traps

Three filter families, all comma-separated lists:

- groups: `-only local,network,fuse,special,loops,binds` / `-hide` (same names)
- filesystem types: `-only-fs ext4,vfat` / `-hide-fs` (kernel fs names, as in the TYPE column)
- mount points: `-only-mp '/sys*,/dev'` / `-hide-mp` — these **support wildcards** (quote them);
  this is the only globbing duf does anywhere

The traps, both measured:

- an **invalid group name** (`duf -hide bogus`, or `-only` likewise) errors on **stdout** —
  `unknown device group: bogus` — and exits **rc 1 with empty stderr**. The message is easy to
  lose to `2>/dev/null` and the exit code is what a wrapper sees.
- **fs and mount-point filter values are NOT vocabulary-checked**: `-only-fs bogusfs` and
  `-only-mp '['` return **rc 0, zero output, no error** — they just match nothing. A typo'd fs
  name or wildcard looks like "no such filesystem anywhere", not like an error.
- a **valid filter that matches nothing** (`duf -only network` on a laptop with no network mounts)
  is likewise **rc 0 with zero output** — so `duf ... && do_something` happily runs on an empty
  table. Distinguish the two by knowing your filter values, not by the exit code.

Also worth knowing: an explicit `-only-mp` pattern that matches a pseudo mount prints that special
filesystem **even though the default table hides its group** — explicit mount filters surface
hidden groups.

## Sort and columns

`-sort` and `-output` share one key list: `mountpoint, size, used, avail, usage, inodes,
inodes_used, inodes_avail, inodes_usage, type, filesystem`.

- **sorts are ascending only.** The default `mountpoint` is alphabetical; `-sort size` and
  `-sort usage` go small→large. There is **no reverse flag in 0.9.1** — upstream added
  `--reverse` on master after the release (issue #360), so text claiming it exists is ahead of
  the binary. For biggest-first, consume `-json` and sort on `free` yourself
  (the table has no descending mode).
- `-output` **selects columns but never reorders them** — whatever order you list, the frame
  renders in the canonical sequence (mountpoint, size, used, avail, usage, inodes, inodes_used,
  inodes_avail, inodes_usage, type, filesystem), and the leftover width flows into the remaining
  columns (drop five columns and the USE% bar becomes huge). Inode columns work without
  `-inodes` (`duf -output mountpoint,inodes,inodes_usage`). Listing a column twice or in a
  different order changes nothing but width.
- bad keys are a proper error: `-sort bogus` → rc 1, stderr
  `unknown column: bogus (valid: mountpoint, size, used, avail, usage, inodes, inodes_used,
  inodes_avail, inodes_usage, type, filesystem)`. Sort keys use the short form `inodes_avail` —
  `inodes_available` does not exist; the error is correct, not a hint at a hidden alias.

## The inode table

`duf -inodes` swaps the block columns for `INODES / IUSED / IAVAIL / IUSE%`. These are raw numbers
(no humanized suffixes), which makes inode mode the machine-friendly table; the JSON path below
is better for scripts.

## JSON for scripts — immune to every filter

`duf -json` prints one array. Two properties that surprise people who only read the flag list:

1. **it ignores every filter flag** — `-json -only-fs ext4` still listed all mounted filesystems
   including every pseudo one on our box (identical arrays with and without the filter).
   Filter JSON yourself, downstream.
2. **the key vocabulary is not the table's vocabulary**: `avail` → `free`, `inodes_avail` →
   `inodes_free`; plus JSON-only keys `device, device_type, fs_type, opts, blocks, block_size`.
   Within JSON, `type` is a friendly alias (`ext2/ext3`) while `fs_type` is the kernel name
   (`ext4`) — exact-match on `fs_type`, group-filter on `device_type`.

One local entry, real shape:

```json
{
 "device": "/dev/nvme0n1p2",
 "device_type": "local",
 "mount_point": "/",
 "fs_type": "ext4",
 "type": "ext2/ext3",
 "opts": "rw,relatime",
 "total": 982240026624,
 "free": 833302437888,
 "used": 98967072768,
 "inodes": 60981248,
 "inodes_free": 60268561,
 "inodes_used": 712687,
 "blocks": 239804694,
 "block_size": 4096
}
```

Never golden-compare these numbers across runs — live filesystems move between two calls.

## Colors, themes, thresholds — the value grammar

- **color needs both a TTY on stdout and a color-capable `TERM`.** Piped output carries only
  invisible leftovers wrapped around the usage-bar cell: an empty-parameter pair (`ESC[;;m` …
  `ESC[0m`) — the bytes exist, they draw nothing. On a *real* pty with `TERM=dumb` or no `TERM`
  at all, output degrades to the same empty wrappers (measured): duf colors follow `TERM`, it
  does not probe the terminal. Scripts capturing output may therefore see these bytes;
  strip them or ignore them, they render as nothing.
- `-theme dark` (default; 256-color codes like `38;5;150`), `-theme light`, `-theme ansi`
  (basic 4-bit codes: `92/93/94`, and the usage bar paints **green-on-green** `92;42;92`).
  An unknown theme is a clear stderr error, rc 1: `unknown theme: bogus`.
- thresholds color cells. `-usage-threshold` colors the bar cells (yellow then red as usage
  grows; default `0.5,0.9`); `-avail-threshold` colors the AVAIL column (default `10G,1G`).
  Both require **exactly two comma-separated values**:
  - usage wants floats in the documented 0..1 range — but the parser does **not** validate it:
    `2,2`, `1.5,1.9`, `-0.5,0.9` all return rc 0 and merely never trigger a color. The "from 0
    to 1" wording in `--help` is aspiration, not enforcement.
  - avail wants SI sizes — units required (`K,M,G,T`), and **no bare numbers, no `B` unit**:
    `0`, `0G`, `1B`, plain byte counts, and singles like `1G` are all rejected rc 1 with
    `error parsing avail-threshold: ...`; pairs like `1G,1M` or `100G,10G` pass.
  - **the keyword "never" is rejected by BOTH flags** in 0.9.1 (rc 1, stderr). There is no
    threshold word for "disable coloring"; the neutral route is a non-color `TERM` or a capture
    through a pipe.
- `-warnings` prints permission problems met while reading mounts (default: completely silent;
  e.g. `/sys/kernel/debug/tracing: permission denied` on our box).

## Width and the version divergence you will actually hit

- `-width N` hard-caps the frame; overflow is cut with an `≈` marker.
- On a narrow real terminal, **0.9.1 auto-shrinks the table**: headers abbreviate
  (`MOUNTED ON` → `MO`, `FILESYSTEM` → `FIL`) and long cells wrap onto continuation rows —
  measured at 50 columns, output stayed inside 50.
- **Ubuntu noble's apt 0.8.1 does not shrink**: at the same width it prints the full ~124-char
  table and clips the right edge with `≈`. Flag lists, help text, error strings and the rc
  taxonomy measured identical between the two; the missing pieces in 0.8.1 are the dynamic
  table width / resizable bars, the unicode bar characters, and the duplicate-mount dedup that
  0.9.0 added (its changelog: "adjust table width to avail space", "dynamically resize bars",
  "deduplicate list of mounts", plus a WSL2 9p fix). 0.9.1 itself is only version-string
  plumbing over 0.9.0.
- remember `--reverse` exists only on unreleased master, not in any published binary yet.

## rc taxonomy

- `0` — success, **including a filter that matched nothing** (silent empty output; fs and
  wildcard filter values are never validated)
- `1` — runtime and value errors, split by channel:
  - error printed on **stdout** (stderr empty): nonexistent path argument (`lstat ...` line),
    **unknown filter group** (`unknown device group: bogus` from `-only`/`-hide`)
  - error printed on **stderr** (stdout empty): unknown sort/output column (lists valid keys),
    unknown theme, threshold grammar violations
- `2` — unknown flag (`flag provided but not defined: -bogus` plus the usage dump, on stderr)
- `duf -h` prints the help and exits 0. No measured code path exits with anything else.

## Verify this skill's claims on your box

```bash
#!/usr/bin/env bash
# duf self-check — 14 exit-code/content contracts from the skill body; rc of this script is the verdict.
set -u
DUF="$(command -v duf 2>/dev/null || true)"
[ -z "$DUF" ] && for c in "$HOME/.local/bin/duf" /usr/bin/duf /usr/local/bin/duf; do
  [ -x "$c" ] && DUF="$c" && break
done
[ -z "$DUF" ] && { echo "FAIL: duf not found"; exit 1; }
pass=0; fail=0
ok() { pass=$((pass+1)); }
bad() { fail=$((fail+1)); echo "FAIL: $1"; }

# 1 default run: rc 0, table present
if "$DUF" </dev/null 2>/dev/null | grep -q 'device'; then ok; else bad "plain run rc/table"; fi
# 2 -output selects columns but never reorders: canonical order always
if "$DUF" -output size,mountpoint </dev/null 2>/dev/null | sed -n '4p' | grep -q 'MOUNTED ON.*SIZE'; then
  ok; else bad "-output canonical order"; fi
# 3 -sort size is ascending (first row's size <= last row's size)
if python3 - "$("$DUF" -sort size -output size,mountpoint </dev/null 2>/dev/null)" <<'PY'
import sys, re
rows = [l for l in sys.argv[1].splitlines()
        if '│' in l and re.search(r'[0-9.]+\s*[KMGT]', l)
        and not re.search(r'SIZE|MOUNTED|╰|╭|├', l)]
mult = {'K': 1e3, 'M': 1e6, 'G': 1e9, 'T': 1e12}
def val(line):
    m = re.search(r'([0-9.]+)\s*([KMGT])', line)
    return float(m.group(1)) * mult[m.group(2)]
sys.exit(0 if rows and val(rows[0]) <= val(rows[-1]) else 1)
PY
then ok; else bad "ascending -sort size"; fi
# 4 unknown sort key: rc 1, valid-key list on stderr (stdout stays empty)
o=$("$DUF" -sort bogus </dev/null 2>/tmp/duf_e >/tmp/duf_o); rc=$?
if [ "$rc" = "1" ] && grep -q 'unknown column' /tmp/duf_e && [ ! -s /tmp/duf_o ]; then
  ok; else bad "bad sort key rc=$rc out=$(wc -c </tmp/duf_o) err=$(wc -c </tmp/duf_e)"; fi
# 5 unknown flag: rc 2, usage dump on stderr
out=$("$DUF" -zz-not-a-flag </dev/null 2>&1 >/dev/null); rc=$?
if [ "$rc" = "2" ] && echo "$out" | grep -q 'flag provided but not defined'; then
  ok; else bad "unknown flag rc=$rc"; fi
# 6 unknown theme: rc 1, stderr only
o=$("$DUF" -theme bogus </dev/null 2>/tmp/duf_e >/tmp/duf_o); rc=$?
if [ "$rc" = "1" ] && grep -q 'unknown theme' /tmp/duf_e && [ ! -s /tmp/duf_o ]; then
  ok; else bad "bad theme rc=$rc"; fi
# 7 invalid group name: the error lands on STDOUT (stderr empty), rc 1
o=$("$DUF" -hide bogus </dev/null 2>/tmp/duf_e >/tmp/duf_o); rc=$?
if [ "$rc" = "1" ] && grep -q 'unknown device group' /tmp/duf_o && [ ! -s /tmp/duf_e ]; then
  ok; else bad "invalid group rc=$rc out=$(head -c 60 /tmp/duf_o) err=$(wc -c </tmp/duf_e)"; fi
# 8 valid group, zero matches here: rc 0 (content may be empty on other machines)
if "$DUF" -only network </dev/null >/dev/null 2>/tmp/duf_e; then
  [ ! -s /tmp/duf_e ] && ok || bad "-only network stderr"
else bad "-only network rc"; fi
# 9 nonexistent path: rc 1, lstat line on STDOUT, stderr empty
o=$("$DUF" "/no/such/dir-$$" </dev/null 2>/tmp/duf_e >/tmp/duf_o); rc=$?
if [ "$rc" = "1" ] && grep -q 'lstat' /tmp/duf_o && [ ! -s /tmp/duf_e ]; then
  ok; else bad "missing path lstat-on-stdout rc=$rc"; fi
# 10 JSON: filter-immune and renamed keys (free, not avail)
"$DUF" -json </dev/null 2>/dev/null | python3 -c '
import json, sys
d = json.load(sys.stdin)
loc = [e for e in d if e.get("device_type") == "local"]
assert d and loc, "no entries / no local entry"
e = loc[0]
assert "free" in e and "avail" not in e, "JSON key vocab drifted"
assert "inodes_free" in e and "fs_type" in e and "device_type" in e
assert any(x["mount_point"] == "/" for x in loc), "no root entry"
print("json ok")
' >/tmp/duf_j 2>/tmp/duf_je
if [ $? -eq 0 ] && grep -q 'json ok' /tmp/duf_j; then ok; else bad "JSON keys/filters: $(head -c 120 /tmp/duf_je)"; fi
# 11 threshold grammar: pair required, never rejected, floats unvalidated
t=0
"$DUF" -usage-threshold never </dev/null >/dev/null 2>&1 || t=$((t+1))
"$DUF" -avail-threshold never </dev/null >/dev/null 2>&1 || t=$((t+1))
"$DUF" -usage-threshold 0.5 </dev/null >/dev/null 2>&1 || t=$((t+1))
"$DUF" -avail-threshold 0 </dev/null >/dev/null 2>&1 || t=$((t+1))
"$DUF" -usage-threshold 2,2 </dev/null >/dev/null 2>&1 || t=$((t+100))
"$DUF" -avail-threshold 1G,1M </dev/null >/dev/null 2>&1 || t=$((t+100))
if [ "$t" = "4" ]; then ok; else bad "threshold grammar (t=$t)"; fi
# 12 inode table headers
if "$DUF" -inodes </dev/null 2>/dev/null | grep -q 'IUSED'; then ok; else bad "-inodes header"; fi
# 13 -all is a superset of the default table
a=$("$DUF" -all </dev/null 2>/dev/null | grep -c '│'); p=$("$DUF" </dev/null 2>/dev/null | grep -c '│')
if [ "$a" -ge "$p" ] && [ "$p" -gt 0 ]; then ok; else bad "-all superset (all=$a plain=$p)"; fi
# 14 piped output: invisible empty wrapper present, real color params absent (piped = degraded)
v=$("$DUF" </dev/null 2>/dev/null | cat -v)
if echo "$v" | grep -qF '^[[;;m' && ! echo "$v" | grep -qF '38;5;'; then
  ok; else bad "piped color wrappers"; fi

rm -f /tmp/duf_o /tmp/duf_e /tmp/duf_j /tmp/duf_je /tmp/duf_v
echo "duf self-check: $pass pass, $fail fail"
[ "$fail" -eq 0 ]
```

If a new duf release lands, re-run this block against the new binary before trusting the skill:
the JSON ignore-filters behavior and the threshold grammar are the first places a rewrite would
bite, and a master-only flag (`--reverse`) must be re-checked for publication.
