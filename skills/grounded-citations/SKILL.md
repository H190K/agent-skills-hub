---
name: grounded-citations
description: Use when a report, comparison, or answer is built on fetched web sources — inline [n] citations, a Sources block, and a verify step so every claim traces to its URL.
version: 1.0.0
author: H190K (adapted from work by Teknium, MIT)
license: MIT
platforms: [linux, macos, windows]
---

# Grounded Citations

Every claim taken from an outside source gets an inline numbered citation and a
`Sources:` list. The `url → [n]` mapping must come from the retrieval itself,
never from memory: the model only ever emits a small integer that was handed to
it in the same step that recorded the URL. Citing from memory is how plausible
URLs that never existed get into a deliverable.

For high-stakes work the same ledger doubles as a fact-checking chain: verbatim
quotes are attached to each source (a quote is rejected unless it literally
appears in the fetched page text), claims from model knowledge are flagged
`[not verified]`, and the verify step fails any draft whose cited sources carry
no evidence.

This skill covers answers in chat and written artifacts (markdown, PDF, docx,
slides). It does not cover academic BibTeX pipelines for conference papers.

## When to Use

- Research, comparisons, news summaries, "what is the current state of X"
- Any deliverable written to disk that quotes, paraphrases, or reports outside
  facts — reports, briefs, docs, decks, wiki pages
- Fact-finding where the reader will want to check your work
- Multi-source synthesis where conflicting sources must be attributed

Skip inline citations when retrieval is incidental to another task — a quick
syntax or version lookup mid-coding, casual conversation, creative writing.
Mention a URL only if the reader would plausibly want the link.

## The ledger is a tool, not a script

Two ways to keep the mapping, depending on what the environment allows:

**Option A — no tooling (always available).** A plain markdown ledger file the
agent maintains by hand, appended at retrieval time and never rewritten after
the fact:

```markdown
# Citation ledger

| id | URL | Title | Retrieved |
| -- | --- | ----- | --------- |
| 1  | https://example.com/spec | Spec | 2026-10-03 |
```

Start one per task (`<task-name>-ledger.md` in the working directory). The
ids are ledger identities: `[4]` in the draft must stay that source for the
whole task. Append rows the moment a URL enters the context via a fetch,
search result, or page extraction — before any prose is written.

**Option B — a real ledger script.** When you may install tooling, a script
keeps ids stable and mechanical. Any stdlib-only script that offers these
operations works; search GitHub for a `citation ledger` implementation rather
than writing one:

| Operation | Purpose |
| --- | --- |
| reset | fresh ledger for a new task |
| add <url> [--title T] | register a source, prints its id — idempotent, URL-normalized, so the same page returns the same id all task |
| list | show the ledger |
| render [--style styles] [--cited-in draft.md] | generate the Sources block from the ledger |
| verify draft.md | fail on unknown ids, a Sources block disagreeing with the ledger, or thin coverage |

`add` being idempotent and URL-normalized is the property worth preserving:
it keeps ids stable across many search-and-extract rounds. If you write one,
store the ledger outside the deliverable directory.

## Procedure

1. **Start the ledger for the task.** Option A: write the empty ledger file.
   Option B: `reset`. Skip this only when continuing work whose ids are
   already in an existing draft — reusing the ledger keeps numbering stable.

2. **Register every source at retrieval time.** After each search hit or page
   fetch, append the row (or run `add`). Do this *before* writing prose.
   Registering later, from memory, is the failure mode this skill exists to
   prevent.

3. **Write cite-while-drafting.** Place the bracketed id(s) immediately after
   each sentence the source supports:

   ````markdown
   Ice floats because it is less dense than liquid water.[1][2]
   ````

   - No space before the bracket; each id in its own brackets.
   - Max 3 ids per sentence. Cite per sentence, not one dump at the end.
   - Only ids the ledger returned. Never invent an id or a URL.
   - Claims from your own knowledge get no citation.
   - Conflicting sources: present both readings, each with its own id.
   - Quote exact figures, dates, and names as the source states them; flag
     gaps explicitly ("no source found for X") instead of smoothing over.
   - Cite the page you read, not the search result. A search snippet's
     description supports only what it literally says — extract the page
     first when the claim needs the body.

4. **Append the Sources block mechanically.** Option A: transcribe the ledger
   table into `## Sources` entries at the end of the draft — read the rows
   back off the file, never retype URLs from memory. Option B: `render
   --cited-in draft.md` generates it. For non-markdown targets: footnotes in
   docx, endnotes in PDF/LaTeX, a Sources slide in decks, per-page source
   lists in wiki output.

5. **Verify before delivering.** Option A: read the draft against the ledger
   — every `[n]` resolves to a row, the Sources block lists exactly the cited
   ids, no URL in the deliverable that is absent from the ledger. Option B:
   `verify draft.md` exits non-zero on violations; read its warnings even
   when it passes — uncited registered sources usually mean a claim lost its
   attribution during editing.

6. **Chat answers** follow the same steps with the draft being the reply:
   register sources, cite inline, end with the rendered `Sources:` list.

## Fact-Checking Mode

For work where the reader must be able to check the chain — medical, legal,
financial, safety, disputed claims, or when asked for fact-checking — upgrade
from citations to evidence:

1. **Attach a verbatim quote per source.** After extracting a page, save its
   text and copy the sentence(s) that carry each claim into the ledger's
   evidence column (Option A) or `quote <id> --text "..."` against the saved
   page file (Option B). The quote must appear verbatim in the fetched text —
   a paraphrase or a misremembered figure cannot masquerade as evidence. Copy,
   never retype: retyping is where the drift enters.

2. **Flag model-knowledge claims with `[not verified]`.** A load-bearing claim
   you could not source gets an explicit marker instead of a citation. The
   goal is declared provenance for every claim, not a citation on every
   sentence. If a key claim can be checked, check it; this marker is for what
   genuinely cannot be, and a fact-check deliverable dominated by it should
   say so in its summary.

3. **Cross-check disputed facts against a second independent source.** When
   two sources disagree, cite both readings with their own ids and quotes, and
   say which you weight and why. One source is reporting; two independent
   sources are corroboration.

4. **Render evidence into the deliverable.** In the Sources block, show each
   source's attached quotes beneath its URL, so the deliverable shows claim →
   source → exact supporting text with nothing taken on faith.

## Pitfalls

- **Registering after writing.** The ledger must be populated from retrieval
  output, not reconstructed from the draft — that reintroduces exactly the
  hallucinated-URL risk the numbering removes.
- **Renumbering mid-task.** Never hand-edit ids in a draft. Ids are ledger
  identities; if a draft cites `[4]`, `[4]` must stay that source. Start a new
  ledger only between tasks.
- **Retyping URLs into the Sources block.** Transcribe from the ledger or
  generate it. A hand-typed URL is an unverified claim.
- **Citing a search snippet as if you had read the page** — extract first.
- **Over-citing.** Three ids on a sentence is the ceiling; a citation on every
  clause hides which source carries the load.
- **Citing the ledger inside generated code.** Source comments belong in prose
  deliverables and doc headers, not in code artifacts.
- **Quoting from a snippet instead of the page.** Evidence quotes must come
  from the extracted page text you saved, not a search description.
- **Paraphrasing until the quote matches.** If the verbatim check rejects it,
  find the actual sentence — do not reword until something matches.
- **Using `[not verified]` as an escape hatch.** It marks the rare claim that
  genuinely cannot be sourced; if most sentences carry it, the task needed
  more retrieval, not more markers.
- **Hand-editing a rendered Sources block.** Regenerate it; a sliced-in block
  goes stale the next time the ledger changes.
- **Parallel subagents with separate ledgers.** Each worker keeps its own
  working directory, so ids collide when outputs merge. Point every worker at
  one shared ledger path and tell that path to each one explicitly.

## What "verified" means here

A delivery is grounded when: every `[n]` in the text resolves to a ledger row
that was recorded at retrieval time, the Sources block lists exactly the cited
ids with those rows' URLs, every load-bearing claim either carries a citation
or an explicit `[not verified]` marker, and — in fact-checking mode — every
cited source has a verbatim quote attached that appears in the saved page text.