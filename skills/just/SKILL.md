---
name: just
description: "Use when writing, debugging, or reviewing a justfile — the casey/just command runner: recipe syntax, /bin/sh per-line semantics, parameters and defaults, variables and dotenv, platform attributes, inspection flags (--list, --evaluate, --dump, --show), --fmt, modules and imports. Cover the portability traps between the current release and older distro builds."
version: 1.0.0
author: original
license: MIT
platforms: [linux, macos, windows]
---

# just — save and run project commands from a justfile

## What it is

`just` is a command runner: one `justfile` per repo, one recipe per task, run
with `just <recipe> <args>`. It has no Make's build-up-to-date logic — every
run executes — which makes it the right tool for "run this thing" commands
(build, test, lint, deploy) and the wrong one for incremental compilation.

Core value over a pile of shell scripts: argument handling, variable
interpolation, dependency between recipes, and per-recipe documentation, all
in one file an agent can read, lint, and extend.

## Install and check

```bash
# GitHub release (pinned, musl static builds) — recommended for agents
curl -sL -o just.tar.gz \
  https://github.com/casey/just/releases/download/1.59.0/just-1.59.0-x86_64-unknown-linux-musl.tar.gz &&
  tar xzf just.tar.gz && chmod +x just
just --version            # "just 1.59.0"

# package managers: cargo install just · brew install just · apt universe (Ubuntu 24.04: 1.21.0)
```

Everything below was measured against the 1.59.0 release build and
cross-checked on Ubuntu's 1.21.0; version gaps are called out inline.

## Mental model of a run

- File discovery: `just` looks for `justfile` (case-insensitive) in the
  current directory, then walks upward. A file named `demo.just` is **not** a
  justfile — the `.just` extension means "import" or "module"; use
  `--justfile <path>` (`-f`) to point at one explicitly.
- Bare `just` runs the **first** recipe, whatever its name is.
- Unless a recipe has a `[no-cd]` attribute, it runs with the justfile's
  directory as cwd, even when invoked from a subdirectory.
- Each recipe line is a separate `/bin/sh -c` (dash on Ubuntu): `cd` and
  shell variables on one line do **not** survive to the next. For state, use
  a shebang recipe (one script, one shell — below) or chain commands on one
  line: `cd deploy && ./run.sh`.
- The recipe's exit code passes through untouched: a recipe containing
  `exit 3` makes `just` exit 3. CI wrappers get real signals, not just 0/1.
- Recipes run under `/bin/sh` regardless of your login shell; `$SHELL` in a
  recipe still holds your user's shell env value. Change the runner with
  `set shell := ["bash", "-cu"]` or `--shell`.

```just
# non-@ lines are echoed before execution; @ silences one line,
# - ignores that line's failure
build:
    cargo build

test: build
    cargo test

deploy:
    -rm -rf staging          # failure here is ignored ...
    rsync -av build/ staging # ... and this line still runs

# shebang recipe: the whole body runs as ONE script in that shell
report:
    #!/usr/bin/env bash
    set -euo pipefail
    out=$(mktemp)
    ./collect > "$out"          # variables persist across lines here
```

Non-@ recipes echo each line as they run it; in logs, the echoed line and its
output are distinguishable because the echo goes to stderr and the command's
output goes to stdout.

## Parameters and variables

```just
version := "1.59"                      # variable, evaluated eagerly
stamp := `date +%s`                    # backtick: runs the command at parse time
export LOG_LEVEL := "debug"            # exported: becomes env inside every recipe

release target arch="x86_64" *files:
    @echo "{{target}} {{arch}} {{files}}"
```

- Parameters without a default are required.
- `name="default"` makes it omittable; defaults may be arbitrary parenthesized
  expressions.
- `*var` is zero-or-more, `+var` is one-or-more; both expand space-joined.
- Interpolate with `{{name}}` in recipe lines, inside backticks, and in
  variables.
- Builtins measured working: `os()`, `arch()`, `num_cpus()`,
  `env_var('X')`, `env_var_or_default('X', 'fallback')`, `trim()`,
  `trim_end()`, `lowercase()`, `uppercase()`. There are **no
  user-defined functions**: `fn double(x):` is a compile error — inline the
  expression instead.
- Make habits do not port: `x ?= "y"` and the trailing-optional-marker
  `recipe param="x" ?: ` are compile errors in 1.21 and 1.59 alike. The only
  optional mechanism is a default value.

## CLI variable overrides

```bash
just --set target debug build          # --set <name> <value> <recipe...>
just target=debug build                # assignment prefix, same effect
```

- Both fail closed when the name is not already defined in the justfile:
  ``variable `v` overridden on the command line but not present in justfile``
  (rc 1). `--set` cannot create variables; edit the file for that.
- `just --evaluate` prints every variable as `name := "value"` (backticks
  evaluate too — parse side effects show up here). `just --evaluate name`
  prints one value **without a trailing newline** — pipe it, don't parse by
  line. `--evaluate-format shell` emits `name="value"` lines for eval.

## Attributes

Recipe attributes are lines in brackets directly above a recipe:

```just
[private]
secret:                 # hidden from --list and --summary
    @echo hush

[doc("Deploy to the given env")]
deploy env:             # --list shows the doc as a comment
    @just deploy-script {{env}}

[group("build")]
compile:                # --list renders under a [build] section at the end
    @cargo build

[confirm("About to deploy to prod — continue?")]
prod:
    @./deploy prod

[no-exit-message]
flaky:
    @./retry.sh         # on failure: silent, rc 1, no error text

[linux]
install-deps:
    @apt-get install gcc

[no-cd]
scratch:
    @pwd                # runs in the INVOCATION cwd, not the justfile dir
```

Measured semantics worth knowing:

- `[linux]`/`[macos]`/`[windows]` remove the recipe on other platforms
  entirely — invoking it reports
  ``justfile does not contain recipe `mx` `` (rc 1), and it is invisible to
  `--list`. A "recipe missing" error on one OS is an os-attribute, not a
  typo'd name (the accompanying "Did you mean?" suggestion helps separate
  them).
- `[confirm]` prompts before running; with no TTY (CI, cron) it **fails
  closed**: `recipe `prod` was not confirmed` (rc 1). `just --yes` runs
  every recipe without confirmation — the automation escape hatch, use it
  knowingly.
- Attribute support is version-gated: Ubuntu's 1.21.0 rejects `[doc(...)]`,
  `[group(...)]`, and `[confirm(...)]` with parse errors ("Unknown attribute
  `doc`"); `[private]`, `[no-exit-message]`, and os attributes work there.

## Dependencies, modules, imports, aliases

```just
build: test lint            # run after test and lint finish
push: (build "release")     # dependency args are EXPRESSIONS: strings need quotes,
                            # bare names are variable/param references

alias b := build            # just b == just build; --list annotates "# [alias: b]"

import 'ci.just'            # textually inline ci.just (vars + recipes)
import? 'local.just'        # optional import: missing file is fine, rc 0
mod sub                     # recipes in sub/justfile become just sub <recipe>
mod? other                  # optional module
```

- Recipe dependency cycles are a compile-time error:
  ``recipe `dep-b` has circular dependency `dep-a -> dep-b -> dep-a` ``
  (rc 1, with file:line).
- A recipe that shells out to `just` (`@just other`) recursing between
  themselves is **not** caught at parse time — those are separate processes
  and they multiply until killed. Cycle-checking at compile time covers
  dependencies only; make `@just` call chains trivially terminating.
- `--list` renders imported recipes at top level and modules as `sub ...`;
  expand modules with `just --list --list-submodules` (the flag alone is a
  usage error, rc 2).

## Inspect before you run

| Want | Use |
| --- | --- |
| Every recipe, with params and docs | `just --list` |
| Bare names, one line (scripting) | `just --summary` |
| One recipe's exact source | `just --show <recipe>` |
| All variables | `just --evaluate` |
| Canonical formatted source | `just --dump` |
| The full parse-tree AST | `just --dump --dump-format json` |
| Dry-run (prints all lines, rc 0) | `just --dry-run <recipe>` |

`--dump --dump-format json` is the authoritative settings read: its
`settings` object shows defaults like `"dotenv_load": false`. Use it to check
what a justfile will actually do instead of guessing.

## Format and lint

```bash
just --fmt              # reformat in place (tabs -> 4 spaces, collapses blanks)
just --fmt --check      # rc 1 + diff when the file is not canonical
just --fmt --check --unstable   # needed on Ubuntu's 1.21.0
```

- `--fmt` compiles the justfile first — a syntactically broken file fails
  with the parse error, not a format diff.
- The `--fmt` command is **unstable before 1.4x**: on distro builds you get
  ``The `--fmt` command is currently unstable. Invoke `just` with the
  `--unstable` flag`` — add `--unstable` for those.

## Environment and dotenv

`.env` files are **not** loaded by default — measured on 1.21 and 1.59
(`dotenv_load: false` in the AST; a recipe reading `$FOO` fails even with a
populated `.env` present). Opt in explicitly:

```just
set dotenv-load := true      # loads .env from the justfile dir and ancestors
```

Or per-invocation: `--dotenv-path <file>` / `--dotenv-filename <name>` /
`--no-dotenv`. Env vars visible to recipes come from the caller's
environment, exported variables, and dotenv in that order of expectation —
don't assume a secret is "already in the env" without checking with
`env_var_or_default`.

## Interactive choosing and completions

- `just --choose` pipes recipes to an external chooser; the default command
  is ``fzf --multi --preview 'just --unstable --color always --show {}' ``
  and without fzf installed it exits rc 127. Override with `--chooser <cmd>`
  or a `JUST_CHOOSER` env value.
- Shell completion on current releases is runtime: eval
  `JUST_COMPLETE=bash just` (or zsh/fish/powershell) inside your shell init.
  Distro builds (1.21) still use `just --completions bash` static scripts.

## Justfile-writing gotchas (measured)

- Comments above a recipe become its documentation in `--list`; the one
  above the FIRST recipe will be shown next to the default recipe — write it
  as if it is a description.
- A recipe line starting with `#` is a comment; lines are joined with a
  trailing backslash into one line.
- Parse errors point at exact file:line:col with the source excerpt:
  `error: expected '*', ':', '$', identifier, or '+', but found ?` — but
  the *cause* is almost always make syntax (`?=`, `?:`) or an attribute on
  the wrong line (they must sit between other lines, not after the recipe
  name on the same line).
- A dependency referencing an unknown recipe is a compile-time error:
  ``recipe `build` has unknown dependency `test` `` (rc 1). Arguments inside
  `(recipe ...)` calls are expressions — a bare name must be a variable or
  parameter in scope, string literals need quotes; an undefined name fails
  with ``variable `x` not defined`` even though a recipe can never have that
  name.
- Unknown recipe: ``justfile does not contain recipe `nope` `` with a
  "Did you mean ...?" suggestion when close by. Distro 1.21 wording is
  capitalized with a trailing period; current releases lower-case both —
  greps pinned to one exact string need both shapes.
- Missing required parameter and extra args both exit 1 with usage lines;
  extra positional args beyond a recipe's signature are tried as the name of
  a following recipe (`just build test` runs build, then test).
- `--set` cannot introduce a new variable, `--evaluate` writes values with
  no trailing newline, `--dry-run` always exits 0, and recipe-line `cd`
  never persists.

## Related

- `verification-before-completion` — treat a green recipe run as an output
  check, not a proof; recipes that always exit 0 hide failures.
- `systematic-debugging` — when a recipe fails, bisect by running its lines
  directly in a shell before rewriting the justfile.