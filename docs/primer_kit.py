"""Shared reportlab kit for the QUANTGEN primers: DejaVu fonts, paragraph
styles and the flowable helpers (P, F, B, TBL, BOX, FIG, CODE) plus the
document template with a footer and PDF outline. `build_models_primer.py`
predates this module and keeps its own copy; new primers import from here."""
from __future__ import annotations

import hashlib
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, PageBreak,
                                PageTemplate, Paragraph, Preformatted, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

_FONT_DIR = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
for _name, _file in (("DejaVuSans", "DejaVuSans.ttf"), ("DejaVuSans-Bold", "DejaVuSans-Bold.ttf"),
                     ("DejaVuSans-Oblique", "DejaVuSans-Oblique.ttf"),
                     ("DejaVuSans-BoldOblique", "DejaVuSans-BoldOblique.ttf"),
                     ("DejaVuSansMono", "DejaVuSansMono.ttf"), ("DejaVuSerif", "DejaVuSerif.ttf")):
    pdfmetrics.registerFont(TTFont(_name, os.path.join(_FONT_DIR, _file)))
pdfmetrics.registerFontFamily("DejaVuSans", normal="DejaVuSans", bold="DejaVuSans-Bold",
                              italic="DejaVuSans-Oblique", boldItalic="DejaVuSans-BoldOblique")
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 9,
                     "axes.labelsize": 8, "legend.fontsize": 7.5, "figure.dpi": 150,
                     "axes.grid": True, "grid.alpha": 0.3, "grid.linewidth": 0.5,
                     "axes.spines.top": False, "axes.spines.right": False})
FIG_W = 15 / 2.54
C_MAIN, C_ALT, C_GREY, C_RED, C_GREEN = "#1f4e79", "#c0504d", "#7f7f7f", "#b22222", "#2e7d32"

MARGIN = 2.2 * cm
TEXT_W = A4[0] - 2 * MARGIN
_BASE = dict(fontName="DejaVuSans", fontSize=10, leading=14, spaceAfter=6)
ST = {
    "body": ParagraphStyle("body", **_BASE),
    "H1": ParagraphStyle("H1", fontName="DejaVuSans-Bold", fontSize=16, leading=20, spaceBefore=6, spaceAfter=10, keepWithNext=True),
    "TOCH": ParagraphStyle("TOCH", fontName="DejaVuSans-Bold", fontSize=16, leading=20, spaceAfter=10),
    "H2": ParagraphStyle("H2", fontName="DejaVuSans-Bold", fontSize=12.5, leading=16, spaceBefore=12, spaceAfter=6, keepWithNext=True),
    "H3": ParagraphStyle("H3", fontName="DejaVuSans-Bold", fontSize=10.5, leading=14, spaceBefore=8, spaceAfter=4),
    "formula": ParagraphStyle("formula", fontName="DejaVuSerif", fontSize=11, leading=16, leftIndent=1.2 * cm, spaceBefore=3, spaceAfter=7),
    "code": ParagraphStyle("code", fontName="DejaVuSansMono", fontSize=8.5, leading=11),
    "caption": ParagraphStyle("caption", fontName="DejaVuSans-Oblique", fontSize=8.5, leading=11,
                              textColor=colors.HexColor("#444444"), spaceBefore=4, spaceAfter=12),
    "cell": ParagraphStyle("cell", fontName="DejaVuSans", fontSize=8, leading=10),
    "cellb": ParagraphStyle("cellb", fontName="DejaVuSans-Bold", fontSize=8, leading=10),
    "bullet": ParagraphStyle("bullet", leftIndent=16, bulletIndent=4, bulletFontName="DejaVuSans", **_BASE),
    "title": ParagraphStyle("title", fontName="DejaVuSans-Bold", fontSize=26, leading=32, spaceAfter=14),
    "subtitle": ParagraphStyle("subtitle", fontName="DejaVuSans", fontSize=12.5, leading=17, spaceAfter=8, textColor=colors.HexColor("#333333")),
    "small": ParagraphStyle("small", fontName="DejaVuSans", fontSize=8.5, leading=11, spaceAfter=4),
    "boxtitle": ParagraphStyle("boxtitle", fontName="DejaVuSans-Bold", fontSize=9.5, leading=12, spaceAfter=3),
}
_GRID = colors.HexColor("#BBBBBB")
_HEAD_BG = colors.HexColor("#E8EEF5")
_CODE_BG = colors.HexColor("#F3F4F6")


def P(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, ST[style])


def P3(text: str) -> list:
    return [CondPageBreak(3 * cm), P(text, "H3")]


def F(formula: str) -> Paragraph:
    return Paragraph(formula, ST["formula"])


def B(items: list[str]) -> list:
    return [Paragraph(t, ST["bullet"], bulletText="•") for t in items]


def CODE(text: str) -> Table:
    t = Table([[Preformatted(text.strip("\n"), ST["code"])]], colWidths=[TEXT_W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), _CODE_BG), ("BOX", (0, 0), (-1, -1), 0.4, _GRID),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    t.spaceAfter = 8
    return t


def TBL(header: list[str], rows: list[list], widths: list[float] | None = None, font: float = 9,
        wrap: bool = False, align_right_from: int | None = None) -> Table:
    if wrap:
        data = [[Paragraph(h, ST["cellb"]) for h in header]] + [[Paragraph(str(c), ST["cell"]) for c in row] for row in rows]
    else:
        data = [header] + rows
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [("FONTNAME", (0, 0), (-1, 0), "DejaVuSans-Bold"), ("FONTNAME", (0, 1), (-1, -1), "DejaVuSans"),
             ("FONTSIZE", (0, 0), (-1, -1), font), ("LEADING", (0, 0), (-1, -1), font + 2.5),
             ("BACKGROUND", (0, 0), (-1, 0), _HEAD_BG), ("GRID", (0, 0), (-1, -1), 0.35, _GRID),
             ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if align_right_from is not None:
        style.append(("ALIGN", (align_right_from, 1), (-1, -1), "RIGHT"))
    t.setStyle(TableStyle(style))
    t.spaceAfter = 8
    return t


def FIG(n: int, caption: str, path: str) -> KeepTogether:
    iw, ih = ImageReader(path).getSize()
    img = Image(path, width=15 * cm, height=15 * cm * ih / iw)
    img.hAlign = "CENTER"
    return KeepTogether([img, P(f"<b>Figure {n}</b> — {caption}", "caption")])


def BOX(title: str, items: list[str], color: str) -> Table:
    inner = [Paragraph(title, ST["boxtitle"])] + B(items)
    t = Table([[inner]], colWidths=[TEXT_W])
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1.2, colors.HexColor(color)),
                           ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    t.spaceAfter = 10
    return t


def TOC() -> list:
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("TOC1", fontName="DejaVuSans-Bold", fontSize=10, leading=15, leftIndent=0),
                       ParagraphStyle("TOC2", fontName="DejaVuSans", fontSize=9, leading=12.5, leftIndent=16)]
    toc.dotsMinLevel = 0
    return [P("Contents", "TOCH"), toc, PageBreak()]


class PrimerDoc(BaseDocTemplate):
    def __init__(self, path: str, title: str, footer: str):
        super().__init__(path, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN,
                         bottomMargin=MARGIN, title=title, author="QUANTGEN")
        self._footer_text = footer
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body")
        self.addPageTemplates([PageTemplate(id="body", frames=[frame], onPage=self._footer)])

    def _footer(self, canv, doc) -> None:
        canv.saveState()
        canv.setFont("DejaVuSans", 8)
        canv.setFillColor(colors.HexColor("#666666"))
        canv.drawString(MARGIN, 1.3 * cm, self._footer_text)
        canv.drawRightString(A4[0] - MARGIN, 1.3 * cm, str(doc.page))
        canv.restoreState()

    def afterFlowable(self, flowable) -> None:
        if isinstance(flowable, Paragraph) and flowable.style.name in ("H1", "H2"):
            level = 0 if flowable.style.name == "H1" else 1
            text = flowable.getPlainText()
            key = "s" + hashlib.md5(text.encode("utf-8")).hexdigest()[:10]
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=level, closed=level > 0)
            self.notify("TOCEntry", (level, text, self.page, key))


def glyph_check(src: str) -> None:
    """No Unicode sub/superscript glyphs, and every non-ASCII character exists in DejaVuSans."""
    bad = sorted({c for c in src if 0x2070 <= ord(c) <= 0x209F or ord(c) in (0xB2, 0xB3, 0xB9)})
    assert not bad, f"Unicode sub/superscript glyphs in source: {bad}"
    try:
        from fontTools.ttLib import TTFont as _TT
    except Exception:
        return
    cmap = _TT(os.path.join(_FONT_DIR, "DejaVuSans.ttf")).getBestCmap()
    missing = sorted(c for c in {c for c in src if ord(c) > 127} if ord(c) not in cmap)
    assert not missing, f"glyphs missing from DejaVuSans: {missing}"


__all__ = ["P", "P3", "F", "B", "CODE", "TBL", "FIG", "BOX", "TOC", "PrimerDoc", "glyph_check", "Spacer", "PageBreak",
           "KeepTogether", "cm", "A4", "TEXT_W", "FIG_W", "C_MAIN", "C_ALT", "C_GREY", "C_RED", "C_GREEN", "plt"]
