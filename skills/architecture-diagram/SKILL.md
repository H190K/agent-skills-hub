---
name: architecture-diagram
description: Use when the user asks to see a system's structure as a diagram — architecture, cloud/infra, topology, deployment, or service maps. Produces a single dark-themed self-contained HTML file with inline SVG, verified to render before it is delivered.
version: 1.0.0
author: adapted from Cocoon AI's architecture-diagram-generator (MIT, © 2025 Cocoon AI)
license: MIT
platforms: [linux, macos, windows]
---

# Architecture diagram

Produce a polished, dark-themed architecture diagram as **one self-contained HTML file** with
inline SVG and CSS. No build step, no rendering library, no API key — write the file, open it in a
browser. The dark engineering-console look with a JetBrains Mono grid is the house style this
skill encodes; the judgment is in the layout rules, which exist because their violations are the
diagrams that come back wrong.

## When to use it

- "Diagram our stack / topology / deployment", "map the architecture", "show how data flows"
- Cloud infrastructure (VPC, regions, managed services), microservice and service-mesh maps
- Database + API maps, on-call run-book overviews, migration before/after pictures

## When not to use it

- Physics, chemistry, biology, floor plans, anatomy, narrative journeys — different domain, different
  visual language.
- Hand-drawn whiteboard sketches or quick UI mockups — use a sketch skill instead; that job is
  disposable variants, this one is one deliberate artifact.
- Subject matter too abstract for boxes and arrows (workflows with time as the main axis) — a
  sequence-style diagram serves better than a topology.

## Design system

**Semantic colors** — component type decides fill and stroke; never color-decorate arbitrarily.

| Component type | Fill (rgba) | Stroke |
| --- | --- | --- |
| Frontend | `rgba(8, 51, 68, 0.4)` | `#22d3ee` (cyan) |
| Backend / worker | `rgba(6, 78, 59, 0.4)` | `#34d399` (emerald) |
| Database / cache | `rgba(76, 29, 149, 0.4)` | `#a78bfa` (violet) |
| Cloud service | `rgba(120, 53, 15, 0.3)` | `#fbbf24` (amber) |
| Security | `rgba(136, 19, 55, 0.4)` | `#fb7185` (rose) |
| Message bus | `rgba(251, 146, 60, 0.3)` | `#fb923c` (orange) |
| External | `rgba(30, 41, 59, 0.5)` | `#94a3b8` (slate) |

- Font: JetBrains Mono (Google Fonts `<link>`), 11–12px names, 9px sublabels, 8–7px annotations.
- Background: `#020617` with a subtle 40px grid pattern; cards/boundaries on `#1e293b` borders.
- Region boundaries: dashed `8,4`, amber, `rx="12"`, transparent amber-tinted fill.
- Security groups: dashed `4,4`, rose, transparent fill, label at top-left inside (`sg-name :port`).

## The template skeleton

Build every diagram from this structure; it is verified to render, export, and behave standalone —
the `[...]` slots are yours to fill:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>[PROJECT] Architecture Diagram</title>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js" integrity="sha384-ZZ1pncU3bQe8y31yfZdMFdSpttDoPmOZg2wguVK9almUodir1PghgT0eY7Mrty8H" crossorigin="anonymous"></script>
  <script src="https://cdn.jsdelivr.net/npm/jspdf@2.5.2/dist/jspdf.umd.min.js" integrity="sha384-en/ztfPSRkGfME4KIm05joYXynqzUgbsG5nMrj/xEFAHXkeZfO3yMK8QQ+mP7p1/" crossorigin="anonymous"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'JetBrains Mono', monospace; background: #020617; min-height: 100vh; padding: 2rem; color: white; }
    .container { max-width: 1200px; margin: 0 auto; }
    .header { margin-bottom: 2rem; }
    .header-row { display: flex; align-items: center; gap: 1rem; margin-bottom: 0.5rem; }
    .pulse-dot { width: 12px; height: 12px; background: #22d3ee; border-radius: 50%; animation: pulse 2s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
    h1 { font-size: 1.5rem; font-weight: 700; letter-spacing: -0.025em; }
    .subtitle { color: #94a3b8; font-size: 0.875rem; margin-left: 1.75rem; }
    .diagram-container { background: rgba(15, 23, 42, 0.5); border-radius: 1rem; border: 1px solid #1e293b; padding: 1.5rem; overflow-x: auto; }
    svg { width: 100%; min-width: 900px; display: block; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; margin-top: 2rem; }
    .card { background: rgba(15, 23, 42, 0.5); border-radius: 0.75rem; border: 1px solid #1e293b; padding: 1.25rem; }
    .card-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.75rem; }
    .card-dot { width: 8px; height: 8px; border-radius: 50%; }
    .card-dot.cyan { background: #22d3ee; }
    .card-dot.emerald { background: #34d399; }
    .card-dot.violet { background: #a78bfa; }
    .card-dot.amber { background: #fbbf24; }
    .card-dot.rose { background: #fb7185; }
    .card h3 { font-size: 0.875rem; font-weight: 600; }
    .card ul { list-style: none; color: #94a3b8; font-size: 0.75rem; }
    .card li { margin-bottom: 0.375rem; }
    .footer { text-align: center; margin-top: 1.5rem; color: #475569; font-size: 0.75rem; }
    .toolbar { display: flex; gap: 0.5rem; margin-left: auto; flex-shrink: 0; align-items: center; }
    .toolbar-toggle { background: transparent; border: none; color: #475569; cursor: pointer; font-size: 1.25rem; line-height: 1; padding: 0.25rem 0.5rem; border-radius: 0.375rem; transition: color 0.2s, background 0.2s; }
    .toolbar-toggle:hover { color: #94a3b8; background: rgba(30, 41, 59, 0.5); }
    .toolbar-actions { display: none; gap: 0.5rem; }
    .toolbar.expanded .toolbar-actions { display: flex; }
    .toolbar-actions button { background: rgba(30, 41, 59, 0.8); border: 1px solid #334155; color: #94a3b8; padding: 0.375rem 0.75rem; border-radius: 0.375rem; font-family: inherit; font-size: 0.75rem; cursor: pointer; transition: all 0.2s; white-space: nowrap; }
    .toolbar-actions button:hover { background: rgba(51, 65, 85, 0.8); color: white; border-color: #475569; }
    @media print { .toolbar { display: none !important; } }
  </style>
</head>
<body>
  <div class="container" id="report-container">
    <div class="header">
      <div class="header-row">
        <div class="pulse-dot"></div>
        <h1>[PROJECT] Architecture</h1>
        <div class="toolbar">
          <div class="toolbar-actions">
            <button onclick="copyAsImage(this)">📋 Copy</button>
            <button onclick="downloadPNG(this)">🖼️ PNG</button>
            <button onclick="downloadPDF(this)">📄 PDF</button>
          </div>
          <button class="toolbar-toggle" onclick="this.parentElement.classList.toggle('expanded')" title="Export options" aria-label="Export options">⋯</button>
        </div>
      </div>
      <p class="subtitle">[One-line description]</p>
    </div>

    <div class="diagram-container">
      <svg viewBox="0 0 1000 680">
        <defs>
          <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#64748b" />
          </marker>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" stroke-width="0.5"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />

        <!-- 1. ARROWS FIRST: they render behind everything drawn later -->
        <!-- 2. BOUNDARIES (regions, then security groups) -->
        <!-- 3. COMPONENT BOXES -->
        <!-- 4. LEGEND, below every other element -->
      </svg>
    </div>

    <div class="cards">
      <div class="card">
        <div class="card-header"><div class="card-dot cyan"></div><h3>[Card 1]</h3></div>
        <ul><li>• [Item]</li><li>• [Item]</li><li>• [Item]</li><li>• [Item]</li></ul>
      </div>
      <div class="card">
        <div class="card-header"><div class="card-dot emerald"></div><h3>[Card 2]</h3></div>
        <ul><li>• [Item]</li><li>• [Item]</li><li>• [Item]</li><li>• [Item]</li></ul>
      </div>
      <div class="card">
        <div class="card-header"><div class="card-dot violet"></div><h3>[Card 3]</h3></div>
        <ul><li>• [Item]</li><li>• [Item]</li><li>• [Item]</li><li>• [Item]</li></ul>
      </div>
    </div>

    <p class="footer">[Project] • [Metadata]</p>
  </div>

  <script>
    async function capture() {
      const el = document.getElementById('report-container');
      const r = el.getBoundingClientRect();
      const pad = 32;
      return await html2canvas(document.body, { backgroundColor: '#020617', scale: 2, useCORS: true, ignoreElements: (e) => e.classList && e.classList.contains('toolbar'), x: r.left + window.scrollX - pad, y: r.top + window.scrollY - pad, width: r.width + pad * 2, height: r.height + pad * 2 });
    }
    async function copyAsImage(btn) {
      const orig = btn.textContent;
      try {
        const canvas = await capture();
        const blob = await new Promise(r => canvas.toBlob(r, 'image/png'));
        await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
        btn.textContent = '✓ Copied!';
      } catch (e) { btn.textContent = '✗ Failed'; }
      setTimeout(() => btn.textContent = orig, 2000);
    }
    async function downloadPNG(btn) {
      const orig = btn.textContent;
      btn.textContent = '⏳ ...';
      try {
        const canvas = await capture();
        const link = document.createElement('a');
        link.download = '[project]-architecture.png';
        link.href = canvas.toDataURL('image/png');
        link.click();
        btn.textContent = '✓ Done!';
      } catch (e) { btn.textContent = '✗ Failed'; }
      setTimeout(() => btn.textContent = orig, 2000);
    }
    async function downloadPDF(btn) {
      const orig = btn.textContent;
      btn.textContent = '⏳ ...';
      try {
        const canvas = await capture();
        const { jsPDF } = window.jspdf;
        const orientation = canvas.width > canvas.height ? 'landscape' : 'portrait';
        const pdf = new jsPDF({ orientation, unit: 'px', format: [canvas.width, canvas.height], hotfixes: ['px_scaling'] });
        pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, 0, canvas.width, canvas.height);
        pdf.save('[project]-architecture.pdf');
        btn.textContent = '✓ Done!';
      } catch (e) { btn.textContent = '✗ Failed'; }
      setTimeout(() => btn.textContent = orig, 2000);
    }
  </script>
</body>
</html>
```

### SVG building blocks

```svg
<!-- Component box (double-rect: opaque mask so arrows don't show through, styled rect on top) -->
<rect x="X" y="Y" width="W" height="H" rx="6" fill="#0f172a"/>
<rect x="X" y="Y" width="W" height="H" rx="6" fill="FILL" stroke="STROKE" stroke-width="1.5"/>
<text x="CX" y="Y+20" fill="white" font-size="11" font-weight="600" text-anchor="middle">NAME</text>
<text x="CX" y="Y+36" fill="#94a3b8" font-size="9" text-anchor="middle">sublabel</text>

<!-- Arrow with label -->
<line x1="A" y1="B" x2="C" y2="D" stroke="STROKE" stroke-width="1.5" marker-end="url(#arrowhead)"/>
<text x="MID_X" y="B-6" fill="#94a3b8" font-size="9" text-anchor="middle">label</text>

<!-- Auth/security flow: dashed rose -->
<path d="M ... " fill="none" stroke="#fb7185" stroke-width="1.5" stroke-dasharray="5,5" marker-end="url(#arrowhead)"/>

<!-- Message bus in a gap -->
<rect x="X" y="Y" width="120" height="20" rx="4" fill="rgba(251, 146, 60, 0.3)" stroke="#fb923c" stroke-width="1"/>
<text x="CX" y="Y+14" fill="#fb923c" font-size="7" text-anchor="middle">Kafka / RabbitMQ</text>

<!-- Region boundary -->
<rect x="X" y="Y" width="W" height="H" rx="12" fill="rgba(251, 191, 36, 0.05)" stroke="#fbbf24" stroke-width="1" stroke-dasharray="8,4"/>
<text x="X+12" y="Y+18" fill="#fbbf24" font-size="10" font-weight="600">AWS Region: [name]</text>

<!-- Security group -->
<rect x="X" y="Y" width="W" height="H" rx="8" fill="transparent" stroke="#fb7185" stroke-width="1" stroke-dasharray="4,4"/>
<text x="X+4" y="Y+14" fill="#fb7185" font-size="8">sg-name :port</text>
```

## Layout rules

- **Draw order (critical):** arrows early (right after the grid), then boundaries, then component
  boxes, then legend. SVG paints in document order; late arrows render on top of boxes.
- **Mask arrows behind transparent fills:** each component box is drawn as two rects — an opaque
  `#0f172a` backer, then the `rgba(..., 0.4)` styled rect. Otherwise arrows pass through the fill.
- **Spacing:** services 60px tall, larger boxes 80–120px; minimum 40px vertical gap. Place message
  buses **inside the gap** (a 20px bus centered in a 40px gap), never overlapping either neighbor.
- **Arrows land on edges, not labels.** An arrowhead that stops over a text label (a security-group
  tag, a port, a title) partially hides it. Endpoint coordinates are chosen deliberately: land on a
  box edge or boundary line, clear of every label — verify by reading the numbers, not hoping.
- **Legend placement (critical):** below the lowest boundary, never inside one. Compute
  `max(boundary.y + boundary.height)` and place the legend at least 20px below it, expanding the
  `viewBox` height as needed. (The upstream template contradicts its own rule here — the legend in
  its example sits inside the region box. Follow the rule, not the example.)
- **Coordinate discipline:** pick a column grid (External / Edge / App / Data reads well), keep box
  widths uniform per column, and write the arrow endpoints against the box coordinates you chose.
  Most broken arrows are arithmetic slips, so re-derive each endpoint from the boxes it connects.

## Verification (do not skip)

**Do not deliver an HTML diagram you have not seen rendered.** If an agent can drive a browser:

1. Open the file; assert zero console errors (`window.addEventListener("error", ...)`).
2. Open export paths at least once across the whole job — measured working: PNG capture produced a
   2528×2618 non-blank canvas (~560 KB data URL) and jsPDF produced `application/pdf` (~8.7 MB with
   scale 1; multi-MB output is normal — raster pixels, not vectors).
3. Read the layout as numbers: label endpoints vs box edges, legend Y vs boundary bottoms, bus Y
   within its gap. Screenshot the finished state.

If a browser is unavailable, say so and re-derive the endpoints by hand; do not present hope as done.

## Export toolbar

Ships with every diagram: a `⋯` toggle revealing 📋 Copy (high-DPI PNG to clipboard), 🖼️ PNG, and
📄 PDF (PNG embedded in a one-page PDF via jsPDF) — one shared html2canvas capture, toolbar
excluded, 32px padding (skeleton above). Two CDN scripts in `<head>`, **pinned and
SRI-hashed** — verified against the live CDN bytes: `html2canvas@1.4.1` and `jspdf@2.5.2`. If you
bump a version, recompute the integrity hash from the new file; never copy a hash between versions.

Measurables and limits, from actually running it:

- PNG capture works from `file://`; JPEG for PDF embedding, PNG for images; both need the
  `viewBox` content to be plain SVG — `<foreignObject>` renders inconsistently (avoid).
- Clipboard write needs **user focus** on the page: from an unfocused/automated tab it rejects with
  `NotAllowedError: Document is not focused` — the button still works for a human whose tab is
  focused, but **PNG download is the path that always works in an agent session**; use it to
  hand the user a real file.
- The capture excludes the toolbar and uses `getBoundingClientRect()`, so scrolling never skewers
  the crop; `scale: 2` is the default, 3–4 buys resolution for print.
- The user's connection must reach cdn.jsdelivr.net for the toolbar (the diagram itself renders
  fine without it; export buttons then show ✗). Font loads from Google Fonts; with neither, the
  page falls back to system monospace. Prefer **plain-CSS-only, no-JS diagrams** when the user asks
  for something embeddable (wikis/issue trackers): drop the toolbar, keep the SVG.

## Gotchas learned the hard way

- SRI hashes must match exactly — a wrong `integrity=` blocks the script silently and every export
  button fails; the two in this document were verified against the live CDN files.
- The upstream template contradicts itself on the legend (inside vs below boundaries) — follow the
  rule, not the example.
- Multi-MB PDFs are expected — the PDF is a rasterized PNG, not vector.
- The clipboard path requires page focus (see Verification); a human at the browser gets working
  Copy, but downloadPNG is the reliable handoff — produce a file the user can open right away.
- Keep every CSS declaration on one line. The generated page is an artifact whose source users may
  edit — compact CSS reads like a style sheet, not a config dump.

## Attribution

Adapted from [Cocoon AI's architecture-diagram-generator](https://github.com/Cocoon-AI/architecture-diagram-generator)
(MIT, © 2025 Cocoon AI) — the design system, component/arrow/security patterns and export toolbar
come from upstream v1.1; layout-rule gotchas verified independently.