---
name: python-debugging
description: Use when a failing test, wrong value, crash or unexplained behaviour needs a debugger rather than print statements — pdb breakpoints, post-mortem inspection of a traceback, attaching to a process that is already running, or debugging a remote or headless one.
version: 1.1.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
---

# Python Debugging

## Overview

A debugger is not an upgrade over `print()`; it is a different tool for a different question. Reach
for one when you need to inspect state that a print cannot reach — a value that is wrong three frames
up, a collection mid-mutation, a process you cannot restart — or when you want to change a variable
and re-run the next few lines without editing the file.

The rule that keeps this cheap: **if `print()` or a longer traceback answers it in under a minute, do
that instead.** Everything below is for the times it does not.

| Tool | Use it for |
| --- | --- |
| `breakpoint()` + pdb | Local, interactive, simplest. Stop where you already suspect the bug. |
| `python -m pdb script.py` | Same, with no edit to the file. |
| `python -m pdb -c continue script.py` | Post-mortem: run until the crash, then inspect the frame it died in. |
| `debugpy` | Attach to a process already running, or debug a remote/headless host. Talks DAP, so any editor can drive it. |

## pdb command reference

Inside a `(Pdb)` prompt:

| Command | Action |
| --- | --- |
| `n` / `s` | next line (step over) / step into |
| `r` | continue until the current function returns |
| `c` | continue |
| `until N` | continue until a line number is reached |
| `j N` | jump to line N (same function only) |
| `l` / `ll` | list source around the current line / the whole function |
| `w` | where — print the call stack |
| `u` / `d` | move up / down the stack |
| `a` | print the arguments of the current function |
| `p expr` / `pp expr` | print / pretty-print an expression |
| `display expr` | auto-print that expression at every stop |
| `b file:line` / `b func` / `b file:line, cond` | breakpoint, including conditional |
| `tbreak file:line` | one-shot breakpoint |
| `cl N` | clear a breakpoint |
| `interact` | a full interactive Python interpreter in the current scope |
| `!stmt` | execute a statement in the current frame — see the trap below |
| `q` | quit |

`interact` is the escape hatch: inside it you can import anything and poke at live objects, then exit
back to the same stopped frame. `p expr` calls `repr()`, so `p some_list` shows the list as code; use
`pp` when the structure is nested.

## Recipe 1 — break where you suspect, run normally

```python
def compute(rows):
    total = sum(r.amount for r in rows)
    breakpoint()          # drops into pdb here, with locals in scope
    return total / len(rows)
```

Run the program the way you always run it. You land at the line with the frame live.

## Recipe 2 — no edit: run the file under pdb

```bash
python -m pdb path/to/script.py arg1 arg2
```

The program is stopped at its first line before anything executes, so you can set breakpoints first:

```
(Pdb) b module.py:118
(Pdb) c
```

This is also the way to debug something you cannot conveniently edit — a console entry point, a
generated file, a third-party module run as `-m`.

## Recipe 3 — post-mortem on a traceback (the most useful one)

You have a traceback and you want the locals at the moment of the crash. This is what makes pdb worth
the keystrokes:

```bash
python -m pdb -c continue path/to/script.py
```

`-c continue` runs the program until an uncaught exception fires, then drops into the debugger at the
crashing frame — no breakpoint needed, no guessing where to stop. `w` shows how you got there and `p`
shows the values. For a script that takes a while to reach the failure, add `-c 'until 118'` with the
line number you care about.

## Recipe 4 — pytest

The same post-mortem idea, one flag (pytest installs with `pip install pytest` if it is not already in
the project):

- `pytest --pdb` — stop in the debugger at the first failure instead of only printing the traceback.
- `pytest --trace` — stop at the **start of every test**, before it runs.
- `pytest -x --lf` — stop at the first failure and then re-run only that test while you work.

`--pdb` is the one to remember: it turns a traceback you have to reason about into a frame you can
inspect. Use `--trace` when the failure is not at the assertion but early, in fixture or setup code.

## Gotchas

These are the ones that cost the most time. Each is behaviour you can reproduce, not folklore.

- **An assignment typed without `!` may be parsed as a command.** pdb first tries the line as a
  debugger command, and many common variable names collide with one: `n`, `c`, `l`, `s`, `b`, `p`,
  `q`, `r`, `u`, `d`, `j`, `w`, `a` are all commands. In the frame `n = 5` fails with
  `*** Invalid argument: = 5` and never assigns — silently leaving you debugging the old value. Any
  name that is also a command needs the prefix: `!n = 5`. When an assignment seems to have no effect,
  this is why.
- **`PYTHONBREAKPOINT=0` turns every `breakpoint()` into a no-op.** If the breakpoints in a script
  never fire, check that variable before suspecting your line numbers. Set `PYTHONBREAKPOINT=` to a
  different callable to route `breakpoint()` to that instead of pdb.
- **Attaching to a process you do not own needs privilege on Linux.** `python -m pdb -p <pid>` and
  `debugpy --pid <pid>` both fail with `insufficient permissions` when the kernel's
  `ptrace_scope` is 1 and the target is not your own child. The check is
  `cat /proc/sys/kernel/yama/ptrace_scope`; the fix is to relax it, run with the needed capability,
  or — usually simplest — launch the process under the debugger instead of attaching to it.
- **On Linux, `debugpy --pid` attaches by shelling out to gdb.** When that fails you get gdb output
  (`No symbol table is loaded`, `ptrace: Inappropriate ioctl`) rather than a clean Python error, so
  read the last lines before concluding your breakpoints are wrong.
- **Start python under debugpy with `-Xfrozen_modules=off`** — otherwise the first thing you see is a
  warning that frozen modules may make it miss breakpoints. It is harmless in most cases and
  confusing in all of them: `python -Xfrozen_modules=off -m debugpy --listen 5678 script.py`.
- **`--wait-for-client` before `-m module` is what lets you debug module startup.** Without it the
  module is already imported and running by the time an editor attaches, so nothing in it can break.
- **`q` on a live session kills the program.** pdb asks `Quit anyway? [y/n]` when the process is
  running; in post-mortem the program has already exited, so quitting just leaves you. Answer it
  rather than assuming it hung.

## Attaching to a process you cannot restart

```bash
# start it with the debugger listening, and block until an editor connects
python -Xfrozen_modules=off -m debugpy --listen 127.0.0.1:5678 --wait-for-client app.py

# or inject the debugger into a process that is already running (needs permission, see Gotchas)
python -Xfrozen_modules=off -m debugpy --listen 127.0.0.1:5678 --pid 12345
```

Once it prints that it is listening, attach your editor to `127.0.0.1:5678` (DAP) and breakpoints
behave normally. Two cautions that matter on a shared or remote host: `--listen 0.0.0.0:5678` exposes
the port to the network, and **anyone who can connect to that port can execute arbitrary code inside
the debugged process** — keep it on localhost or tunnel it. To launch without waiting for a client,
drop `--wait-for-client`.

`debugpy` installs with `pip install debugpy`. `pdb` is in the standard library — nothing to install.

## Reading a debugger session without watching it

Anything you type can be piped in, which makes a debug run reproducible and scriptable:

```bash
printf 'b app.py:118\nc\np payload\nw\nc\n' | python -m pdb app.py
```

The output is the transcript, so this is a reasonable way to capture state from a machine you are not
sitting at. Expect a `Quit anyway? [y/n]` prompt if the run ends while stopped.

## Related skills

- **Which bug to chase, and why the obvious fix is usually wrong** — the `systematic-debugging` skill.
  Use it to find the failing path; use this one to look inside it.
- **Turning the reproduction into a permanent test** — the `test-driven-development` skill. A debugger
  session that proved the cause should end as a test that fails without the fix.
- **The Node.js counterpart** — the `node-debugging` skill: probe mode, the `debug>` REPL, attaching
  to a process that is already running.
