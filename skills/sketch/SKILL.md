---
name: sketch
description: Use when the user wants to see a design before committing to it — "show me what this screen could look like", "compare layout A vs B", "give me 2-3 takes", throwaway HTML mockups to react to rather than a built component.
version: 1.1.0
author: adapted from gsd-build/get-shit-done (MIT, Lex Christopherson)
license: MIT
platforms: [linux, macos, windows]
---

# Sketch

## Overview

When a design is still a direction rather than a decision, the fastest way to settle it is to **build
two or three disposable versions and look at them side by side**. Describing a layout in prose and
describing three of them are both cheap to produce and hard to compare; three rendered pages are
easy to compare and instantly reveal which one was the bad idea.

**Core rule:** never build one variant. One variant is a proposal — three are a comparison, and the
comparison is what produces a decision.

## When to use it

- "Sketch this screen", "show me what X could look like", "give me a few takes on this UI"
- "Compare layout A vs B", "should this be a sidebar or a single column?"
- The visual direction is undecided and building the real component would lock it in
- An existing screen needs a second opinion, not a refactor

## When not to use it

- The design is already decided — just build it properly.
- The user wants the production component. A sketch is throwaway by design; promoting it is a
  deliberate later step, not something the sketch quietly becomes.
- The user wants a diagram of a system's structure — that is a different job with different output —
  the `architecture-diagram` skill produces a single dark-themed HTML+SVG architecture/topology map,
  verified rendered before delivery.
- The user wants a polished, shippable single artifact (a landing page, a deck). That is production
  work and should be built as such.

## Method

```
intake → variants → look at them → head-to-head → pick one (or iterate)
```

### 1. Intake

If the user has not already answered these, ask **one at a time** — not as a three-part questionnaire.
Briefly reflect each answer back before moving on, because each one changes what you build.

1. **Feel** — "What should this feel like? Adjectives, a mood, a vibe." *"Calm, editorial, like a
   good newspaper"* is worth more than *"clean"*.
2. **References** — "What products or sites have the feel you're imagining?" A named reference
   collapses a hundred words of description.
3. **Core action** — "What is the single most important thing a user does on this screen?" Every
   variant should serve that one thing. A variant that looks lovely and buries the core action has
   failed, however good it looks.

If the user already gave you all three, skip straight to building. Do not ask for permission to start.

### 2. Build 2–3 variants, never 1

Each variant is a **complete, standalone HTML file**. Build them; do not describe them.

The variants must take **different design stances**, not different pixel values. Two variants that
differ only in accent colour are one variant with a wasted second attempt — the user cannot choose
between them because they cannot see a difference.

Pick one axis and pull hard against it:

| Axis | Poles |
|---|---|
| **Density** | airy / compact / ultra-dense |
| **Emphasis** | content-first / action-first / tool-first |
| **Aesthetic** | editorial / utilitarian / playful |
| **Layout** | single column / sidebar / split pane |
| **Grounding** | card-based / bare content / document-style |

**Name each variant after its stance, not its number** — `001-calm-editorial`, `002-utilitarian-dense`.
A number tells the user nothing when they are comparing; the stance name is the argument.

```
sketches/
├── 001-calm-editorial/index.html   (+ README.md)
├── 002-utilitarian-dense/index.html (+ README.md)
└── 003-playful-split/index.html    (+ README.md)
```

### 3. Make them real

A sketch is one self-contained HTML file:

- Inline `<style>` — no build step, no external stylesheet
- System font stack, or one web font via a `<link>`
- A CDN utility framework is fine; a build pipeline is not
- **Realistic content** — real sentences, real names, plausible numbers. Placeholder text hides
  every problem that over-long real content would have exposed, and the whole point is to see those.
- **Interactive** — the clickable things click, the hovers exist, and at least one state actually
  changes (a filter applies, a panel opens, a mode toggles). A frozen static image is a worse sketch
  than a rough animated one, because the user cannot feel the interaction they are being asked to
  judge.

Start from this reset, which is enough for most attempts:

```html
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    color: #1a1a1a; background: #fafafa; line-height: 1.5;
  }
</style>
```

### 4. Look at every variant before showing it

**Do not write HTML and assume it rendered.** Open each file and inspect the actual page:

1. Load it in a browser at `file:///absolute/path/to/sketches/001-calm-editorial/index.html`.
2. Get a **rendered image** of the page — screenshot it and look at the image, or use whatever
   preview capability your environment provides. The check that matters is the one on the pixels.
3. Ask of the image: does this read as intended, and is anything visibly broken — overlapping text,
   unstyled elements, a collapsed flex container, a missing image, a font fallback that did not load.
4. Resize to at least one narrow (phone) and one wide width and look again.
5. Fix and reload until it is right. **Never hand the user a variant you have not seen.** A blank page
   due to one unclosed tag wastes the user's whole review.

This step catches the class of bug that reading the source cannot: a font import that silently
failed, a container that collapsed to zero height, text that overflows its card. Source inspection
confirms what you wrote, not what the browser drew.

### 5. Variant notes

Each variant gets a short `README.md` next to it:

```markdown
## Variant: calm-editorial

### Design stance
The principle driving this variant, in one sentence.

### Key choices
- Layout:
- Typography:
- Colour:
- Interaction:

### Trade-offs
- Strong at:
- Weak at:

### Best for
The user or use case this variant actually serves.
```

### 6. Head-to-head

Present the comparison, and **have an opinion**. A table of neutral observations makes the user do
the synthesis you were supposed to do.

```markdown
## Three takes on the home screen

| Dimension | Calm editorial | Utilitarian dense | Playful split |
|---|---|---|---|
| Density | Low | High | Medium |
| Primary action visibility | Low | High | Medium |
| Scan-ability | High | Medium | Low |
| Feel | Calm, trusted | Sharp, tool-like | Inviting, energetic |

**My take:** utilitarian-dense for power users, calm-editorial for a content-forward audience.
playful-split is the weakest — it tries to do both and commits to neither.
```

Then let the user pick, combine two into a hybrid, or ask for another round. A hybrid is a normal
outcome and usually means the intake missed something worth naming.

## Interactivity bar

A sketch is interactive enough when the user can:

1. **Click the primary action** and something visible happens — a state change, a modal, a toast.
2. **Trigger one meaningful state transition** — filter a list, toggle a mode, open a panel.
3. **Hover** the recognisable affordances — buttons, rows, tabs.

More than that is over-engineering a throwaway. Less than that is a screenshot.

## Picking what to sketch next

When variants already exist and the user asks "what should we sketch next?", look for the gaps rather
than inventing new screens:

- **Composition gaps** — two variants each won something in different areas, and nobody has seen the
  two choices together on one screen.
- **Unsketched surfaces** — screens that are referenced but never explored.
- **State coverage** — the happy path was sketched; empty, loading, error and 1000-items were not.
  This is usually where the real design problems live.
- **Width gaps** — approved at one viewport, never seen at phone or ultrawide.
- **Motion gaps** — static layouts exist; the transitions and drag behaviour do not.

Propose two to four named candidates and let the user choose.

## Output

- Create `sketches/` at the project root (or wherever the user's conventions put design work).
- One directory per variant: `NNN-stance-name/index.html` plus `README.md`.
- Tell the user how to open them — `open` on macOS, `xdg-open` on Linux, `start` on Windows.
- **Keep them disposable.** A sketch you feel the need to preserve should be promoted into real code,
  not curated as an asset. That instinct is the signal that the design has been decided.

## Common Mistakes

1. Building one variant instead of two or three — nothing to compare, no decision.
2. Variants that differ only in colour, so the comparison is meaningless.
3. Handing over a variant nobody looked at, and shipping a blank or broken page.
4. Placeholder text instead of realistic content, hiding every overflow and wrapping problem.
5. A static page with no interaction, so the user judges the wrong thing.
6. A neutral comparison table with no recommendation, leaving the synthesis to the user.
7. Polishing a throwaway until it is not throwaway — the sketch is meant to be cheap.
