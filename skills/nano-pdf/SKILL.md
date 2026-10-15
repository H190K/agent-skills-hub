---
name: nano-pdf
description: Use when an existing PDF needs edits you can't do by hand — change text, dates, charts, logos or branding on rendered pages, or insert a new slide that matches the deck's style, driven by natural-language prompts through the nano-pdf CLI (Gemini image generation). Covers install order (system deps first), edit/add page-number semantics, the fail-closed error matrix, and the raster/OCR trade-offs.
version: 1.0.0
author: H190K
license: MIT
platforms: [linux, macos, windows]
---

# Nano PDF (`nano-pdf`)

`nano-pdf` edits **existing** PDF pages with natural-language prompts. It renders the target page
with Poppler, sends it to Google's Gemini image model, then rebuilds the page as a raster image
with a searchable OCR text layer (Tesseract) and stitches it back into the PDF with `pypdf`. Two
commands: `edit` existing pages, `add` new slides. The output is always a **new file**; the input
is never modified. Source repo: github.com/gavrielc/Nano-PDF (MIT).

Verified against `nano-pdf` **0.2.1** (PyPI latest, released 2025-11-29). The Gemini model name is
hardcoded in this release (`gemini-3-pro-image-preview`) — re-check `nano-pdf --help` and the repo
README after upgrading.

## Install

System dependencies come **first** — the pip package checks for them and refuses to run without:

```bash
# Debian/Ubuntu
sudo apt-get install poppler-utils tesseract-ocr
# macOS: brew install poppler tesseract
# Windows: choco install poppler tesseract

pip install nano-pdf      # one-shot alternative: uvx nano-pdf <args>
nano-pdf version          # → Nano PDF v0.2.1
```

- `pip install` alone still emits a harmless warning: `The package typer==0.27.3 does not have an
  extra named 'all'` — safe to ignore.
- With poppler/tesseract missing from PATH, the first command dies before touching your file:
  `Error: Missing system dependencies: pdftotext (poppler/poppler-utils), tesseract` (exit 1,
  with the apt/brew/choco line for your platform). Note the check looks for `pdftotext` — not
  `pdftoppm` — so a partial poppler install can pass or fail differently than you expect.

## API key (required, paid)

- Set `GEMINI_API_KEY` (a Google AI Studio key). This release's model requires a **paid** key with
  billing enabled; free-tier keys do not support image generation.
- **`.env` gotcha:** the tool auto-loads a `.env` from the current working directory (measured with
  a dummy key reaching the real API). If an exported `GEMINI_API_KEY` seems ignored, look for a
  stray `.env` in the directory you ran from.
- A rejected key comes back rewritten by the tool:
  `Error processing Page N: Gemini API Error: Invalid API key. Please check that your
  GEMINI_API_KEY environment variable is set correctly. …`

## `edit` — change existing pages

Arguments are **pairs** of page number and prompt (repeat for multiple pages):

```bash
nano-pdf edit deck.pdf 1 "Change the title to 'Q3 Results'" \
    3 "Update the date from January to February 2026"
```

Measured error matrix (all exit 1, nothing is generated):

- Missing file → `Error: File missing.pdf not found.`
- Unpaired arguments → `Error: Edits must be pairs of 'PageNumber Prompt'.`
- Page out of range → `Error: Invalid page number(s) [9]. PDF has 1 pages.` — page numbers are
  1-indexed and **validated before any API call**. There is no 0-based mode to "retry with ±1":
  if an edit lands on the wrong page, the number was valid and your prompt was mis-scoped.
- No API key → the run starts (progress lines print), then per page:
  `Error processing Page 1: GEMINI_API_KEY not found in environment variables`, followed by
  `No pages were successfully processed.`

Behavior worth knowing:

- Repeat page numbers are merged into **one** generation call per page — `1 "A" 1 "B"` becomes a
  single prompt joined with `ALSO:` (source: the edits are grouped by page before dispatch).
- Pages are processed in parallel (thread pool, 10 workers); progress prints per page.
- `--style-refs "2,3"` adds pages as visual style anchors. Out-of-range refs only warn
  (`Warning: Invalid style ref '3'`) and are skipped — the run continues.
- `--output out.pdf` sets the sink; default is `edited_<input-filename>` in the current directory.
- `--resolution "1K"|"2K"|"4K"` (default 4K) — not validated locally, so an invalid value only
  fails at the Gemini call.
- `--use-context` includes the full document text as context, each page truncated at ~2000 chars.
  Off by default for `edit`: page-local edits don't see the rest of the document unless you pass it.
- Google Search grounding is **on by default** (the model may look up facts before generating).
  `--disable-google-search` confines the edit to your prompt and the document.

## `add` — insert a new slide

```bash
nano-pdf add deck.pdf 0 "Title slide with 'Q3 2025 Review'"
nano-pdf add deck.pdf 5 "Summary slide with key takeaways as bullets"
```

- Position semantics differ from `edit`: `0` inserts at the beginning, `N` inserts **after** page
  N (1-indexed). Out of range: `Error: after_page must be between 0 and 1. Use 0 to insert at the
  beginning.` (measured).
- `--use-context` is **on by default** here (opposite of `edit`) and `--style-refs` defaults to
  page 1, so the new slide automatically borrows the first page's look.
- Like `edit`, the result is written to a new file (`edited_<input-filename>` unless `--output`).

## What an edit actually does to the file

- The replaced page becomes a **raster image + hidden OCR text layer**: the original vector text on
  that page is gone. Untouched pages keep their real text layer. The PDF stays searchable and
  selectable, but OCR quality governs the replaced page — stylized fonts and small text can come
  out imperfect.
- New pages are scaled to the original page size, so geometry holds.
- Each edited/added page is one image-generation API call — multi-page edits bill per page.

## Verify the output

```bash
pdfinfo edited_deck.pdf                 # page count, file size
pdftotext -layout edited_deck.pdf - | grep -i "Q3 Results"   # OCR text landed
pdftoppm -png -r 60 -f 1 -l 1 edited_deck.pdf check         # render to eyeball the design
```

OCR re-extraction is the honest check for text edits: grep for the new string, not just the file
size. For visual changes, render a thumbnail and look at it.

## When not to use it

- Form filling, text extraction, merging, splitting: `pdftotext`/`pypdf` do those deterministically
  with no LLM and no API cost.
- Building a document from scratch: create it with normal PDF tooling first; `nano-pdf` is best for
  cosmetic and content iteration on pages you already have.
- Anything that must preserve untouched vector content on an edited page — the whole page is
  re-rendered as an image, so pixel-exact original elements don't survive.