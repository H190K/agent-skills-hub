---
name: hyperfine
version: 1.0.0
description: "Use when benchmarking or comparing commands, scripts or binaries from the terminal — timing a single command, racing two or more for speed, sweeping a parameter, or measuring peak memory/CPU instead of guessing. Covers hyperfine 2.x's shell-less-by-default execution model, run hooks, parameters, metrics, exports and its traps."
---

# hyperfine — stop guessing which command is faster

`hyperfine` times commands with proper timing (multiple runs, warmup, outlier
handling) and reports mean ± σ, min … max, peak memory, and relative speed
comparisons. Use it whenever you are about to claim "this way is faster" or
need a stable number for a script's runtime or footprint.

## Install

Prebuilt binaries are published on the GitHub releases page for every
architecture. For the version pinned in this skill (see the last section for
licence and versions):

```bash
curl -sL https://github.com/sharkdp/hyperfine/releases/download/v2.0.0/hyperfine-v2.0.0-x86_64-unknown-linux-gnu.tar.gz | tar xz
mv hyperfine-v2.0.0-x86_64-unknown-linux-gnu/hyperfine ~/.local/bin/   # or any PATH dir
hyperfine --version
```

A musl build exists for glibc-less systems; `cargo install hyperfine`
(installs the current release from crates.io) and system packages are the
upstream-documented alternatives. Beware the distro lag: one major distro
still shipped `hyperfine 1.18.0` while 2.0.0 was current — an old package
silently changes the semantics below, most importantly the `-S` flag (see
`-S` means two different things).

## The 2.x execution model: no shell unless you ask

In hyperfine 2.x the benchmarked command is executed **directly** — no
intermediate shell. Pipes, `&&`, `;`, `$VAR`, quotes and globs are not
interpreted; they are either rejected or passed as literal arguments.

```bash
hyperfine 'true && echo hi'
```

fails with the verbatim explanation:

```text
Error: Command 'true && echo hi' contains unquoted shell syntax ('&&').
Explicitly choose how to execute it:
  -S / --shell=default  Interpret shell syntax.
  -N / --shell=none     Run directly, passing '&&' as a literal argument.
```

- `-S` restores the old behaviour: the command runs through the platform
  shell. On Unix that is `sh` (measured: `hyperfine -S 'echo $0'` prints
  `sh`), not bash. Pick a specific interpreter with the long form —
  `--shell 'bash --norc'` accepts a full command line.
- `-N` (alias for `--shell=none`) makes the direct execution explicit. With
  `-N`, the same string `true && echo hi` **runs** — hyperfine splits it on
  whitespace and invokes `true` with `&&`, `echo`, `hi` as literal arguments
  (measured, exit code 0 and no error). The syntax check above only fires in
  the ambiguous default mode.
- Shell builtins do not exist without a shell: `hyperfine 'cd .'` fails with
  `Error: Failed to run command 'cd .': No such file or directory (os error 2)`.
- To pass environment values without a shell there is a first-class option
  (measured end-to-end with `--env 'W=hello' 'printenv W'` — it printed
  `hello`):

```bash
hyperfine --env 'OMP_NUM_THREADS=8' 'my_benchmark'
```

- `--setup`, `--prepare`, `--conclude` and `--cleanup` commands **always run
  in a shell** (the platform shell), even when the benchmarked command runs
  shell-less — measured by logging from `--setup` with no `-S` flag.
- Fast commands under `-S` trigger a warning: *"Command took less than 5 ms
  to complete … hyperfine can not calibrate the shell startup time … use the
  `-N`/`--shell=none` option"*. Shell-less runs of the same command produce
  no warning.

**Version trap.** In hyperfine 1.x, `-S` is the short form of
`--shell <SHELL>` and **takes a value**. `hyperfine -S -r 100 'sleep 0.1'`
under 1.x makes `-r` the shell and aborts with `error: a value is required
for '--shell <SHELL>'`. The same input is valid under 2.x (where `-S` is a
bare alias). Scripts shared between the two versions must spell out
`--shell=…` or `--shell` with its value.

## Runs, warmup and the four hook commands

- `-w/--warmup N` — N discarded runs before timing (fills caches).
- `-r/--runs N` — exactly N measured runs (a single run is allowed: the
  results table then shows one `Value` column instead of mean ± σ).
- `-m/--min-runs N` (default 10) and `-M/--max-runs N` — let hyperfine
  choose how many runs to reach a stable number.
- `--style none` suppresses all output on both streams and still exits 0 —
  useful when the export files are the product.

Hooks (order measured over two commands × 2 runs; `S`=setup, `P`=prepare,
`C`=conclude, `X`=cleanup, the benchmarked command between them):

```text
S P C P C X   S P C P C X
setup once per command, then (prepare → command → conclude) per run,
then cleanup once, then the same cycle for the next command
```

- `--prepare` is where "clear the cache" and `make clean` belong; it runs
  before every measured run (its own time is excluded).
- `--setup` runs before each command's runs (compile-once, start the server),
  **it repeats for every benchmarked command**, not once per invocation.
- `--conclude` runs after each run (kill the process the run started);
  `--cleanup` runs once after all runs of a command (delete artifacts).
- Per-run logging: hyperfine sets `$HYPERFINE_ITERATION` on every iteration,
  starting at 0 (measured: `-S -r 2 'echo it-${HYPERFINE_ITERATION} > out-${HYPERFINE_ITERATION}.log'`
  produced `out-0.log`, `out-1.log`). Redirection needs the shell, hence
  `-S` in that one-liner.

## Parameters: sweeps and grids

`{VAR}` placeholders are only substituted when the matching parameter option
is given; otherwise the braces stay literal text.

```bash
# sweep with an explicit step: sleeps 0.05 then 0.1
hyperfine -P delay 0.05 0.1 -D 0.05 -r 5 'sleep {delay}'

# grid of two variables: four benchmarks (x/p, y/p, x/q, y/q)
hyperfine -L impl ref,new -L size 1,2 -r 5 'my_tool --impl {impl} --size {size}'
```

Benchmark titles show the parameter values, e.g. `Benchmark 3: true
(a = x, b = q)`.

## Metrics beyond wall time (2.x)

The default output table is wall time plus peak RSS (`Memory` row — the
child's own peak RSS; measured 13.5 MiB for a small Python process).
`--metrics` accepts presets (`default`, `time`, `all`) or explicit metric
names, optionally with a unit (`--metrics time_wall_clock:ms`):

- `--metrics time` adds CPU, user and system time rows.
- Hardware counters (`cpu_cycles`, `instructions`, `cache_misses`,
  `branch_misses`) require **no shell** and **kernel support**: with a shell
  enabled you get `Error: Metric 'cpu_cycles' is unavailable when a shell is
  enabled`; with `kernel.perf_event_paranoid` too strict you get
  `Error: Metric 'cpu_cycles' is unavailable for '<command>'. Check platform
  support and hardware-counter permissions.` (both rc 1).
- The `all` preset behaves differently: on the same restricted system it ran
  fine and simply **omitted** the counter rows — preset `all` silently drops
  unavailable metrics, an explicit `--metrics cpu_cycles` hard-fails.

## Exports

`--export-json`, `--export-markdown`, `--export-csv`, `--export-asciidoc`,
`--export-orgmode` write to the given file. The 2.x JSON schema (version 2)
is completely different from the 1.x JSON that most published reading
recipes expect:

```json
{
  "schema_version": 2,
  "primary_metric": "time_wall_clock",
  "metadata": { "hyperfine_version": "…", "start_time": "…", "platform": "…" },
  "results": [
    {
      "command": "sleep 1",
      "name": "…",
      "parameters": {"duration": {"value": "1"}},
      "measurements": [
        {"time_wall_clock": {"value": 1.0, "unit": "second"},
         "…": "…", "exit_code": 0}
      ],
      "summary": {
        "time_wall_clock": {"unit": "second", "count": 2,
          "mean": 1.0, "stddev": 0.0, "median": 1.0, "min": 1.0, "max": 1.0}
      }
    }
  ]
}
```

Migration for 1.x-era readers: `results[i].mean` →
`results[i].summary.time_wall_clock.mean`; `results[i].times` →
`results[i].measurements[j].time_wall_clock.value`; there is no top-level
`exit_codes` array any more — each run carries its own `exit_code` inside
`measurements` (measured: alternating exit codes landed one per run).
JSON values are always base units (seconds, bytes, counts).

For README tables, the Markdown export produces a comparison table whose
`Change` and `Factor` columns are measured **against the first command**:

```text
| Command | Mean Wall Time [ms] | Change | Factor |
|:---|---:|---:|:---|
| `sleep 0.05` | 52.8 ± 0.7 |  |  |
| `sleep 0.09` | 92.7 ± 0.6 | +75.6% | (1.8x slower) |
```

CSV columns are metric-prefixed (`time_wall_clock_mean`, `memory_peak_resident_mean`, …)
in base units. In a non-TTY session all human-readable output goes to
stdout (measured: stderr empty), so `2>/dev/null` does not silence results;
use `--style none` for that.

Reading the JSON export with jq pairs well with the `jq` skill.

## Exit codes and failure handling

- rc 0 — benchmark completed.
- rc 1 — benchmark command failed or could not run. A non-zero exit of the
  benchmarked command **aborts at the first failing run**: `hyperfine
  'false'` → `Error: Command 'false' terminated with non-zero exit code 1 in
  the first benchmark run. Use the '-i'/'--ignore-failure' option …`.
- `-i` / `--ignore-failure[=<MODE>]` ignores failures and adds a
  *"Warning: Ignoring non-zero exit code."* note; the benchmark still exits 0.
  A comma-separated list makes it selective: `--ignore-failure=1,2` ignores
  exit codes 1 and 2. The list is **fail-closed** — measured: a command
  exiting 1 with `--ignore-failure=2` still aborts with rc 1.
- rc 2 — CLI usage errors (unknown flag, missing command, a removed flag
  such as `--min-bench-time` or `--time-unit`, which no longer exist in 2.x).
- Ctrl-C is not a feature: on interruption no partial summary table is
  printed (measured on both 2.0.0 and 1.19.0 in a non-TTY session).

## Other flags worth knowing

- `--show-output` — print the benchmark's stdout/stderr instead of
  suppressing it; the debugging first step when a suspiciously fast command
  is actually failing.
- `--output <WHERE>` — where each run's output goes: `null` (default —
  /dev/null, which programs like grep detect and optimise for),
  `pipe` (avoid that detection), `inherit`, or a file. **A file path must
  not look like a keyword**: a bare relative path is parsed as a policy name
  and fails with `Error: Unknown output policy 'ofile.txt'. Use
  './ofile.txt' to output to a file named 'ofile.txt'.` (rc 1; measured also
  to fail under `-S`; the `./`-prefixed path works).
- `--input <WHERE>` — `null` (read from /dev/null, the default) or a file;
  measured: `--input in.txt 'wc -c'` counts the file where the default
  reports 0.
- `-n/--command-name NAME` — rename the entry in output tables (repeat it
  per command).
- `--shell` also accepts `"default"` explicitly; setup/prepare/conclude/
  cleanup always use a shell regardless of this option.

## Recipe: race two implementations and export for the README

```bash
hyperfine --warmup 3 --runs 30 \
  -n old 'tool --legacy input.txt' \
  -n new 'tool input.txt' \
  --shell 'bash --norc' \
  --metrics time \
  --export-json bench.json --export-markdown bench.md \
  --style none
cat bench.md
```

The command lines carry shell syntax? They don't here — the flags are plain
arguments — so this works in the default shell-less mode too; `-S`/`--shell`
is only needed when the string itself contains redirections, `&&`, quotes or
variables.

## How this skill was written

Every behaviour above was measured live against the hyperfine 2.0.0 release
tarball (x86_64 gnu build) and cross-checked against the same probes on
hyperfine 1.19.0 and a distro-built 1.18.0. Verbatim strings (errors,
warnings, table rows) are quoted from that binary. The shell-less default,
the `-S` semantics change, the JSON schema v2 and the hook behaviour are
documented breaking changes of the 2.0 release. Upstream: sharkdp/hyperfine
by David Peter and contributors, dual-licensed MIT OR Apache-2.0 (both
licence files ship in the release tarball; the MIT branch covers the MIT
licensing used in this library's NOTICE).