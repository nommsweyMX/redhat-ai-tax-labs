#!/usr/bin/env python3
"""Build the PowerPoint export of the event deck.

The reveal.js slides in slides/slides.adoc are the source of truth for the
narrative. This script produces the .pptx that event platforms and agency
review processes tend to insist on, carrying the same content and the same
speaker notes.

  python3 bin/build-pptx.py [--out slides/exports/redhat-ai-tax-administration.pptx]

Requires python-pptx (pip install python-pptx).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

# Palette — the same one the HTML deck uses.
RED = RGBColor(0xCC, 0x00, 0x00)
INK = RGBColor(0x1B, 0x12, 0x11)
INK_2 = RGBColor(0x54, 0x42, 0x3E)
INK_3 = RGBColor(0x8A, 0x76, 0x71)
GROUND = RGBColor(0xFB, 0xF9, 0xF8)
SURFACE_2 = RGBColor(0xF4, 0xEF, 0xED)
BORDER = RGBColor(0xE6, 0xDD, 0xDA)

HEAD_FONT = "Red Hat Display"
BODY_FONT = "Red Hat Text"
MONO_FONT = "Red Hat Mono"

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)
MARGIN = Inches(0.85)


def add_base(prs: Presentation, notes: str = "") -> "Slide":
    """A blank slide with the ground colour and the accent rule."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = GROUND

    rule = slide.shapes.add_shape(1, 0, 0, SLIDE_W, Emu(45720))  # 1 = rectangle
    rule.fill.solid()
    rule.fill.fore_color.rgb = RED
    rule.line.fill.background()
    rule.shadow.inherit = False

    if notes:
        slide.notes_slide.notes_text_frame.text = notes.strip()
    return slide


def add_text(slide, left, top, width, height, runs, align=PP_ALIGN.LEFT):
    """runs: list of (text, size, bold, colour, font, space_after_pt)."""
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
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


def eyebrow_and_title(slide, eyebrow, title, lede=""):
    add_text(
        slide,
        MARGIN,
        Inches(0.62),
        SLIDE_W - 2 * MARGIN,
        Inches(0.34),
        [(eyebrow.upper(), 11, True, INK_3, MONO_FONT, 0)],
    )
    add_text(
        slide,
        MARGIN,
        Inches(1.02),
        SLIDE_W - 2 * MARGIN,
        Inches(1.0),
        [(title, 34, True, INK, HEAD_FONT, 0)],
    )
    if lede:
        add_text(
            slide,
            MARGIN,
            Inches(2.05),
            Inches(9.6),
            Inches(0.7),
            [(lede, 15, False, INK_2, BODY_FONT, 0)],
        )


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


def bullet_cards(slide, top, cards):
    """cards: list of (heading, body). Laid out as a row of accent-ruled blocks."""
    gap = Inches(0.32)
    count = len(cards)
    total = SLIDE_W - 2 * MARGIN
    width = int((total - gap * (count - 1)) / count)

    for i, (heading, body) in enumerate(cards):
        left = MARGIN + i * (width + gap)
        bar = slide.shapes.add_shape(1, left, top, Inches(0.045), Inches(1.9))
        bar.fill.solid()
        bar.fill.fore_color.rgb = RED
        bar.line.fill.background()
        bar.shadow.inherit = False
        add_text(
            slide,
            left + Inches(0.18),
            top,
            width - Inches(0.18),
            Inches(1.9),
            [
                (heading, 15, True, INK, HEAD_FONT, 6),
                (body, 12, False, INK_2, BODY_FONT, 0),
            ],
        )


def build(out_path: Path) -> None:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    # ---- 1 title -----------------------------------------------------------
    s = add_base(
        prs,
        "Open by naming the room: Red Hat, Four Inc. and Carahsoft. Frame the "
        "hour - 25 minutes of story, 30 minutes of live terminal, 5 for "
        "questions. The promise: every claim we make today, we run in a shell "
        "before you leave.",
    )
    add_text(
        s,
        MARGIN,
        Inches(2.05),
        Inches(11.2),
        Inches(0.34),
        [("RED HAT  ·  FOUR INC.  ·  CARAHSOFT — VIRTUAL EVENT", 12, True, RED, MONO_FONT, 0)],
    )
    add_text(
        s,
        MARGIN,
        Inches(2.55),
        Inches(10.6),
        Inches(2.0),
        [("Turning AI strategy into tax administration outcomes", 44, True, INK, HEAD_FONT, 0)],
    )
    add_text(
        s,
        MARGIN,
        Inches(4.75),
        Inches(9.4),
        Inches(1.1),
        [
            (
                "A secure, flexible foundation that connects automation, hybrid "
                "cloud and intelligent workflows — then six labs where you run "
                "it yourself.",
                17,
                False,
                INK_2,
                BODY_FONT,
                0,
            )
        ],
    )

    # ---- 2 operating reality ----------------------------------------------
    s = add_base(
        prs,
        "Do not lead with the technology. Lead with the shape of the problem: "
        "seasonal demand against a fixed workforce, decades of correspondence "
        "logic locked in code nobody wants to touch, and data spread across "
        "systems never designed to talk. AI is interesting here because it "
        "works on unstructured language - which is most of what a tax agency "
        "handles.",
    )
    eyebrow_and_title(s, "The operating reality", "The work is seasonal, textual and unforgiving")
    bullet_cards(
        s,
        Inches(2.55),
        [
            ("Peak load, fixed staff", "Filing season concentrates a year of volume into weeks. Idle capacity in August cannot be justified; exhausted capacity in April becomes a headline."),
            ("Rules locked in legacy code", "Notice, eligibility and offset logic live in systems written decades ago. Rewriting them is a decade. Wrapping them is a quarter."),
            ("Answers are in the text", "Correspondence, transcripts and guidance are unstructured. Analytics never reached them; language models are built for them."),
        ],
    )
    add_text(
        s,
        MARGIN,
        Inches(5.0),
        Inches(11.5),
        Inches(1.4),
        [
            ("The constraint that decides the architecture", 17, True, INK, HEAD_FONT, 8),
            (
                "Federal tax information carries handling rules that rule out "
                "sending prompts to a public endpoint. The model has to come to "
                "the data — on premises, in an accredited cloud region, or in an "
                "air-gapped enclave.",
                14,
                False,
                INK_2,
                BODY_FONT,
                0,
            ),
        ],
    )

    # ---- 3 where AI lands --------------------------------------------------
    s = add_base(
        prs,
        "Walk the table top to bottom. The 'yes' rows already have a human "
        "reviewer in the loop, which makes them honest places to start. Exam "
        "selection is deliberately excluded: that is a determination affecting "
        "a taxpayer and needs a much heavier governance conversation. Saying "
        "this unprompted buys enormous credibility.",
    )
    eyebrow_and_title(
        s,
        "Workflow map",
        "Where AI actually lands in the filing lifecycle",
        "Start where a human already reviews the output.",
    )
    add_table(
        s,
        [
            ["Stage", "Work", "Good first candidate?"],
            ["Intake and classification", "Route contacts by intent, not keyword", "Yes"],
            ["Validation", "Flag gaps before a case is opened", "Yes"],
            ["Correspondence", "Draft notices for a reviewer to sign", "Yes"],
            ["Exam selection", "Determinations affecting a taxpayer", "No — governance first"],
            ["Collections support", "Summarize case history for an officer", "Yes"],
            ["Taxpayer service", "Answer from guidance, with the citation", "Yes"],
        ],
        Inches(2.75),
        [Inches(3.3), Inches(5.6), Inches(2.7)],
        mono_cols=(2,),
    )

    # ---- 4 five outcomes ---------------------------------------------------
    s = add_base(
        prs,
        "These five are the event abstract made concrete. Each names the "
        "product that delivers it and the lab where the audience runs it. Do "
        "not linger - this slide exists so people can map the rest of the hour.",
    )
    eyebrow_and_title(s, "What teams get", "Five outcomes, and where each one is proven")
    add_table(
        s,
        [
            ["Outcome", "Platform capability", "Lab"],
            ["Modernize mission-critical operations", "Ansible Automation Platform, Event-Driven Ansible", "05"],
            ["Improve efficiency and accuracy", "Red Hat Enterprise Linux AI, InstructLab", "01, 02"],
            ["Unlock data-driven insights", "OpenShift AI, vector retrieval", "04"],
            ["Strengthen security and compliance", "FIPS, Compliance Operator, TrustyAI, Sigstore", "06"],
            ["Build an AI-ready foundation", "OpenShift AI, KServe, vLLM", "03"],
        ],
        Inches(2.5),
        [Inches(4.6), Inches(5.9), Inches(1.1)],
        mono_cols=(2,),
    )

    # ---- 5 architecture ----------------------------------------------------
    s = add_base(
        prs,
        "Read bottom to top. The point is the two vertical concerns: automation "
        "and trust are not a layer you add at the end. A project that treats "
        "compliance as a phase after deployment discovers, at the worst "
        "possible moment, that it cannot produce evidence for anything that "
        "already happened.",
    )
    eyebrow_and_title(s, "Reference architecture", "One foundation, from bare metal to the taxpayer")
    add_table(
        s,
        [
            ["Layer", "What it provides"],
            ["Mission applications", "Correspondence intake · notice drafting · case summarization · guidance assistant"],
            ["Red Hat OpenShift AI", "KServe + vLLM serving · tuning pipelines · model registry · retrieval"],
            ["Red Hat OpenShift", "Scheduling · GPU partitioning · network policy · GitOps delivery"],
            ["RHEL / RHEL AI", "Bare metal · virtualized · accredited cloud · classified enclave"],
        ],
        Inches(2.5),
        [Inches(3.5), Inches(8.1)],
    )
    add_text(
        s,
        MARGIN,
        Inches(5.15),
        Inches(11.5),
        Inches(1.3),
        [
            ("Running vertically through every layer", 16, True, INK, HEAD_FONT, 8),
            ("Automation — Ansible Automation Platform provisions, patches, remediates and collects evidence (Lab 05)", 13, False, INK_2, BODY_FONT, 4),
            ("Trust — signed models, FIPS crypto, SELinux, Compliance Operator, TrustyAI, disconnected mirroring (Lab 06)", 13, False, INK_2, BODY_FONT, 0),
        ],
    )

    # ---- 6 AO questions ----------------------------------------------------
    s = add_base(
        prs,
        "This is the slide that unblocks the deal. Every row is a control the "
        "platform provides, mapped to the question an authorizing official "
        "actually asks. Expect interruptions here - let them happen, this is "
        "the conversation you want. Offer to take the table offline with their "
        "ISSO.",
    )
    eyebrow_and_title(s, "Trusted, enterprise-ready AI", "The questions an authorizing official will ask")
    add_table(
        s,
        [
            ["Their question", "The platform control", "Where"],
            ["Where does our data go?", "Nowhere. Inference runs on your cluster, your accelerators.", "RHEL AI"],
            ["Is this the model we approved?", "Artifacts signed and verified before admission", "Sigstore"],
            ["Is the cryptography validated?", "FIPS mode is a supported operating state", "RHEL"],
            ["Still compliant next quarter?", "Scheduled scans, machine-readable results", "Compliance Op."],
            ["How do we detect drift?", "Drift and fairness metrics on live traffic", "TrustyAI"],
            ["What if we are air-gapped?", "Mirror images and models into the enclave", "oc-mirror"],
            ["Who is accountable?", "A named reviewer. The model drafts; it never sends.", "Workflow"],
        ],
        Inches(2.5),
        [Inches(3.6), Inches(5.9), Inches(2.1)],
        mono_cols=(2,),
    )

    # ---- 7 adoption path ---------------------------------------------------
    s = add_base(
        prs,
        "Be honest about sequencing. Most agencies stall on rows 2 and 3 of the "
        "Prove phase - no accelerator capacity plan, and no written agreement "
        "on which data may be used. Neither is technical. Ask the room directly "
        "which phase they are in.",
    )
    eyebrow_and_title(
        s,
        "Adoption path",
        "Ninety days, then ninety more",
        "Nothing here requires a rewrite of a system of record.",
    )
    add_table(
        s,
        [
            ["Prove — days 0–90", "Ground — days 90–180", "Scale — days 180+"],
            ["One endpoint on RHEL AI", "Serving on OpenShift AI", "Registry with real approvals"],
            ["Accelerator capacity plan", "Retrieval over your guidance", "Workflows two to five"],
            ["Data classes agreed in writing", "Tune on agency vocabulary", "Filing-season rehearsal"],
            ["One workflow with a reviewer", "Drift and compliance wired", "Extend to the enclave"],
            ["Baseline measured first", "Provisioning automated", "Report in mission terms"],
        ],
        Inches(2.75),
        [Inches(3.87), Inches(3.87), Inches(3.87)],
    )

    # ---- 8 labs ------------------------------------------------------------
    s = add_base(
        prs,
        "Transition slide. Switch to a terminal now. Tell them the labs run in "
        "simulate mode on a laptop with no cluster, and in live mode against "
        "their own environment - same script, same commands. Run Lab 01 and "
        "stop hard on step 4, the endpoint bound to 127.0.0.1.",
    )
    eyebrow_and_title(
        s,
        "Hands on",
        "Six labs — real commands, run them yourself",
        "Simulate mode needs no cluster, no GPU and no credentials.",
    )
    add_table(
        s,
        [
            ["Lab", "What you do", "Product"],
            ["01", "Serve a model inside your boundary", "RHEL AI"],
            ["02", "Teach it your notice taxonomy", "InstructLab"],
            ["03", "Survive filing season", "OpenShift AI"],
            ["04", "Ground answers in your guidance", "Retrieval"],
            ["05", "Automate the toil around the model", "Ansible"],
            ["06", "Prove it to your ISSO", "Compliance, TrustyAI"],
        ],
        Inches(2.75),
        [Inches(1.0), Inches(6.6), Inches(4.0)],
        mono_cols=(0, 2),
    )

    # ---- 9 next steps ------------------------------------------------------
    s = add_base(
        prs,
        "Close with a specific ask, not a thank-you. The architecture workshop "
        "is the natural next step. Then hand off to Four Inc. and Carahsoft for "
        "the contract vehicle conversation.",
    )
    eyebrow_and_title(s, "Next steps", "What happens after this hour")
    bullet_cards(
        s,
        Inches(2.6),
        [
            ("Architecture workshop", "Half a day with your platform and security teams to size accelerators, place the first workload and name the data classes in scope."),
            ("Guided pilot", "One workflow, on your infrastructure, with a measured baseline and an agreed definition of success before we start."),
            ("Acquisition path", "Four Inc. and Carahsoft carry the vehicles and pricing. Bring them into the conversation early, not at the end."),
        ],
    )
    add_text(
        s,
        MARGIN,
        Inches(5.2),
        Inches(11.5),
        Inches(1.3),
        [
            ("One thing to remember", 17, True, INK, HEAD_FONT, 8),
            (
                "Nothing in these six labs required a public model endpoint, an "
                "internet connection at inference time, or a rewrite of a system "
                "of record. That is the whole argument.",
                14,
                False,
                INK_2,
                BODY_FONT,
                0,
            ),
        ],
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out_path)
    print(f"Wrote {out_path} ({len(prs.slides)} slides)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("slides/exports/redhat-ai-tax-administration.pptx"),
    )
    args = parser.parse_args()
    build(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
