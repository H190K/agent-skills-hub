---
name: trace-mcp
description: Use when an agent needs precomputed code intelligence over a repo without reading files — symbol search, file outlines, call/import graphs, test coverage, change-impact analysis, quality gates, security scans — via the trace-mcp MCP server (stdio). Covers registration, the presets/deferral tool surface, the load-tools-then-batch call doctrine, symbol-id format, and the silent full/standard preset failure.
version: 1.0.0
author: H190K (original; upstream Nikolai Vysotskyi/trace-mcp, MIT; behavior verified live)
license: MIT
platforms: [linux, macos, windows]
---

# Trace — precomputed code intelligence, served over MCP

## Overview

`trace-mcp` indexes a repository into a local SQLite code graph (files, symbols,
import/call/test-cover edges, coupling snapshots per commit) and serves that graph over
MCP so an agent can *ask* instead of *read*: symbol search, outlines, call graphs,
coverage, change-impact, security and quality answers in one tool call. Its server
describes itself (measured, 3.38.0): *"Precomputed code graph for AI agents … served
instead of raw file reads. Not a distributed-tracing or logging server."*

Every behavior below was measured against a real installed build ([nikolai-vysotskyi/trace-mcp](https://github.com/nikolai-vysotskyi/trace-mcp),
`npm i -g trace-mcp`, v3.38.0, Node 22; upstream MIT) on a 4-file fixture; re-measure
version-specific claims with `trace --help` and a `tools/list` before relying on them. This
skill is original text from the observed binary, not upstream documentation.

## Install

```bash
# requires Node >= 22 (package engines: ">=22.0.0")
npm install -g trace-mcp
trace --version          # trace & trace-mcp are two bins from the same dist/cli.js
```

Gotchas (measured, npm 12 + v3.38.0):

- **npm blocks the package's native postinstalls by default** (`npm warn install-scripts`
  for `@parcel/watcher`, `onnxruntime-node`, `protobufjs`). The core verify path works
  regardless: `add`, `index`, `serve` (stdio), `check`, `scan-security` all ran fine on a
  script-blocked install. The watcher builds when allowed:
  `npm config set allow-scripts=trace-mcp,@parcel/watcher,onnxruntime-node,protobufjs --location=user`
  then re-run `npm i -g trace-mcp`.
- **One telemetry ping per day by default** (anonymous: version, OS, client, counts). Disable
  with `TRACE_MCP_TELEMETRY=off` env, or `telemetry.usage_ping: false` in `~/.trace/.config.json`.
- First run creates its data home in `~/.trace/` (`.config.json`, `registry.json`,
  `index/*.db`, `decisions.db`, `topology.db`, `activity.db`, `sessions/`, daemon files).
  Some printed help strings say `~/.trace-mcp/...` — that path does not exist; the actual
  home is `~/.trace/`.

## Register and index

```bash
cd your-repo
trace add . --json       # detect root, create DB, register, index immediately
trace list               # registered projects + DB health + last indexed
trace index -f .         # full reindex (plain `trace index [dir]` = incremental)
trace doctor             # registry/DB integrity + competing-tool check
trace prune              # audit index DBs — dry-run by default, --apply to delete
trace remove . --force   # unregister + delete DB (see gotcha below)
```

Measured on a 4-file fixture: `add --json` reported `status: registered`, the DB path
`~/.trace/index/<name>-<8-hex>.db`, and indexing stats (files indexed/skipped/errors,
durationMs) plus resolved edges — ES-module imports, TS/JS call edges, `test_covers`
edges, coupling snapshots keyed to the current commit SHA. The per-project config file is
`.trace-mcp.json` (its error help suggests `include`/`exclude` globs there).

Gotchas:

- `trace remove` prompts interactively (default answer **No**); pass `--force` for scripts.
  `--keep-db` unregisters while keeping the DB; `--json` for machine output.
- `trace prune` is dry-run by default — a script that intends deletion needs `--apply`.
- `trace add` fails-closed on overlaps unless `--allow-overlap` (a registered root that
  contains, or is contained by, another registered root).

## Wire the MCP server

Stdio transport: `trace serve`. Register it in any MCP client with a generic config:

```json
{
  "command": "trace",
  "args": ["serve"],
  "env": { "TRACE_MCP_TELEMETRY": "off" }
}
```

The vendor ships `trace init` / `trace setup-hooks` for one-time global setup against its
own list of MCP clients, hooks and instruction files — run `trace init --dry-run` first
and use its `--skip-mcp-client` / `--skip-hooks` / `--skip-claude-md` / `--skip-app`
skips to keep it from writing to agent configs. Nothing here requires it: `serve` works
as a plain stdio server.

One-shot drive (works for probes and CI):

```bash
printf '%s\n%s\n%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0.0.1"}}}' \
 '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
 | timeout 60 trace serve
```

Measured: `serverInfo` = `{name: "trace", version: "3.38.0", title: "Trace — Code Intelligence"}`;
the server shuts down cleanly on `stdin-end` (its log says so). For a deterministic
local-only session (no background daemon), set `TRACE_MCP_NO_DAEMON=1`.

## Tool surface: presets and the deferral gate

`tools/list` on the default preset (29 tools, measured) includes the always-on core:
`search`, `search_text`, `get_outline`, `get_symbol`, `get_call_graph`, `find_usages`,
`get_change_impact`, `get_context_bundle`, `get_coverage_report`, `get_diagnostics`,
`get_feature_context`, `get_task_context`, `suggest_queries`, `get_index_health`,
`get_project_map`, `get_preset_info`, plus meta/infra: `batch`, `load_tools`,
`plan_turn`, `get_session_*`, `remember_decision`/`query_decisions`/`invalidate_decision`,
`register_edit`, `get_real_savings`, `get_usage_trends`.

Presets (`--preset` on `serve`, or env `TRACE_MCP_PRESET=...`, or config
`tools.preset`), tools measured in `tools/list` on the same session:

| preset       | tools/list measured |
|--------------|---------------------|
| default/minimal | 29 |
| router       | 10 (meta-only: batch, plan_turn, load_tools, preset/savings/analytics info) |
| state        | 20 |
| design       | 21 |
| perf         | 35 |
| security     | 36 |
| review       | 33 |
| dev          | 44 |
| architecture | 42 |
| standard     | **no response** |
| full         | **no response** |

Gotchas (all measured, v3.38.0):

- **`full` and `standard` presets never answer `tools/list`** — silently, no error logged,
  through *both* the flag and the env channel, while every other preset answers in the
  same one-shot drive. Treat `standard`/`full` as broken in this version; use a working
  preset + deferral (below) instead.
- `get_preset_info` reports its own `toolCount` numbers (minimal 20, standard 52, review
  24, ...) — these *disagree* with `tools/list` on every preset, because always-on infra
  tools (`batch`, session analytics, decision memory, ...) ride along in every preset.
  Trust the measured `tools/list`, not the advertised count.
- The default preset carries **~134 deferred tools**. `get_preset_info` lists them
  (`deferred_tools`): `reindex`, `embed_repo`, `verify_index`, `repair_index`,
  `get_related_symbols`, `get_tests_for`, `get_implementations`, `get_api_surface`,
  `get_type_hierarchy`, `get_import_graph`, `get_untested_symbols`, `get_dataflow`,
  `taint_analysis`, `generate_sbom`, `apply_rename`, `remove_dead_code`, `graph_query`,
  `traverse_graph`, `get_code_owners`, `get_dead_code`, `scan_security`,
  `detect_antipatterns`, `predict_bugs`, session/decision/memory tools, ... (list from
  `load_tools` with no arguments).

### The call doctrine: load_tools, then batch

Deferred tools behave differently from always-on tools (all measured):

1. `tools/call` on a deferred tool that was not loaded: JSON-RPC error
   `-32601 "Tool ... is not available in this session's tool preset"`.
2. `tools/call` `load_tools` with `{"tools": ["get_import_graph", "get_tests_for"]}`
   (or `{"preset": "review"}`) answers `{"loaded": [...], "deferred_tools": [...],
   "hint": ...}`.
3. Even after `load_tools` replies **loaded**, a *direct* `tools/call` of that tool still
   fails `-32601`, and `tools/list` still shows 29 tools — the activation is visible to the
   server's router, not to the standard tool surface.
4. **The working path is `batch`**: call the activated tool through `batch`'s
   `calls` array. This also works for always-on tools — it is the one reliable round-trip
   mechanism in a one-shot or tool-list-caching client.

```json
{"jsonrpc":"2.0","id":10,"method":"tools/call","params":{
  "name":"batch","arguments":{"calls":[
    {"tool":"get_import_graph","args":{"file_path":"src/index.js"}},
    {"tool":"get_outline","args":{"path":"src/utils/orders.js"}}
  ]}}}
```

Measured `batch` response: `{"batch_results":[{"tool":"get_import_graph","result":{...}},
{"tool":"get_outline","result":{...}}],"total":2}` — import graph rows carry
`source`/`target`/`specifiers`.

Validation nuance worth knowing: invalid arguments fail *before* the availability gate, so
a wrong-args call to a disabled tool returns a zod argument error (e.g. `expected string,
received undefined at file_path`) instead of `-32601`. Do not read that as success — fix
the args and mind the gate (3).

## Core queries that work as advertised

Symbol ids have the form `path/file.ts::Name#kind` (e.g.
`src/index.js::checkout#function`; a JS module body is `...::__module__#namespace`). Get
them from `search` or `get_outline` first.

- `search` `{"query":"createOrder"}` — full-text over **symbol names/signatures**. Measured:
  returns `items[]` with `symbol_id`, `kind`, `signature`, `file:line`, `score`,
  `_freshness`, plus a verdict. A natural-language query (`"order total discount"`) returns
  zero items with `verdict:"not_found"` and an anti-retry suggestion ("Do not retry with
  similar terms … use fuzzy=true or use search_text"). Sub-word fuzzy is on by default to a
  degree: searching `discount` still hit `apply_discount`.
- `search_text` `{"query":"MAX_ITEMS"}` — raw content match: per-file `hits[]` with
  `line`, `column`, `context` (the matched line prefixed `> 3:`), `language`, totals, and
  `truncated`/`timed_out` flags.
- `get_outline` `{"path":"src/index.js"}` — symbols of one file: `symbolId`, `kind`,
  `signature`, `lineStart`/`lineEnd`; freshness metadata and a batch optimization hint.
- `get_symbol` `{"symbol_id":"src/utils/orders.js::createOrder#function"}` (or `fqn`);
  `get_call_graph` `{"symbol":"src/index.js::checkout"}` — errors are structured:
  `{"error":{"code":"NOT_FOUND","message":"'unknown' is not in the index","help":"Symbol
  IDs have the form `path/to/file.ts::Name#kind` …"}}`. `NOT_FOUND` and
  `VALIDATION_ERROR` are the codes to expect; help strings point at the right next step.
- `get_change_impact`, `find_usages`, `get_coverage_report` (`test_covers` edges),
  `get_diagnostics`, `get_context_bundle` — same pattern: locate a symbol via `search`,
  then query.

## CLI utilities beyond the server

- `trace check` — quality gates against the index; **exit 0 = pass, 1 = fail** (the only
  CI-friendly exit contract measured). Defaults on the fixture printed four gates
  (cyclomatic complexity 3 ≤ 30, circular imports 0, tech-debt grade D ≤ D, security
  critical findings 0) and `Result: PASS`.
- `trace scan-security` — OWASP-style scan; JSON out (`files_scanned`, `findings[]`,
  `summary` by severity, `suppressed_low_confidence`).
- `trace ci-report` — change-impact report for a PR/branch. `trace benchmark [path]` —
  token-waste estimator. `trace savings` — measured token-savings ledger (needs ~25
  instrumented calls before it reports).
- Daemon: `trace daemon start|stop|restart` (hidden from `--help`; it appears in the
  auto-spawn log line). Stdio sessions auto-spawn a background daemon by default; a
  daemon run measured `node .../bin/trace-mcp serve-http --port 3741` at ~341 MB RSS.
  `trace daemon stop` also sweeps stray daemons **and disables auto-spawn** ("stdio
  sessions will run local-only ... Re-enable with daemon start").
- `trace upgrade` — runs migrations + reindex after an npm version bump.

## Gotchas, consolidated

1. `full`/`standard` presets: `tools/list` never returns (silent) in 3.38.0 — avoid.
2. Deferred tools: direct `tools/call` fails `-32601` even after `load_tools` says loaded —
   call them through `batch`, and do not trust `tools/list` to grow.
3. `preset_info` `toolCount` ≠ measured `tools/list` on every preset.
4. `search()` is symbol-keyword search, not semantic search — natural-language queries
   return a `verdict: not_found` with an explicit do-not-retry suggestion; use
   `search_text` for content, `fuzzy: true` for loose symbol names. (Embedding-based
   features exist — `embed_repo`, `check_embedding_drift` in the deferred list — but were
   not measured on the script-blocked install.)
5. Native postinstalls are script-gated by npm 12; core flow works without them, but
   plan for the allow-scripts set when a feature needs them.
6. Config/data home is `~/.trace/`; strings naming `~/.trace-mcp/` are stale. The CLI's
   top banner ("for Laravel/Vue/Inertia/Nuxt") is also stale relative to the package's own
   description (88 framework integrations, 81 languages).
7. `trace remove` prompts (default No) — `--force` in scripts; `trace prune` is dry-run
   until `--apply`; `check`/`scan-security` are safe read-only.

## Cleanup

```bash
trace remove . --force   # per project
trace daemon stop        # kill the daemon + stop auto-spawn
npm rm -g trace-mcp      # remove the binary
```

`~/.trace/` holds the remaining state (registry, config, DBs); delete it manually if a
full reset is wanted (the uninstall leaves it in place).

## See also

`skills/mcporter` — drive this (or any) MCP server from the shell with one-shot calls and
selector syntax instead of hand-rolled JSON-RPC.