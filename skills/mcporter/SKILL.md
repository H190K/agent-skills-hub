---
name: mcporter
description: Use when driving MCP servers from the shell — list tools, call one tool once (stdio or HTTP), read resources, complete or seed OAuth, bridge servers behind one `mcporter serve` endpoint, record/replay MCP traffic, or emit typed clients. Covers selector syntax, argument styles, the config-file stdio-cwd gotcha, exit-code behavior, and daemon/keep-alive wiring.
version: 1.0.0
author: adapted from the openclaw mcporter skill (OpenClaw Foundation, MIT; verified against openclaw/mcporter's own docs and CLI)
license: MIT
platforms: [linux, macos, windows]
---

# McPorter — drive MCP servers from the shell

## Overview

MCPorter (`mcporter`) is a Node CLI and runtime for discovering, inspecting, and calling
Model Context Protocol servers without writing harness code: one-shot `call`s, resource
reads, OAuth flows, an aggregate bridge over daemon-managed keep-alive servers, generated
stand-alone CLIs, and TypeScript type emission. Every behavior below is stated only where
it was measured against the real CLI or read from its `--help`; install it and re-measure
anything version-specific with `mcporter -h` / `mcporter <command> -h` before relying on it.

## Install

```bash
npx mcporter --version        # try it first
brew install steipete/tap/mcporter
# or
npm install -g mcporter       # requires Node >= 24
```

Gotcha (npm installs): the package declares `engines.node >= 24` **and** `devEngines`, so
npm refuses it on older runtimes (`EBADDEVENGINES Invalid devEngines.runtime`). The runtime
code itself still executes on older Node — a one-shot `npm install mcporter
--force --engine-strict=false` into a project directory beats the installer check. `npx`
respects devEngines; prefer the already-installed global or the project-local binary for
probes instead of re-running npx and hitting the same wall.

## List what a server offers

```bash
mcporter list                          # every configured server: auth status, transport, tool count
mcporter list --json                   # machine-readable summary
mcporter list myserver                 # TypeScript-style signatures + doc comments per tool
mcporter list myserver --schema        # adds raw JSON schemas under each signature
mcporter list myserver tool_name --schema     # one tool only
mcporter list https://mcp.context7.com/mcp --brief   # ad-hoc HTTP server, compact signatures
```

- `--brief` (alias `--signatures`) prints compact signatures only; it cannot combine with
  `--json`/`--schema`/`--verbose`/`--all-parameters`.
- Truncated signatures hide optional parameters beyond the second and print a footer
  `Optional parameters hidden; run with --all-parameters to view all fields.` — pass
  `--all-parameters` whenever a call fails on a "missing" field.
- Hidden aliases (measured, not advertised): `mcporter describe <server>` equals
  `mcporter list <server>`; `mcporter list-tools` equals `mcporter list`.
- Exit codes: a dead server prints a dim `(server appears offline)` line but **exits 0**.
  Health gates only fail on demand: `--exit-code` (prints the diagnosis, exits 1) or
  `--quiet` (silence plus implied `--exit-code`). Gating scripts on a bare `mcporter list`
  always returns success.

## Call a tool

Selectors: `server.tool`, or the tool's full HTTP URL (`https://host/mcp.getWidget`), or a
bare tool name after an ad-hoc server flag.

```bash
mcporter call server.tool key=value other:5            # flag-style arguments
mcporter call 'server.tool(a: "x", b: 2)'              # function-call style, single-quoting
mcporter call server.tool --args '{"key": "value"}'    # JSON payload
echo '{"key": "value"}' | mcporter call server.tool --args -   # JSON from stdin
mcporter call --stdio "python3 fix.py" toolname key=val       # ad-hoc stdio server
mcporter call server.tool --output json                # text | markdown | json | raw
```

Argument mechanics (all measured):

- `key=value`, `key:value`, `key: value`, `--key value`, and `key:=value` map to the same
  named arguments; long-flavored keys convert kebab-case to camelCase
  (`--save-to-drafts true` arrives as `saveToDrafts: true`).
- Coercion is schema-aware: `id=12345.678` against a `string` schema arrives as the
  `"12345.678"` string it is typed as, while `n=2.5` against a `number` arrives as a
  float. `--raw-strings` forces strings for all flag/positional values (message-like IDs
  such as `thread_ts=1234567890.123456`), and `--no-coerce` disables coercion entirely.
- `key=@file` reads a UTF-8 file value, strings only, no coercion — and it does **not**
  strip a trailing newline. For a clean string value, printf the file without the final
  `\n` or send the exact literal instead.
- Values after `--` are literal positionals; but positional mapping is schema-bounded and
  overshoot errors clearly: `Too many positional arguments (2) supplied; only 1 parameter
  remain on <tool>`. Count the tool's required/optional positions before relying on
  position.

Failure semantics (measured):

- A tool that returns an `isError: true` result prints the error envelope and **exits 0** —
  inspect the output (or use `--output json` and look for `isError`), never the exit code.
- A protocol-level failure (`Tool x not found`, transport closed, auth) exits 1.
- Misspelled tools: within Levenshtein distance `max(2, floor(len × 0.3))` (or case/punct
  differences) the CLI retries itself and prints
  `[mcporter] Auto-corrected tool call to server.echo (input: server.ech).`; larger typos
  keep the failure but print `[mcporter] Did you mean server.echo?`. The correction only
  inspects the catalog when the server replied with a real `Tool … not found` **error** —
  a server that returns "not found" as a normal error *result* defeats the heuristic.
  The same heuristic corrects server-name typos in `list` and `auth`.

The generic long-flag forms get validated against the selected tool's schema before
dispatch — an undeclared flag fails with guidance to use `key=value` or `--args` instead.

## Configure, or don't

MCPorter reads `./config/mcporter.json` in the working directory, then the system file
`~/.mcporter/mcporter.json`, then imports definitions from editor MCP clients it knows
(Cursor, Claude Desktop, Codex, OpenCode, VS Code, Windsurf — the tool's own import
feature, not a requirement on any of them). Both files accept JSONC and env placeholders
(`$env:VAR` as a whole value, or `${VAR}` / `${VAR:-fallback}` inside values; the
`${env:VAR}` spelling some clients use is explicitly rejected with the alternatives).

```bash
mcporter config add myserver https://host/mcp            # defaults write ./config/mcporter.json
mcporter config add myserver "python3 /abs/path/server.py" --yes   # stdio server, absolute path
mcporter config get myserver --json                      # inspect the stored definition
mcporter config list --json                              # merged view incl. imported servers
mcporter config import cursor --copy                     # seed from an editor client's config
mcporter config doctor                                   # validate both config surfaces
```

The stdio working-directory gotcha (measured on 0.14.3): a **relative** command saved by
`config add --stdio` executes with its working directory set to the directory *containing
the config file*, not the directory you invoked `mcporter` from — `python3 fix.py` saved
from that parent directory resolves inside the `config/` folder and fails to start.
`--cwd` on the add did not override it; the `--root` global changes where configuration is
discovered, not where the command runs. Use absolute paths (or `cd`-stable commands) in
saved stdio definitions and keep ad-hoc `--stdio` flags for relative scripts.

A missing `--config <file>` target fails with a raw ENOENT stack — the CLI surfaces the
underlying error rather than a friendly message; check the path itself first.

## Auth and OAuth

```bash
mcporter auth myserver                       # OAuth only, no tool listing
mcporter auth myserver --no-browser          # print the authorization URL (alias: --browser none)
mcporter auth myserver --reset               # clear cached credentials first
MCPORTER_OAUTH_NO_BROWSER=1 mcporter auth ...  # same via environment
mcporter vault set myserver --stdin          # seed tokens non-interactively (see payload below)
mcporter vault clear myserver                # remove the stored entry
```

Vault payload (from `mcporter vault -h`):
`{"tokens": {"access_token": "...", "token_type": "Bearer"}, "clientInfo": {"client_id": "..."}}`.
`vault set` stores to `~/.mcporter/credentials.json`.

Headless OAuth (upstream known-issues, unmeasurable without an OAuth server here): any
`auth` run keeps a loopback callback listener alive until the browser redirects back, so
running it through a short-lived process group can print the URL and then reap the
listener, losing the tokens. Run headless OAuth from a persistent terminal, `tmux`, or a
supervisor, or with a configured `oauthRedirectUrl`/loopback tunnel when the browser is on
another machine. Hosted servers that reject dynamic client registration fail fast;
per-provider fixes live in `oauthClientId`/`oauthClientSecretEnv` server fields.

## The aggregate bridge: keep-alive servers, daemon, serve

Server definitions marked `"lifecycle": "keep-alive"` stay running across calls under a
single user daemon:

```bash
mcporter daemon start | status | stop        # socket lives at ~/.mcporter/daemon/user.sock
mcporter serve --stdio                       # expose keep-alives as ONE MCP server (stdio)
mcporter serve --http 3000                   # /mcp aggregate + /mcp/<server> raw views
```

Measured behavior (v0.14.3):

- The daemon itself owns nothing: `daemon status --json` reports `configPath: ""` and an
  empty `servers` list even when your local config has keep-alives. Clients register
  their own view of servers at connect time; the host just serves them. Empty daemon
  status is normal.
- `serve --stdio` answers `initialize` immediately with the aggregate identity —
  `serverInfo.mcporter-serve` and the instruction that tool names are namespaced
  `server__tool` (`demo2__echo`), descriptions prefixed `[server]`.
- One unhealthy keep-alive entry poisons the bridge: an aggregated `tools/list` fails with
  `MCP operation failed (CONNECTION_CLOSED); the request was not replayed.` when a single
  selected server cannot start, even though direct `call`s to a healthy sibling work.
  Restrict the bridge (`--servers healthy_alias`) or health-gate the config
  (`mcporter list --exit-code`) before exposing it.
- Bridged `tools/call` routes through the daemon and returns the tool result.

## Codegen, types, record/replay

```bash
mcporter generate-cli myserver --bundle dist/my.js  --runtime node   # stand-alone CLI
mcporter generate-cli myserver --compile dist/my-bin                 # Bun-compiled binary
node dist/my.js tool-name --some-flag value                          # kebab-case flags in the generated CLI
mcporter emit-ts myserver --mode types  --out my.d.ts                # types only
mcporter emit-ts myserver --mode client --out my-client.ts           # interface + createServerProxy factory
mcporter record mysession -- mcporter call server.tool key=val       # capture NDJSON traffic
mcporter replay mysession -- mcporter call server.tool key=val       # determinism check
```

- `generate-cli` bundles with Rolldown (or Bun) into a single runnable artifact; the
  generated CLI maps tool parameters to kebab-case long flags and worked end-to-end
  against a stdio server in the same run that measured it.
- `emit-ts` works offline from cached discovery and stamps the file with the generating
  mcporter version, server name, and transport — useful provenance for typed clients.
- `replay` verifies determinism by matching outgoing requests **byte-for-byte** against
  the recording: different arguments fail with `Replay mismatch for server 'demo':
  request tools/call {"name":"echo","arguments":{"text":"new"}} did not match next
  expected recv tools/call {"name":"echo","arguments":{"text":"old"}}`. Only identical
  invocations pass — use it to prove a change did not alter traffic, not as a
  parameterized test runner.

## Smoke-test an MCP server with a hand-rolled fixture

Before trusting a new stdio server (or your own), verify its transport with a
minimal fixture client — JSON-RPC over newline-delimited stdio, no SDK needed:

```python
# fix_probe.py — drive an MCP stdio server through initialize + tools/list + one call
import json, subprocess, sys

def rpc(stdin, method, params=None, rid=None, note=False):
    m = {"jsonrpc": "2.0", "method": method}
    if rid is not None: m["id"] = rid
    if params is not None: m["params"] = params
    stdin.write((json.dumps(m) + "\n").encode()); stdin.flush()

p = subprocess.Popen(sys.argv[1:], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
rpc(p.stdin, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
    "clientInfo": {"name": "probe", "version": "0.0.1"}}, rid=1)
print("initialize:", json.loads(p.stdout.readline())["result"]["serverInfo"])
rpc(p.stdin, "notifications/initialized")                     # no response expected
rpc(p.stdin, "tools/list", {}, rid=2)
print("tools:", [t["name"] for t in json.loads(p.stdout.readline())["result"]["tools"]])
rpc(p.stdin, "tools/call", {"name": "echo", "arguments": {"text": "hi"}}, rid=3)
print("call:", json.loads(p.stdout.readline()))
p.terminate()
```

Drive it against the server under test (`python3 fix_probe.py python3 server.py`), then
hand the same absolute command to mcporter for the fuller check:
`mcporter list --stdio "python3 /abs/path/server.py" --schema` confirms what the server
advertises before a full agent run.

## Cross-checking and sources

- Re-verify flags per release: `mcporter -h` lists every command; `mcporter <command> -h`
  prints that command's flags. Note the asymmetry (measured): `mcporter list --help`
  prints the **root** help and exits 1 — after a subcommand, only `-h` shows command help.
- `daemon` has no `-h` (fixed subcommands only: `start`, `status`, `stop`, `restart`).
- Hidden aliases (`describe`, `list-tools`, `--sse`, `--insecure`) parse but are
  deliberately unadvertised; never assume they were removed just because help omits them.
- The project docs cover config precedence, protocols (`2026-07-28` negotiation plus a
  legacy fallback), the daemon, and known hosted-OAuth gaps.

## Related

- `mcporter serve --http` output feeds any MCP client that consumes Streamable HTTP.
- In repo: `verification-before-completion` (run the smoke recipe before declaring an MCP
  integration done) and `background-coding-agents` (run mcporter calls in isolated
  worker worktrees with per-worker environment isolation).