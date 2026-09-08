#!/usr/bin/env python3
"""Generate slides/adventure.html — the self-guided catalogue of the whole kit.

The page is built from two sources so it cannot drift from them:

* slides/ladder-map.json — the rung definitions, colours and the
  technology → rung table.
* bin/adventure-inventory.json — one entry per lab, slide, guide, tool,
  export, talk track and data file: what it teaches, the screen to
  remember, prerequisites, and where it lives on the published site.

Usage: python3 bin/build-adventure.py [--out slides/adventure.html]
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://nommsweymx.github.io/redhat-ai-tax-labs/"
REPO = "https://github.com/nommsweyMX/redhat-ai-tax-labs"
BLOB = REPO + "/blob/main/"


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


# ----------------------------------------------------------------- links
def site_link(url: str) -> str:
    """Relative links so the page works on GitHub Pages and from a checkout."""
    if not url:
        return "./"
    if url.startswith(SITE):
        return "./" + url[len(SITE):]
    if url.startswith("/"):
        return "." + url
    return url


def blob(path: str) -> str:
    path = path.replace(str(ROOT) + "/", "")
    return BLOB + path.lstrip("/")


def rung_class(text: str) -> str:
    t = (text or "").lower()
    if "judgement" in t:
        return "r-judge"
    if "knowledge" in t:
        return "r-know"
    if "information" in t:
        return "r-info"
    return "r-data"


def chip(text: str, cls: str | None = None) -> str:
    return f'<span class="rung {cls or rung_class(text)}">{esc(text)}</span>'


HAT = ("M46,114 C40,58 58,16 100,14 C142,16 160,58 154,114 C184,112 196,124 194,132 "
       "C190,148 142,156 100,156 C58,156 10,148 6,132 C4,124 16,112 46,114 Z")


def photo_src(name: str, base: str) -> str:
    """Inline the photo when it is in slides/assets/, else point at the site copy."""
    p = ROOT / "slides" / "assets" / name
    if p.exists():
        import base64
        return "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode("ascii")
    return f"{base}assets/{name}"


def hat(uid: str, initials: str, photo: str, base: str) -> str:
    """A portrait inside a Red Hat fedora outline; initials show until the photo exists."""
    return (f'<svg class="hatpic" viewBox="0 0 200 160" role="img" aria-label="{initials}">'
            f'<defs><clipPath id="hat-{uid}"><path d="{HAT}"/></clipPath></defs>'
            f'<g clip-path="url(#hat-{uid})"><rect x="0" y="0" width="200" height="160" fill="var(--accent-wash)"/>'
            f'<text x="100" y="82" text-anchor="middle" font-family="Red Hat Display, sans-serif" font-weight="800" font-size="42" fill="var(--accent-ink)">{initials}</text>'
            f'<image href="{photo_src(photo, base)}" x="8" y="12" width="184" height="148" preserveAspectRatio="xMidYMin slice" onerror="this.remove()"/></g>'
            f'<path d="{HAT}" fill="none" stroke="var(--accent)" stroke-width="4.5" stroke-linejoin="round"/>'
            f'<path d="M46,114 L154,114" fill="none" stroke="var(--accent)" stroke-width="3"/></svg>')


# ----------------------------------------------------------------- data
def build(out: Path, base: str = "./") -> None:
    ladder = load_json(ROOT / "slides" / "ladder-map.json")
    inv = load_json(ROOT / "bin" / "adventure-inventory.json")["items"]
    by_id = {it["id"]: it for it in inv}
    labs = sorted((it for it in inv if it["kind"] == "lab"), key=lambda i: i["id"])
    slides = sorted((it for it in inv if it["kind"] == "slide"), key=lambda i: i["id"])
    talks = [it for it in inv if it["kind"] == "talk-track"]

    def lab_num(it) -> int:
        return int(it["id"].split("-")[1])

    def slide_num(it) -> int:
        return int(it["id"].split("-")[1])

    # Where each catalogue item is opened from (the thing a reader clicks first).
    def primary(it) -> str:
        k, i = it["kind"], it["id"]
        if k == "lab":
            return f"./#lab-{lab_num(it)}"
        if k == "slide":
            return f"./#slide-{slide_num(it)}"
        if i == "deck-labs":
            return "./#labs"
        if i == "deck-demo":
            return "./#demo"
        if k in ("page", "talk-track"):
            return "./presenter-notes.html" if "presenter" in i or k == "talk-track" else "./"
        if k == "table":
            return "./#slide-17"
        if k == "nav":
            return "./"
        url = it.get("site_url") or ""
        if url.startswith("http") and "github.com" not in url:
            return site_link(url)
        if url.startswith("/"):
            return site_link(url)
        if url:
            return url
        return blob(it["path"])

    def short_title(it) -> str:
        t = it["title"]
        t = re.sub(r"^Lab \d\d — ", "", t)
        return t.split(" — ")[0]

    # ------------------------------------------------------------- paths
    PATHS = [
        {
            "who": "I own a mission or a programme",
            "tag": "Programme owner · mission lead · acquisition",
            "why": "You need to know what is real, what is safe to start, and what to ask for. Read first, then watch one lab refuse to guess.",
            "steps": [
                ("slide-03", "Why now — a year of demand in six weeks, and the data cannot leave."),
                ("slide-05", "The ladder. If you remember one picture, make it this one."),
                ("slide-07", "Where AI lands first, and why exam selection is deliberately not on the list."),
                ("slide-08", "Five outcomes, each tied to the lab that proves it."),
                ("event-brief", "The brief: the same argument in prose, for the people you have to convince."),
                ("lab-04", "Watch the system refuse a question it has no guidance for. That is the governance story."),
                ("slide-14", "Ninety days, then ninety more — where programmes actually stall."),
                ("slide-15", "Your move: Solution Architect, community of practice, hardest question."),
            ],
        },
        {
            "who": "I run the platform",
            "tag": "Platform · infrastructure · capacity",
            "why": "One foundation from bare metal to the taxpayer. Serve a model on localhost, then survive April, then let automation carry the toil.",
            "steps": [
                ("slide-09", "The reference architecture — read it bottom to top; trust and automation span every layer."),
                ("slide-11", "Define the service once, run it in the datacenter, the accredited cloud or the enclave."),
                ("lab-01", "Serve Granite on 127.0.0.1 with the AI Inference Server. Stop on ss -ltnp."),
                ("lab-03", "KServe + vLLM on OpenShift AI: 2 → 20 replicas under a 400-user rehearsal."),
                ("lab-05", "Event-Driven Ansible remediates saturation in 62 seconds, with an audit row."),
                ("lib-sh", "How every lab is built: one step call per real command, simulate or live."),
                ("preflight", "Which labs can run live on the machine in front of you."),
                ("docs-workflow", "How this site is tested, built and published on every push."),
            ],
        },
        {
            "who": "I sign the authorization",
            "tag": "ISSO · authorizing official · assessor",
            "why": "Evidence is information; your decision is judgement. Everything here produces the first so a person can make the second.",
            "steps": [
                ("slide-17", "The questions an authorizing official will ask, each mapped to a control."),
                ("lab-06", "cosign, FIPS, a Compliance Operator scan that honestly says NON-COMPLIANT, and drift read correctly."),
                ("lab-01", "One line — the endpoint bound to 127.0.0.1 — answers 'where does our data go?'"),
                ("lab-05", "The rulebook escalates a provenance mismatch instead of fixing it; the audit row writes itself."),
                ("event-brief", "The AO questions table in prose, with the lab that proves each answer."),
                ("facilitator-guide", "Six stock answers: air-gapped, GPUs, hallucination, training on our data, other models, FedRAMP."),
                ("ladder", "The definitions the whole kit assumes — including why judgement is never automated."),
            ],
        },
        {
            "who": "I own the data, the notices, the guidance",
            "tag": "Subject-matter expert · data lead · correspondence",
            "why": "Knowledge is the institution's memory, retrievable and cited. You write it once as seeds and guidance; the model learns the vocabulary and cites the source.",
            "steps": [
                ("slide-04", "An LLM is the engine, not the vehicle — fine-tuning studies for the test, retrieval brings the notebook."),
                ("slide-06", "Predictive and generative fail differently, so they are governed differently."),
                ("lab-02", "Twelve seed examples become 2,200 kept samples; the tuned model beats the base on your taxonomy."),
                ("taxonomy-qna", "What an expert actually writes: contexts and Q&A pairs in qna.yaml, reviewed like code."),
                ("lab-04", "Ingest Publications 17, 501 and 594; get a cited CP14 answer; watch the refusal."),
                ("rag-corpus", "Where your own published guidance goes before a live run — and why the repo ships it empty."),
                ("rag-ingest", "Chunk, embed, index. Deliberately boring."),
                ("rag-query", "The four-rule system prompt, the 0.75 threshold and the --explain trace for a governance board."),
                ("slide-12", "The knowledge flywheel: generated text is a draft until it passes the same curation as any record."),
            ],
        },
        {
            "who": "I get paged",
            "tag": "Operations · SRE · on-call",
            "why": "Predict, explain, ground, act, learn. Point the same retrieval pattern at your own logs and watch diagnosis collapse from hours to minutes.",
            "steps": [
                ("slide-12", "The useful pattern is a loop, not a chatbot."),
                ("slide-13", "Where the hours actually live: diagnosis. MTTR is the proof."),
                ("lab-07", "Ninety days of logs, 48 runbooks, 312 postmortems — a cited diagnosis of an OOM in seconds."),
                ("lab-05", "The remediation that follows, with the digest check people forget."),
                ("lab-04", "The retrieval stack Lab 07 reuses — only the corpus changed."),
                ("lib-sh", "LAB_PACE=step and the other knobs for rehearsing on a projector."),
            ],
        },
        {
            "who": "I have to present this myself",
            "tag": "Facilitator · Solution Architect · partner",
            "why": "Everything you need to re-run the hour: the run of show, the talk track, the labs that demo well live, and the files people ask for afterwards.",
            "steps": [
                ("facilitator-guide", "Minute-by-minute timing, which labs to run live, projector settings, the honesty checklist."),
                ("page-presenter-console", "The console: 24 steps in lockstep with the deck, planted questions and 'on the ladder' beats."),
                ("run-all-labs", "Rehearse all seven labs in one command; CI runs the same thing."),
                ("deck-demo", "The Demo view plays every lab hands-free — a holding screen before you start."),
                ("reveal-slides", "The reveal.js cut of the deck, with speaker notes on S."),
                ("pptx-export", "The PowerPoint for platforms that insist on an upload."),
                ("ladder-map", "The source of truth for every rung chip, if you add a slide or a product."),
            ],
        },
    ]

    def step_html(sid: str, why: str) -> str:
        it = by_id.get(sid)
        if not it:
            raise SystemExit(f"unknown inventory id in path: {sid}")
        kind = it["kind"]
        if kind == "lab":
            label = f"Lab {lab_num(it):02d}"
        elif kind == "slide":
            label = f"Slide {slide_num(it):02d}"
        else:
            label = {"page": "page", "guide": "guide", "brief": "brief", "facilitator": "guide", "tool": "tool", "export": "export", "spec": "spec", "data": "data"}.get(kind, kind)
        return (f'<li><a href="{esc(primary(it))}"><span class="k">{esc(label)}</span>'
                f'<b>{esc(short_title(it))}</b></a><span>{esc(why)}</span></li>')

    paths_html = "".join(
        f'<article class="path" data-search="{esc(p["who"] + " " + p["tag"])}">'
        f'<span class="tag">{esc(p["tag"])}</span><h3>{esc(p["who"])}</h3><p>{esc(p["why"])}</p>'
        f'<ol>{"".join(step_html(s, w) for s, w in p["steps"])}</ol></article>'
        for p in PATHS)

    # ------------------------------------------------------------- ladder
    rung_cards = ""
    for key, r in ladder["rungs"].items():
        rung_cards += (f'<div class="rungcard {r["css"]}" style="--c:{r["color"]};--w:{r["wash"]}">'
                       f'<span class="rung {r["css"]}">{esc(r["label"])}</span><p>{esc(r["definition"])}</p></div>')
    tech_rows = "".join(
        f'<tr><td>{esc(k)}</td><td>{chip(v)}</td></tr>' for k, v in ladder["technologies"].items())

    # ------------------------------------------------------------- labs
    def lab_card(it) -> str:
        n = lab_num(it)
        nxt = " ".join(f'<a href="#lab-card-{int(x.split("-")[1])}">Lab {int(x.split("-")[1]):02d}</a>' for x in it.get("next", []) if x.startswith("lab-"))
        hl = "".join(f"<li>{esc(h)}</li>" for h in it["highlights"])
        pre = it.get("prerequisites", "")
        return f'''<article class="labcard" id="lab-card-{n}" data-search="{esc(it["title"] + " " + it.get("audience", "") + " " + it["what_you_learn"])}">
  <header><span class="badge">{n:02d}</span><div><h3>{esc(short_title(it))}</h3><div class="meta">{chip(it["rung"])}<span class="pill">{esc(it.get("minutes", ""))}</span></div></div></header>
  <p class="aud"><b>For</b> {esc(it.get("audience", ""))}</p>
  <p>{esc(it["what_you_learn"])}</p>
  <h4>The screens people remember</h4><ul>{hl}</ul>
  <p class="pre"><b>To run it for real</b> {esc(pre)}</p>
  <div class="links"><a class="btn" href="./#lab-{n}">Run it in the browser</a><a class="btn ghost" href="./docs/index.html#lab-{n:02d}">Lab guide</a><a class="btn ghost" href="{esc(blob(it["path"]))}">run.sh on GitHub</a><a class="btn ghost" href="./#demo">Watch the demo</a>{('<span class="next">Then: ' + nxt + '</span>') if nxt else ''}</div>
</article>'''

    labs_html = "".join(lab_card(it) for it in labs)
    flow = "".join(f'<a href="#lab-card-{lab_num(it)}"><i>{lab_num(it):02d}</i>{esc(short_title(it))}</a>' for it in labs)

    # ------------------------------------------------------------- slides
    slide_rows = ""
    for it in slides:
        n = slide_num(it)
        chips = " ".join(chip(x.strip()) for x in re.split(r"\s*[·,]\s*", it.get("rung", "")) if x.strip())
        remember = it["highlights"][0] if it.get("highlights") else ""
        slide_rows += (f'<tr data-search="{esc(it["title"] + " " + it["what_you_learn"])}"><td class="mono">{n:02d}</td>'
                       f'<td><a href="./#slide-{n}"><b>{esc(it["title"])}</b></a><span>{esc(it["what_you_learn"])}</span></td>'
                       f'<td>{chips}</td><td class="rem">{esc(remember)}</td></tr>')

    # ------------------------------------------------------------- catalogue groups
    def cat_card(it, extra_links: list[tuple[str, str]] | None = None) -> str:
        hl = "".join(f"<li>{esc(h)}</li>" for h in it.get("highlights", [])[:4])
        links = [("Open", primary(it))]
        p = it.get("path", "")
        if p and not primary(it).startswith("https://github.com") and Path(p.replace(str(ROOT) + "/", "")).suffix:
            links.append(("Source", blob(p)))
        for lnk in extra_links or []:
            links.append(lnk)
        lk = "".join(f'<a class="btn{" ghost" if i else ""}" href="{esc(u)}">{esc(t)}</a>' for i, (t, u) in enumerate(links))
        meta = "".join(f'<span class="pill">{esc(x)}</span>' for x in [it.get("minutes", "")] if x)
        rung = chip(it["rung"]) if it.get("rung") and len(it["rung"]) < 40 else ""
        return f'''<article class="cat" data-search="{esc(it["title"] + " " + it.get("what_you_learn", "") + " " + it.get("audience", ""))}">
  <h3>{esc(it["title"])}</h3><div class="meta">{rung}{meta}</div>
  <p>{esc(it.get("what_you_learn", ""))}</p><ul>{hl}</ul>
  {('<p class="aud"><b>For</b> ' + esc(it["audience"]) + '</p>') if it.get("audience") else ''}
  <div class="links">{lk}</div>
</article>'''

    guides = [by_id[i] for i in ["readme", "docs-index", "ladder", "event-brief", "facilitator-guide", "page-presenter-console"] if i in by_id]
    exports = [by_id[i] for i in ["deck-labs", "deck-demo", "reveal-slides", "pptx-export", "pdf-export"] if i in by_id]
    tools = [by_id[i] for i in ["lib-sh", "preflight", "run-all-labs", "makefile", "docs-workflow", "build-pptx", "attributes", "ladder-map", "repo-hygiene"] if i in by_id]
    data = [by_id[i] for i in ["taxonomy-qna", "rag-corpus", "rag-ingest", "rag-query"] if i in by_id]

    talks_html = "".join(
        f'<article class="talk" data-search="{esc(t["title"] + " " + t.get("what_you_learn", ""))}"><span class="tag">{esc(t.get("minutes") or t.get("audience") or "planted question")}</span>'
        f'<h3>{esc(t["title"].replace("PLANTED: ", ""))}</h3><p>{esc(t.get("what_you_learn", ""))}</p>'
        f'<ul>{"".join(f"<li>{esc(h)}</li>" for h in t.get("highlights", [])[:3])}</ul>'
        f'<a class="btn ghost" href="./presenter-notes.html">Open the console</a></article>'
        for t in talks)

    env_rows = [
        ("LAB_MODE", "simulate", "simulate prints the expected output of every command; live executes it against your environment."),
        ("LAB_PACE", "auto", "step pauses before each command: Enter runs it, s skips, q quits."),
        ("LAB_SPEED", "0.04", "seconds per character when typing commands; 0 for CI, 0.08 on a projector."),
        ("NO_COLOR", "unset", "any value disables ANSI colour — use it when screen sharing mangles it."),
    ]
    env_html = "".join(f'<tr><td class="mono">{k}</td><td class="mono">{d}</td><td>{esc(w)}</td></tr>' for k, d, w in env_rows)

    quick = [
        ("Deck", "./"), ("Labs", "./#labs"), ("Demo", "./#demo"), ("Presenter console", "./presenter-notes.html"),
        ("Documentation", "./docs/index.html"), ("Slides (reveal.js)", "./slides.html"),
        ("PowerPoint", "./exports/redhat-ai-tax-administration.pptx"), ("PDF", "./redhat-ai-tax-administration.pdf"),
        ("GitHub", REPO),
    ]
    quick_html = "".join(f'<a href="{esc(u)}">{esc(t)}</a>' for t, u in quick)

    css_rungs = "".join(
        f'.rung.{r["css"]}{{color:{r["color"]};border-color:{r["color"]};background:{r["wash"]}}}' for r in ladder["rungs"].values())

    page = f'''<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Choose Your Own Adventure</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@400;500;700;800;900&family=Red+Hat+Mono:wght@400;500;600;700&family=Red+Hat+Text:wght@400;500;700&display=swap">
<style>
:root{{--ground:#FBF9F8;--surface:#FFFFFF;--surface-2:#F4EFED;--border:#E6DDDA;--border-strong:#CFC2BE;--ink:#1B1211;--ink-2:#54423E;--ink-3:#7E6A64;--accent:#CC0000;--accent-ink:#A30000;--accent-wash:#FBEAE8;--shadow:0 1px 2px rgba(27,18,17,.06),0 8px 28px -14px rgba(27,18,17,.28)}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--ground);color:var(--ink);font-family:"Red Hat Text","Segoe UI",system-ui,sans-serif;font-size:16px;line-height:1.55;-webkit-font-smoothing:antialiased}}
h1,h2,h3,h4{{font-family:"Red Hat Display","Red Hat Text",system-ui,sans-serif;margin:0;line-height:1.1;letter-spacing:-.018em}}
p{{margin:0}} a{{color:var(--accent-ink)}}
.mono,code{{font-family:"Red Hat Mono",ui-monospace,monospace}}
.wrap{{max-width:1180px;margin:0 auto;padding:0 clamp(18px,3vw,40px)}}
.tag{{font-family:"Red Hat Mono",monospace;font-size:.66rem;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3)}}
.rung{{display:inline-flex;align-items:center;gap:5px;font-family:"Red Hat Mono",monospace;font-size:.6rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;border-radius:100px;padding:2px 8px 2px 6px;border:1px solid;vertical-align:middle;white-space:nowrap;line-height:1.5}}
.rung::before{{content:"";width:7px;height:7px;border-radius:50%;background:currentColor;flex:none}}
{css_rungs}
.pill{{font-family:"Red Hat Mono",monospace;font-size:.64rem;border:1px solid var(--border-strong);border-radius:100px;padding:2px 9px;color:var(--ink-2)}}
.reach .rung,.labcard .rung,.cat .rung{{align-self:flex-start}}
.btn{{display:inline-block;font-family:"Red Hat Display",sans-serif;font-weight:700;font-size:.8rem;border:1px solid var(--accent);background:var(--accent);color:#fff;border-radius:5px;padding:6px 12px;text-decoration:none}}
.btn.ghost{{background:transparent;color:var(--accent-ink)}}
.btn:hover{{filter:brightness(1.06)}}
header.hero{{border-top:4px solid var(--accent);background:radial-gradient(120% 90% at 92% 0%,var(--accent-wash) 0%,transparent 55%);padding:44px 0 26px}}
.brand{{display:flex;align-items:center;gap:10px;margin-bottom:22px}}
.brand .bars{{display:flex;gap:3px}} .brand .bars i{{display:block;width:14px;height:5px;background:var(--accent);border-radius:1px}} .brand .bars i:nth-child(2){{opacity:.55;width:9px}} .brand .bars i:nth-child(3){{opacity:.28;width:5px}}
.brand span{{font-family:"Red Hat Mono",monospace;font-size:.7rem;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3)}}
.hero h1{{font-size:clamp(2rem,4.4vw,3.6rem);font-weight:900;letter-spacing:-.03em;max-width:18ch}}
.hero .kicker{{font-size:clamp(1rem,1.3vw,1.2rem);color:var(--ink-2);max-width:62ch;margin-top:16px}}
.quick{{display:flex;flex-wrap:wrap;gap:8px;margin-top:22px}}
.quick a{{font-family:"Red Hat Mono",monospace;font-size:.72rem;font-weight:600;border:1px solid var(--border-strong);border-radius:100px;padding:5px 12px;color:var(--ink-2);text-decoration:none;background:var(--surface)}}
.quick a:first-child{{border-color:var(--accent);color:var(--accent-ink)}}
.search{{margin-top:22px;display:flex;gap:10px;align-items:center}}
.search input{{flex:1;max-width:520px;font:inherit;font-size:.95rem;padding:9px 14px;border:1px solid var(--border-strong);border-radius:8px;background:var(--surface)}}
.search span{{font-size:.8rem;color:var(--ink-3)}}
section{{padding:36px 0;border-top:1px solid var(--border)}}
section h2{{font-size:clamp(1.5rem,2.4vw,2.1rem);font-weight:800}}
section .lede{{color:var(--ink-2);max-width:70ch;margin-top:10px}}
.grid{{display:grid;gap:16px;margin-top:22px}}
.g2{{grid-template-columns:1fr 1fr}} .g3{{grid-template-columns:repeat(3,1fr)}} .g4{{grid-template-columns:repeat(4,1fr)}}
.path{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:18px 18px 14px;box-shadow:var(--shadow);display:flex;flex-direction:column;gap:8px}}
.path h3{{font-size:1.15rem}} .path > p{{font-size:.88rem;color:var(--ink-2)}}
.path ol{{margin:8px 0 0;padding:0;list-style:none;counter-reset:s;display:flex;flex-direction:column;gap:6px}}
.path li{{counter-increment:s;display:grid;grid-template-columns:22px 1fr;gap:8px;align-items:start;font-size:.82rem;color:var(--ink-2);padding:6px 0;border-top:1px solid var(--border)}}
.path li::before{{content:counter(s);font-family:"Red Hat Mono",monospace;font-size:.68rem;font-weight:700;color:var(--accent);border:1px solid var(--accent);border-radius:4px;text-align:center;line-height:18px;height:20px;margin-top:2px}}
.path li a{{display:flex;flex-direction:column;text-decoration:none;color:var(--ink)}}
.path li a .k{{font-family:"Red Hat Mono",monospace;font-size:.62rem;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3)}}
.path li a b{{font-family:"Red Hat Display",sans-serif;font-size:.92rem}}
.path li a:hover b{{color:var(--accent-ink)}}
.path li > span{{grid-column:2}}
.rungcard{{border:1px solid var(--c);background:var(--w);border-radius:10px;padding:14px}} .rungcard p{{font-size:.84rem;color:var(--ink-2);margin-top:8px}}
table{{width:100%;border-collapse:collapse;font-size:.86rem;background:var(--surface);border:1px solid var(--border);border-radius:8px;overflow:hidden}}
th,td{{text-align:left;padding:9px 12px;border-bottom:1px solid var(--border);vertical-align:top}}
th{{font-family:"Red Hat Mono",monospace;font-size:.66rem;text-transform:uppercase;letter-spacing:.12em;color:var(--ink-3);font-weight:600;background:var(--surface-2)}}
td.mono{{font-family:"Red Hat Mono",monospace;font-size:.8rem;color:var(--ink-3)}}
td span{{display:block;font-size:.8rem;color:var(--ink-2);margin-top:2px}}
td.rem{{font-size:.8rem;color:var(--ink-2);max-width:34ch}}
.tablewrap{{overflow-x:auto;margin-top:18px}}
.flow{{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:18px}}
.flow a{{display:inline-flex;align-items:center;gap:8px;text-decoration:none;color:var(--ink);font-family:"Red Hat Display",sans-serif;font-weight:700;font-size:.86rem;border:1px solid var(--border-strong);border-radius:100px;padding:5px 12px 5px 5px;background:var(--surface)}}
.flow a i{{font-style:normal;font-family:"Red Hat Mono",monospace;font-size:.72rem;color:#fff;background:var(--accent);border-radius:100px;padding:2px 7px}}
.flow a + a::before{{content:"→";margin-right:6px;color:var(--ink-3)}}
.labcard,.cat,.talk{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:18px;box-shadow:var(--shadow);display:flex;flex-direction:column;gap:9px;min-width:0}}
.labcard header{{display:grid;grid-template-columns:44px 1fr;gap:12px;align-items:start}}
.labcard .badge{{font-family:"Red Hat Mono",monospace;font-weight:700;font-size:.8rem;color:#fff;background:var(--accent);border-radius:5px;text-align:center;padding:6px 0}}
.labcard h3,.cat h3,.talk h3{{font-size:1.05rem}}
.meta{{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px;align-items:center}}
.labcard p,.cat p,.talk p{{font-size:.86rem;color:var(--ink-2)}}
.labcard h4{{font-family:"Red Hat Mono",monospace;font-size:.64rem;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3);font-weight:600;margin-top:2px}}
.labcard ul,.cat ul,.talk ul{{margin:0;padding-left:18px;display:flex;flex-direction:column;gap:4px;font-size:.82rem;color:var(--ink-2)}}
.aud,.pre{{font-size:.8rem!important;color:var(--ink-3)!important}} .aud b,.pre b{{font-family:"Red Hat Mono",monospace;font-size:.62rem;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3);margin-right:6px}}
.links{{display:flex;flex-wrap:wrap;gap:7px;align-items:center;margin-top:auto;padding-top:6px}}
.links .next{{font-size:.76rem;color:var(--ink-3);margin-left:auto}} .links .next a{{margin-left:4px}}
.talk .tag{{color:var(--accent)}}
.moves{{display:grid;grid-template-columns:1.1fr 1fr;gap:16px;margin-top:22px}}
.reach{{background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:10px;padding:18px;display:flex;flex-direction:column;gap:12px}}
.person{{display:grid;grid-template-columns:64px 1fr;gap:12px;align-items:center}} .hatpic{{display:block;width:64px;height:auto}}
.avatar{{width:44px;height:44px;border-radius:50%;background:var(--accent-wash);border:1px solid var(--accent);display:flex;align-items:center;justify-content:center;font-family:"Red Hat Display",sans-serif;font-weight:800;color:var(--accent-ink);font-size:.86rem;overflow:hidden;position:relative}}
.avatar::before{{content:attr(data-initials)}} .avatar img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
.person > div{{display:flex;flex-direction:column;line-height:1.3}} .person b{{font-family:"Red Hat Display",sans-serif}} .person span{{font-size:.8rem;color:var(--ink-2)}} .person a{{font-family:"Red Hat Mono",monospace;font-size:.82rem;font-weight:600;text-decoration:none}}
.movelist{{display:flex;flex-direction:column;gap:10px}}
.move{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 16px}} .move b{{font-family:"Red Hat Display",sans-serif;display:block;margin-bottom:3px}} .move span{{font-size:.84rem;color:var(--ink-2)}}
footer{{border-top:1px solid var(--border);padding:26px 0 40px;font-size:.8rem;color:var(--ink-3)}}
footer a{{color:var(--ink-2)}}
.hint{{font-size:.78rem;color:var(--ink-3);margin-top:8px}}
[hidden]{{display:none!important}}
@media (max-width:1000px){{.g3,.g4{{grid-template-columns:1fr 1fr}}}}
@media (max-width:700px){{.g2,.g3,.g4,.moves{{grid-template-columns:1fr}}.hero h1{{max-width:none}}}}
</style>

<header class="hero"><div class="wrap">
  <div class="brand"><div class="bars"><i></i><i></i><i></i></div><span>Red Hat · Four Inc. · Carahsoft · September 17, 2026</span></div>
  <h1>Choose your own adventure</h1>
  <p class="kicker">Everything from the session — the deck, seven virtual-terminal labs, the guides, the talk track, the tools and the files — catalogued and connected, so you can follow it on your own. Pick the path that matches your job, or browse the whole kit below.</p>
  <div class="quick">{quick_html}</div>
  <div class="search"><input id="q" type="search" placeholder="Filter the catalogue — try: refusal, FIPS, MTTR, pgvector, taxonomy" aria-label="Filter the catalogue"><span id="qn"></span></div>
</div></header>

<section id="paths"><div class="wrap">
  <span class="tag">Start here</span>
  <h2>Six paths through the kit</h2>
  <p class="lede">Each path is a reading order. Steps open the deck at the right slide, run a lab in your browser, or jump to the guide. Nothing here needs a cluster, a GPU or credentials — every lab runs in simulate mode.</p>
  <div class="grid g3">{paths_html}</div>
</div></section>

<section id="ladder"><div class="wrap">
  <span class="tag">The one thing to remember</span>
  <h2>The ladder: data → information → knowledge → judgement</h2>
  <p class="lede">Every technology, slide and lab in the kit is tagged with the rung it serves — in rainbow order, so nobody has to learn a palette. AI moves work up the ladder; it never takes the top step. <a href="./#slide-5">See the slide</a> · <a href="./docs/index.html#ladder">read the definitions</a> · <a href="{esc(blob('slides/ladder-map.json'))}">the machine-readable map</a>.</p>
  <div class="grid g4">{rung_cards}</div>
  <div class="tablewrap"><table><thead><tr><th>Technology</th><th>Rung it serves</th></tr></thead><tbody>{tech_rows}</tbody></table></div>
</div></section>

<section id="labs"><div class="wrap">
  <span class="tag">Hands on</span>
  <h2>The seven labs, connected</h2>
  <p class="lede">Real commands, representative output. Run them in the browser from the deck's Labs view, watch them in the Demo view, or clone the repo and run <code>./bin/run-all-labs.sh</code>. Each card says who it is for, what you will see, and what a live run needs.</p>
  <div class="flow">{flow}</div>
  <p class="hint">Labs 02 and 07 ship as walkthroughs: their run.sh files narrate the helper scripts they call, and those scripts are not in the repository yet — simulate mode is complete, live mode for those two is a to-do.</p>
  <div class="grid g2">{labs_html}</div>
</div></section>

<section id="slides"><div class="wrap">
  <span class="tag">The narrative</span>
  <h2>The deck, slide by slide</h2>
  <p class="lede">Seventeen slides, each with the rung it serves and the line to remember. Links open the interactive deck at that slide; press <kbd>N</kbd> there for the presenter notes.</p>
  <div class="tablewrap"><table><thead><tr><th>#</th><th>Slide</th><th>Rungs</th><th>The line to remember</th></tr></thead><tbody>{slide_rows}</tbody></table></div>
</div></section>

<section id="guides"><div class="wrap">
  <span class="tag">Read</span>
  <h2>Guides and documents</h2>
  <div class="grid g3">{"".join(cat_card(g) for g in guides)}</div>
</div></section>

<section id="exports"><div class="wrap">
  <span class="tag">Watch, present, download</span>
  <h2>Views and exports</h2>
  <div class="grid g3">{"".join(cat_card(e) for e in exports)}</div>
</div></section>

<section id="tools"><div class="wrap">
  <span class="tag">Under the hood</span>
  <h2>Tools, data and specs</h2>
  <p class="lede">The lab runtime and its four knobs, the readiness check, the build, and the data files a subject-matter expert or a data team will actually edit.</p>
  <div class="tablewrap"><table><thead><tr><th>Variable</th><th>Default</th><th>What it does</th></tr></thead><tbody>{env_html}</tbody></table></div>
  <div class="grid g3">{"".join(cat_card(t) for t in tools)}</div>
  <h3 style="margin-top:26px;font-size:1.2rem">Data you will replace with your own</h3>
  <div class="grid g2">{"".join(cat_card(d) for d in data)}</div>
</div></section>

<section id="talk"><div class="wrap">
  <span class="tag">Steal these</span>
  <h2>The talk track — five planted questions</h2>
  <p class="lede">The exchanges Jon and Brad rehearsed, and the answers. They work just as well in your own briefing.</p>
  <div class="grid g3">{talks_html}</div>
</div></section>

<section id="move"><div class="wrap">
  <span class="tag">Your move</span>
  <h2>Take it home</h2>
  <div class="moves">
    <div class="reach">
      <span class="tag">Reach us — Brad is your connector</span>
      <div class="person">{hat("bs", "BS", "brad-scalio.jpg", base)}<div><b>Brad Scalio</b><span>Red Hat · if nothing else, he will get you to the right person</span><a href="mailto:bscalio@redhat.com">bscalio@redhat.com</a></div></div>
      <div class="person">{hat("jk", "JK", "jon-keam.jpg", base)}<div><b>Jon Keam</b><span>Red Hat</span><a href="mailto:jkeam@redhat.com">jkeam@redhat.com</a></div></div>
      <p style="font-size:.84rem;color:var(--ink-2)">Four Inc. and Carahsoft carry the contract vehicles — bring them into the conversation early, not at the end.</p>
      <span class="rung r-judge">the next decision is yours</span>
    </div>
    <div class="movelist">
      <div class="move"><b>Already a Red Hat customer? Ask for your Solution Architect.</b><span>Not sure who that is? Email Brad, open a ticket in the Customer Portal and ask support, or ask through your management line. The foundational questions are free to ask and expensive to skip.</span></div>
      <div class="move"><b>Start a community of practice.</b><span>A standing group across platform, security and mission teams, built around one workflow. We will help seed it and we will show up.</span></div>
      <div class="move"><b>Bring your hardest question.</b><span>Air-gapped operation, FedRAMP boundaries, accelerator scarcity, model provenance. If you did not see it here, that does not mean it does not exist — ask.</span></div>
      <div class="move"><b>Book the architecture workshop.</b><span>Half a day with your platform and security teams to size accelerators, place the first workload and name the data classes in scope — then a guided pilot with a measured baseline.</span></div>
    </div>
  </div>
</div></section>

<footer><div class="wrap">Published from <a href="{REPO}">{REPO.replace("https://", "")}</a> · site <a href="{SITE}">{SITE.replace("https://", "")}</a> · regenerate this page with <code>python3 bin/build-adventure.py</code>. Sample notices, figures and outputs are illustrative, written for the exercise; no agency reviewed them. Every workflow keeps a named human on the signature.</div></footer>

<script>
(function(){{
  var q = document.getElementById('q'), n = document.getElementById('qn');
  var cards = Array.prototype.slice.call(document.querySelectorAll('[data-search]'));
  function apply(){{
    var t = q.value.trim().toLowerCase(), shown = 0;
    cards.forEach(function(c){{
      var hit = !t || (c.getAttribute('data-search') + ' ' + c.textContent).toLowerCase().indexOf(t) >= 0;
      c.hidden = !hit; if(hit) shown++;
    }});
    n.textContent = t ? shown + ' of ' + cards.length + ' match' : '';
  }}
  q.addEventListener('input', apply);
  if(location.hash === '#q' || /[?&]q=/.test(location.search)){{ var m = /[?&]q=([^&]*)/.exec(location.search); if(m){{ q.value = decodeURIComponent(m[1]); apply(); }} }}
}})();
</script>
'''
    if base != "./":
        page = page.replace('href="./', 'href="' + base)
    out.write_text(page, encoding="utf-8")
    print(f"Wrote {out} ({len(page):,} bytes, {len(inv)} inventory items)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "slides" / "adventure.html")
    ap.add_argument("--base", default="./", help="link base, e.g. the published site URL for a standalone copy")
    args = ap.parse_args()
    build(args.out, args.base)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
