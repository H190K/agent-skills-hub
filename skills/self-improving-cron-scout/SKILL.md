---
name: self-improving-cron-scout
description: "Recurring cron scouts that improve their own prompt."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [cron, research, monitoring, scout, digest, automation]
    related_skills: [hermes-agent, rss-feeds, grounded-citations, blogwatcher, competitor-news-monitor]
---

# Self-Improving Cron Scout

Builds a scheduled job that researches a domain daily, reports it, and **evolves its own prompt**
when a run reveals a gap. Use for digests, scouts, watchdogs, market/monitor briefs — anything where
coverage should compound instead of resetting each morning.

## Design shape

Three state layers, each with one job:

| Layer | Mechanism | Holds |
|---|---|---|
| Recall of last run | `--continuity` (writes `context_from: ['self']`) | the previous report, so it dedupes |
| Durable knowledge | `hermes cron notepad <job_id> ...` | watchlist, coverage log, changelog |
| Behaviour | the prompt itself | mission, lanes, output shape |

The prompt is editable at runtime, so the job can improve its own instruction set. That is the
whole trick — no plugin, no code.

## Build it

1. Write the full prompt to a file first (`/tmp/<name>_prompt.md`). Editing a 5 KB prompt through
   shell quoting is how you lose it; the file is also what `hermes cron edit --prompt` reads.
2. Create:
   `hermes cron create "0 7 * * *" "$(cat /tmp/<name>_prompt.md)" --name "..." --deliver origin --continuity --skill <relevant-skill>`
3. Seed the notepad — **no empty state**. Keys: `job_id`, `source_watchlist`, `coverage`, `changelog`.
4. Fire one seed run (`hermes cron run <id>`, or the `cronjob_manage` tool's `action=run`) to prove
   the pipeline and let the first report populate `coverage`.

## Prompt requirements (all four, or the job degrades)

- **Self-contained.** Cron runs in a fresh session: no chat context, no follow-up questions. Name
  the user, the deliverable, and the language.
- **Explicit output shape.** The final response is delivered verbatim — spell out sections, ordering,
  and formatting for the target platform (bullets, not tables, on Telegram).
- **Honest-empty rule.** "If a lane has nothing genuinely new, say so; never invent links, versions,
  prices or dates." A model that must fill four sections will fabricate to fill them.
- **Guarded self-edit.** The rewrite MUST preserve the mission, lanes and safeguards verbatim, may
  only add/sharpen, and is capped (`keep under 8000 chars`). Without this the prompt bloats or gets
  quietly lobotomised by an over-eager rewrite.

## Self-edit mechanism (give the model the exact command)

```
hermes cron notepad <job_id> set <key> "<value>"      # get | list | delete
hermes cron edit <job_id> --prompt "$(cat /tmp/prompt.md)"
```

The job id is not in the model's context — put it in the notepad under `job_id` and tell the prompt
that is where to find it. `render_notepad_section()` auto-injects all of a job's notepad keys into
the prompt each run, so the watchlist returns automatically.

**The notepad has no append verb.** To append a changelog line: `get` the key, concatenate, `set` it
back. Tell the prompt to keep only the last ~40 lines.

**Caps are enforced and raise:** 16 KB per value, 64 KB per job (key+value). A bloat strategy
("append everything") hits `ValueError` and the run's state write fails — always bound growth.

## Audit the self-edit — the model WILL degrade its own prompt

Every self-edit needs a human/agent review pass. Observed in a real first run: the job found a real
workaround for a broken backend, then wrote the **opposite** rule into its own prompt — "web_extract is
unusable, skip it" — which would have deleted a working capability. Other observed failure classes:

- **Effort limits.** It adds "do not retry", "give up after N", "do not wait longer". These buy a
  quiet run by silently deleting results. Ban them in the prompt: *hard limits on effort are
  prohibited; when something fails, say so in the coverage log instead of implying "no news".*
- **Unverified capability claims.** A tool is only "broken" after the run exercised it and captured
  the error. Require the actual HTTP status before a source is called dead (403/timeout = blocked, not
  gone).
- **Silent deletions.** Require that a self-edit may never remove an existing probe command, source,
  or safeguard — only add or sharpen.
- **Hallucinated facts in the plumbing.** It wrote a wrong weekday in one draft. Add the same rule for
  the job as for the report: confirm with `date +%A` before naming a day.

Add a `### Do not do this (learned the hard way)` section to the prompt — negative rules stick better
than positive ones for this failure class — and a **verification duty**: spot-check the 2–3 most
load-bearing claims against the primary page before composing, and label anything unopened as
unverified rather than stating it flatly.

## Pitfalls

- **Prompt cap is load-bearing.** A self-editing prompt grows every run. Set an explicit character
  ceiling and make the job consolidate rather than grow past it; re-read the stored prompt in
  `~/.hermes/cron/jobs.json` after each edit and confirm the mission, every lane, and every safeguard
  still appear (grep for each one — do not eyeball it).
- **Timezone.** `0 7 * * *` is the host's local time, not the user's stated one. Run `date` and check
  `timedatectl`; a host on a different zone than the user's stated offset fires at the wrong hour.
- **`--continuity` writes `context_from: ['self']`.** Expected, not a bug.
- **Prompt-cache note:** an empty notepad renders as `''` so non-adopters get a byte-identical
  prompt. Writing a key to a job's notepad changes every future prompt — deliberate here, but do not
  set junk keys.
- **Catch-up.** Half-period, clamped 120s–2h. A machine that slept past 07:00 fires late with a
  `catch_up` dispatch note rather than skipping; `cron.catch_up_missed: false` changes that.
- **Inactivity watchdog** is idle time (default 600s, `HERMES_CRON_TIMEOUT`), not wall clock — a long
  but active report is never cut off. `0` = unlimited.
- **No search backend is guaranteed.** A search-only backend configured as `web.extract_backend`
  makes `web_extract` fail with a typed error, and keyless/anonymous search tiers 403 under load.
  Give the prompt named substitutes that need no credentials — a browser driver reading
  `document.body.innerText`, or `curl -sL <url> | python3 -c "...strip tags..."` — not just
  "search the web".
- **Verify the edit landed**: read `~/.hermes/cron/jobs.json` and check the prompt length/content,
  not just the CLI's "Updated job" line.
- **Never pin the model** unless asked (`--pin`); unpinned jobs follow the main agent model.
- **A catch-up dispatch on an unrelated pre-existing job** is a stale-fire warning, not caused by
  your work; `hermes cron doctor` explains it.

## Related

`hermes cron notepad` is the generic durable-KV path; for a job that needs real data collection
before reasoning, prefer `--script` (its stdout is injected) or a monitor URL that gates the LLM
entirely. Load the `hermes-agent` skill before changing Hermes config around any of this.
