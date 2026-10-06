---
name: spike
description: Use when an idea's feasibility is unknown and building is the only honest way to find out — "can this even work?", "does library A hold up against B?", "try X before we commit" — throwaway experiments that end in a verdict, not a codebase.
version: 1.0.0
author: adapted from gsd-build/get-shit-done (MIT, Lex Christopherson)
license: MIT
platforms: [linux, macos, windows]
---

# Spike

A spike is a throwaway experiment whose product is **knowledge, not code**. If the question can be
answered by reading documentation, do that instead. If the answer is knowable but only from an
API's actual behaviour, a library's real-world performance, or two approaches measured against each
other — that is what spikes are for. Spikes are disposable by design; a spike that is kept, curated,
and maintained was not a spike.

**Core loop:** decompose → research → build → verdict, then iterate on what the findings reveal.
A spike without a verdict is unfinished work, and a verdict without evidence is a guess.

## When to use it

- "Is this even possible?", "can we do X at all?", "see if this works before we build it"
- "Compare A vs B for our case" — same question, competing approaches
- A load-bearing unknown: something the real build depends on but no amount of reading will settle
- An idea where the riskiest part is unproven and cheap to test

## When not to use it

- The answer is in the docs, README, or source — research, don't build
- The idea is already validated — go straight to the real implementation
- The request is a production feature — use the `plan` skill instead
- The question is about visual design, not feasibility — the `sketch` skill does that job

## Decompose: one question per spike

Break the idea into 2–5 independent feasibility questions; each becomes one spike. Frame each as
Given/When/Then with observable output:

| # | Spike | Validates (Given/When/Then) | Risk |
|---|-------|----------------------------|------|
| 001 | ws-stream-latency | Given a WS connection, when tokens stream, then client renders chunks < 100 ms | High |
| 002a | pdf-parse-pdfjs | Given a 200-page PDF, when parsed with pdfjs, then structured text extracts | Medium |
| 002b | pdf-parse-camelot | Same question, different library | Medium |

- **Standard spike** — one approach, one question. **Comparison spike** — same question, competing
  approaches; shared number, letter suffix (`002a`, `002b`).
- **Good spike questions** are narrow and falsifiable, with output you can observe.
- **Bad spike questions** are broad ("can we build a chat app?"), unobservable, or answerable by
  reading.
- **Order by risk.** The spike most likely to kill the idea runs first — no point prototyping the
  easy parts if the hard part cannot work. If 001 is invalidated, everything downstream may be
  moot.
- Skip decomposition only when the user already knows the one thing to test.

Present the table for adjustment before building; let the user drop or reorder spikes. If the
agent runs autonomously, state the order and proceed — do not stall on a checkpoint nobody will
answer.

## Research before each spike, not once at the start

Per spike: brief it (2–3 sentences — what this spike is, why it matters, the key risk), then
research enough to pick an approach. Surface competing approaches in a table (approach, tool,
pros, cons, maintenance status); pick one and say why. If two or more are credible, build quick
variants within the spike and compare. Skip research only for pure logic with no external
dependencies. Capture findings in the spike's `## Research` section so the build step spends no
time re-deriving them.

## Build: throwaway, observable, honest

One directory per spike, named `NNN-descriptive-name`, under `spikes/` in the repo root (or a
git-ignored workspace — see below). Each spike gets a `README.md` with the question, approach,
how to run, and the verdict.

**The verdict must be experienced, not asserted.** A log line saying "it works" is not a spike
result. Default choices, in order of preference:

1. A runnable CLI taking real input, printing observable output
2. A minimal page or UI demonstrating the behaviour — something a person can try
3. A small web server with one endpoint
4. A unit test exercising the question with recognizable assertions

Stdout-only verification is acceptable only when the spike is genuinely about a fact, not a
feeling: a parse succeeds or fails, an API authenticates or not, a benchmark number.

**Depth over speed.** Never declare a verdict after one happy-path run. Test edge cases — large
inputs, malformed data, network failures, concurrency. When a result surprises you, stop and
follow it: write a follow-up probe isolating the surprise. The verdict is only as trustworthy as
the investigation behind it.

**Avoid anything production-shaped** unless the spike specifically requires it: build tools,
bundlers, Docker, config systems, packaging, .env files. Hardcode everything. The moment a spike
starts needing infrastructure, split it into smaller spikes.

**Keep it invisible.** Spikes are experiments, not project files — they should not surface in the
project's `git status`. Either keep the spike directories git-ignored permanently (the project
already ignore-files such scratch space), or add one line to `.git/info/exclude` (measured: a
`spikes/` entry hides the whole tree while `git status` stays clean and no tracked file changes) —
it stays local and cannot be committed, unlike `.gitignore`. A spike whose cleanup costs a commit
was overweight.

**Parallel comparison spikes.** When comparison spikes are truly independent (no shared files,
ports, or fixtures), dispatch one focused agent per variant in a single batch — the
`dispatching-parallel-agents` skill covers the shape. Each returns its own verdict with evidence;
you write the head-to-head. If the variants share any resource, build them sequentially instead —
parallel agents contending for the same port or files produce comparisons of the contention, not
the approaches.

## Verdict

Each spike's README closes with a verdict. Use the three-value scheme — not a bare yes:

```markdown
## Verdict: VALIDATED | PARTIAL | INVALIDATED

### What worked
- ...

### What didn't
- ...

### Surprises
- ...

### Recommendation for the real build
- ...
```

- **VALIDATED** — the question answered yes, with evidence you observed.
- **PARTIAL** — yes under constraints; name the constraints (works with ≤ 1 000 rows, fails
  without network). This is the most common real-world outcome, so document the boundaries.
- **INVALIDATED** — the approach does not work, for a stated reason. **This is a successful
  spike**: it purchased certainty cheaply. Kill the idea or pivot the approach — never ship a
  build on an invalidated spike.

Do not rush a verdict. "VALIDATED — it works" with no nuance is almost always incomplete.

## Comparison spikes: back to back, then head to head

Build both variants back to back, then close the comparison in one table:

```markdown
## Head-to-head: pdfjs vs camelot

| Dimension            | pdfjs (002a)     | camelot (002b)      |
|----------------------|------------------|---------------------|
| Extraction quality   | structured text  | tables only         |
| Setup complexity     | one npm install  | pip + ghostscript   |
| 100-page parse time | 3 s              | 18 s                |
| Rotated text         | no               | yes                 |

**Winner:** pdfjs for this use case — camelot if table-first extraction is ever needed.
```

Include the dimensions that decided it for this project (quality, setup cost, performance,
failure modes) — not every dimension. Name a winner; a neutral table without a
recommendation leaves the decision unfinished. If the loser's strength might matter later, say
under what conditions to revisit.

## Frontier: what to spike next

When spikes already exist and the user asks what to spike next, walk the existing spike READMEs
and look for:

- **Integration risks** — two validated spikes touching the same resource (API, database, state,
  data format), each tested independently, never proven together
- **Data handoffs** — spike A's output assumed compatible with spike B's input, never proven
- **Timing/ordering** — spikes that work in isolation but have sequencing dependencies in the
  real flow
- **Resource contention** — individually fine, competing for connections, memory, or rate limits
  when combined
- **Gaps in the vision** — capabilities the real build assumes but nothing has proven
- **Discovered dependencies** — findings from earlier spikes that opened new questions
- **Alternative approaches** — different angles on PARTIAL or INVALIDATED results

Propose 2–4 candidates as Given/When/Then, ordered by risk. Let the user pick.

## What NOT to turn a spike into

- **A module.** The moment spike code starts being imported by real code, write the real thing
  properly — spike code carries no tests, no error handling, and no licence you may not have
  verified.
- **A tutorial.** If the finding is worth keeping, the verdict's "Recommendation for the real
  build" is where it lives.
- **A benchmark suite.** One question, one answer. If two spikes share a benchmark, that is a
  new spike — number it.
- **A permanent directory.** Spike `README.md` files record what was learned; the code is
  throwaway. If you feel the urge to tidy spike code for a future reader, that instinct is the
  signal to promote the idea into the real build and delete the spike.

## Common mistakes

1. **Research-free build** — picking a library by reputation, then discovering its limit two
   hours into the spike. Research each spike's approach first.
2. **One happy path, verdict declared** — the spike proved nothing about real inputs.
3. **A verdict with no evidence** — "it works" with nothing observed. If the evidence is not in
   the transcript, run it again.
4. **Building the easy part first** — risk ordering exists so the idea can die cheaply.
5. **The comparison with no winner** — a head-to-head that ends "both are fine" was not a
   comparison; pick one and say why.
6. **The spike kept alive** — keeping spike dirs checked in, tidied, and curated. The verdict
   is the deliverable; the code is refuse.
7. **Skipping the INVALIDATED case** — an invalidated spike saved the project weeks; it is a
   win, and the reason for the failure must be written down.

## Related skills

- The question is about visual design, not feasibility — the `sketch` skill (also throwaway, also
  comparison-driven, different output).
- The idea is validated and moving to production — the `plan` skill writes the implementation
  plan the spikes de-risked.
- Comparison spikes are truly independent — the `dispatching-parallel-agents` skill covers the
  one-agent-per-domain shape.
- A spike's verdict claims facts from fetched documentation — the `grounded-citations` skill keeps
  those claims traceable to what was read.
- An experiment produced a surprising result that looks like a bug in your probe, not the code —
  the `systematic-debugging` skill's four phases separate the two.

## Attribution

Adapted from the GSD (Get Shit Done) project's `/gsd:spike` workflow — MIT © 2025 Lex
Christopherson ([gsd-build/get-shit-done](https://github.com/gsd-build/get-shit-done)). The full
GSD system tracks spike state persistently across sessions and integrates spiking with a broader
spec-driven pipeline; this skill is the lightweight standalone shape.