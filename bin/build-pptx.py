#!/usr/bin/env python3
"""Build the PowerPoint export of the event deck.

The reveal.js slides in slides/slides.adoc are the source of truth for the
narrative. This script produces the .pptx that event platforms and agency
review processes tend to insist on, carrying the same content, the same
speaker notes, and native (editable) PowerPoint graphics: a filing-season
demand curve, a chevron lifecycle flow, a layered architecture diagram and a
roadmap timeline — real shapes, not screenshots.

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


def eyebrow_and_title(slide, eyebrow, title, lede=""):
    add_text(slide, MARGIN, Inches(0.55), SLIDE_W - 2 * MARGIN, Inches(0.34),
             [(eyebrow.upper(), 11, True, INK_3, MONO_FONT, 0)])
    add_text(slide, MARGIN, Inches(0.95), SLIDE_W - 2 * MARGIN, Inches(0.9),
             [(title, 34, True, INK, HEAD_FONT, 0)])
    if lede:
        add_text(slide, MARGIN, Inches(1.68), Inches(10.6), Inches(0.5),
                 [(lede, 14, False, INK_2, BODY_FONT, 0)])


def add_table(slide, rows, top, col_widths, header=True, mono_cols=()):
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
            cell.margin_top = Inches(0.05)
            cell.margin_bottom = Inches(0.05)
            cell.fill.solid()
            cell.fill.fore_color.rgb = SURFACE_2 if (header and r == 0) else GROUND
            para = cell.text_frame.paragraphs[0]
            cell.text_frame.word_wrap = True
            run = para.add_run()
            run.text = text
            is_head = header and r == 0
            run.font.size = Pt(10.5 if is_head else 12)
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
    s = add_base(prs, "Jon Keam and Brad Scalio present. Open by naming the room: Red Hat, Four "
                      "Inc. and Carahsoft. Frame the hour — foundations, then the platform story, "
                      "then live terminal, 5 for questions. "
                      "The promise: every claim we make today, we run in a shell before you leave.")
    add_text(s, MARGIN, Inches(2.05), Inches(11.2), Inches(0.34),
             [("RED HAT  ·  FOUR INC.  ·  CARAHSOFT — VIRTUAL EVENT", 12, True, RED, MONO_FONT, 0)])
    add_text(s, MARGIN, Inches(2.55), Inches(10.6), Inches(2.0),
             [("AI foundations for intelligent tax administration", 44, True, INK, HEAD_FONT, 0)])
    add_text(s, MARGIN, Inches(4.75), Inches(9.4), Inches(1.1),
             [("What predictive AI, generative AI and LLMs actually do — then how Red Hat turns "
               "models, agency knowledge and automation into an operable mission capability, "
               "proven in seven labs you run yourself.", 17, False, INK_2, BODY_FONT, 0)])
    add_text(s, MARGIN, Inches(5.85), Inches(9.4), Inches(0.4),
             [("Presented by Jon Keam and Brad Scalio", 14, True, INK_2, BODY_FONT, 0)])

    # ---- 2 the ladder: data to judgement --------------------------------------
    s = add_base(prs, "The spine of the hour. Read it left to right: the platform holds the data, "
                      "predictive AI and inference turn it into information, generative AI with "
                      "retrieval turns that into knowledge, and a person turns knowledge into a "
                      "determination they sign. Judgement is deliberately never automated — "
                      "Ansible, the registry and Sigstore execute and record what a person decided. "
                      "Every later slide tags its technologies with one of these four rungs.")
    eyebrow_and_title(s, "Why it matters", "From data to judgement — and who climbs each step",
                      "Every technology in this hour is tagged with the rung it serves. AI moves work up the ladder; it never takes the top step.")
    rungs = [
        ("Data", STEEL, "What happened, uninterpreted: returns, transcripts, calls, logs, telemetry. Where it lives decides the architecture.",
         "RHEL · OpenShift · OpenShift Logging · accelerators"),
        ("Information", AMBER, "Data in context for one case: a classification, a score, a diagnosis, a metric. What predictive AI and inference produce.",
         "AI Inference Server · KServe + vLLM · Granite · TrustyAI · Models-as-a-Service"),
        ("Knowledge", RED, "Information that informs an outcome: guidance, precedent, runbooks, taxonomies. The institution's memory, retrievable and cited.",
         "SDG Hub · Training Hub · pipelines · retrieval / vector store"),
        ("Judgement", GREEN, "A determination someone signs. Deliberately human; automation executes what was decided, it never decides.",
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

    # ---- 3 operating reality: demand curve -------------------------------------
    s = add_base(prs, "Do not lead with the technology. Lead with the shape of the problem. The "
                      "chart is the argument: a year of demand arrives in six weeks, far above any "
                      "capacity you can justify staffing year-round. The shaded gap is what "
                      "automation absorbs. The card on the right that matters most is the last one: "
                      "the data cannot leave, so the platform is the decision.")
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

    # ---- 4 where AI lands: chevron lifecycle -----------------------------------
    s = add_base(prs, "Walk the flow left to right. The red stages already have a human reviewer "
                      "in the loop, which makes them honest places to start. Exam selection is "
                      "deliberately gray: that is a determination affecting a taxpayer, and it "
                      "needs a much heavier governance conversation. Saying this unprompted buys "
                      "enormous credibility.")
    eyebrow_and_title(s, "Workflow map", "Where AI actually lands in the filing lifecycle",
                      "Red stages ship with a human on the signature. The gray one waits for governance.")
    stages = [
        ("Intake &\nclassification", "Route by intent,\nnot keyword", True),
        ("Validation", "Catch gaps before\na case is opened", True),
        ("Correspondence", "Draft; a reviewer\nedits and signs", True),
        ("Exam\nselection", "Taxpayer\ndeterminations", False),
        ("Collections\nsupport", "Brief the officer\nbefore the case", True),
        ("Taxpayer\nservice", "Answers carry\ntheir citation", True),
    ]
    cw = Inches(1.98)
    gap = Inches(0.02)
    x = MARGIN
    y = Inches(2.35)
    for title, caption, ai in stages:
        chev = s.shapes.add_shape(MSO_SHAPE.CHEVRON, x, y, cw, Inches(0.85))
        solid(chev, RED if ai else BORDER_STRONG)
        tf = chev.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        for li, lt in enumerate(title.split("\n")):
            para = tf.paragraphs[0] if li == 0 else tf.add_paragraph()
            para.alignment = PP_ALIGN.CENTER
            run = para.add_run()
            run.text = lt
            run.font.size = Pt(12)
            run.font.bold = True
            run.font.name = HEAD_FONT
            run.font.color.rgb = SURFACE if ai else INK
        add_text(s, x + Inches(0.12), y + Inches(1.0), cw - Inches(0.1), Inches(0.62),
                 [(caption.replace("\n", " "), 10, False, INK_2, BODY_FONT, 0)], align=PP_ALIGN.CENTER)
        pill = rrect(s, x + Inches(0.22), y + Inches(1.68), cw - Inches(0.46), Inches(0.3),
                     RED_WASH if ai else SURFACE_2, radius=0.5)
        ptf = pill.text_frame
        ptf.word_wrap = False
        ptf.vertical_anchor = MSO_ANCHOR.MIDDLE
        para = ptf.paragraphs[0]
        para.alignment = PP_ALIGN.CENTER
        run = para.add_run()
        run.text = "human in the loop" if ai else "governance first"
        run.font.size = Pt(8.5)
        run.font.bold = True
        run.font.name = MONO_FONT
        run.font.color.rgb = RED_DARK if ai else INK_3
        x += cw + gap
    bullet_cards(s, Inches(5.05), [
        ("Start where a human already reviews the output",
         "If a person signs the letter today, a model that drafts it changes throughput "
         "without changing accountability."),
        ("Automate the toil around the model, not just the model",
         "Provisioning, patching, scaling and evidence collection are most of the work — "
         "and that problem is already solved."),
    ], height=Inches(1.5))

    # ---- 5 five outcomes -------------------------------------------------------
    s = add_base(prs, "These five are the event abstract made concrete. Each names the product "
                      "that delivers it and the lab where the audience runs it. Do not linger — "
                      "this slide exists so people can map the rest of the hour.")
    eyebrow_and_title(s, "What teams get", "Five outcomes, and where each one is proven")
    add_table(s, [
        ["Outcome", "Platform capability", "Lab", "Rung"],
        ["Modernize mission-critical operations", "Ansible Automation Platform, Event-Driven Ansible", "05", "executes judgement"],
        ["Improve efficiency and accuracy", "Red Hat AI Inference Server, SDG Hub + Training Hub", "01, 02", "information + knowledge"],
        ["Unlock data-driven insights", "OpenShift AI, vector retrieval", "04", "knowledge"],
        ["Strengthen security and compliance", "FIPS, Compliance Operator, TrustyAI, Sigstore", "06", "evidence → judgement"],
        ["Build an AI-ready foundation", "OpenShift AI, KServe, vLLM", "03", "data → information"],
    ], Inches(2.4), [Inches(3.9), Inches(4.7), Inches(0.9), Inches(2.1)], mono_cols=(2, 3))

    # ---- 6 architecture: layered diagram ---------------------------------------
    s = add_base(prs, "Read bottom to top. The point is the two vertical pillars: automation and "
                      "trust are not a layer you add at the end. A project that treats compliance "
                      "as a phase after deployment discovers, at the worst possible moment, that "
                      "it cannot produce evidence for anything that already happened.")
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

    def layer(y, h, title, caption, fill=SURFACE, line=BORDER_STRONG, line_w=1.0, tag=""):
        rrect(s, lx, y, lw, h, fill, line, line_w, radius=0.10)
        add_text(s, lx + Inches(0.22), y + Inches(0.05), lw - Inches(1.2), h,
                 [(title, 12.5, True, INK, HEAD_FONT, 2),
                  (caption, 9.5, False, INK_2, BODY_FONT, 0)])
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
          tag="Lab 01")
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

    # ---- 7 adoption path: roadmap timeline -------------------------------------
    s = add_base(prs, "Be honest about sequencing. Most agencies stall on rows 2 and 3 of the "
                      "Prove phase — no accelerator capacity plan, and no written agreement on "
                      "which data may be used. Neither is technical. Ask the room directly which "
                      "phase they are in.")
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

    # ---- 8 next steps ----------------------------------------------------------
    s = add_base(prs, "Close with a specific ask, not a thank-you. The architecture workshop is "
                      "the natural next step. Then hand off to Four Inc. and Carahsoft for the "
                      "contract vehicle conversation.")
    eyebrow_and_title(s, "Next steps", "What happens after this hour")
    bullet_cards(s, Inches(2.45), [
        ("Architecture workshop", "Half a day with your platform and security teams to size "
         "accelerators, place the first workload and name the data classes in scope."),
        ("Guided pilot", "One workflow, on your infrastructure, with a measured baseline and an "
         "agreed definition of success before we start."),
        ("Acquisition path", "Four Inc. and Carahsoft carry the vehicles and pricing. Bring them "
         "into the conversation early, not at the end."),
    ])
    add_text(s, MARGIN, Inches(5.1), Inches(11.5), Inches(1.3),
             [("One thing to remember", 17, True, INK, HEAD_FONT, 8),
              ("Nothing in these seven labs required a public model endpoint, an internet "
               "connection at inference time, or a rewrite of a system of record. That is the "
               "whole argument.", 14, False, INK_2, BODY_FONT, 0)])

    # ---- 9 labs ----------------------------------------------------------------
    s = add_base(prs, "Transition slide. Switch to a terminal now. Tell them the labs run in "
                      "simulate mode on a laptop with no cluster, and in live mode against their "
                      "own environment — same script, same commands. Run Lab 01 and stop hard on "
                      "step 4, the endpoint bound to 127.0.0.1. The deck's Demo view plays every "
                      "lab hands-free if you would rather narrate than type.")
    eyebrow_and_title(s, "Hands on", "Seven labs — real commands, run them yourself",
                      "Simulate mode needs no cluster, no GPU and no credentials. The Demo view plays them hands-free.")
    add_table(s, [
        ["Lab", "What you do", "Product", "Rung"],
        ["01", "Serve a model inside your boundary", "AI Inference Server", "data → information"],
        ["02", "Teach it your notice taxonomy", "SDG Hub + Training Hub", "knowledge"],
        ["03", "Survive filing season", "OpenShift AI", "information at scale"],
        ["04", "Ground answers in your own guidance", "Retrieval", "knowledge"],
        ["05", "Automate the toil around the model", "Ansible", "executes judgement"],
        ["06", "Prove it to your ISSO", "Compliance, TrustyAI", "evidence → judgement"],
        ["07", "Ask your own logs", "Ops notebook", "information → knowledge"],
    ], Inches(2.4), [Inches(0.9), Inches(4.9), Inches(3.0), Inches(2.8)], mono_cols=(0, 2, 3))

    # ---- 10 appendix: AO questions ----------------------------------------------
    s = add_base(prs, "This is the slide that unblocks the deal. Every row is a control the "
                      "platform provides, mapped to the question an authorizing official actually "
                      "asks. Expect interruptions here — let them happen, this is the conversation "
                      "you want. Offer to take the table offline with their ISSO.")
    eyebrow_and_title(s, "Appendix · Trusted, enterprise-ready AI", "The questions an authorizing official will ask")
    add_table(s, [
        ["Their question", "The platform control", "Where"],
        ["Where does our data go?", "Nowhere. Inference runs on your cluster, your accelerators.", "AI Inference"],
        ["Is this the model we approved?", "Artifacts signed and verified before admission", "Sigstore"],
        ["Is the cryptography validated?", "FIPS mode is a supported operating state", "RHEL"],
        ["Still compliant next quarter?", "Scheduled scans, machine-readable results", "Compliance Op."],
        ["How do we detect drift?", "Drift and fairness metrics on live traffic", "TrustyAI"],
        ["What if we are air-gapped?", "Mirror images and models into the enclave", "oc-mirror"],
        ["Who is accountable?", "A named reviewer. The model drafts; it never sends.", "Workflow"],
    ], Inches(2.3), [Inches(3.6), Inches(5.9), Inches(2.1)], mono_cols=(2,))

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
