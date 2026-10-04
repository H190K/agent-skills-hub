---
name: simplify-code
description: Use when the user asks to simplify, clean up or review recent code changes — a pre-merge cleanup pass over the diff with three narrow parallel reviewers (reuse, quality, efficiency), findings aggregated and deduplicated, then only the fixes that survive verification get applied.
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
---

# Simplify Code — Parallel Review and Cleanup

Review recent code changes with three focused reviewers running in parallel,
aggregate their findings, and apply only the fixes that survive judgment.

**Core principle:** three narrow reviewers beat one broad reviewer. Each
searches the codebase deeply for a single class of problem — reuse, quality,
efficiency — instead of diluting attention across all three. They run
concurrently, so you pay the latency of one review, not three. This works
because reviewers investigate, not guess: every finding must point at real
code (`file:line`), or it is dropped.

## When to Use

Trigger this when the user says any of:

- "simplify" / "simplify my changes" / "clean up these changes"
- "review my code" / "review my recent changes"
- "/simplify" (the habit carried over from tooling that has a command for it)

Modifiers the user may add — honor them:

- **Focus:** "simplify, focus on efficiency" → run only the efficiency
  reviewer, or weight the aggregation toward it. Recognized focuses: `reuse`,
  `quality`, `efficiency`.
- **Dry run:** "simplify but don't change anything" → run the reviewers,
  present findings, apply nothing; ask before applying.
- **Scope:** "simplify the last commit" / "simplify staged" / "simplify
  src/foo.py" → narrow the diff source (Phase 1).

Do NOT auto-run this after every edit. It costs parallel agent tokens —
invoke it only when asked. It is the after-the-fact cleanup pass, not the
per-change gate: receiving review feedback is a different skill.

## Phase 1 — Capture the changes

Pick the diff source by what the user asked, in this default order:

```bash
git diff                    # 1. default: uncommitted changes (tracked files)
git diff HEAD               # 2. if empty, include staged changes too
git diff --staged           # scoped: "only what I staged"
git diff HEAD~1             # scoped: "the last commit"
git diff main...HEAD        # scoped: "this branch"
git diff -- src/foo.py      # scoped: named files
```

If both defaults are empty and no files were named or recently edited, stop
and say so — there is nothing to simplify. Capture the full diff text. If it
exceeds roughly 2000 changed lines, tell the user that three reviewers each
carrying the whole diff is token-heavy, and offer to scope it down
(per-directory, per-commit) first.

## Phase 2 — Three reviewers in parallel

Dispatch all reviewers in the same batch so they run concurrently. Three is
the right fan-out by default.

Give **every** reviewer the **complete diff** — never fragments, because
cross-file issues hide in the gaps — plus the repository root so they can
search the wider codebase. Tell each reviewer to:

- Search the existing codebase for evidence (read files, grep) instead of
  reasoning from the diff alone.
- Report findings as `file:line → problem → suggested fix` with a
  `high` / `medium` / `low` confidence on each.
- Skip nits and style-only churn. Flag only what materially improves the code.

The three review goals (drop any the user's focus excludes):

**Reviewer 1 — Code reuse.** Search utility modules, shared helpers and
adjacent files for existing functions, constants or patterns the new code
could call instead of reimplementing. Flag: new functions duplicating
existing ones; hand-rolled logic an existing utility already covers (manual
string/path manipulation, ad-hoc type guards, re-implemented parsing). For
each finding, name the existing thing and where it lives — a reuse finding
without that pointer is speculation, not a finding.

**Reviewer 2 — Code quality.** Look for redundant state (values duplicating
or derivable from existing state; caches that don't need to exist); parameter
sprawl (new params bolted on where the function should have been
restructured); copy-paste-with-variation (near-duplicate blocks that should
share an abstraction); leaky abstractions (exposing internals, breaking an
encapsulation boundary); stringly-typed code (raw strings where a constant
or registry already exists — check canonical registries before flagging).
For each, name the concrete refactor.

**Reviewer 3 — Efficiency.** Look for unnecessary work (redundant
computation, repeated file reads, duplicate API calls, N+1 access patterns);
missed concurrency (independent operations run sequentially); hot-path bloat
(heavy or blocking work in startup or per-request paths); TOCTOU
anti-patterns (existence pre-checks before an operation, instead of the
operation plus error handling); unbounded growth or missing cleanup; reading
whole files where a slice would do. For each, the concrete fix and why it is
faster or lighter.

If the repo has a contribution guide or linter config listing conventions,
fold those rules into every reviewer's brief so suggestions match house style
rather than fight it.

## Phase 3 — Aggregate, decide, apply

Wait for all reviewers to return, then:

1. **Merge** into one list, deduplicating where they overlap.
2. **Discard weak findings** — you hold the most context; drop suggestions
   that are wrong or marginal without arguing with the reviewer.
3. **Resolve conflicts.** Reviewers genuinely disagree (reuse says "call
   existing util X", efficiency says "X is slow on this path, inline it").
   Resolution order: **correctness > the user's stated focus > readability
   and reuse > micro-performance.** Never apply a perf "fix" that hurts
   clarity unless the path is genuinely hot. When two options are defensible
   and mutually exclusive, take the one touching less code and note the
   alternative in your summary.
4. **Apply** the surviving fixes directly, as scoped minimal edits — unless
   the user asked for a dry run, in which case present the list and ask.
5. **Verify nothing broke:** run the project's targeted tests for the touched
   files (not the full suite), plus any linter or type checker the repo uses.
   A fix that breaks a test is reverted, not repaired into the test.
6. **Summarize** the applied fixes grouped by reviewer category, plus the
   findings you deliberately skipped and why.

## Pitfalls

- **Don't fan out wider than three.** More reviewers means more cost and more
  conflicting suggestions to reconcile, not better coverage. Three categories
  cover the space.
- **Ship the whole diff to each reviewer.** Partial diffs defeat the design:
  cross-file duplication and N+1 patterns only show up with full context.
- **Reviewers search, they don't guess.** Require `file:line` evidence; drop
  findings that lack it.
- **Clean-up is not a refactor.** Editing only what the diff touched, plus
  the minimal surrounding change a fix needs, is the whole licence. A
  "quick cleanup" that rewrites the module is a different task with its own
  review.
- **Findings are claims, not orders.** A reviewer's claim is verified against
  the code before it is acted on — the same discipline as accepting any
  review feedback: check it, then agree or push back with reasons.
- **Large diffs blow capacity.** Three agents each carrying a 5000-line diff
  risks truncated attention; scope the diff down before dispatching rather
  than feeding fragments.

## Related

- `code-review-reception` — the complementary case: evaluating feedback
  *someone else* gives you, not running your own review pass.
- `test-driven-development` — the verification half: prove a fix changed
  behavior, don't just re-run the affected tests and shrug.
- `verification-before-completion` — the claim gate before you report back
  what was applied.