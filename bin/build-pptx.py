#!/usr/bin/env python3
"""Build the PowerPoint export of the event deck.

The reveal.js slides in slides/slides.adoc are the source of truth for the
narrative. This script produces the .pptx that event platforms and agency
review processes tend to insist on, carrying the same content, the same
speaker notes, and native (editable) PowerPoint graphics: a filing-season
demand curve, a chevron lifecycle flow, a layered architecture diagram, a
roadmap timeline and the ladder pyramid in the corner of every slide — real
shapes, not screenshots.

  python3 bin/build-pptx.py [--out slides/exports/redhat-ai-tax-administration.pptx]

Requires python-pptx (pip install python-pptx).
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

try:  # dash styles moved names across python-pptx versions
    from pptx.enum.line import MSO_LINE

    DASH = MSO_LINE.DASH
except Exception:  # pragma: no cover
    DASH = None

# Palette — the same one the HTML deck uses.
RED = RGBColor(0xCC, 0x00, 0x00)
RED_DARK = RGBColor(0xA3, 0x00, 0x00)
RED_WASH = RGBColor(0xFB, 0xEA, 0xE8)
RED_TINT = RGBColor(0xF6, 0xCD, 0xC8)
RED_TINT2 = RGBColor(0xED, 0xA7, 0x9F)
STEEL = RGBColor(0x28, 0x6C, 0x88)
STEEL_WASH = RGBColor(0xE7, 0xF1, 0xF5)
AMBER = RGBColor(0x96, 0x62, 0x0A)
AMBER_WASH = RGBColor(0xF8, 0xEF, 0xDC)
GREEN = RGBColor(0x1E, 0x7A, 0x55)
INK = RGBColor(0x1B, 0x12, 0x11)
INK_2 = RGBColor(0x54, 0x42, 0x3E)
INK_3 = RGBColor(0x7E, 0x6A, 0x64)
GROUND = RGBColor(0xFB, 0xF9, 0xF8)
SURFACE = RGBColor(0xFF, 0xFF, 0xFF)
SURFACE_2 = RGBColor(0xF4, 0xEF, 0xED)
BORDER = RGBColor(0xE6, 0xDD, 0xDA)
BORDER_STRONG = RGBColor(0xCF, 0xC2, 0xBE)
CHIP = RGBColor(0x54, 0x42, 0x3E)

# The ladder rungs follow the rainbow: red, orange, (yellow), green, (blue), violet.
R_DATA = RED
R_INFO = RGBColor(0xC2, 0x41, 0x0C)
R_KNOW = GREEN
R_JUDGE = RGBColor(0x5B, 0x2E, 0x91)
RB_YELLOW = RGBColor(0xD9, 0x9A, 0x00)   # the thin bands between the rungs
RB_BLUE = RGBColor(0x1D, 0x4E, 0xD8)

HEAD_FONT = "Red Hat Display"
BODY_FONT = "Red Hat Text"
MONO_FONT = "Red Hat Mono"

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)
MARGIN = Inches(0.85)


# ---------------------------------------------------------------- primitives
def add_base(prs, notes=""):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = GROUND
    rule = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, Emu(45720))
    rule.fill.solid()
    rule.fill.fore_color.rgb = RED
    rule.line.fill.background()
    rule.shadow.inherit = False
    if notes:
        slide.notes_slide.notes_text_frame.text = notes.strip()
    return slide


def add_text(slide, left, top, width, height, runs, align=PP_ALIGN.LEFT, anchor=None):
    """runs: list of (text, size, bold, colour, font, space_after_pt)."""
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    if anchor is not None:
        tf.vertical_anchor = anchor
    for index, (text, size, bold, colour, font, space_after) in enumerate(runs):
        para = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        para.alignment = align
        para.space_after = Pt(space_after)
        run = para.add_run()
        run.text = text
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = colour
        run.font.name = font
    return box


def solid(shape, fill, line=None, line_w=None):
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(line_w or 1)
    shape.shadow.inherit = False
    return shape


def rrect(slide, x, y, w, h, fill, line=None, line_w=None, radius=None):
    sp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    if radius is not None:
        try:
            sp.adjustments[0] = radius
        except Exception:
            pass
    return solid(sp, fill, line, line_w)


# ---------------------------------------------------------------- the ladder icon
# The deck's stacked pyramid (deck.html: PYR_TIERS / pyramidSVG). viewBox 150x38:
# judgement at the apex, data at the base, the rainbow's blue and yellow kept as
# thin bands between the rungs. A slide lights the rungs it serves; the rest are
# dimmed (the deck drops them to 20% opacity — here, a pale tint of the colour).
PYR_VIEW_W = 150.0
PYR_APEX = (24.0, 1.0)
PYR_BASE = (1.0, 47.0, 37.0)            # x-left, x-right, y
PYR_TIERS = [                           # colour, y-top, y-bottom, rungs that must all be lit
    (R_JUDGE, 1.0, 10.0, ("judgement",)),
    (RB_BLUE, 10.0, 11.6, ("judgement", "knowledge")),
    (R_KNOW, 11.6, 20.5, ("knowledge",)),
    (RB_YELLOW, 20.5, 22.0, ("knowledge", "information")),
    (R_INFO, 22.0, 30.0, ("information",)),
    (R_DATA, 30.0, 37.0, ("data",)),
]
PYR_LABELS = [("judgement", 8.0), ("knowledge", 17.5), ("information", 26.5), ("data", 35.0)]
PYR_LABEL_X = 54.0
PYR_W = Inches(1.6)                     # sits in the top margin band, right-aligned
PYR_TOP = Inches(0.12)

# Which rungs each slide serves: the deck's data-rungs, keyed by deck.html's
# data-title. Every pptx slide names the deck slide it corresponds to.
DECK_RUNGS = {
    "Title": ("data", "information", "knowledge", "judgement"),
    "AI in plain English": ("information", "knowledge", "judgement"),
    "Why now": ("data",),
    "Inside an LLM": ("data", "information", "knowledge", "judgement"),
    "Data to judgement": ("data", "information", "knowledge", "judgement"),
    "Two kinds of AI": ("information", "knowledge"),
    "Where AI lands": ("judgement",),
    "Five outcomes": ("data", "information", "knowledge", "judgement"),
    "Architecture": ("data", "information", "knowledge", "judgement"),
    "Why Red Hat AI": ("data", "information", "knowledge", "judgement"),
    "Why one platform": ("data", "information", "judgement"),
    "AI for operations": ("information", "knowledge", "judgement"),
    "Logs to MTTR": ("data", "information", "knowledge"),
    "Adoption path": ("data", "information", "knowledge"),
    "Next steps": ("judgement",),
    "Labs preview": ("data", "information", "knowledge", "judgement"),
    "One loop": ("data", "information", "knowledge", "judgement"),
    "Security posture": ("information", "judgement"),
}


def tint(colour, toward=SURFACE, amount=0.8):
    """Blend a colour `amount` of the way toward `toward` (stands in for opacity)."""
    return RGBColor(*(round(c + (t - c) * amount) for c, t in zip(colour, toward)))


def add_pyramid(slide, rungs, left, top, width):
    """Draw the ladder pyramid at (left, top): six stacked tiers cut to the triangle,
    lit for the rungs this slide serves, a thin outline and the four rung labels."""
    on = set(rungs)
    k = width / PYR_VIEW_W                # EMU per viewBox unit
    ax, ay = PYR_APEX
    bx0, bx1, by = PYR_BASE

    def X(v):
        return int(left + v * k)

    def Y(v):
        return int(top + v * k)

    def edges(y):                         # the triangle's left and right x at height y
        f = (y - ay) / (by - ay)
        return ax + (bx0 - ax) * f, ax + (bx1 - ax) * f

    def polygon(pts):
        ff = slide.shapes.build_freeform(*pts[0], scale=1)
        ff.add_line_segments(pts[1:], close=True)
        sp = ff.convert_to_shape()
        # drop the theme style reference: fill and line are set explicitly, and
        # its effect style would otherwise give the tiers a shadow in some viewers
        sp._element.remove(sp._element.find(qn("p:style")))
        return sp

    for colour, y0, y1, needs in PYR_TIERS:
        lit = all(r in on for r in needs)
        l0, r0 = edges(y0)
        l1, r1 = edges(y1)
        pts = [(X(l0), Y(y0)), (X(r0), Y(y0)), (X(r1), Y(y1)), (X(l1), Y(y1))]
        pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]   # apex tier is a triangle
        solid(polygon(pts), colour if lit else tint(colour))

    outline = polygon([(X(ax), Y(ay)), (X(bx1), Y(by)), (X(bx0), Y(by))])
    outline.fill.background()
    outline.line.color.rgb = BORDER_STRONG
    outline.line.width = Pt(0.5)
    outline.shadow.inherit = False

    # labels: one text box, a paragraph per rung on a fixed pitch so each line sits
    # beside its tier (baseline ~80% down a fixed-height line)
    pitch = 9.0 * k
    box = slide.shapes.add_textbox(X(PYR_LABEL_X), int(Y(PYR_LABELS[0][1]) - 0.8 * pitch),
                                   int(width - PYR_LABEL_X * k), int(pitch * len(PYR_LABELS)))
    tf = box.text_frame
    tf.word_wrap = False
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for index, (rung, _) in enumerate(PYR_LABELS):
        lit = rung in on
        para = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        para.line_spacing = Emu(int(pitch))
        para.space_before = para.space_after = Pt(0)
        run = para.add_run()
        run.text = rung.upper()
        run.font.size = Pt(7)
        run.font.bold = lit
        run.font.color.rgb = INK if lit else INK_3
        run.font.name = MONO_FONT
    return box


def add_spine(slide, deck_title):
    """The ladder icon every slide carries, top-right beside the title band."""
    add_pyramid(slide, DECK_RUNGS[deck_title], SLIDE_W - MARGIN - PYR_W, PYR_TOP, PYR_W)


# ---------------------------------------------------------------- the title pyramid
# The title slide's graphic (deck.html: TITLE_LAYERS / titlePyramidSVG): the ladder as
# a layered pyramid, each layer with the question it answers, what lives there and
# who does the work; a rail up the side (data informs every layer), the end state at
# the apex and the rule along the base. Geometry follows the deck: half-width 150
# over a height of 364 viewBox units, tiers on the icon's 1..37 scale.
TITLE_LAYERS = [
    ("judgement", "04", R_JUDGE, 1.0, 10.0, 0.0, "Judgement", "What will we do, and who signs?",
     "A determination a named person signs. Deliberately human: automation executes it and never decides.",
     "PEOPLE DECIDE · ANSIBLE EXECUTES · SIGSTORE RECORDS"),
    (None, None, RB_BLUE, 10.0, 11.6, 0.0, None, None, None, None),
    ("knowledge", "03", R_KNOW, 11.6, 20.5, 0.0, "Knowledge", "What do we know that bears on this?",
     "Information that informs an outcome: guidance, precedent, runbooks. The institution’s memory, retrievable and cited.",
     "GENERATIVE AI · GROUNDED IN APPROVED SOURCES · CITED"),
    (None, None, RB_YELLOW, 20.5, 22.0, 0.0, None, None, None, None),
    ("information", "02", R_INFO, 22.0, 30.0, -0.08, "Information", "What does it mean for this case?",
     "Data in context: a score, a classification, a diagnosis, a metric. A model estimates it; a person checks it.",
     "PREDICTIVE AI · INFERENCE"),
    ("data", "01", R_DATA, 30.0, 37.0, 0.12, "Data", "What happened?",
     "Uninterpreted: returns, transcripts, calls, logs, telemetry. Where it lives decides the architecture.",
     "THE PLATFORM · INGEST · STORE · GOVERN"),
]
TITLE_APEX = "THE END STATE: KNOWING ENOUGH TO DECIDE"
TITLE_RAIL = "DATA INFORMS EVERY LAYER"
TITLE_RULE = "Solve a problem someone has. Don’t invent a solution to one no one has."


def add_title_pyramid(slide, left, top, height):
    """Draw the title slide's layered pyramid with its layer notes at (left, top)."""
    unit = height / 36.0
    half = height * 150.0 / 364.0
    ax = left + half

    def Y(u):
        return int(top + (u - 1.0) * unit)

    def edges(y):
        f = (y - top) / height
        return ax - half * f, ax + half * f

    def polygon(pts):
        ff = slide.shapes.build_freeform(*pts[0], scale=1)
        ff.add_line_segments(pts[1:], close=True)
        sp = ff.convert_to_shape()
        sp._element.remove(sp._element.find(qn("p:style")))
        return sp

    rail_x = int(ax + half + Inches(0.14))
    label_x = int(ax + half + Inches(0.46))
    label_w = int(SLIDE_W - MARGIN - label_x)

    add_text(slide, int(left), int(top - Inches(0.32)), int(half * 2 + Inches(0.3)), Inches(0.25),
             [(TITLE_APEX, 7, True, R_JUDGE, MONO_FONT, 0)])

    for key, num, colour, u0, u1, dy, name, question, definition, who in TITLE_LAYERS:
        gap = Inches(0.012)
        y0, y1 = int(Y(u0) + gap), int(Y(u1) - gap)
        l0, r0 = edges(y0)
        l1, r1 = edges(y1)
        pts = [(int(l0), y0), (int(r0), y0), (int(r1), y1), (int(l1), y1)]
        pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
        solid(polygon(pts), colour)
        if not key:
            continue
        yc = (y0 + y1) // 2
        add_text(slide, int(ax - Inches(0.3)), int(yc - Inches(0.11)), Inches(0.6), Inches(0.22),
                 [(num, 9, True, SURFACE, MONO_FONT, 0)], align=PP_ALIGN.CENTER)
        tick = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, int(edges(yc)[1] + Inches(0.05)), yc,
                                          int(rail_x - Inches(0.06)), yc)
        tick.line.color.rgb = BORDER_STRONG
        tick.line.width = Pt(0.75)
        block_h = Inches(0.78)
        add_text(slide, label_x, int(yc - block_h / 2 + Inches(dy)), label_w, block_h,
                 [(name.upper(), 7, True, colour, MONO_FONT, 1),
                  (question, 10, True, INK, HEAD_FONT, 2),
                  (definition, 7.5, False, INK_2, BODY_FONT, 2),
                  (who, 6, True, INK_3, MONO_FONT, 0)])

    outline = polygon([(int(ax), int(top)), (int(ax + half), int(top + height)), (int(ax - half), int(top + height))])
    outline.fill.background()
    outline.line.color.rgb = BORDER_STRONG
    outline.line.width = Pt(0.5)
    outline.shadow.inherit = False

    rail = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, rail_x, int(top + height), rail_x, int(top + Inches(0.12)))
    rail.line.color.rgb = INK_3
    rail.line.width = Pt(1.1)
    head = slide.shapes.add_shape(MSO_SHAPE.ISOSCELES_TRIANGLE, int(rail_x - Inches(0.05)), int(top), Inches(0.1), Inches(0.13))
    solid(head, INK_3)
    rail_label = add_text(slide, int(rail_x + Inches(0.1) - Inches(1.5)), int(top + height / 2 - Inches(0.12)),
                          Inches(3.0), Inches(0.24), [(TITLE_RAIL, 6.5, True, INK_3, MONO_FONT, 0)], align=PP_ALIGN.CENTER)
    rail_label.rotation = 270.0

    by = int(top + height + Inches(0.2))
    bw = int(SLIDE_W - MARGIN - left)
    rrect(slide, int(left), by, bw, Inches(0.42), SURFACE_2, BORDER, 0.75, radius=0.2)
    solid(slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, int(left), by, Inches(0.05), Inches(0.42)), RED)
    add_text(slide, int(left + Inches(0.1)), int(by + Inches(0.07)), int(bw - Inches(0.2)), Inches(0.3),
             [(TITLE_RULE, 10, True, INK, HEAD_FONT, 0)], align=PP_ALIGN.CENTER)


TITLE_NOTES = (
    "Brad drives, Jon adds color commentary. Open by naming the room: Red Hat, Four Inc. and Carahsoft. "
    "THE PYRAMID, the only graphic on this slide and the spine of the hour; read it bottom to top. "
    "01 Data, the base and the widest layer: what happened, uninterpreted (returns, transcripts, calls, logs, telemetry); "
    "nothing above it exists without it, and where it lives decides the architecture. "
    "02 Information: data put in context for one case (a score, a classification, a diagnosis); what predictive AI and inference produce; "
    "a model makes the estimate, a person checks it. "
    "03 Knowledge: information that informs an outcome (guidance, precedent, runbooks), the institution's memory, retrievable and cited; "
    "generative AI grounded in approved sources works here; if it cannot cite, it is not knowledge. "
    "04 Judgement, the apex: a determination a named person signs; deliberately human, automation executes what was decided and never decides. "
    "The arrow up the side: data informs every layer, so anything higher up the stack has to trace back down to data or it is decoration. "
    "The label at the apex: the end state is knowing, knowing enough to decide, with the evidence in hand. "
    "WHY WE ARE HERE: not to sell a model. Every technology in the hour is tagged with the layer it serves, and every claim gets run in a shell before you leave. "
    "The test for anything we show, and for anything a vendor shows you: which layer does it move work up, and which problem in your queue does that solve? "
    "Solve a problem someone has; do not invent a solution to one no one has. If a proposal cannot name the layer and the problem, it is technology looking for a mission. "
    "Frame the hour: foundations, then the platform story, then live terminal, 5 for questions."
)


def eyebrow_and_title(slide, eyebrow, title, lede="", lede_top=Inches(1.68), title_size=34):
    add_text(slide, MARGIN, Inches(0.55), SLIDE_W - 2 * MARGIN, Inches(0.34),
             [(eyebrow.upper(), 11, True, INK_3, MONO_FONT, 0)])
    add_text(slide, MARGIN, Inches(0.95), SLIDE_W - 2 * MARGIN, Inches(0.9),
             [(title, title_size, True, INK, HEAD_FONT, 0)])
    if lede:
        add_text(slide, MARGIN, lede_top, Inches(10.6), Inches(0.5),
                 [(lede, 14, False, INK_2, BODY_FONT, 0)])


def add_table(slide, rows, top, col_widths, header=True, mono_cols=(), size=12, pad_y=Inches(0.05)):
    n_rows, n_cols = len(rows), len(rows[0])
    width = sum(col_widths)
    shape = slide.shapes.add_table(n_rows, n_cols, MARGIN, top, width, Inches(0.4))
    table = shape.table
    for i, w in enumerate(col_widths):
        table.columns[i].width = w
    for r, row in enumerate(rows):
        table.rows[r].height = Inches(0.36)
        for c, text in enumerate(row):
            cell = table.cell(r, c)
            cell.text = ""
            cell.margin_left = Inches(0.12)
            cell.margin_right = Inches(0.12)
            cell.margin_top = pad_y
            cell.margin_bottom = pad_y
            cell.fill.solid()
            cell.fill.fore_color.rgb = SURFACE_2 if (header and r == 0) else GROUND
            para = cell.text_frame.paragraphs[0]
            cell.text_frame.word_wrap = True
            run = para.add_run()
            run.text = text
            is_head = header and r == 0
            run.font.size = Pt(10.5 if is_head else size)
            run.font.bold = is_head
            run.font.color.rgb = INK_3 if is_head else INK
            run.font.name = MONO_FONT if (is_head or c in mono_cols) else BODY_FONT
    return table


def bullet_cards(slide, top, cards, height=Inches(1.9)):
    gap = Inches(0.32)
    count = len(cards)
    total = SLIDE_W - 2 * MARGIN
    width = int((total - gap * (count - 1)) / count)
    for i, (heading, body) in enumerate(cards):
        left = MARGIN + i * (width + gap)
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, Inches(0.045), height)
        solid(bar, RED)
        add_text(slide, left + Inches(0.18), top, width - Inches(0.18), height,
                 [(heading, 15, True, INK, HEAD_FONT, 6),
                  (body, 12, False, INK_2, BODY_FONT, 0)])


def side_card(slide, x, y, w, h, tag, heading, body, bar=RED):
    solid(slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, Inches(0.045), h), bar)
    add_text(slide, x + Inches(0.16), y - Inches(0.05), w - Inches(0.16), h,
             [(tag.upper(), 8.5, True, INK_3, MONO_FONT, 3),
              (heading, 13, True, INK, HEAD_FONT, 3),
              (body, 10, False, INK_2, BODY_FONT, 0)])


# ---------------------------------------------------------------- chart math
def cosine_curve(values, samples=10):
    """Smooth interpolation between month values -> list of (t, v), t in 0..1."""
    pts = []
    n = len(values)
    for i in range(n - 1):
        for k in range(samples):
            f = k / samples
            mu = (1 - math.cos(f * math.pi)) / 2
            v = values[i] * (1 - mu) + values[i + 1] * mu
            pts.append(((i + f) / (n - 1), v))
    pts.append((1.0, values[-1]))
    return pts


def demand_chart(slide, x0, y0, w, h):
    """Native freeform area chart: filing-season demand vs staffed capacity."""
    values = [0.35, 0.45, 0.72, 1.00, 0.42, 0.30, 0.27, 0.25, 0.30, 0.55, 0.28, 0.32]
    cap = 0.62
    panel = rrect(slide, x0, y0, w, h, SURFACE, BORDER, 1, radius=0.045)
    panel.shadow.inherit = True
    add_text(slide, x0 + Inches(0.28), y0 + Inches(0.14), w - Inches(0.5), Inches(0.6),
             [("A year of demand arrives in six weeks", 16, True, INK, HEAD_FONT, 2),
              ("Taxpayer contacts per week — illustrative shape of a filing year", 10, False, INK_3, BODY_FONT, 0)])

    px0 = x0 + Inches(0.45)
    px1 = x0 + w - Inches(0.45)
    pyb = y0 + h - Inches(0.55)          # baseline
    pyt = y0 + Inches(0.95)              # top of scale
    span = px1 - px0
    rise = pyb - pyt

    def X(t):
        return int(px0 + t * span)

    def Y(v):
        return int(pyb - v * rise)

    # gridlines + baseline
    for gv in (0.3, 0.8):
        g = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, X(0), Y(gv), X(1), Y(gv))
        g.line.color.rgb = BORDER
        g.line.width = Pt(0.75)
        g.shadow.inherit = False
    base = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, X(0), Y(0), X(1), Y(0))
    base.line.color.rgb = BORDER_STRONG
    base.line.width = Pt(1)
    base.shadow.inherit = False

    curve = cosine_curve(values, samples=10)

    # filled area
    ff = slide.shapes.build_freeform(X(curve[0][0]), Y(curve[0][1]), scale=1)
    ff.add_line_segments([(X(t), Y(v)) for t, v in curve[1:]] + [(X(1), Y(0)), (X(0), Y(0))], close=True)
    area = ff.convert_to_shape()
    solid(area, RED_TINT)

    # surge gap above capacity
    over = [(t, v) for t, v in curve if v >= cap]
    if over:
        gap_pts = [(over[0][0], cap)] + over + [(over[-1][0], cap)]
        fg = slide.shapes.build_freeform(X(gap_pts[0][0]), Y(gap_pts[0][1]), scale=1)
        fg.add_line_segments([(X(t), Y(v)) for t, v in gap_pts[1:]], close=True)
        solid(fg.convert_to_shape(), RED_TINT2)

    # curve outline
    fl = slide.shapes.build_freeform(X(curve[0][0]), Y(curve[0][1]), scale=1)
    fl.add_line_segments([(X(t), Y(v)) for t, v in curve[1:]], close=False)
    line = fl.convert_to_shape()
    line.fill.background()
    line.line.color.rgb = RED
    line.line.width = Pt(2.5)
    line.shadow.inherit = False

    # capacity line
    capline = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, X(0), Y(cap), X(1), Y(cap))
    capline.line.color.rgb = INK_2
    capline.line.width = Pt(1.75)
    capline.shadow.inherit = False
    if DASH is not None:
        capline.line.dash_style = DASH

    # apex marker + labels
    apex_t = 3 / 11
    dot = slide.shapes.add_shape(MSO_SHAPE.OVAL, X(apex_t) - Emu(50800), Y(1.0) - Emu(50800), Emu(101600), Emu(101600))
    solid(dot, RED, SURFACE, 1.5)
    add_text(slide, X(apex_t) + Inches(0.18), Y(1.0) - Inches(0.14), Inches(3.2), Inches(0.3),
             [("April — 6× the August low", 12.5, True, INK, HEAD_FONT, 0)])
    add_text(slide, X(apex_t) + Inches(0.55), Y(0.80), Inches(2.6), Inches(0.3),
             [("the surge automation absorbs", 10.5, False, INK_2, BODY_FONT, 0)])
    add_text(slide, X(1) - Inches(1.62), Y(cap) - Inches(0.26), Inches(1.6), Inches(0.24),
             [("staffed capacity", 9.5, True, INK_2, MONO_FONT, 0)], align=PP_ALIGN.RIGHT)
    add_text(slide, X(9 / 11) - Inches(0.6), Y(0.55) - Inches(0.35), Inches(1.6), Inches(0.24),
             [("extension deadline", 9, False, INK_3, BODY_FONT, 0)], align=PP_ALIGN.CENTER)

    # month labels
    months = list("JFMAMJJASOND")
    for i, m in enumerate(months):
        add_text(slide, X(i / 11) - Inches(0.2), pyb + Inches(0.06), Inches(0.4), Inches(0.24),
                 [(m, 9, False, INK_3, MONO_FONT, 0)], align=PP_ALIGN.CENTER)


# ---------------------------------------------------------------- build deck
def build(out_path: Path) -> None:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    # ---- 1 title ---------------------------------------------------------------
    s = add_base(prs, TITLE_NOTES)
    add_spine(s, "Title")
    add_text(s, MARGIN, Inches(1.75), Inches(4.8), Inches(0.5),
             [("RED HAT  ·  FOUR INC.  ·  CARAHSOFT — VIRTUAL EVENT", 11, True, RED, MONO_FONT, 0)])
    add_text(s, MARGIN, Inches(2.25), Inches(4.8), Inches(2.0),
             [("AI foundations for intelligent tax administration", 32, True, INK, HEAD_FONT, 0)])
    add_text(s, MARGIN, Inches(4.3), Inches(4.8), Inches(1.4),
             [("What predictive AI, generative AI and LLMs actually do — then how Red Hat turns "
               "models, agency knowledge and automation into an operable mission capability, "
               "proven in eight labs you run yourself.", 13, False, INK_2, BODY_FONT, 0)])
    add_text(s, MARGIN, Inches(5.75), Inches(4.8), Inches(0.5),
             [("Presented by Jon Keam (jkeam@redhat.com) and Brad Scalio (bscalio@redhat.com)", 11, True, INK_2, BODY_FONT, 0)])
    add_title_pyramid(s, Inches(5.75), Inches(1.45), Inches(3.7))

    # ---- 2 operating reality: demand curve -------------------------------------
    s = add_base(prs, "Do not lead with the technology. Lead with the shape of the problem. The "
                      "chart is the argument: a year of demand arrives in six weeks, far above any "
                      "capacity you can justify staffing year-round. The shaded gap is what "
                      "automation absorbs. The card on the right that matters most is the last one: "
                      "the data cannot leave, so the platform is the decision.")
    add_spine(s, "Why now")
    eyebrow_and_title(s, "The operating reality", "The work is seasonal, textual and unforgiving")
    demand_chart(s, MARGIN, Inches(1.95), Inches(7.55), Inches(4.9))
    cx = Inches(8.75)
    cw = Inches(3.9)
    side_card(s, cx, Inches(1.95), cw, Inches(1.05), "Demand", "Peak load, fixed staff",
              "Idle capacity in August is unjustifiable; exhausted capacity in April is a headline.")
    side_card(s, cx, Inches(3.13), cw, Inches(1.05), "Systems", "Rules locked in legacy code",
              "Rewriting the systems of record is a decade. Wrapping them is a quarter.")
    side_card(s, cx, Inches(4.31), cw, Inches(1.05), "Data", "The answers are in the text",
              "Correspondence and case notes are unstructured — what language models are built for.")
    side_card(s, cx, Inches(5.49), cw, Inches(1.3), "The constraint", "The data cannot leave",
              "FTI rules rule out public endpoints. The model comes to the data — on premises, "
              "accredited cloud, or air-gapped enclave.", bar=GREEN)

    # ---- 3 the ladder: data to judgement --------------------------------------
    s = add_base(prs, "The spine of the hour. Read it left to right: the platform holds the data, "
                      "predictive AI and inference turn it into information, generative AI with "
                      "retrieval turns that into knowledge, and a person turns knowledge into a "
                      "determination they sign. Judgement is deliberately never automated — "
                      "Ansible, the registry and Sigstore execute and record what a person decided. "
                      "Every later slide tags its technologies with one of these four rungs.")
    add_spine(s, "Data to judgement")
    eyebrow_and_title(s, "Why it matters", "From data to judgement — and who climbs each step",
                      "Every technology in this hour is tagged with the rung it serves. AI moves work up the ladder; it never takes the top step.")
    rungs = [
        ("Data", R_DATA, "What happened, uninterpreted: returns, transcripts, calls, logs, telemetry. Where it lives decides the architecture.",
         "RHEL · OpenShift · OpenShift Logging · accelerators"),
        ("Information", R_INFO, "Data in context for one case: a classification, a score, a diagnosis, a metric. What predictive AI and inference produce.",
         "AI Inference Server · KServe + vLLM · Granite · TrustyAI · Models-as-a-Service"),
        ("Knowledge", R_KNOW, "Information that informs an outcome: guidance, precedent, runbooks, taxonomies. The institution's memory, retrievable and cited.",
         "SDG Hub · Training Hub · pipelines · retrieval / vector store"),
        ("Judgement", R_JUDGE, "A determination someone signs. Deliberately human; automation executes what was decided, it never decides.",
         "Human reviewer · model registry · Sigstore · Ansible executes it"),
    ]
    gap, step = Inches(0.28), Inches(0.42)
    width = int((SLIDE_W - 2 * MARGIN - gap * 3) / 4)
    for i, (name, colour, definition, tech) in enumerate(rungs):
        left = MARGIN + i * (width + gap)
        top = Inches(2.5) + step * (3 - i)           # a staircase rising to the right
        h = Inches(4.1) - step * (3 - i)
        rrect(s, left, top, width, h, SURFACE, BORDER_STRONG, 1.0, radius=0.05)
        solid(s.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, Inches(0.07)), colour)
        add_text(s, left + Inches(0.2), top + Inches(0.2), width - Inches(0.4), h - Inches(0.35),
                 [(name.upper(), 11, True, colour, MONO_FONT, 6),
                  (definition, 12, False, INK_2, BODY_FONT, 10),
                  (tech, 9, False, INK_3, MONO_FONT, 0)])
        if i < 3:
            arrow = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, left + width + Inches(0.03), top - Inches(0.05),
                                       Inches(0.22), Inches(0.2))
            solid(arrow, colour)

    # ---- 4 where AI lands: the eight-station rail ------------------------------
    s = add_base(prs, "Walk the eight stations left to right, the same eight as the graphic (G): AI "
                      "reads, classifies, grounds and drafts on the first four; a person reviews "
                      "and signs on five and six; automation sends the notice; operations close the "
                      "loop. The first four are where language models earn their keep first — "
                      "high-volume, text-heavy, and a human reviewer is already in the loop, which "
                      "makes them the honest places to start. Exam selection is deliberately NOT on "
                      "this rail (an earlier version of the slide showed it held back): that is a "
                      "determination affecting a taxpayer and needs a much heavier governance "
                      "conversation — saying so unprompted buys enormous credibility. Two rules of "
                      "thumb: start where a human already reviews the output; and automate the toil "
                      "around the model, not just the model. Worth naming: most of the effort in "
                      "production AI is provisioning, patching, scaling and data collection — an "
                      "automation problem, already solved. GRAPHIC (G) — Where AI actually lands in "
                      "the filing lifecycle: An eight-station rail, Intake, Classification, "
                      "Guidance, Drafting, Review, Decision, Notice and Operations, with five red "
                      "call-outs over the first five stations; notice that the fifth call-out is a "
                      "human reviewer and Decision has no call-out at all. Talk to it: (1) Read the "
                      "rail against the ladder: Intake through Drafting turn data into information "
                      "and knowledge; Review and Decision are where a person supplies the judgement "
                      "that stays human. (2) The four AI cards sit where a reviewer already checks "
                      "the output; neither this graphic nor the slide puts AI on exam selection, "
                      "because a taxpayer determination needs governance first. (3) Operations "
                      "closes the loop: what Review corrects and Notice sends goes back into the "
                      "knowledge base between seasons, and pooled GPUs absorb the 6× April surge on "
                      "a fixed workforce. (4) One platform under all eight stations: the model "
                      "comes to the data, the seams stay boring, and controls accredited once for "
                      "Intake are inherited all the way to Operations.")
    add_spine(s, "Where AI lands")
    # 30 pt keeps this long title on one line above the lede; at 34 pt it wraps into it.
    eyebrow_and_title(s, "Workflow map", "Where AI actually lands in the filing lifecycle",
                      "AI lands on the first four stages, where a reviewer already checks the "
                      "output; the decision stays with a person; operations close the loop.",
                      title_size=30)
    # (number, station, what happens, pill, rung colour). Top bars follow the ladder:
    # information for 01-02, knowledge for 03-04 and 08, judgement for 05-07.
    stations = [
        ("01", "Intake", "Capture correspondence from any channel", "AI reads it", R_INFO),
        ("02", "Classification", "Understand intent, route to the case type", "AI classifies", R_INFO),
        ("03", "Guidance", "Rules, policy and precedent", "AI grounds and cites", R_KNOW),
        ("04", "Drafting", "Letters, responses, memos, with citations", "AI drafts", R_KNOW),
        ("05", "Review", "Check accuracy, add judgment, approve", "human in the loop", R_JUDGE),
        ("06", "Decision", "Finalize and issue the outcome", "a person signs", R_JUDGE),
        ("07", "Notice", "Send letters and update records", "automation executes", R_JUDGE),
        ("08", "Operations", "Track performance, learn and improve", "the loop closes", R_KNOW),
    ]
    # Two rows of four: the pill text does not fit eight cards across at 9 pt.
    per_row = 4
    gap = Inches(0.3)
    cw = int((SLIDE_W - 2 * MARGIN - gap * (per_row - 1)) / per_row)
    ch = Inches(1.32)
    row_gap = Inches(0.22)
    top = Inches(2.38)
    for i, (num, name, desc, pill_text, colour) in enumerate(stations):
        r, c = divmod(i, per_row)
        x = MARGIN + c * (cw + gap)
        y = top + r * (ch + row_gap)
        rrect(s, x, y, cw, ch, SURFACE, line=BORDER_STRONG, line_w=0.75, radius=0.08)
        bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, x + Inches(0.1), y, cw - Inches(0.2), Inches(0.05))
        solid(bar, colour)
        badge = s.shapes.add_shape(MSO_SHAPE.OVAL, x + Inches(0.16), y + Inches(0.2),
                                   Inches(0.36), Inches(0.36))
        solid(badge, colour)
        btf = badge.text_frame
        btf.margin_left = btf.margin_right = btf.margin_top = btf.margin_bottom = 0
        btf.vertical_anchor = MSO_ANCHOR.MIDDLE
        para = btf.paragraphs[0]
        para.alignment = PP_ALIGN.CENTER
        run = para.add_run()
        run.text = num
        run.font.size = Pt(9)
        run.font.bold = True
        run.font.name = MONO_FONT
        run.font.color.rgb = SURFACE
        add_text(s, x + Inches(0.6), y + Inches(0.12), cw - Inches(0.72), Inches(0.75),
                 [(name, 13, True, INK, HEAD_FONT, 2),
                  (desc, 9.5, False, INK_2, BODY_FONT, 0)])
        pill = rrect(s, x + Inches(0.6), y + ch - Inches(0.42), Inches(1.75), Inches(0.27),
                     tint(colour, amount=0.86), radius=0.5)
        ptf = pill.text_frame
        ptf.margin_left = ptf.margin_right = Inches(0.05)
        ptf.margin_top = ptf.margin_bottom = 0
        ptf.word_wrap = False
        ptf.vertical_anchor = MSO_ANCHOR.MIDDLE
        para = ptf.paragraphs[0]
        para.alignment = PP_ALIGN.CENTER
        run = para.add_run()
        run.text = pill_text
        run.font.size = Pt(9)
        run.font.bold = True
        run.font.name = MONO_FONT
        run.font.color.rgb = colour
        if c < per_row - 1:
            arrow = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, x + cw + Inches(0.06),
                                       y + ch // 2 - Inches(0.09), Inches(0.18), Inches(0.18))
            solid(arrow, INK_3)
    bullet_cards(s, Inches(5.5), [
        ("Start where a human already reviews the output",
         "If a person signs the letter today, a model that drafts it changes throughput "
         "without changing accountability."),
        ("Automate the toil around the model, not just the model",
         "Provisioning, patching, scaling and evidence collection are most of the work — "
         "and that problem is already solved."),
    ], height=Inches(1.4))

    # ---- 5 five outcomes -------------------------------------------------------
    s = add_base(prs, "These five are the event abstract made concrete. Each names the product "
                      "that delivers it and the lab where the audience runs it. Do not linger — "
                      "this slide exists so people can map the rest of the hour.")
    add_spine(s, "Five outcomes")
    eyebrow_and_title(s, "What teams get", "Five outcomes, and where each one is proven")
    add_table(s, [
        ["Outcome", "Platform capability", "Lab", "Rung"],
        ["Modernize mission-critical operations", "Ansible Automation Platform, Event-Driven Ansible, OpenShift", "05, 07", "executes judgement"],
        ["Improve efficiency and accuracy", "Red Hat AI Inference Server, SDG Hub + Training Hub", "01, 02", "information + knowledge"],
        ["Unlock data-driven insights", "OpenShift AI, vector retrieval", "04", "knowledge"],
        ["Strengthen security and compliance", "FIPS, Compliance Operator, TrustyAI, Sigstore", "06", "evidence → judgement"],
        ["Build an AI-ready foundation", "OpenShift AI, KServe, vLLM", "03", "data → information"],
    ], Inches(2.4), [Inches(3.9), Inches(4.7), Inches(0.9), Inches(2.1)], mono_cols=(2, 3))
    # outcome 01 spelled out: the closed loop the deck puts under the first pillar
    add_text(s, MARGIN, Inches(5.35), Inches(11.5), Inches(1.2),
             [("Outcome 01 in practice: the closed loop", 15, True, INK, HEAD_FONT, 6),
              ("Wrap legacy systems in intelligent workflows instead of rewriting them. An error "
               "string in a log fires an Event-Driven Ansible rule, a playbook runs on the right "
               "hosts, the on-call gets an email, and a ticket opens and closes in ServiceNow or "
               "Remedy. The system of record stays untouched.", 12.5, False, INK_2, BODY_FONT, 0)])

    # ---- 6 architecture: layered diagram ---------------------------------------
    s = add_base(prs, "Read bottom to top. The point is the two vertical pillars: automation and "
                      "trust are not a layer you add at the end. A project that treats compliance "
                      "as a phase after deployment discovers, at the worst possible moment, that "
                      "it cannot produce evidence for anything that already happened.")
    add_spine(s, "Architecture")
    eyebrow_and_title(s, "Reference architecture", "One foundation, from bare metal to the taxpayer")

    top = Inches(2.0)
    bottom = Inches(7.05)
    pill_w = Inches(1.3)
    # trust pillar
    rrect(s, MARGIN, top, pill_w, bottom - top, RED_WASH, RED, 1.25, radius=0.08)
    add_text(s, MARGIN, top + Inches(0.12), pill_w, bottom - top - Inches(0.2),
             [("TRUST", 11, True, RED_DARK, MONO_FONT, 8),
              ("Signed models", 9.5, False, INK_2, BODY_FONT, 4),
              ("FIPS crypto", 9.5, False, INK_2, BODY_FONT, 4),
              ("SELinux", 9.5, False, INK_2, BODY_FONT, 4),
              ("Compliance Operator", 9.5, False, INK_2, BODY_FONT, 4),
              ("TrustyAI drift + bias", 9.5, False, INK_2, BODY_FONT, 4),
              ("Audit trail", 9.5, False, INK_2, BODY_FONT, 4),
              ("Air-gap mirroring", 9.5, False, INK_2, BODY_FONT, 8),
              ("Lab 06", 8.5, False, INK_3, MONO_FONT, 0)], align=PP_ALIGN.CENTER)
    # automation pillar
    ax = SLIDE_W - MARGIN - pill_w
    rrect(s, ax, top, pill_w, bottom - top, STEEL_WASH, STEEL, 1.25, radius=0.08)
    add_text(s, ax, top + Inches(0.12), pill_w, bottom - top - Inches(0.2),
             [("AUTOMATION", 11, True, STEEL, MONO_FONT, 8),
              ("Ansible Automation Platform", 9.5, False, INK_2, BODY_FONT, 4),
              ("Event-Driven Ansible", 9.5, False, INK_2, BODY_FONT, 4),
              ("Provision", 9.5, False, INK_2, BODY_FONT, 4),
              ("Patch", 9.5, False, INK_2, BODY_FONT, 4),
              ("Remediate", 9.5, False, INK_2, BODY_FONT, 4),
              ("Evidence collection", 9.5, False, INK_2, BODY_FONT, 8),
              ("Lab 05", 8.5, False, INK_3, MONO_FONT, 0)], align=PP_ALIGN.CENTER)

    lx = MARGIN + pill_w + Inches(0.25)
    lw = ax - lx - Inches(0.25)

    def layer(y, h, title, caption, fill=SURFACE, line=BORDER_STRONG, line_w=1.0, tag="", note=""):
        rrect(s, lx, y, lw, h, fill, line, line_w, radius=0.10)
        runs = [(title, 12.5, True, INK, HEAD_FONT, 2),
                (caption, 9.5, False, INK_2, BODY_FONT, 3 if note else 0)]
        if note:                         # small third line, e.g. the hardware the base is tested on
            runs.append((note, 8.5, True, STEEL, BODY_FONT, 0))
        add_text(s, lx + Inches(0.22), y + Inches(0.05), lw - Inches(1.2), h, runs)
        if tag:
            add_text(s, lx + lw - Inches(1.35), y + Inches(0.06), Inches(1.25), Inches(0.25),
                     [(tag, 8.5, False, INK_3, MONO_FONT, 0)], align=PP_ALIGN.RIGHT)

    # apps
    layer(top, Inches(1.0), "Mission applications",
          "Correspondence intake · Notice drafting · Case summarization · Guidance assistant")
    # dots row for apps
    for i, col in enumerate((RED, STEEL, AMBER, GREEN)):
        d = s.shapes.add_shape(MSO_SHAPE.OVAL, lx + Inches(0.25 + i * 2.35), top + Inches(0.72),
                               Emu(91440), Emu(91440))
        solid(d, col)
    # openshift ai
    aiy = top + Inches(1.18)
    layer(aiy, Inches(1.32), "Red Hat OpenShift AI", "", RED_WASH, RED, 1.25, tag="Labs 02 · 03 · 04")
    subs = [("Model serving", "KServe + vLLM"), ("Pipelines", "tune · eval · promote"),
            ("Model registry", "versions · approvals"), ("Retrieval", "vector store · citations")]
    sw = (lw - Inches(0.7)) / 4
    for i, (t, c) in enumerate(subs):
        bx = lx + Inches(0.22) + i * (sw + Inches(0.09))
        rrect(s, bx, aiy + Inches(0.5), sw, Inches(0.62), SURFACE, BORDER_STRONG, 0.75, radius=0.14)
        add_text(s, bx + Inches(0.08), aiy + Inches(0.52), sw - Inches(0.12), Inches(0.58),
                 [(t, 10, True, INK, HEAD_FONT, 1),
                  (c, 8.5, False, INK_3, BODY_FONT, 0)])
    # openshift
    osy = aiy + Inches(1.5)
    layer(osy, Inches(0.85), "Red Hat OpenShift",
          "Scheduling · GPU partitioning · network policy · multi-site placement · GitOps delivery")
    # rhel
    ry = osy + Inches(1.03)
    layer(ry, Inches(1.0), "Red Hat Enterprise Linux · AI Inference Server",
          "Bare metal GPU nodes · virtualized datacenter · accredited cloud · classified enclave",
          tag="Lab 01", note="Tested with the hardware: mainframes · TPM · PIV/CAC cryptography")
    for i in range(2):
        chip = rrect(s, lx + lw - Inches(1.55) + i * Inches(0.72), ry + Inches(0.5),
                     Inches(0.6), Inches(0.36), CHIP, radius=0.15)
        tf = chip.text_frame
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        para = tf.paragraphs[0]
        para.alignment = PP_ALIGN.CENTER
        run = para.add_run()
        run.text = "GPU"
        run.font.size = Pt(8.5)
        run.font.bold = True
        run.font.name = MONO_FONT
        run.font.color.rgb = SURFACE
    # up arrows between layers
    for ay in (aiy - Inches(0.16), osy - Inches(0.16), ry - Inches(0.16)):
        ar = s.shapes.add_shape(MSO_SHAPE.UP_ARROW, lx + lw / 2 - Inches(0.09), ay,
                                Inches(0.18), Inches(0.14))
        solid(ar, BORDER_STRONG)

    # ---- 7 one loop, end to end (Lab 08) ----------------------------------------
    s = add_base(prs, "Lab 08 is the whole hour in one loop; run it if the room is operational, or "
                      "walk the map. Read the map clockwise: logs from the mainframe and the servers "
                      "land in Loki (data); the outage-risk model scores who fails next in the next 72 "
                      "hours (information); Lightspeed drafts the playbook and the rulebook with "
                      "citations (knowledge); a person reviews, edits and merges the pull request, and "
                      "that merge is the promotion into the repo, AAP and the knowledge base "
                      "(judgement); Event-Driven Ansible runs the approved job when the event fires, "
                      "42 seconds, no page; and the assistant answers from what the loop wrote, probing "
                      "hosts through job templates a person approved. Say the two takeaways out loud: "
                      "the platform is also the KM system and the documentation, because every "
                      "promoted change is a cited record; and the assistant does not change anything, "
                      "it launches approved jobs and reports with evidence. Ask the room: what is the "
                      "last runbook you wrote that the on-call actually found? HAND-OFF: Jon takes the "
                      "assistant questions, Brad takes the mainframe row.")
    add_spine(s, "One loop")
    eyebrow_and_title(s, "Lab 08 · the whole loop", "One loop, end to end",
                      "Logs in, risk scored, fix drafted by Lightspeed, merged by a person, run by "
                      "Event-Driven Ansible, remembered by the platform, so you can ask.")
    # the eight stations of the deck's stage map (LOOP_STATIONS), as a numbered 4 x 2 grid:
    # 01 to 04 across the top, 05 to 08 across the bottom, and 08 feeds 01 again
    stations = [
        ("01", "Mainframe + servers", "MVSA · server1..12", R_DATA),
        ("02", "Vector · Loki", "OpenShift Logging", R_DATA),
        ("03", "outage-risk scorer", "KServe · sklearn · OpenShift AI", R_INFO),
        ("04", "Granite · Lightspeed", "vLLM · OpenShift AI", R_KNOW),
        ("05", "Pull request", "a person reviews and merges", R_JUDGE),
        ("06", "Repo → AAP → EDA", "the merge is the promotion", R_JUDGE),
        ("07", "Event-Driven Ansible", "approved job templates", R_JUDGE),
        ("08", "Knowledge base + assistant", "pgvector · ops notebook", R_KNOW),
    ]
    gap = Inches(0.22)
    bw = int((SLIDE_W - 2 * MARGIN - gap * 3) / 4)
    bh = Inches(0.86)
    gy = Inches(2.28)
    for i, (num, name, sub, colour) in enumerate(stations):
        x = MARGIN + (i % 4) * (bw + gap)
        y = gy + (i // 4) * (bh + Inches(0.14))
        rrect(s, x, y, bw, bh, SURFACE, BORDER_STRONG, 0.75, radius=0.08)
        solid(s.shapes.add_shape(MSO_SHAPE.RECTANGLE, x + Inches(0.1), y + Inches(0.12),
                                 Inches(0.05), bh - Inches(0.24)), colour)
        add_text(s, x + Inches(0.22), y + Inches(0.06), bw - Inches(0.3), bh - Inches(0.1),
                 [(num, 8.5, True, colour, MONO_FONT, 0),
                  (name, 11, True, INK, HEAD_FONT, 0),
                  (sub, 8.5, False, INK_3, MONO_FONT, 0)])
    add_text(s, MARGIN, gy + 2 * bh + Inches(0.16), SLIDE_W - 2 * MARGIN, Inches(0.22),
             [("THE LOOP · ASK, THEN PROBE · 08 FEEDS 01", 8.5, True, INK_3, MONO_FONT, 0)],
             align=PP_ALIGN.RIGHT)

    # ask the platform: the three questions, each with its answer and its evidence
    qy, qh = Inches(4.5), Inches(1.2)
    rrect(s, MARGIN, qy, SLIDE_W - 2 * MARGIN, qh, SURFACE, BORDER, 1.0, radius=0.06)
    qbox = s.shapes.add_textbox(MARGIN + Inches(0.18), qy + Inches(0.05),
                                SLIDE_W - 2 * MARGIN - Inches(0.36), qh - Inches(0.1))
    qtf = qbox.text_frame
    qtf.word_wrap = True
    head = qtf.paragraphs[0]
    head.space_after = Pt(3)
    hr = head.add_run()
    hr.text = "ASK THE PLATFORM"
    hr.font.size, hr.font.bold, hr.font.name, hr.font.color.rgb = Pt(8.5), True, MONO_FONT, INK_3
    for q, a, ev in [
        ("How is server1-taxreturns?",
         "Online, up 41d, mem 62%, 72h risk 0.22 and falling; last change CR-9088.", "job 40518 · journald · RB-214"),
        ("How is server8-audits?",
         "Restored 03:13 by job 40512 (Xmx 7g); risk 0.91 → 0.34; PR #482 merged, INC-2340 closed.", "job 40519"),
        ("Which servers are showing online?",
         "13 of 14: server1..12 ok, MVSA reachable, MVSB in its IPL window until 06:00.", "job 40520 · estate ping"),
    ]:
        para = qtf.add_paragraph()
        para.space_after = Pt(2)
        for text, colour, bold in ((q + "   ", INK, True), (a + "  ", INK_2, False), ("[" + ev + "]", STEEL, False)):
            run = para.add_run()
            run.text = text
            run.font.size, run.font.bold, run.font.name, run.font.color.rgb = Pt(9), bold, MONO_FONT, colour

    # the four takeaways
    cy, ch = Inches(5.82), Inches(1.5)
    gap = Inches(0.3)
    cw = int((SLIDE_W - 2 * MARGIN - gap * 3) / 4)
    for i, (heading, body) in enumerate([
        ("The loop is the documentation",
         "Every promoted change, its review thread and its job outcome are indexed where the "
         "assistant searches. The KM system writes itself."),
        ("Two kinds of AI, one platform",
         "The scorer and the drafter share a GPU node, a registry and an identity. Predictive "
         "and generative are pods, not projects."),
        ("Promotion is a merge",
         "Repo, AAP and knowledge base update together, and a person decides. Nothing runs "
         "from a chat window."),
        ("Ask, then probe",
         "The assistant's tools are approved job templates, so \"how is server8?\" becomes a "
         "job with evidence, not a guess."),
    ]):
        side_card(s, MARGIN + i * (cw + gap), cy, cw, ch, "Takeaway", heading, body)

    # ---- 8 adoption path: roadmap timeline -------------------------------------
    s = add_base(prs, "Be honest about sequencing. Most agencies stall on rows 2 and 3 of the "
                      "Prove phase — no accelerator capacity plan, and no written agreement on "
                      "which data may be used. Neither is technical. Ask the room directly which "
                      "phase they are in.")
    add_spine(s, "Adoption path")
    eyebrow_and_title(s, "Adoption path", "Ninety days, then ninety more",
                      "Nothing here requires a rewrite of a system of record.")
    ty = Inches(2.65)
    spine = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(1.0), ty, Inches(12.5), ty)
    spine.line.color.rgb = BORDER_STRONG
    spine.line.width = Pt(2)
    spine.shadow.inherit = False
    seg_w = Inches(3.62)
    seg_xs = [Inches(1.15), Inches(4.92), Inches(8.69)]
    for sx, col, label in zip(seg_xs, (STEEL, AMBER, RED), ("PROVE", "GROUND", "SCALE")):
        rrect(s, sx, ty - Inches(0.07), seg_w, Inches(0.14), col, radius=0.5)
        add_text(s, sx, ty - Inches(0.5), seg_w, Inches(0.3),
                 [(label, 12, True, col, MONO_FONT, 0)], align=PP_ALIGN.CENTER)
    for dx, dl in ((Inches(1.15), "day 0"), (Inches(4.92), "day 90"),
                   (Inches(8.69), "day 180"), (Inches(12.31), "day 270+")):
        d = s.shapes.add_shape(MSO_SHAPE.OVAL, dx - Inches(0.07), ty - Inches(0.07),
                               Inches(0.14), Inches(0.14))
        solid(d, SURFACE, INK_2, 1.5)
        add_text(s, dx - Inches(0.55), ty + Inches(0.14), Inches(1.1), Inches(0.24),
                 [(dl, 9, False, INK_3, MONO_FONT, 0)], align=PP_ALIGN.CENTER)
    phase_cols = [
        (STEEL_WASH, STEEL, "Prove — days 0–90",
         ["One endpoint on AI Inference Server", "Accelerator capacity plan", "Data classes agreed in writing",
          "One workflow with a reviewer", "Baseline measured first"]),
        (AMBER_WASH, AMBER, "Ground — days 90–180",
         ["Serving on OpenShift AI", "Retrieval over your guidance", "Tune on agency vocabulary",
          "Drift and compliance wired", "Provisioning automated"]),
        (RED_WASH, RED_DARK, "Scale — days 180+",
         ["Registry with real approvals", "Workflows two to five", "Filing-season rehearsal",
          "Extend to the enclave", "Report in mission terms"]),
    ]
    py = Inches(3.45)
    pw = Inches(3.77)
    for i, (wash, col, head, items) in enumerate(phase_cols):
        px = MARGIN + i * (pw + Inches(0.16))
        rrect(s, px, py, pw, Inches(0.42), wash, radius=0.18)
        add_text(s, px + Inches(0.16), py + Inches(0.04), pw - Inches(0.3), Inches(0.34),
                 [(head, 12.5, True, col, HEAD_FONT, 0)])
        runs = []
        for it in items:
            runs.append(("•  " + it, 11, False, INK_2, BODY_FONT, 5))
        add_text(s, px + Inches(0.16), py + Inches(0.52), pw - Inches(0.3), Inches(2.6), runs)

    # ---- 9 next steps ----------------------------------------------------------
    s = add_base(prs, "Close with a specific ask, not a thank-you. Step zero is the lab "
                      "walk-through: an hour running the eight labs together to find the point in "
                      "the stack where they want to prove value, which scopes the pilot. The "
                      "architecture workshop follows, then hand off to Four Inc. and Carahsoft for "
                      "the contract vehicle conversation. Point at the contact panel: Brad's email "
                      "is there deliberately, and if nothing else he is the connector to the right "
                      "person. Ask for the cyber team by name: if nobody from IRS cyber is on, get "
                      "a referral to the ISSO and run the appendix for them in depth.")
    add_spine(s, "Next steps")
    eyebrow_and_title(s, "Next steps", "What happens after this hour")
    steps = [
        ("Step zero", "Lab walk-through",
         "An hour where we run the eight labs together, show and tell, and find the point in "
         "the stack where you want to prove value. That scopes the pilot."),
        ("Step one", "Architecture workshop",
         "A half-day with your platform and security teams to size accelerators, place the "
         "first workload and name the data classes in scope."),
        ("Step two", "Guided pilot",
         "One workflow, on your infrastructure, with a measured baseline and an agreed "
         "definition of success before we start."),
        ("Step three", "Acquisition path",
         "Four Inc. and Carahsoft carry the vehicles and pricing — bring them in early, not at "
         "the end."),
    ]
    gap = Inches(0.3)
    cw = int((SLIDE_W - 2 * MARGIN - gap * 3) / 4)
    for i, (tag, heading, body) in enumerate(steps):
        side_card(s, MARGIN + i * (cw + gap), Inches(2.0), cw, Inches(1.45), tag, heading, body)

    # the contact panel on the left and the moves on the right, as the deck lays them out
    cy = Inches(3.6)
    ch = Inches(2.8)
    pw = Inches(5.5)
    rrect(s, MARGIN, cy, pw, ch, SURFACE, BORDER, 1.0, radius=0.05)
    add_text(s, MARGIN + Inches(0.2), cy + Inches(0.12), pw - Inches(0.4), ch - Inches(0.2),
             [("Point of contact — Brad will follow up".upper(), 8.5, True, INK_3, MONO_FONT, 6),
              ("Brad Scalio", 16, True, INK, HEAD_FONT, 1),
              ("Red Hat · if nothing else, he will get you to the right person", 10, False, INK_2, BODY_FONT, 2),
              ("bscalio@redhat.com", 11, True, RED_DARK, MONO_FONT, 5),
              ("IRS account executive: Ted Craig, Red Hat. Everyone else, email Brad and he "
               "connects you to yours.", 10, False, INK_2, BODY_FONT, 8),
              ("RED HAT  ·  FOUR INC.  ·  CARAHSOFT", 8.5, True, INK_3, MONO_FONT, 6),
              ("Everything from today — deck, labs, guides — at nommsweymx.github.io/redhat-ai-tax-labs. "
               "The eight labs are the commands your engineers will run on day one. Follow it on "
               "your own: …/adventure.html.", 9, False, INK_3, BODY_FONT, 0)])
    mx = MARGIN + pw + Inches(0.35)
    mw = SLIDE_W - MARGIN - mx
    moves = [
        ("Already a Red Hat customer? Ask for your Solution Architect.",
         "Not sure who that is? Email Brad, open a ticket in the Customer Portal and ask "
         "support, or ask through your management line. The foundational questions are free "
         "to ask and expensive to skip."),
        ("Start a community of practice.",
         "A standing group across platform, security and mission teams, built around one "
         "workflow. We will help seed it and we will show up."),
        ("Bring your hardest question.",
         "Air-gapped operation, FedRAMP boundaries, accelerator scarcity, model provenance. If "
         "you did not see it here today, that does not mean it does not exist — ask."),
        ("Bring your cyber team.",
         "If nobody from IRS cyber is on today, refer us to your ISSO or security lead. We will "
         "run a dedicated security session for them: the appendix, in depth."),
    ]
    runs = [("YOUR MOVE", 8.5, True, INK_3, MONO_FONT, 6)]
    for lead, detail in moves:
        runs.append((lead, 11, True, INK, BODY_FONT, 1))
        runs.append((detail, 9.5, False, INK_2, BODY_FONT, 7))
    add_text(s, mx, cy - Inches(0.05), mw, ch, runs)

    # ---- 10 labs ----------------------------------------------------------------
    s = add_base(prs, "Transition slide. Switch to a terminal now. Tell them the labs run in "
                      "simulate mode on a laptop with no cluster, and in live mode against their "
                      "own environment — same script, same commands. Run Lab 01 and stop hard on "
                      "step 4, the endpoint bound to 127.0.0.1. The deck's Demo view plays every "
                      "lab hands-free if you would rather narrate than type.")
    add_spine(s, "Labs preview")
    eyebrow_and_title(s, "Hands on · the takeaway", "Eight labs — real commands, run them yourself",
                      "An opinionated path on a personal laptop — not an MVP, never production, never on "
                      "a government computer. Free of charge and open to anyone: one self-contained HTML "
                      "on the Carahsoft event page, source at nommsweymx.github.io/redhat-ai-tax-labs. "
                      "Prove it to yourself: watch the model serve on 127.0.0.1.",
                      lede_top=Inches(2.05))
    add_table(s, [
        ["Lab", "What you do", "Product", "Rung"],
        ["01", "Serve a model inside your boundary", "AI Inference Server", "data → information"],
        ["02", "Teach it your notice taxonomy", "SDG Hub + Training Hub", "knowledge"],
        ["03", "Survive filing season", "OpenShift AI", "information at scale"],
        ["04", "Ground answers in your own guidance", "Retrieval", "knowledge"],
        ["05", "Automate the toil around the model", "Ansible", "executes judgement"],
        ["06", "Prove it to your ISSO", "Compliance, TrustyAI", "evidence → judgement"],
        ["07", "Ask your own logs", "Ops notebook", "information → knowledge"],
        ["08", "One loop, end to end", "OpenShift AI · Lightspeed · EDA", "data → judgement"],
    ], Inches(3.05), [Inches(0.9), Inches(4.9), Inches(3.0), Inches(2.8)], mono_cols=(0, 2, 3))
    add_text(s, MARGIN, Inches(6.42), Inches(11.5), Inches(1.0),
             [("One thing to remember: nothing here needed a public endpoint", 15, True, INK, HEAD_FONT, 4),
              ("No public model endpoint, no internet connection at inference time, no rewrite of a "
               "system of record. The labs run the upstream bits on a laptop; what an agency "
               "accredits is the supported Red Hat product built from them. Lab 08 chains the whole loop.",
               12, False, INK_2, BODY_FONT, 0)])

    # ---- 11 appendix: AO questions ----------------------------------------------
    s = add_base(prs, "This is the slide that unblocks the deal. Every row is a control the "
                      "platform provides, mapped to the question an authorizing official actually "
                      "asks. Expect interruptions here — let them happen, this is the conversation "
                      "you want. Pick a few rows and drill in rather than reading the table. Say "
                      "it plainly: do not roll your own validations, reach out and we connect "
                      "you with a specialist. Offer to take the table offline with their ISSO.")
    add_spine(s, "Security posture")
    eyebrow_and_title(s, "Appendix · Trusted, enterprise-ready AI", "The questions an authorizing official will ask")
    # the deck's full table: ten rows by four columns, so 9 pt with tight cell padding
    add_table(s, [
        ["Their question", "The platform control", "Where it lives", "Proven in"],
        ["Where does our data go when someone prompts the model?",
         "Nowhere. Inference runs on your cluster, in your enclave, on your accelerators.",
         "AI Inference Server · OpenShift AI", "Lab 01 · 127.0.0.1, no egress"],
        ["Can you prove this model is the one we approved?",
         "Model artifacts are signed and verified before they are admitted to the cluster.",
         "Sigstore / cosign", "Lab 06 · cosign verify"],
        ["Is the cryptography validated?",
         "FIPS mode is set once in RHEL CoreOS and inherited up the chain by OpenShift and "
         "OpenShift AI; where a component is not inherited, the exception is documented and "
         "covered by compensating controls.",
         "RHEL FIPS mode", "Lab 06 · fips-mode-setup, sestatus"],
        ["Does it work with our smart cards and hardware crypto?",
         "Tested with the hardware vendors: TPM, PIV/CAC smart-card authentication and "
         "hardware cryptography supported from the operating system up, on mainframes included.",
         "RHEL · hardware certification", "Slide 09 · base band"],
        ["Can this land in our FISMA moderate or high boundary?",
         "Platform controls map to the NIST 800-53 moderate and high baselines; your FIPS 199 "
         "categorization picks the venue — the platform is the same in all of them.",
         "RHEL · OpenShift", "Slide 11 · one manifest"],
        ["How do we know it stays compliant next quarter?",
         "Scheduled scans against a hardening profile, with machine-readable results.",
         "Compliance Operator", "Lab 06 · compliancescan"],
        ["What about the applications and containers we build on it?",
         "The same tooling spans your own application lifecycle on the platform: signing, "
         "scanning and admission policy at build, at deploy and at run time.",
         "OpenShift build · registry · admission", "Lab 06 · signature gate"],
        ["How do we detect the model drifting or skewing?",
         "Continuous drift and fairness metrics on live inference traffic.",
         "TrustyAI", "Lab 06 · drift, fairness"],
        ["What if we have no internet at all?",
         "Mirror images and models into the enclave; the platform is built for disconnected "
         "operation.",
         "oc-mirror · registry", "Slide 11 · enclave"],
        ["Who is accountable when it is wrong?",
         "A named reviewer on the signature, and every automated action launched from one "
         "governed console under enterprise RBAC, so each action carries the identity that "
         "ran it.",
         "Workflow design · Ansible Automation Platform", "Lab 05 · job history"],
    ], Inches(2.3), [Inches(2.9), Inches(4.9), Inches(1.95), Inches(1.85)], mono_cols=(2, 3),
       size=9, pad_y=Inches(0.03))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out_path)
    print(f"Wrote {out_path} ({len(prs.slides)} slides)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=Path("slides/exports/redhat-ai-tax-administration.pptx"))
    args = parser.parse_args()
    build(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
