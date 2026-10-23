---
name: actionlint
description: "Use when writing, reviewing or committing GitHub Actions workflow files — a workflow won't start, runs-on labels or matrix values look wrong, an action's `with:` inputs need checking, `run:` shell or python steps need a local lint pass, or CI should gate workflows before merge. Covers actionlint 1.7.12: install, exit codes 0/1/2/3, bundled runner-label and popular-actions metadata checks, shellcheck/pyflakes integration, actionlint.yaml config. All behaviors measured live."
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos]
---

# actionlint — lint GitHub Actions workflows before they run

`actionlint` ([rhysd/actionlint](https://github.com/rhysd/actionlint), MIT) is a single static
Go binary that checks GitHub Actions workflow YAML: expression syntax and types, matrix and
`needs` property references, `runs-on` labels, `with:` inputs, deprecated workflow commands,
schedule cron strings, and basic YAML structure. It integrates optional `shellcheck` (for
`run:` shell scripts) and `pyflakes` (for `shell: python` steps). It is offline-friendly —
runner labels and a popular-actions metadata database are bundled, no API round-trip. Every
behavior below was measured live against actionlint 1.7.12 on Linux; flags are quoted from
`actionlint --help`. Runner-label lists and metadata evolve per release — re-check `--help`
after upgrading.

## Install

Pin a release tarball (this exact binary is what the measurements below come from):

```bash
curl -sSfL -o actionlint.tgz \
  https://github.com/rhysd/actionlint/releases/download/v1.7.12/actionlint_1.7.12_linux_amd64.tar.gz
tar xzf actionlint.tgz actionlint && ./actionlint -version
```

`-version` prints three lines — version, how it was installed, build compiler — for the
tarball binary:

```text
1.7.12
installed by downloading from release page
built with go1.26.1 compiler for linux/amd64
```

The upstream README also documents `brew install actionlint` and
`go install github.com/rhysd/actionlint/cmd/actionlint@latest`.

## Project scan (default mode)

Running bare inside a repository lints every workflow it can find, walking parent
directories to locate `.github/workflows`:

```bash
cd <repo-root>
actionlint
```

Measured first: **both a git repository and the workflows directory are required.** In a
plain folder containing only `.github/workflows/`, the command refuses with an error and
exit code 3:

```text
no project was found in any parent directories of "<current-dir>". check workflows directory is put correctly in your Git repository
```

It does not matter that the folder looks like a repo root — there is no `git init` fallback.
Two escapes exist when you are outside a git repo: explicit file paths and stdin (below).

## What findings look like

Each finding is `file:line:column: message [rule-id]` followed by a source excerpt with a
caret. Real example from a matrix typo (key is `node_version`, used as `matrix.node-version`):

```text
.github/workflows/ci.yaml:13:29: property "node-version" is not defined in object type {node_version: number} [expression]
   |
13 |           node-version: ${{ matrix.node-version }}
   |                             ^~~~~~~~~~~~~~~~~~~
```

## Exit codes (all measured)

- **0** — no findings.
- **1** — findings exist. This includes YAML that fails to parse: a broken file produces
  `could not parse as YAML: ... [syntax-check]` findings (reported per file) and linting of
  the remaining files continues. So a syntax error still exits 1, not 3.
- **2** — CLI usage error: an unknown or malformed flag. Usage text is printed and nothing
  is linted.
- **3** — runtime failure: no project found (above), an argument file cannot be read
  (`could not read "<name>": no such file or directory`), or an unreadable `-config-file`.

In CI, exit 1 is the gate; exit 3 usually means the invocation itself was wrong.

## What it catches — measured examples

- **Matrix and `needs` property typos** (`expression`): aside from the matrix example above,
  `needs.build.outputs.ok` with no such job reports
  `property "build" is not defined in object type {}` — an invalid `needs:` reference leaves
  the object empty, and every downstream expression over it becomes a finding.
- **Missing dependency** (`job-needs`):
  `job "build" needs job "test" which does not exist in this workflow` — reported on the
  *job name* line, not on the `needs:` key.
- **Unknown `runs-on` labels** (`runner-label`): the message embeds the full available-label
  list (as of 1.7.12: `ubuntu-24.04(-arm)`, `ubuntu-latest(-4/-8/-16-cores)`, `macos-26*`,
  `macos-15*`, `windows-2025(-vs2026)`, `self-hosted`, `x64`/`arm`/`arm64` family, bare
  `linux`/`macos`/`windows`, …) and ends with a hint to declare custom self-hosted labels in
  the config file.
- **Deprecated workflow commands** (`deprecated-commands`):

  ```text
  workflow command "set-output" was deprecated. use `echo "{name}={value}" >> $GITHUB_OUTPUT` instead: https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions
  ```
- **Schedule cron typos** (`events`):
  `invalid CRON format "0 5 * * " in schedule event: expected exactly 5 fields, found 4: [0 5 * *]`
  — note a trailing space splits off a phantom field and produces this.
- **`with:` inputs against action metadata** (`action`): two different sources, see below.
- **YAML structure** (`syntax-check`): parse failures, `"steps" section is missing in job "j"`,
  `"steps" section should not be empty`.
- The full check catalog for the pinned version lives at
  `github.com/rhysd/actionlint/tree/v1.7.12/docs/checks.md` (linked from `--help`); the
  release tarball also ships a local `docs/` copy and a man page.

## `with:` input checks — local vs popular vs unknown

The `action` rule validates inputs against different sources:

- **Local composite actions** (`uses: ./.github/actions/<name>`) are validated against the
  action's own `action.yml`. Both measured forms fire:
  `missing input "req" which is required by action "Pop" defined at "./.github/actions/pop". all required inputs are "req"` and
  `input "wrong_name" is not defined in action "Pop" defined at "./.github/actions/pop". available inputs are "req"`.
- **Popular remote actions** are checked against a database bundled in the binary. A bogus
  input for `actions/setup-node@v4` fires
  `input "bogus_input" is not defined in action "actions/setup-node@v4". available inputs are ...`
  — and the available list even includes fork-only inputs like `mirror`/`mirror-token` that
  plain `actions/setup-node` does not have, so the database is curated, not scraped.
- **Unknown remote actions get NO input check.** `uses: totally/unknown-action@v99` with a
  made-up input produced no finding — do not assume inputs are validated for actions outside
  the bundled list. (Nothing is fetched remotely; there is no network metadata path.)
- **A nonexistent local action path also passes silently** (measured: `uses:` pointing at an
  `./.github/actions/` directory that does not exist → clean exit 0). actionlint checks
  metadata that exists; it does not verify the path itself.

## The shellcheck / pyflakes trap

`run:` shell scripts and `shell: python` scripts are linted by **external programs**, and the
integrations are **off unless the binary is on PATH** — silently:

```text
verbose: Rule "shellcheck" was disabled: exec: "shellcheck": executable file not found in $PATH
verbose: Rule "pyflakes" was disabled: exec: "pyflakes": executable file not found in $PATH
```

A repository can look lint-clean purely because `run:` blocks were never checked. When
installing shellcheck/pyflakes on a new box or CI image, confirm with `-verbose`.

- **shellcheck** (shellcheck.net releases; a single static tarball) linting a `run:` block
  reports, measured:
  `shellcheck reported issue in this script: SC2086:info:1:6: Double quote to prevent globbing and word splitting [shellcheck]`
  — the inner `1:6` coordinates are positions in the extracted script, and the caret still
  points at the whole `run:` block.
- **pyflakes** applies only where the step runs Python: `shell: python`, or the job's
  `defaults.run.shell: python`. Expression placeholders are substituted before pyflakes sees
  the script (`print('${{ runner.os }}')` → pyflakes sees `print('Linux')`, no false hit).
  Finding measured: `pyflakes reported issue in this script: 1:7: undefined name 'hello' [pyflakes]`.
- **Custom paths and opt-outs**: `-shellcheck <cmd-or-path>` and `-pyflakes <cmd-or-path>`
  override PATH lookup (both honored in measurement, including pointing at a venv's pyflakes);
  `-shellcheck= -pyflakes=` disables both — the help text notes disabling them also makes
  actionlint faster, because each `run:` block otherwise spawns an external process.

## Config file

`actionlint` auto-discovers `.github/actionlint.yaml` at the project root, or use
`-config-file <path>`. Scaffold a default with `actionlint -init-config` (writes the file,
exit 0). The generated shape:

```yaml
self-hosted-runner:
  # Labels of self-hosted runner in array of strings.
  labels: []

# Configuration variables in array of strings ...
config-variables: null
```

Declaring a custom self-hosted label silences the `runner-label` finding: with
`self-hosted-runner: {labels: ["cuda"]}`, `runs-on: [self-hosted, cuda]` lints clean
(measured).

**Gotcha, measured: wrong schema keys are silently ignored.** A flat `self-hosted: [cuda]`
top-level key produced no finding AND no warning — the label stayed unknown — while the
nested `self-hosted-runner.labels:` shape actually filtered it. If a config file appears
ineffective, re-check the key names against `-init-config` output before doubting the run.

For quick suppressions without config changes, `-ignore <regex>` is repeatable and matches
error-message text (dropping findings 5 → 4 in measurement, leaving the non-matching ones
untouched).

## Machine-readable output

- `-oneline` — one line per finding (no caret excerpt), parser-friendly.
- `-format '{{json .}}'` — findings as a JSON array; measured keys per item:
  `message`, `filepath`, `line`, `column`, `end_column`, `kind` (the rule id), `snippet`.

## Lint in CI, and lint pre-commit

To gate the repo's own workflows with CI (using the pinned binary, no shellcheck there):

```yaml
jobs:
  lint-workflows:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          curl -sSfL -o actionlint.tgz https://github.com/rhysd/actionlint/releases/download/v1.7.12/actionlint_1.7.12_linux_amd64.tar.gz
          tar xzf actionlint.tgz actionlint
          ./actionlint -shellcheck=
```

Exit 1 from findings fails the step; exit 3 usually means the checkout layout is wrong.
For editor/pre-commit use, lint explicit paths or stdin (`actionlint -`); only the
project-scan default requires the git-repository context.

## Draft-mode usage outside a repo

When iterating on a workflow file that is not in a git tree yet, both non-scan forms work
(measured outside any git repository):

```bash
actionlint draft-ci.yaml               # explicit path, relative to CWD
actionlint - < draft-ci.yaml           # stdin
actionlint - -stdin-filename ci.yaml   # name findings after the real file
```

## Limits

- Static only: secrets, runner tool versions, environment propagation, network behavior, and
  `if:` truthiness at runtime are invisible to it. A clean run means the workflow is
  well-formed and internally consistent — not that it will pass.
- Input checks are only as current as the bundled database; a just-released action's new
  inputs may produce false `action` findings on older binaries — report the upgrade path
  rather than deleting real inputs.