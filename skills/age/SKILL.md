---
name: age
description: "Handle age encryption from measured behavior: keygen and the -pq hybrid, the recipient/identity zoo (X25519, SSH, recipients files), armor, passphrase mode's hard TTY-only gate, the hidden -j batchpass plugin path, age-inspect JSON, the 1.3.x header caps (1024 stanzas / 2 MiB) that 1.1.x lacks, and the rc/stream error taxonomy. Use when scripting age, debugging decrypt failures, or picking identities."
version: 1.0.0
---

# age

`age` encrypts files with explicit keys instead of configuration. This skill
records what the CLI actually does when driven headless: every claim below was
measured on the official **v1.3.2** linux-amd64 release archive from
https://github.com/FiloSottile/age/releases (tag `v1.3.2`), cross-checked on
conda-forge's 1.3.2 build and on Ubuntu noble's **1.1.1** apt build for the
divergences. Two binaries matter (`age`, `age-keygen`), one is new in 1.3
(`age-inspect`), and the 1.3 release archives ship four plugin binaries.

## Install

Download the archive for your platform from the releases page. The v1.3 linux
archive unpacks to a single folder with seven files: `age`, `age-keygen`,
`age-inspect`, `age-plugin-pq`, `age-plugin-batchpass`, `age-plugin-tag`,
`age-plugin-tagpq`, plus `LICENSE`. Copy at least `age` and `age-keygen` into a
directory on `PATH`.

Release assets ship a `.proof` sidecar instead of checksum lists — a Sigsum
v2 record (`version=2`, log id, leaf hash, merkle root, a signature plus three
cosignatures, leaf index, and the node-hash path). Verifying it end-to-end
needs external Sigsum tooling; the pragmatic check is to compute
`sha256sum` yourself from the official download and treat that digest as the
pin (a verified download on 2026-11 measured the linux-amd64 archive at
19,405,817 bytes). `age --version` then prints the release tag (`v1.3.2`).

- **conda-forge** ships the same 1.3.2; builds there report `--version` as
  `devel` because no version is stamped at build time. The `age -h` and
  `age-keygen -h` output is identical to the release build.
- **Ubuntu noble** apt ships `1.1.1` — its walls are listed at the bottom.

## Keygen

```bash
age-keygen -o key.txt          # 3-line file: "# created:", "# public key: age1...", secret line
age-keygen                     # same three lines to stdout instead
age-keygen -y key.txt          # prints the bare recipient, one line, no comments
age-keygen -pq -o pqkey.txt    # hybrid ML-KEM-768 + X25519 keypair
```

- With `-o`, the public key is printed on **stderr** as `Public key: age1...`
  (the `# public key:` comment inside the file is not the stderr line).
- An existing `-o` target is refused, never overwritten; the file keeps its
  single secret line and stays 0600.
- The classic recipient is 62 characters. The hybrid one is ~1959 characters,
  starts `age1pq1`, and its secret line starts `AGE-SECRET-KEY-PQ-1`.
- `-y` accepts a file or stdin and works on classic and PQ identities alike;
  it strips comments and blank lines.

## Recipients and identities

- `-r RECIPIENT` is repeatable; each recipient becomes its own stanza.
- **Duplicates are kept, not deduped**: `-r K -r K` produces two identical
  stanzas (also true on 1.1.1); `age-inspect` lists the type twice.
- `-R FILE` reads a recipients file: one per line, `#` comments and blank
  lines ignored, `-` reads from stdin. A malformed line (plain garbage or a
  broken SSH key) fails hard on 1.3.2: `malformed recipient at line N`.
- SSH public keys work as recipients (`ssh-ed25519 AAAA...`,
  `ssh-rsa AAAA...`); pass the matching **private** key file to decrypt with
  `-i`. Both the ed25519 and the rsa roundtrip work without an agent.
- Identity files hold one or more secret-key lines (or an SSH key), and a
  passphrase-encrypted age *file* can also serve as an identity. Several
  `-i` files may be given; unused ones are ignored — but a syntactically bad
  line aborts everything fast: `error at line N: unknown identity type`.
- `-i -` reads identities from stdin, but stdin can only have one job:
  piping the input too fails with `standard input is used for multiple
  purposes`. With the input as a file argument it works:

```bash
cat key.txt | age -e -i - -o out.age input.txt   # identity from stdin, input from a file
age -d -i key.txt out.age
```

- `--encrypt` with `-i` selects symmetric-to-identity encryption: the same
  key file both created the stanza and decrypts it, with classic X25519
  stanzas in the header.

## Encrypt / decrypt workflows

```bash
age -r age1... -o secret.age file.txt       # encrypt a file
tar cz - data | age -r age1... > data.tgz.age
age -d -i key.txt secret.age                # decrypt
age -r a -r b -o multi.age file.txt         # both recipients decrypt it
age -a -r age1... > f.age                   # ASCII armor
age -d -i key.txt f.age                     # armor auto-detected, no -a needed
age -o - file.age                           # force output to stdout
```

- Output defaults to stdout, input to stdin; `-o` overwrites existing **files**
  silently but refuses a directory (`is a directory`).
- `-o -` means stdout and is the documented way to force binary/binary-ish
  plaintext through where a terminal would refuse it.
- Armor emits `-----BEGIN AGE ENCRYPTED FILE-----` and decryption detects it
  automatically.

## Header shape and the 1.3.x caps

The format is plain ASCII up front, which makes files greppable:

```text
age-encryption.org/v1
-> X25519 <43-char-arg> <43-char-arg>
<43-char wrapped file key>
-> X25519 ...
--- <43-char MAC>
<binary payload>
```

- Body lines are at most 64 characters and a **short last body line (< 64)
  terminates each stanza**; a stanza that ends without one fails parsing
  (`stanza ended without a short line`). The X25519 wrapped-file-key body
  must decode to exactly 32 bytes or you get `incorrect file key size`.
- Measured header sizes: one X25519 recipient = 168 bytes; one scrypt
  recipient = 150; one PQ recipient = 1627.
- **Decrypt-side caps in 1.3.x** (absent in 1.1.1, measured both): a header
  with **more than 1024 recipient stanzas** is refused (`header contains more
  than 1024 recipient stanzas`), and a header of **2 MiB or more** is refused
  (`header exceeds 2 MiB` — measured rejected at exactly 2,097,152 bytes,
  accepted at 1,048,576). The stanza-count check runs before the size check,
  and both fire before any MAC verification.
- The same walls do not exist on the encrypt side: `age -R file-with-1025`
  still succeeds with rc 0, so oversized files produced by age itself (or
  another implementation) simply refuse to decrypt on 1.3.x while 1.1.x
  parses them through.

## Passphrase mode is TTY-only

`-p` reads the passphrase from the terminal. Headless, it fails fast —
there is no env var, no stdin fallback (deliberate):

```text
age: error: could not read passphrase: standard input is not a terminal,
and /dev/tty is not available: open /dev/tty: no such device or address
```

Behavior measured on a real pty:

- Encrypt prompts `Enter passphrase (leave empty to autogenerate a secure
  one):` and then a confirmation; a mismatch answers `passphrases didn't
  match` (rc 1, no file written). An empty passphrase triggers an
  autogenerated one, printed as `age: using autogenerated passphrase
  "ten-hyphenated-words"` (10 words).
- Decrypt prompts `Enter passphrase:` and gets **one attempt**: a wrong
  passphrase is an immediate rc 1 `incorrect passphrase`, no retry loop.
- The scrypt stanza renders the work factor as plain decimal text:
  `-> scrypt <22-char salt> 18`.
- `AGE_PASSPHRASE_WORK_FACTOR=N` (1–30, default 18) is honored natively on
  the **encrypt** side. On decrypt the native CLI refuses factors above 22
  with `scrypt work factor too large: N`; `AGE_PASSPHRASE_MAX_WORK_FACTOR`
  does **not** lift that native cap (measured: still refused with the env
  set) — that variable belongs to the batchpass plugin only.

## Scripting passphrases: the hidden -j plugin path

`-j PLUGIN` never appears in `--help`. It routes a single recipient through a
plugin resolved from `PATH` as `age-plugin-<name>`:

```bash
AGE_PASSPHRASE=s3cret age -e -j batchpass file > file.age
AGE_PASSPHRASE=s3cret age -d -j batchpass file.age > file
```

- The wrapper is still an rc-1 `recipient #0` wrapper if the plugin is
  missing: `failed to wrap key for recipient #0: name plugin: couldn't start
  plugin: ... not found`.
- A wrong `AGE_PASSPHRASE` on decrypt fails rc 1 without retry, same class as
  the native passphrase path.
- Combines with armor (`-e -j batchpass -a`) and with `-o`.
- The release archives ship the plugins: `batchpass` (env-var passphrases —
  its help carries a loud warning that native keys are almost always the
  right answer, since scrypt is intentionally slow), `pq` (compatibility
  layer adding ML-KEM-768 + X25519 to *any* plugin-capable build, plus
  `-identity` to convert native PQ identities into `AGE-PLUGIN-PQ-1...`
  form), and `tag`/`tagpq` (the public sides of hardware keys).

## age-inspect (new in 1.3)

```bash
age-inspect f.age        # human-readable
age-inspect --json f.age # machine-readable
```

- Human output names the file, the format version, the recipient types (one
  line per stanza, duplicates listed), a post-quantum note, and a size
  breakdown starting from `Header 168 bytes` for a single X25519 recipient.
- JSON keys: `version`, `postquantum` (`no`/`yes`), `armor`,
  `stanza_types`, and `sizes` with byte-exact header/armor sizes.
- It inspects **encrypted files only**: a native key file is rejected with
  `inspection failed: ... unexpected intro: "# created: ..."`, an
  empty/stdinless source yields `file is empty`, and a tiny non-age blob
  yields `unexpected EOF reading intro`.

## Post-quantum and SSH recipients

```bash
age-keygen -pq -o pqkey.txt          # AGE-SECRET-KEY-PQ-1..., ~1959-char recipient
age -r "$(grep -o 'age1pq1[^ ]*' pqkey.txt)" -o pq.age file
age -d -i pqkey.txt pq.age           # decrypts the mlkem768x25519 stanza
age-inspect --json pq.age            # postquantum: yes, stanza_types: ["mlkem768x25519"]
```

- The PQ stanza type is `mlkem768x25519`, encrypted-to natively by 1.3+.
- `age-plugin-pq -identity pqkey.txt` produces plugin identities for
  deployments where age itself is too old to know the stanza.
- SSH: `-R <pubkey-file>` / `-r "ssh-ed25519 AAAA..."` encrypt; `-i
  <private-key>` decrypts. Both `ssh-ed25519` and `ssh-rsa` roundtrip
  natively; the stanza types are `ssh-ed25519` / `ssh-rsa`.

## Error taxonomy (measured on 1.3.2)

Fatal errors go to **stderr** with rc 1 and a trailing
`report unexpected or unhelpful errors at https://filippo.io/age/report`
line; the age-CLI's own selection errors that read like prose (decrypt
no-match) are also stderr, rc 1. Usage errors are rc 2. Full list:

- `unknown recipient type: "X"` — bad `-r` value, rc 1.
- `no identity matched any of the recipients` — decrypting with an unrelated
  key; stdout stays empty, message on stderr, rc 1 (same wording on 1.1.1).
- `failed to open input file "X": open X: no such file or directory` — rc 1.
- `failed to read header: parsing age header: file is empty` — empty input,
  rc 1 (also the inspect wording).
- A short non-age payload dies as `unexpected EOF reading intro`; a longer
  blob with a different first line as `unexpected intro: "..."`.
- `failed to parse recipient file "X": malformed recipient at line N` —
  including malformed SSH keys (the 1.3.2 hardening).
- `reading "X": failed to read "X": error at line N: unknown identity type`
  — one bad line spoils a whole identity file.
- Conflicts with hints: `-r` with `-d` answers
  `can't be used with -d/--decrypt` plus a `hint: did you mean to use
  -i/--identity ...` line; `-p` with `-r` is refused; `-j`/`-i` without an
  explicit `-e` prints a hint about `-e/--encrypt`.
- `--help` and `-h` both print the usage to **stderr** and exit **0**; an
  unknown flag prints `flag provided but not defined: -X` plus the usage and
  exits **2**.
- `-i -` with piped stdin: `standard input is used for multiple purposes`.

## Version walls

- **1.1.x (e.g. Ubuntu noble's 1.1.1):** no `-pq` (`flag provided but not
  defined: -pq`), no `age-inspect`, no bundled plugin binaries, and —
  measured — **no decrypt-side caps**: 1025-stanza and 2-MiB+ headers parse
  through (they fail later on real content checks). `-j` and the plugin
  lookup already exist there; duplicate recipients are kept there too.
- **1.3.x:** caps + PQ + inspect + shipped plugins, as above.
- **conda-forge 1.3.2:** identical help text but `--version` prints
  `devel` (no build stamp).

## Verify your install (recipe)

Run standalone; it exercises the roundtrip and the sharp behaviors above in a
throwaway directory. Override the binary with `AGE_BIN=/path/to/age`.

```bash
#!/bin/sh
set -u
W="$(mktemp -d)"; cd "$W"; trap 'rm -rf "$W"' EXIT
A="${AGE_BIN:-age}"; command -v "$A" >/dev/null 2>&1 || { echo "install age (https://filippo.io/age)"; exit 0; }
p=0; f=0
ck() { p=$((p+1)); printf 'PASS %s\n' "$1"; }
fa() { p=$((p+1)); f=$((f+1)); printf 'FAIL %s :: %s\n' "$1" "$2"; }
run() { "$@" >o.txt 2>e.txt; echo "$?" > rc.txt; }
printf 'hello age' > p.txt

run "$A" --version; rc=$(cat rc.txt)
if [ "$rc" = 0 ] && grep -Eq 'v?[0-9]+\.[0-9]+' o.txt; then ck v; else fa v "rc=$rc"; fi
run "$A" -h >/dev/null; rc=$(cat rc.txt)
if [ "$rc" = 0 ] && [ ! -s o.txt ] && [ -s e.txt ]; then ck help-stream; else fa help-stream "rc=$rc"; fi

KG="${A%age}age-keygen"
run "$KG" -o key.txt 2>/dev/null; rc=$(cat rc.txt)
if [ "$rc" = 0 ] && [ "$(grep -c '^# ' key.txt)" = 2 ] && grep -q '^AGE-SECRET-KEY-1' key.txt && grep -q 'Public key:' e.txt; then
  ck keygen; else fa keygen "rc=$rc"; fi
R=$(grep '# public key' key.txt | cut -d' ' -f4)
run "$KG" -y key.txt; rc=$(cat rc.txt)
if [ "$rc" = 0 ] && [ "$(cat o.txt)" = "$R" ]; then ck y-convert; else fa y-convert "rc=$rc"; fi

run "$A" -r "$R" -o enc.age p.txt; rc=$(cat rc.txt)
if [ "$rc" = 0 ] && [ "$(head -c 22 enc.age)" = 'age-encryption.org/v1' ] && grep -q '^-> X25519 ' enc.age && grep -q '^--- ' enc.age; then
  ck encrypt; else fa encrypt "rc=$rc"; fi
run "$A" -d -i key.txt enc.age; rc=$(cat rc.txt)
if [ "$rc" = 0 ] && [ "$(cat o.txt)" = 'hello age' ]; then ck roundtrip; else fa roundtrip "rc=$rc"; fi

run "$A" -a -r "$R" -o arm.age p.txt; rc=$(cat rc.txt)
if [ "$rc" = 0 ] && [ "$(head -1 arm.age)" = '-----BEGIN AGE ENCRYPTED FILE-----' ]; then
  run "$A" -d -i key.txt arm.age
  [ "$(cat rc.txt)" = 0 ] && [ "$(cat o.txt)" = 'hello age' ] && ck armor || fa armor "dec"
else fa armor "rc=$(cat rc.txt)"; fi

run "$A" -r "$R" -r "$R" -o dup.age p.txt; rc=$(cat rc.txt)
if [ "$rc" = 0 ] && [ "$(grep -c '^->' dup.age)" = 2 ]; then ck dup-kept; else fa dup-kept "rc=$rc"; fi

run "$A" -d -i key.txt nosuch.age; rc=$(cat rc.txt)
if [ "$rc" = 1 ] && grep -q 'no such file' e.txt && [ ! -s o.txt ]; then ck err-stream; else fa err-stream "rc=$rc"; fi
run "$A" -r not-a-key -o /dev/null p.txt; rc=$(cat rc.txt)
if [ "$rc" = 1 ] && grep -q 'unknown recipient type' e.txt; then ck bad-recipient; else fa bad-recipient "rc=$rc"; fi
run "$A" --totally-bogus -o /dev/null - < /dev/null; rc=$(cat rc.txt)
if [ "$rc" = 2 ] && grep -q 'Usage:' e.txt; then ck bad-flag; else fa bad-flag "rc=$rc"; fi
run "$A" -p -o /dev/null p.txt < /dev/null; rc=$(cat rc.txt)
if [ "$rc" = 1 ] && grep -q 'standard input is not a terminal' e.txt; then ck headless-p; else fa headless-p "rc=$rc"; fi

run "$KG" -pq -o pqkey.txt 2>/dev/null; rc=$(cat rc.txt)
if [ "$rc" = 0 ] && grep -q 'AGE-SECRET-KEY-PQ-1' pqkey.txt; then
  QR=$(grep '# public key' pqkey.txt | cut -d' ' -f4)
  run "$A" -r "$QR" -o pq.age p.txt; rc=$(cat rc.txt)
  if [ "$rc" = 0 ] && grep -aq 'mlkem\|X25519' pq.age; then
    run "$A" -d -i pqkey.txt pq.age
    [ "$(cat rc.txt)" = 0 ] && [ "$(cat o.txt)" = 'hello age' ] && ck pq || fa pq "dec"
  else fa pq "enc rc=$rc"; fi
else printf 'SKIP pq (older build)\n'; fi
if command -v ssh-keygen >/dev/null 2>&1; then
  ssh-keygen -t ed25519 -N '' -f sk -q -C ''
  run "$A" -R sk.pub -o ed.age p.txt; rc=$(cat rc.txt)
  if [ "$rc" = 0 ]; then
    run "$A" -d -i sk ed.age
    [ "$(cat rc.txt)" = 0 ] && [ "$(cat o.txt)" = 'hello age' ] && ck ssh || fa ssh "dec"
  else fa ssh "enc rc=$rc"; fi
else printf 'SKIP ssh (no ssh-keygen)\n'; fi
printf 'SUMMARY: %d checks, %d failures\n' "$p" "$f"
exit "$f"
```
