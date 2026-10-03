---
name: node-debugging
description: Use when a Node.js bug needs more than console.log — one-shot breakpoint probes (node inspect --probe), the interactive debug> REPL, attaching to a process that is already running, or CPU/heap profiles of a running process.
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
---

# Node Debugging

## Overview

A debugger is not an upgrade over `console.log`; it is a different tool for a different question. Reach
for one when a value is wrong deep in a call chain, a variable lives in a closure you cannot print
without patching the file, or a process is already running and you cannot restart it.

The rule that keeps this cheap: **if a `console.log` answers it in under a minute, do that instead.**

| Tool | Use it for |
| --- | --- |
| `node inspect --probe <file>:<line> --expr '<expr>'` | One-shot: print an expression's value every time execution reaches a line. No interaction, scriptable, safe to run from an automated tool loop. |
| `node inspect script.js` | Interactive REPL: breakpoints, stepping, changing values. |
| `kill -USR1 <pid>` + `node inspect -p <pid>` | Attach to a process that is already running. |
| `node --cpu-prof` / `node --heap-prof` | Performance and memory questions, not state questions. |

Probe mode and the commands below were verified on Node 26.x. On older runtimes the `--probe` form may
not exist — check `node inspect -h`; the REPL flow and `--inspect*` flags existed long before it.

## One-shot probes (try this first)

```bash
node inspect --probe app.js:42 --expr 'user.id' app.js
node inspect --probe app.js:42 --expr 'items.length' --cond 'items.length > 0' app.js
node inspect --probe app.js:42 --expr 'state' --json app.js
```

Output is a transcript, not a session — the program exits normally afterwards:

```
Hit 1 at file:///work/app.js:42:15
  user.id = "u-771"
Completed
```

- `--expr` evaluates in the lexical scope of the probe location; it can call functions and walk
  objects (`hidden.nested.length` is fine).
- `--cond '<js>'` skips hits that do not satisfy the condition.
- `--max-hit <n>` and `--timeout=<ms>` cap the wait; several `--probe`/`--expr` pairs in one command
  are allowed and all fire in one run.
- `--json` prints structured results (`{"type":"number","value":5,...}` per hit) plus an explicit
  `{"event":"completed"}` marker — use it when another program parses the output.
- `--preview` previews object contents; with primitive-valued probes the plain output is unchanged.

## Probe gotchas (each one measured)

1. **Everything exits with status 0**, including `Missed probes:` lines and per-hit `[error]`
   ReferenceErrors. Never judge success by the exit code — parse the output for `Hit N at` /
   `Missed probes` / `[error]`.
2. **A probe on a line with no executable statement silently fires at the NEXT executable statement.**
   Probing line 1 of `if (false) { ... }` reports `Hit 1 at ...:2:1`. Always read back the location
   the hit actually reports, and prefer `file:line:column` for statement-level precision.
3. **Loops: the probe binds to the first executable column of the line** — on a one-line
   `for (...) { body }` that is the loop header, where the counter is often not yet initialized
   (`Cannot access 'i' from debugger`) or always evaluates pre-increment. Give the body statement's
   own column (`:1:24`), or put the body on its own line.
4. **Temporal dead zone.** Probing the line where a `let`/`const` is declared reads it before
   initialization and fails with `Cannot access 'X' from debugger` — even where reading the same
   variable one statement later would be legal. Probe a later line. A plain `X is not defined` is the
   unrelated case: wrong scope or a typo.
5. **The debuggee's own stdout and stderr do not appear** in probe output — only the probe transcript
   does. A `console.log` inside the program is invisible; that is fine, probes read state, they do not
   relay the program's prints.
6. **`Missed probes: <file>:<line>`** means the line never executed (dead branch, wrong file) — or your
   `--cond` excluded every hit. Check the condition first.
7. **`Timeout (3000) waiting for 127.0.0.1:9229 to be free`** means a previous inspector session's
   debuggee or driver is still running and holding the default port. Kill the stray process
   (`pgrep -af 'node inspect'`) or pass `--port=<other>` to both sides.
8. **`<file>` matches as a path suffix** of the loaded script URL. Running from the script's own
   directory, the bare filename works; in a multi-package tree, use a longer unambiguous suffix.

## Interactive REPL

```bash
node inspect script.js          # starts the script, pauses on the first line
node --inspect-brk script.js    # inspector on; attach separately (see below)
```

The `debug>` prompt accepts (all verified):

| Command | Action |
| --- | --- |
| `c` / `cont` | continue to the next breakpoint or exit |
| `n` / `next`, `s` / `step`, `o` / `out` | step over / into / out |
| `sb(N)` | breakpoint at line N of the current file; fires when execution next reaches it |
| `exec <expr>` | evaluate an expression in the paused frame (locals and closure state reachable) |
| `bt` | call stack while paused; prints `null` when the program is running or dead |
| `list(N)` | show N lines of source around the current line |
| `watch('<expr>')` / `watchers` | re-evaluate the expression at every pause |
| `repl` | drop into a sub-REPL in the current scope; `Ctrl+C` to return to `debug>` |
| `.exit` | quit the debugger |

Gotchas:

- **`sb('someFunctionName')` is not reliable** — on Node 26.7.0 it fails with
  `Uncaught Error [-32602]: Invalid parameters`. Set breakpoints by line number.
- **Early commands are lost.** The client spends its first second or two connecting; anything piped
  into stdin before `Debugger attached` appears is silently dropped. When driving over a pipe, wait
  ~2s after launch before the first command. If stdin ends early the session can hang — an
  agent/terminal without a PTY is better served by probe mode.
- **A dead debuggee still shows a live `debug>` prompt.** After `cont` past every breakpoint the
  program finishes; every subsequent command errors with
  `Uncaught Error [-32000]: Cannot find context with specified id` and `bt` prints `null`. That is
  your sign the process is gone: `.exit` and relaunch (with `--inspect-brk` if you need to break
  before any code runs).
- **`--inspect` vs `--inspect-brk`.** `--inspect` starts the inspector but lets the program run;
  attach too late and the interesting lines are already past. `--inspect-brk` pauses on the first
  line so breakpoints can be set before any code runs.

## Attaching to a process you cannot restart

```bash
kill -USR1 <pid>                  # Node starts its inspector (it need not have been started with --inspect)
curl -s http://127.0.0.1:9229/json/list   # [{ "id": "...", "webSocketDebuggerUrl": "ws://127.0.0.1:9229/..." }]
node inspect 127.0.0.1:9229       # or: node inspect -p <pid>
```

- `node inspect -p <pid>` resolves the port for you; the `host:port` form works too (the WebSocket URL
  from `/json/list` is what a graphical DevTools client consumes).
- For multiple Node processes at once, start them with `NODE_OPTIONS='--inspect=0'` — the option is
  inherited by spawned children, each picks a random port, and each parent/child prints its own
  `Debugger listening on ws://127.0.0.1:<port>/<id>` to stderr. Read the URLs from the logs or
  `/json/list` per port.
- **Security.** The inspector is arbitrary code execution. Node binds to `127.0.0.1` by default and
  keeps it that way; never expose it with a `0.0.0.0` binding on a shared network. `--disable-sigusr1`
  exists for environments that must not be debuggable via signal.

## Profiling without a debugger

```bash
node --cpu-prof  --cpu-prof-name=run.cpuprofile  script.js   # Chromium DevTools > Performance
node --heap-prof --heap-prof-name=run.heapsnapshot script.js # Chromium DevTools > Memory
```

Both write the artifact into the working directory by default (`--cpu-prof-dir` / `--heap-prof-dir`
relocate). Use these when the question is time or memory; a probe cannot answer either.

## Related skills

- **Which bug to chase, and why the obvious fix is usually wrong** — the `systematic-debugging` skill.
  Use it to find the failing path; use this one to look inside it.
- **The Python counterpart** — the `python-debugging` skill (pdb, debugpy, post-mortem).
- **Turning the reproduction into a permanent test** — the `test-driven-development` skill.