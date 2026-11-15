---
name: tealdeer
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
description: "Use when a tldr client lookup breaks or example-driven man pages are needed — cache-first flow with error on stderr and tips on stdout, the 30-day dir-mtime staleness warning silenced only via warn_cache_age never, multi-word args joined into one hyphenated page, -p override hiding unlisted platforms, -L limited to downloaded languages, TEALDEER_* envs, custom .page.md overriding cache pages, auto-update firing on render, and the empty-PAGER segfault under --pager. Measured on tealdeer 1.9.1."
---

# tealdeer — the cache-first tldr client, measured

tealdeer ([tealdeer-rs/tealdeer](https://github.com/tealdeer-rs/tealdeer)) is the Rust client for
tldr's example-driven command pages. Its whole design is cache-first: nothing renders without a
downloaded cache, and the age of that cache decides whether a page render also prints a warning
or silently hits the network.

Everything below was measured live on tealdeer **1.9.1** — the official
`tealdeer-linux-x86_64-musl` release binary — cross-checked on **conda-forge 1.9.1**
(md5-identical `--help`) and against the **Ubuntu 24.04 apt build 1.6.1** where it diverges.
Version walls are called out where they bite.

## Install and verify

- Per-arch static release binaries (`tealdeer-linux-x86_64-musl`, aarch64, i686, arm variants,
  macos, windows), each with a plain `<sha256>  <filename>` `.sha256` sidecar — verify with
  `sha256sum -c`. The x86_64 musl checksum for v1.9.1 is
  `5a9c3f0691b9cf375ee5c99de802885f3d50498cf686a539e2ddda028eb6b4f6`.
- The same release ships `completions_bash/fish/zsh` assets and `LICENSE-MIT.txt` /
  `LICENSE-APACHE.txt` (dual licensed). The repo's upstream licence is MIT **or** Apache-2.0.
- The binary name is flexible: running it as `tldr` or `tealdeer` changes only the `Usage:` line;
  both work. With `cargo install tealdeer` the binary lands as `tldr`.
- **apt wall**: Ubuntu noble's 1.6.1 lacks six later flags (`--edit-page`, `--edit-patch`,
  `--config-path`, `--override-config`, `--short-options`, `--long-options`) and its `--update`
  fails against the current upstream asset layout — rc 1 with
  `Could not decompress downloaded ZIP archive` / `invalid Zip archive: Could not find central
  directory end`, because tldr-pages now publishes per-language ZIPs
  (`tldr-pages.en_US.zip`). Use the release binary, not the distro build.

## The path map — `--show-paths`

```text
Config dir:       <config>/tealdeer/                  (OS convention)
Config path:      <config>/tealdeer/config.toml
Cache dir:        <cache>/tealdeer
Pages dir:        <cache>/tealdeer/tldr-pages/      — an extracted tree, not a tarball
Custom pages dir: <data>/tealdeer/pages/
```

derived from the XDG variables, and each line is suffixed `(OS convention)` — or
`(env variable)` when an override moved the path:

- `TEALDEER_CONFIG_DIR` relocates the config dir.
- `TEALDEER_CACHE_DIR` relocates the cache but prints a deprecation warning recommending the
  `cache_dir` config key.
- The `TLDR_*` names (`TLDR_CACHE_DIR`, `TLDR_CONFIG`) are the wrong names and do nothing —
  only `TEALDEER_*` exists. `LANG`/`LANGUAGE` feed the language defaults.

## Cache-first flow

- A page lookup or `--list` with no cache exits rc 1, and the message is split across streams:
  the bare error `Page cache not found. Please run \`tldr --update\` to download the cache.` goes
  to **stderr**, while the tips block (auto_update hint, config-path pointer, seed-config hint,
  docs URL) goes to **stdout**. Script against the two streams separately.
- `tldr --update` downloads per-language ZIPs from the release that `updates.archive_source`
  points at (default: tldr-pages latest release `download` directory) and replaces the
  `tldr-pages/` directory. First run prints `Successfully created cache directory ...`; every
  update prints `Successfully updated cache.` plus `Pages for the following languages were
  downloaded: en` — the list follows `[updates] download_languages`, defaulting to `en`.
  `-q` silences all update chatter.
- Update failures fail closed rc 1, with the cause plus a fixed TLS hint block ending
  `This build of tealdeer has support for the following options: rustls-with-webpki-roots,
  rustls-with-native-roots` (the default backend is the webpki-roots one).
- `tldr update` is **not** a subcommand in 1.9.1 — it is a page lookup for a page named
  `update` (rc 1, not found). Only flags are real.
- There is no `--search` flag in 1.9.1 (rc 2 clap error). Discovery is `--list`: 7417 pages on
  an en-only cache, and the list includes punctuation-only page names such as `!`, `$`, `((` and
  `,`.

## Staleness is a directory mtime

- The freshness marker is the mtime of the `tldr-pages` directory itself. Refreshing the cache
  resets it by replacing the directory; touching page files inside does **not** age it and
  touching the directory outright does.
- The warning fires at strictly more than 30 days (2,592,000 s, hardcoded — 29-day-old caches
  stay silent, 31-day-old ones warn on stderr with `The cache hasn't been updated for N days.`
  and the page still renders at rc 0).
- The only config knob is `updates.warn_cache_age = "never"` — the option is a single-value
  enum, so a numeric attempt is a load-time parse error rc 1
  (`invalid type: unit variant, expected string only` under `updates.warn_cache_age`). There is
  also no `cache_timeout` key in 1.9.x; unknown top-level fields fail closed listing the allowed
  tables (`style`, `display`, `updates`, `directories`, `search`).
- With `[updates] auto_update = true`, a plain page render triggers a **full network refresh**
  once the cache age passes `updates.auto_update_interval_hours` (default 720 h = 30 days).
  Measured: a 40-day-old dir, a `tldr git`, and the cache silently refreshed (warning gone,
  dir mtime reset) — a footgun on air-gapped or metered boxes. `--no-auto-update` blocks it for
  that run and the stale warning survives.

## Lookup semantics — the traps

- **Multi-word arguments join into one page name.** `tldr git log` renders `git-log`; and
  `tldr git node` fails rc 1 with `Page \`git-node\` not found in cache.` — the join, not an
  argument error, is the message you must read.
- `-p/--platform` repeats to build a preference list of `linux, macos, sunos, windows, android,
  freebsd, netbsd, openbsd, common`:
  - Unlisted platform directories are not searched: `-p linux ipconfig` (a windows-dir page)
    fails rc 1, even with `common` in the list. The `common` directory is always consulted —
    common-only pages (`jq`, `gron`) render under `-p linux` alone.
  - Values fail closed rc 2 with the nine-name list — but the legacy spelling `osx` is still
    accepted (rc 0, page renders) even though both help and error text say `macos`.
- `-L/--language` selects among languages **actually downloaded**: `-L de git` on an en-only
  cache fails like any missing page. Set `updates.download_languages = ["en", "de"]`, re-run
  `--update` (the report then lists `en, de`), and the German page renders.
- Rendering rewrites `{{placeholder}}` markup: braces are dropped and paired option
  placeholders collapse to their **long** variant by default (`{{[-A|--all]}}` renders as
  `--all`). `--short-options` — or `display.placeholder_format = "short"` — flips to `-A`.
  `--raw` prints the markdown verbatim with every `{{...}}` intact.
- `-f <file>` renders any local markdown file through the same engine (rc 0); a missing file is
  rc 1 with `Could not open page file at <path>` and an `os error 2` cause line.
- `--edit-page <cmd>` opens the custom target `$XDG_DATA_HOME/tealdeer/pages/<cmd>.page.md` in
  `$EDITOR`; `--edit-patch` targets the sibling `<cmd>.patch.md`. An unset/empty `EDITOR` fails
  with `No such file or directory (os error 2)`.

## Custom pages

- Custom pages are `<cmd>.page.md` files in the custom pages dir (`$XDG_DATA_HOME/tealdeer/pages/`
  or `directories.custom_pages_dir`). A custom page **overrides the cache page of the same
  name** — measured: a custom `git.page.md` replaced the cache's git page outright.
- The `.page.md` suffix is required: a bare `mytool.md` in the same directory never resolves
  (page not found).

## Configuration

- `--seed-config` writes a commented template to the resolved config path and refuses rc 1 when
  one already exists (`A configuration file already exists at <path>, no action was taken.`).
- The full key surface (template + measured overrides): `[style.<description|command_name|
  example_text|example_code|example_variable>]` each with `foreground`/`background`/`underline`/
  `bold`/`italic`; `[display]` `compact`, `use_pager`, `show_title`, `placeholder_format`
  (long|short), `indent` (defaults base 2 / command 6); `[updates]` `auto_update`,
  `auto_update_interval_hours`, `archive_source`, `tls_backend`, `download_languages`,
  `warn_cache_age`; `[directories]` `cache_dir`, `custom_pages_dir`; `[search]` `languages`,
  `platforms`.
- `--config-path <file>` relocates the config for one run. `--override-config` overlays dotted
  TOML keys after loading, e.g. `updates.auto_update = true`. Measured working overrides:
  `display.compact = true`, `display.show_title = true` (the page-title line appears),
  `display.indent = { base = 0, command = 0 }`, `updates.download_languages`,
  `directories.custom_pages_dir`, `updates.archive_source`, `updates.warn_cache_age`. Anything
  unknown fails closed with the allowed-tables error.

## Colors and pager — pty-measured

- Colors are **TTY-gated only**: on a pty with `TERM` empty the ANSI escapes still appear.
  Piped output is plain by default; `--color always` forces escapes through a pipe and
  `--color never` strips them on a TTY.
- `--pager` pipes through `$PAGER`. Two sharp edges, both measured on 1.9.1:
  - **An empty `PAGER=""` with `--pager` segfaults** — the process dies with SIGSEGV
    (stable across repeated runs). Never export an empty PAGER; unset it instead.
  - A bogus pager command still exits rc 0 — the failure is silent.
- Exit codes: 0 for success including the stale warning (which rides stderr); 1 for page not
  found, empty cache, config errors, seed refusal, and update failure; 2 for clap errors
  (unknown flags, invalid enum values). `-h`/`--help`/`--version` are rc 0.

## Reproduce the sharpest traps — offline battery

Run from a checkout of the binary on PATH as `tldr` (pinned to 1.9.1; re-measure after any
version bump). No cache and no network needed — every assert targets the failure paths the
skill documents.

```bash
export XDG_CACHE_HOME="$(mktemp -d)/cache" XDG_CONFIG_HOME="$(mktemp -d)/config"
fail=0
ok() { if eval "$1"; then echo "ok: $2"; else echo "FAIL: $2"; fail=1; fi; }
ok 'tldr --version | grep -q "1.9.1"'                                        'version pin'
ok 'tldr --help > /dev/null 2>&1'                                            'help rc 0'
ok '[ "$(tldr git 2>/dev/null | wc -l)" -gt 5 ]'                             'tips block on stdout'
ok '[ -n "$(tldr git 2>/dev/null | grep auto_update)" ]'                     'tips mention auto_update'
ok '[ -n "$(tldr git 2>&1 >/dev/null | grep "Page cache not found")" ]'      'bare error on stderr'
ok '[ "$(tldr git > /dev/null 2>&1; echo $?)" = 1 ]'                         'empty-cache rc 1'
ok '[ "$(tldr --list > /dev/null 2>&1; echo $?)" = 1 ]'                      'list without cache rc 1'
tldr --seed-config > /dev/null 2>&1
ok '[ -f "$XDG_CONFIG_HOME/tealdeer/config.toml" ]'                          'seed config written'
ok '[ "$(tldr --seed-config > /dev/null 2>&1; echo $?)" = 1 ]'               'second seed refused rc 1'
ok '[ "$(tldr --search x > /dev/null 2>&1; echo $?)" = 2 ]'                  'no --search: clap rc 2'
ok '[ "$(tldr -p zzz git > /dev/null 2>&1; echo $?)" = 2 ]'                  'invalid platform rc 2'
ok '[ "$(tldr --override-config "cache_timeout = 5" git > /dev/null 2>&1; echo $?)" = 1 ]' 'unknown field rc 1'
echo "battery rc will be $fail"; exit $fail
```

## Related

- `glow` — render the same markdown-style pages and repo readmes in the terminal.
- `fd` — find the command directories when the page you want is named differently from the file.
- `duf` — another tool from the measured-binary family with the same TTY-color caveat pattern.
