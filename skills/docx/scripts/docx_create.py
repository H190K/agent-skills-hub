#!/usr/bin/env python3
# MIT License. Part of the Hermes docx skill.
"""Create a .docx document from a JSON spec.

Usage: docx_create.py spec.json output.docx
Run with --help for the spec format summary.

Spec (JSON object):
{
  "page": {"width_mm": 210, "height_mm": 297,
           "margins_mm": {"top": 25, "bottom": 25, "left": 20, "right": 20}},
  "header": "text shown in page header",
  "footer": "text shown in page footer",
  "footer_page_numbers": true,
  "styles": [{"name": "MyStyle", "base": "Normal", "font": "Arial",
              "size_pt": 12, "bold": true, "color": "1F4E79"}],
  "blocks": [
    {"type": "heading", "text": "Title", "level": 1},
    {"type": "paragraph", "style": "MyStyle", "alignment": "right",
     "shading": "F0F4F8", "border_bottom": "0F3556",
     "runs": [
        {"text": "plain "}, {"text": "bold", "bold": true},
        {"text": " italic", "italic": true},
        {"text": " under", "underline": true}]},
    {"type": "paragraph", "text": "shortcut: single plain run"},
    {"type": "bullet_list", "items": ["a", "b"], "alignment": "right"},
    {"type": "numbered_list", "items": ["one", "two"]},
    {"type": "table", "header": ["Col1", "Col2"],
     "rows": [["1", "2"]], "style": "Light Grid Accent 1",
     "header_bold": true},
    {"type": "image", "path": "pic.png", "width_mm": 60},
    {"type": "page_break"},
    {"type": "toc"}
  ]
}

Extras:
  * `"footer_page_numbers": true` at the top level adds a "Page X of Y"
    footer built from PAGE/NUMPAGES fields. The page-number line is
    written into a SEPARATE paragraph below the footer text so the two
    don't collide on one line.
  * A `toc` block inserts a Table of Contents field.
  * Per-paragraph `"alignment"` values: "left" | "center" | "right" |
    "justify".
  * `"shading"` (hex color) on a paragraph renders a solid background
    bar — use this for badge/header/footer cards.
  * `"border_bottom"` (hex color) on a paragraph adds a colored bottom
    rule under the paragraph — useful for headline underlines.

All field results (TOC entries, PAGE/NUMPAGES numbers) are computed by
Word/LibreOffice when the file is opened, not by python-docx.

Arabic / RTL notes (added 2026-09-01 for polished templates):
  * The script defaults to Arabic (ar-SA) language and bidi direction on
    the document defaults so any Arabic text renders right-to-left
    without per-run configuration.
  * Every paragraph block applies per-run `w:rtl="1"` and `xml:lang`
    tagging automatically; you do NOT need to set them in the spec.
  * Header text is right-aligned and its paragraph carries a `w:bidi`
    flag for guaranteed RTL.
  * Tables get `w:bidiVisual` on `tblPr` so columns read right-to-left;
    cell paragraphs are also right-aligned.
  * Bullet/numbered lists inherit an Arabic font and right-alignment.
  * Recommended Arabic font fallbacks for visual polish: "Noto Kufi
    Arabic" for headings, "Noto Naskh Arabic" for body. "Noto Sans
    Arabic" works as a neutral sans-serif.
"""
from __future__ import annotations

import argparse
import json
import sys

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_BREAK
from docx.shared import Mm, Pt, RGBColor


def apply_page(doc, page: dict) -> None:
    section = doc.sections[0]
    if "width_mm" in page:
        section.page_width = Mm(page["width_mm"])
    if "height_mm" in page:
        section.page_height = Mm(page["height_mm"])
    m = page.get("margins_mm", {})
    for side in ("top", "bottom", "left", "right"):
        if side in m:
            setattr(section, f"{side}_margin", Mm(m[side]))


def add_styles(doc, styles: list) -> None:
    for s in styles:
        style = doc.styles.add_style(s["name"], WD_STYLE_TYPE.PARAGRAPH)
        if s.get("base"):
            style.base_style = doc.styles[s["base"]]
        font = style.font
        if s.get("font"):
            font.name = s["font"]
        if s.get("size_pt"):
            font.size = Pt(s["size_pt"])
        if s.get("bold") is not None:
            font.bold = s["bold"]
        if s.get("italic") is not None:
            font.italic = s["italic"]
        if s.get("color"):
            font.color.rgb = RGBColor.from_string(s["color"])


def add_runs(para, block: dict) -> None:
    runs = block.get("runs")
    if runs is None:
        runs = [{"text": block.get("text", "")}]
    for r in runs:
        run = para.add_run(r.get("text", ""))
        if r.get("bold"):
            run.bold = True
        if r.get("italic"):
            run.italic = True
        if r.get("underline"):
            run.underline = True


def _apply_run_font_color(run, hex_color: str) -> None:
    from docx.shared import RGBColor as _RGB
    run.font.color.rgb = _RGB.from_string(hex_color)


def _shade_paragraph(para, fill_hex: str) -> None:
    """Add a solid background fill to a paragraph (renders as a colored bar)."""
    from docx.oxml.ns import qn as _q
    from lxml import etree as _et
    pPr = para._element.find(_q("w:pPr"))
    if pPr is None:
        pPr = _et.SubElement(para._element, _q("w:pPr"))
        para._element.insert(0, pPr)
    shd = pPr.find(_q("w:shd"))
    if shd is None:
        shd = _et.SubElement(pPr, _q("w:shd"))
    shd.set(_q("w:val"), "clear")
    shd.set(_q("w:color"), "auto")
    shd.set(_q("w:fill"), fill_hex)


def _border_paragraph_bottom(para, color_hex: str, sz: int = 12) -> None:
    """Add a colored bottom border under a paragraph (heading underline)."""
    from docx.oxml.ns import qn as _q
    from lxml import etree as _et
    pPr = para._element.find(_q("w:pPr"))
    if pPr is None:
        pPr = _et.SubElement(para._element, _q("w:pPr"))
        para._element.insert(0, pPr)
    pbdr = pPr.find(_q("w:pBdr"))
    if pbdr is None:
        pbdr = _et.SubElement(pPr, _q("w:pBdr"))
    bottom = pbdr.find(_q("w:bottom"))
    if bottom is None:
        bottom = _et.SubElement(pbdr, _q("w:bottom"))
    bottom.set(_q("w:val"), "single")
    bottom.set(_q("w:sz"), str(sz))
    bottom.set(_q("w:space"), "4")
    bottom.set(_q("w:color"), color_hex)


_ALIGN = {"center": 1, "right": 2, "left": 0, "justify": 3}


def _maybe_align(para, block: dict) -> None:
    if "alignment" in block and block["alignment"] in _ALIGN:
        from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
        para.alignment = WD_PARAGRAPH_ALIGNMENT(_ALIGN[block["alignment"]])


def add_block(doc, block: dict) -> None:
    btype = block["type"]
    if btype == "heading":
        para = doc.add_heading(block.get("text", ""), level=block.get("level", 1))
        _maybe_align(para, block)
        # Force RTL on heading runs so Arabic reads correctly
        for run in para.runs:
            run._element.getparent().set("{http://www.w3.org/XML/1998/namespace}lang", "ar-SA")
            rpr = run._element.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rPr")
            if rpr is not None:
                from docx.oxml.ns import qn
                rtl = rpr.find(qn("w:rtl"))
                if rtl is None:
                    from lxml import etree
                    rtl = etree.SubElement(rpr, qn("w:rtl"))
                rtl.set(qn("w:val"), "1")
    elif btype == "paragraph":
        para = doc.add_paragraph(style=block.get("style"))
        add_runs(para, block)
        _maybe_align(para, block)
        # Optional paragraph shading (renders as a colored bar/box)
        if "shading" in block:
            _shade_paragraph(para, block["shading"])
        # Optional paragraph bottom border
        if "border_bottom" in block:
            _border_paragraph_bottom(para, block["border_bottom"])
        # Tag every run as RTL Arabic so word/LibreOffice render right-to-left
        from docx.oxml.ns import qn as _q
        from lxml import etree as _et
        for run in para.runs:
            rpr = run._element.find(_q("w:rPr"))
            if rpr is None:
                rpr = _et.SubElement(run._element, _q("w:rPr"))
                run._element.insert(0, rpr)
            rtl = rpr.find(_q("w:rtl"))
            if rtl is None:
                rtl = _et.SubElement(rpr, _q("w:rtl"))
            rtl.set(_q("w:val"), "1")
            for r in run._element.iter(_q("w:r")):
                r.set("{http://www.w3.org/XML/1998/namespace}lang", "ar-SA")
    elif btype == "bullet_list":
        for item in block.get("items", []):
            p = doc.add_paragraph(item, style="List Bullet")
            _maybe_align(p, {"alignment": "right"})
            from docx.oxml.ns import qn as _q
            from lxml import etree as _et
            for run in p.runs:
                rpr = run._element.find(_q("w:rPr"))
                if rpr is None:
                    rpr = _et.SubElement(run._element, _q("w:rPr"))
                    run._element.insert(0, rpr)
                rtl = rpr.find(_q("w:rtl"))
                if rtl is None:
                    rtl = _et.SubElement(rpr, _q("w:rtl"))
                rtl.set(_q("w:val"), "1")
    elif btype == "numbered_list":
        for item in block.get("items", []):
            p = doc.add_paragraph(item, style="List Number")
            _maybe_align(p, {"alignment": "right"})
    elif btype == "table":
        header = block.get("header", [])
        rows = block.get("rows", [])
        ncols = len(header) if header else (len(rows[0]) if rows else 1)
        table = doc.add_table(rows=0, cols=ncols)
        table.style = block.get("style", "Table Grid")
        # Set RTL direction on table
        from docx.oxml.ns import qn as _q
        from lxml import etree as _et
        tblPr = table._element.tblPr
        bidi = tblPr.find(_q("w:bidiVisual"))
        if bidi is None:
            _et.SubElement(tblPr, _q("w:bidiVisual"))
        if header:
            cells = table.add_row().cells
            for i, text in enumerate(header):
                cells[i].text = str(text)
                if block.get("header_bold", True):
                    for para in cells[i].paragraphs:
                        for run in para.runs:
                            run.bold = True
                        para.alignment = 2  # right
        for row in rows:
            cells = table.add_row().cells
            for i, text in enumerate(row):
                cells[i].text = str(text)
                for para in cells[i].paragraphs:
                    para.alignment = 2  # right-align Arabic cells
    elif btype == "image":
        width = Mm(block["width_mm"]) if block.get("width_mm") else None
        doc.add_picture(block["path"], width=width)
    elif btype == "page_break":
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    elif btype == "toc":
        from docx_edit import _add_field
        para = doc.add_paragraph()
        _add_field(para, r' TOC \o "1-3" \h \z \u ',
                   "Table of contents - open in Word/LibreOffice and "
                   "update fields to populate.")
    else:
        raise ValueError(f"unknown block type: {btype}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Create a .docx from a JSON spec.",
        epilog="See the module docstring (top of this file) for the spec format.")
    ap.add_argument("spec", help="path to JSON spec file")
    ap.add_argument("output", help="path of .docx to write")
    args = ap.parse_args()

    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)

    doc = Document()
    if spec.get("page"):
        apply_page(doc, spec["page"])
    if spec.get("styles"):
        add_styles(doc, spec["styles"])

    # Set the document default language to Arabic (RTL)
    try:
        from docx.oxml.ns import qn
        styles_el = doc.styles.element
        docDefaults = styles_el.find(qn("w:docDefaults"))
        if docDefaults is not None:
            rPrDefault = docDefaults.find(qn("w:rPrDefault"))
            if rPrDefault is not None:
                rpr = rPrDefault.find(qn("w:rPr"))
                if rpr is not None:
                    lang = rpr.find(qn("w:lang"))
                    if lang is None:
                        from lxml import etree
                        lang = etree.SubElement(rpr, qn("w:lang"))
                    lang.set(qn("w:val"), "ar-SA")
                    lang.set(qn("w:eastAsia"), "ar-SA")
                    lang.set(qn("w:bidi"), "ar-SA")
                    rtl = rpr.find(qn("w:rtl"))
                    if rtl is None:
                        from lxml import etree as et
                        rtl = et.SubElement(rpr, qn("w:rtl"))
                    rtl.set(qn("w:val"), "1")
    except Exception as e:
        print(f"warning: could not set docDefaults language: {e}", file=__import__("sys").stderr)

    if spec.get("header"):
        hdr = doc.sections[0].header.paragraphs[0]
        hdr.text = spec["header"]
        hdr.alignment = 2  # right for Arabic
        for r in hdr.runs:
            r.font.name = "Noto Naskh Arabic"
            # Mark header paragraph as bidi/RTL
            from docx.oxml.ns import qn as __q
            from lxml import etree as __et
            rpr = r._element.find(__q("w:rPr"))
            if rpr is None:
                rpr = __et.SubElement(r._element, __q("w:rPr"))
                r._element.insert(0, rpr)
            rtl = rpr.find(__q("w:rtl"))
            if rtl is None:
                rtl = __et.SubElement(rpr, __q("w:rtl"))
            rtl.set(__q("w:val"), "1")
            rpr_color = rpr.find(__q("w:color"))
            if rpr_color is None:
                rpr_color = __et.SubElement(rpr, __q("w:color"))
            rpr_color.set(__q("w:val"), "0F3556")
        # Mark header paragraphs as RTL
        from docx.oxml.ns import qn as __q
        for p in doc.sections[0].header.paragraphs:
            pPr = p._element.find(__q("w:pPr"))
            if pPr is not None:
                bidi = pPr.find(__q("w:bidi"))
                if bidi is None:
                    from lxml import etree as __et
                    bidi = __et.SubElement(pPr, __q("w:bidi"))
                bidi.set(__q("w:val"), "1")
                # Add a bottom border to header
                pbdr = pPr.find(__q("w:pBdr"))
                if pbdr is None:
                    from lxml import etree as __et
                    pbdr = __et.SubElement(pPr, __q("w:pBdr"))
                bottom = pbdr.find(__q("w:bottom"))
                if bottom is None:
                    from lxml import etree as __et
                    bottom = __et.SubElement(pbdr, __q("w:bottom"))
                bottom.set(__q("w:val"), "single")
                bottom.set(__q("w:sz"), "6")
                bottom.set(__q("w:space"), "1")
                bottom.set(__q("w:color"), "0F3556")
    if spec.get("footer"):
        ftr = doc.sections[0].footer.paragraphs[0]
        ftr.text = spec["footer"]
        ftr.alignment = 1  # center
    for block in spec.get("blocks", []):
        add_block(doc, block)
    if spec.get("footer_page_numbers"):
        from docx_edit import _add_field
        from docx.shared import Pt as _Pt
        from docx.oxml.ns import qn as _qns
        from lxml import etree as _lt
        # Use a SEPARATE paragraph so the page number doesn't collide
        # with the centered footer text on the same line.
        page_para = doc.sections[0].footer.add_paragraph()
        page_para.alignment = 2  # right-align for Arabic
        # Add thin top border separator to give it visual room
        ppr = page_para._element.find(_qns("w:pPr"))
        if ppr is None:
            ppr = _lt.SubElement(page_para._element, _qns("w:pPr"))
            page_para._element.insert(0, ppr)
        pbdr = _lt.SubElement(ppr, _qns("w:pBdr"))
        top = _lt.SubElement(pbdr, _qns("w:top"))
        top.set(_qns("w:val"), "single")
        top.set(_qns("w:sz"), "6")
        top.set(_qns("w:space"), "1")
        top.set(_qns("w:color"), "1F4E79")
        run1 = page_para.add_run("صفحة ")
        run1.font.size = _Pt(10)
        run1.font.color.rgb = __import__("docx").shared.RGBColor.from_string("555555")
        _add_field(page_para, " PAGE ", "1")
        run2 = page_para.add_run(" من ")
        run2.font.size = _Pt(10)
        run2.font.color.rgb = __import__("docx").shared.RGBColor.from_string("555555")
        _add_field(page_para, " NUMPAGES ", "1")
    doc.save(args.output)
    print(json.dumps({"ok": True, "output": args.output,
                      "blocks": len(spec.get("blocks", []))}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
