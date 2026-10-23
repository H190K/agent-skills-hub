---
name: oracle
description: Use when a second model should review a diff, debug a stubborn failure, pressure-test a design, or sanity-check a refactor — install and drive @steipete/oracle, a CLI that bundles your prompt plus selected repo files into a one-shot ChatGPT/OpenAI/Gemini/Claude request.
version: 1.3.1
author: adapted from steipete/oracle (Peter Steinberger, MIT)
license: MIT
platforms: [linux, macos, windows]
---

# Oracle CLI — second-model review with real repository context

## Overview

You are a second opinion, not the decision. Oracle takes one prompt plus an
explicit file set and sends them as a single one-shot request to another model —
through the OpenAI API, or by automating a signed-in ChatGPT/Gemini web session.
The reply comes back with real file context, so the answer is about *your* code,
not a hypothetical one.

**Core rule:** treat output as advisory — each claim is a review finding to be
checked against the code and tests, not an instruction to obey. The
`code-review-reception` skill is the standard for weighing it.

## Install and check availability

```bash
npm install -g @steipete/oracle   # requires Node >= 24; or run ephemeral: npx -y @steipete/oracle
oracle --version
```

- Without a global install, prefix every command with `npx -y @steipete/oracle`.
- Default target is `gpt-5.5-pro`. If you omit `--engine`, Oracle still picks a
  route — `ORACLE_ENGINE` env (or the `engine` setting in Oracle's config)
  first, then `api` when `OPENAI_API_KEY` is set, otherwise the browser engine
  (automated ChatGPT/Gemini web). Pass `--engine` explicitly whenever the
  default is not what you want: an omitted engine is a route choice, not a
  neutral one.
- `oracle doctor` and `oracle doctor --providers` report provider readiness and
  routing without printing secrets.

## Golden path

1. Pick the smallest file set that still contains the truth.
2. Preview the payload and token spend with `--dry-run summary --files-report`.
   `--dry-run` takes `summary` (default), `json` or `full`; `full` prints the
   resolved route plus the exact composer JSON and text that would be sent.
3. Send the real run; give it a memorable `--slug`.
4. If it detaches or times out, **reattach to the stored session — never re-run**.

```bash
# 1. Preview — no tokens, no model call
oracle --dry-run summary --files-report -p "<task>" --file "src/**" --file "!**/*.test.*"

# 2. Browser run (no API key needed; long-running is normal for Pro tiers)
oracle --engine browser --browser-manual-login --browser-thinking-time extra-high \
  -p "<task>" --file "src/**" --slug "auth-review"

# 3. API run (explicit consent path — may incur usage cost)
oracle --engine api --model gpt-5.5-pro -p "<task>" --file "src/**" --slug "auth-review"
```

## Attaching files (`--file`)

`--file` accepts files, directories, and globs; pass it multiple times or
comma-separate entries. Prefix a pattern with `!` to exclude.

```bash
oracle ... --file "src/**/*.ts" --file "!src/**/*.test.ts" --file docs/adr
```

Measured behavior (v0.21.4):

- Globs honor `.gitignore` and do not follow symlinks.
- Files over 1 MB are rejected with a hard error listing the offenders; raise
  the cap via `ORACLE_MAX_FILE_SIZE_BYTES` or `--max-file-size-bytes` only when
  a large fixture is genuinely needed.
- A pattern that matches nothing aborts before any model call with
  "No files matched the provided --file patterns" — a misspelled glob costs
  nothing, but check the spelling anyway.
- Dotfiles need an explicit dot-segment in the pattern, e.g. `--file ".github/**"`.
- Keep total input under ~196k tokens — `--files-report` shows the per-file spend
  before you commit. Never attach `.env`, keys, or tokens; redact first.

## Engines and model selection

- Auto-pick: API when `OPENAI_API_KEY` is set, otherwise the browser engine.
  Browser works for GPT (ChatGPT web) and Gemini (gemini.google.com cookie
  mode); Claude and Grok models are API-only — the full API target list is in
  `oracle --help --verbose`.
- Model families currently supported: GPT-5.5/5.4/5.2/5.1, GPT-5.6, Gemini 3.x,
  Claude 4.x; the default is `gpt-5.5-pro`.
- `--browser-thinking-time <level>` sets picker effort for Thinking/Pro browser
  targets: `light, standard, extended, extra-high, pro, heavy` (the ChatGPT UI
  aliases `instant, medium, high, xhigh` also parse). In v0.21.4–v0.21.5 the flag
  is hidden from *both* `--help` and `--debug-help`; from v0.21.6 through
  v0.22.0 it is listed in
  `--debug-help` (with the level names printed inline) while staying out of plain
  `--help`. The accepted list also surfaces in the fail-closed error a bad value
  provokes — an invalid value costs nothing to send, so probe with one to see the
  list (the string is identical in v0.21.5 and v0.21.6:
  `Thinking time must be one of "light", "standard", "extended", "extra-high",
  "pro", "heavy", or a ChatGPT UI alias like "instant", "medium", "high", or
  "xhigh".`).
- Flags that joined `--debug-help` with v0.21.6, for long browser waits and
  synced/fiddly Chrome setups: `--browser-attachment-timeout`,
  `--browser-max-concurrent-tabs <n>` (soft limit per manual-login profile,
  default 3), the cookie plumbing (`--browser-cookie-names`,
  `--browser-inline-cookies <jsonOrBase64>`, `--browser-inline-cookies-file
  <path>`, `--browser-allow-cookie-errors`), and
  `--browser-manual-login-profile-dir <path>`. The recheck/reattach family
  (`--browser-recheck-delay`, `--browser-recheck-timeout`,
  `--browser-reuse-wait`, `--browser-auto-reattach-*`) predates this release —
  read `--debug-help` on the installed version for the full current list.
  v0.22.0 adds `--browser-no-focus` / `--no-browser-no-focus` (keep Chrome in
  the background during launch, new tabs, and send — or let it come forward).
- `--browser-research search|deep` activates Web Search / Deep Research in the
  browser conversation; only when explicitly wanted.
- API preflight before a paid run:
  `oracle doctor --providers --models gpt-5.4,claude-4.6-sonnet` then
  `oracle --route --model gpt-5.4`.

## Provenance — requested vs. delivered

A consult is worth keeping only if the record says what actually ran. Report
the request and the delivery separately:

- Requested: engine, model, effort (`--browser-thinking-time`), files.
- Observed: the resolved route, session id, the effective picker target, and
  any deviation from the request.
- Anything unobserved is unknown, not satisfied.

Measured trap (v0.21.4, re-verified unchanged through v0.22.0): `--dry-run full` in
browser mode resolves `target=GPT-5.5` for `--model gpt-5.5-pro` — a requested
model maps to a *picker target*, and a picker label only proves UI selection,
not what the server executed. A preview's predicted route is likewise not
execution evidence, and a completed answer cannot prove an effort constraint on
its own. Never silently reduce a requested model or effort to fit the route: if
the route cannot honor the request, say so and stop.

## Sessions: reattach, never duplicate

Browser and Pro API runs detach often — the CLI may exit while the run continues
remotely. Sessions are stored under `~/.oracle/sessions` (override with
`ORACLE_HOME_DIR`).

```bash
oracle status --hours 72 --limit 50   # list recent runs
oracle session <id> --render          # attach: streams the saved transcript
```

- Duplicate-prompt guard: a new run with the same prompt while one is still
  active is blocked. `--force` exists for genuinely fresh identical runs —
  prefer reattaching.
- Multi-turn: `--followup <sessionId|responseId>` continues a stored run;
  `--browser-follow-up "<prompt>"` adds turns inside one browser conversation.
- Timeout: `--timeout 10m` sets an overall deadline; auto is 60m for Pro models.

## Prompt template

Oracle starts with **zero** project knowledge — nothing about your stack,
build commands, conventions, or "obvious" paths. A low-effort prompt gets a
generic answer. Include:

- Project briefing: stack, services, build/test commands, platform constraints
- Where things live: entrypoints, configs, key modules, boundaries
- The exact question, prior attempts, and verbatim error text
- Constraints: "keep the public API", "don't touch the migration"
- Desired output: "patch plan + tests", "three options with tradeoffs"

For a long investigation, write the prompt so it is *restorable*: a 6–30
sentence briefing at the top, reproduction steps and errors in the middle, the
full context file set at the bottom. Runs are one-shot — "restoring context"
means re-running with the same prompt + files (or reattaching a live session).

## Manual-paste fallback

When browser automation is not available (headless box, no Chrome), build the
bundle anyway and paste it into any chat UI by hand:

```bash
oracle --render --copy -p "<task>" --file "src/**"
```

`--copy` is a hidden alias for `--copy-markdown`; it copies the assembled
markdown bundle to the clipboard and prints the token count. Note `--render`
cannot combine with `--dry-run` (hard conflict), and `--write-output <path>`
captures the final assistant message to a file for automation.

## Multi-model panels

Run the same question past several models in one call and compare:

```bash
oracle --models "gpt-5.5-pro,gemini-3-pro" --allow-partial --write-output review.md -p "<task>" --file "src/**"
```

`--allow-partial` exits 0 when at least one model succeeds and writes
per-model outputs (`review.md` plus `review.<model>.md` files).

## Through MCP

The package ships a second binary, `oracle-mcp`, a stdio MCP server. Two
helpers print ready-made wiring snippets for two of the coding agents:
`oracle bridge codex-config` (Codex CLI MCP config) and `oracle bridge
claude-config` (Anthropic's claude CLI `.mcp.json`); `oracle bridge
doctor` checks the browser bridge first. From v0.22.0, `oracle bridge
--help` lists these subcommands; on 0.21.6 they run but are unlisted
(the help shows only `host`, whose counterpart `client` points a box at a
remote oracle host).

Its `consult` tool mirrors the CLI flags — schema measured in v0.21.4:

- `engine` (`api` | `browser`) and `model` behave like the CLI flags; `models`
  fans out (API only).
- Browser-only controls ride on the call: `browserThinkingTime`,
  `browserAttachments` (`auto|never|always` — `always` uploads real files,
  `never` pastes contents inline), `browserArchive` (`auto|always|never`),
  `browserModelLabel`, `browserModelStrategy`, `browserResearchMode`
  (`search|deep`), `browserFollowUps`.
- `dryRun: true` previews; `waitForCompletion: false` detaches and returns a
  `sessionId` immediately (blocking on the separate `wait` tool); `slug`
  names the session for later lookup.
- If a call detaches or times out, inspect its stored session before
  retrying — never duplicate a running consult.

The `sessions` tool takes an id or slug; `detail: true` includes the stored
metadata and the original request — the evidence source when you need to
report what a detached call actually did.

## Agent-session gotchas

- **Cost and consent:** API runs may spend money — get a yes before the first
  paid run, then preflight with `--route`/`doctor --providers`.
- **Do not run two consults at once:** an active session blocks new API runs;
  attach to the existing one instead of spawning duplicates.
- **Secrets:** `--file` grabs whole directories — run `oracle --render` (or
  `--dry-run full`) and skim the bundle for credentials *before* sending
  anything to an external model.
- **Verify before applying:** an advisory "this looks fine" is not a test
  result. Route the reply back through normal review practice — for how to
  weigh reviewer findings, see the `code-review-reception` skill; for how to
  package a diff for review in the first place, see the `requesting-code-review`
  skill. For the broader coding workflow, the `coding-development` skill
  indexes when a second-model consult fits.