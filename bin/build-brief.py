#!/usr/bin/env python3
"""Build the solution-architect briefing deck (how the kit was built, what agentic tooling
adds, where it fails for federal customers) from its JSON outline.

    python3 bin/build-brief.py --outline slides/how-it-was-built.json --out slides/how-it-was-built.html
    python3 bin/build-brief.py --outline slides/how-it-was-built-talk.json --out slides/how-it-was-built-talk.html
    python3 bin/build-brief.py --essay slides/how-it-was-built-essay.json --out slides/how-it-was-built-essay.html \
        --adoc docs/96-how-it-was-built-essay.adoc
    python3 bin/build-brief.py --svg-dir slides/assets/graphics/built

One file, no framework: the same tokens and type as slides/deck.html, keyboard navigation,
N for presenter notes, F for full screen, a timer per slide in the eyebrow band, and inline
SVG graphics chosen by each slide's `graphic` key."""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

E = html.escape

CSS = r"""
:root{--ground:#FBF9F8;--surface:#FFFFFF;--surface-2:#F4EFED;--border:#E6DDDA;--border-strong:#CFC2BE;--ink:#1B1211;--ink-2:#54423E;--ink-3:#7E6A64;--accent:#CC0000;--accent-ink:#A30000;--accent-wash:#FBEAE8;--steel:#286C88;--steel-wash:#E7F1F5;--amber:#96620A;--amber-wash:#F8EFDC;--good:#1E7A55;--good-wash:#E4F3EC;--violet:#5B2E91;--violet-wash:#EFE6F7;--term-bg:#120D0C;--term-bg-2:#1C1513;--term-border:#3A2B27;--term-ink:#E8DFDC;--term-dim:#93807B;--term-green:#4FC1A0;--term-blue:#77B9E0;--shadow:0 1px 2px rgba(27,18,17,.06),0 8px 28px -14px rgba(27,18,17,.28)}
:root[data-theme="dark"]{--ground:#141010;--surface:#1E1817;--surface-2:#271F1D;--border:#382B28;--border-strong:#4E3C38;--ink:#F1E9E7;--ink-2:#C4B1AC;--ink-3:#A08E88;--accent:#FF5747;--accent-ink:#FF7A6B;--accent-wash:#3A1613;--steel:#6FBCD8;--steel-wash:#132A34;--amber:#E5AB4B;--amber-wash:#33260F;--good:#4FC1A0;--good-wash:#12352A;--violet:#A78BDA;--violet-wash:#251438;--shadow:0 1px 2px rgba(0,0,0,.5),0 8px 28px -14px rgba(0,0,0,.8)}
*{box-sizing:border-box}[hidden]{display:none!important}
html,body{height:100%}
body{margin:0;background:var(--ground);color:var(--ink);font-family:"Red Hat Text","Segoe UI",system-ui,sans-serif;font-size:16px;line-height:1.5;-webkit-font-smoothing:antialiased;display:flex;flex-direction:column;min-height:100vh}
h1,h2,h3,h4{font-family:"Red Hat Display","Red Hat Text",system-ui,sans-serif;margin:0;line-height:1.08;letter-spacing:-.018em;text-wrap:balance}
p{margin:0}a{color:var(--accent-ink)}
.mono,code,kbd{font-family:"Red Hat Mono",ui-monospace,monospace}
.eyebrow{font-family:"Red Hat Mono",ui-monospace,monospace;font-size:.68rem;font-weight:600;text-transform:uppercase;letter-spacing:.16em;color:var(--ink-3)}
.wrap{flex:1;display:flex;flex-direction:column;padding:22px 28px 12px;gap:12px;max-width:1260px;margin:0 auto;width:100%}
.stage{width:100%;aspect-ratio:16/9;background:var(--surface);border:1px solid var(--border);border-radius:10px;box-shadow:var(--shadow);position:relative;overflow:hidden}
.slide{position:absolute;inset:0;padding:clamp(26px,3.2vw,50px);display:none;flex-direction:column;overflow:hidden}
.slide[data-active="true"]{display:flex}
.rule{position:absolute;left:0;top:0;height:4px;width:100%;background:var(--accent)}
.head{display:flex;flex-direction:column;gap:7px;padding-bottom:12px;border-bottom:1px solid var(--border)}
.head .meta{display:flex;align-items:center;gap:12px}
.head .min{font-family:"Red Hat Mono",monospace;font-size:.62rem;letter-spacing:.1em;color:var(--accent-ink);border:1px solid var(--accent);border-radius:100px;padding:1px 8px}
.slide h2{font-size:clamp(1.35rem,2.3vw,2.2rem);font-weight:800;max-width:30ch}
.lede{color:var(--ink-2);font-size:clamp(.88rem,1vw,1.05rem);max-width:84ch;margin-top:2px}
.body{flex:1;min-height:0;padding-top:14px;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.25fr);gap:clamp(14px,1.8vw,30px);align-items:stretch}
.body.nogfx{grid-template-columns:1fr}
.body.wide{grid-template-columns:minmax(0,.85fr) minmax(0,1.5fr)}
ul.pts{margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:9px}
ul.pts li{position:relative;padding-left:18px;font-size:clamp(.8rem,.92vw,.98rem);color:var(--ink-2);line-height:1.42}
ul.pts li::before{content:"";position:absolute;left:0;top:.55em;width:8px;height:8px;border-radius:2px;background:var(--accent)}
ul.pts li b{color:var(--ink)}
.gfx{min-width:0;min-height:0;display:flex;align-items:center;justify-content:center}
.gfx svg{width:100%;height:auto;max-height:100%;display:block}
.gfx svg text{font-family:"Red Hat Text",system-ui,sans-serif}
.slidenum{position:absolute;right:clamp(26px,3.2vw,50px);top:calc(clamp(26px,3.2vw,50px) + 2px);font-family:"Red Hat Mono",monospace;font-size:.62rem;color:var(--ink-3);letter-spacing:.06em}
.chip{display:inline-flex;align-items:center;gap:6px;font-family:"Red Hat Mono",monospace;font-size:.6rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;border:1px solid;border-radius:100px;padding:2px 9px 2px 7px;white-space:nowrap;line-height:1.5}
.chip::before{content:"";width:7px;height:7px;border-radius:50%;background:currentColor}
.chip.red{color:var(--accent-ink);border-color:var(--accent);background:var(--accent-wash)}
.chip.green{color:var(--good);border-color:var(--good);background:var(--good-wash)}
.chip.violet{color:var(--violet);border-color:var(--violet);background:var(--violet-wash)}
.chip.steel{color:var(--steel);border-color:var(--steel);background:var(--steel-wash)}
.title-slide{justify-content:center;background:radial-gradient(120% 90% at 88% 8%,var(--accent-wash) 0%,transparent 56%)}
.title-slide h2{font-size:clamp(1.6rem,3.1vw,2.8rem);font-weight:900;letter-spacing:-.03em;max-width:22ch}
.title-slide .kicker{color:var(--ink-2);font-size:clamp(.9rem,1.1vw,1.05rem);max-width:70ch;margin-top:12px}
.title-slide .hosts{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}
.title-slide .host{border:1px solid var(--border-strong);border-radius:100px;padding:5px 14px;font-family:"Red Hat Mono",monospace;font-size:.72rem;font-weight:600;color:var(--ink-2)}
.title-slide .host:first-child{border-color:var(--accent);color:var(--accent-ink)}
.agenda{display:grid;grid-template-columns:repeat(3,1fr);gap:4px 18px;margin-top:18px;max-width:1000px}
.agenda div{display:grid;grid-template-columns:26px 1fr auto;gap:8px;align-items:baseline;font-size:.78rem;color:var(--ink-2);border-bottom:1px solid var(--border);padding:4px 0}
.agenda i{font-style:normal;font-family:"Red Hat Mono",monospace;font-size:.68rem;color:var(--accent)}
.agenda span.m{font-family:"Red Hat Mono",monospace;font-size:.64rem;color:var(--ink-3)}
.agenda.four{grid-template-columns:repeat(4,1fr);max-width:none;gap:0 14px;margin-top:12px}.agenda.four div{font-size:.7rem;padding:2px 0;line-height:1.3}
.checklist{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.checklist div{border:1px solid var(--border);border-radius:8px;padding:10px 12px;background:var(--surface-2);font-size:.84rem;color:var(--ink-2);display:grid;grid-template-columns:20px 1fr;gap:8px;align-items:start}
.checklist div::before{content:"✓";font-family:"Red Hat Mono",monospace;font-weight:700;color:var(--good)}
.notes{border:1px solid var(--border);border-left:3px solid var(--amber);border-radius:6px;background:var(--surface);padding:12px 16px;font-size:.86rem;color:var(--ink-2);max-height:28vh;overflow:auto}
.notes b{font-family:"Red Hat Mono",monospace;font-size:.66rem;letter-spacing:.12em;text-transform:uppercase;color:var(--amber);display:block;margin-bottom:5px}
.notes .src{display:block;margin-top:8px;font-family:"Red Hat Mono",monospace;font-size:.66rem;color:var(--ink-3);word-break:break-all}
.bar{display:flex;align-items:center;justify-content:space-between;gap:12px;font-family:"Red Hat Mono",monospace;font-size:.68rem;color:var(--ink-3)}
.bar .grp{display:flex;gap:6px;align-items:center}
button.ghost{appearance:none;background:transparent;border:1px solid var(--border);color:var(--ink-2);border-radius:5px;padding:5px 9px;font-family:"Red Hat Mono",monospace;font-size:.68rem;cursor:pointer}
button.ghost:hover{border-color:var(--border-strong);color:var(--ink)}
kbd{border:1px solid var(--border-strong);border-bottom-width:2px;border-radius:4px;padding:1px 5px;font-size:.66rem;color:var(--ink-2);background:var(--surface)}
.stage:fullscreen{border:0;border-radius:0}
.stage::backdrop{background:#FBF9F8}
:root[data-theme="dark"] .stage::backdrop{background:#141010}
.verify{margin-top:10px;border:1px dashed var(--border-strong);border-radius:8px;padding:8px 12px;font-size:.76rem;color:var(--ink-3);background:var(--surface-2)}
.verify b{color:var(--amber);font-family:"Red Hat Mono",monospace;font-size:.62rem;letter-spacing:.1em;text-transform:uppercase}
/* Small or short screens: the 16:9 stage becomes a scrolling card, graphics pan sideways, swipe moves between slides. */
@media (max-width:900px),(max-height:560px){
.wrap{padding:10px 10px 8px;gap:8px}
.stage{aspect-ratio:auto;height:auto;min-height:calc(100vh - 70px)}
.slide{position:relative;inset:auto;padding:18px 16px 24px;overflow:visible;min-height:calc(100vh - 70px)}
.slide h2{max-width:none;font-size:clamp(1.25rem,5.2vw,1.9rem)}
.lede{font-size:.95rem;max-width:none}
.head{padding-right:54px}
.body,.body.wide{display:flex;flex-direction:column;gap:14px;padding-top:12px}
ul.pts li{font-size:.93rem}
.gfx{display:block;overflow-x:auto;overflow-y:hidden;-webkit-overflow-scrolling:touch;border:1px solid var(--border);border-radius:8px;background:var(--surface);padding:6px 6px 2px}
.gfx svg{width:620px;min-width:620px;max-height:none}
.gfx::after{content:"drag sideways to pan the graphic";display:block;position:sticky;left:0;text-align:center;font-family:"Red Hat Mono",monospace;font-size:.6rem;letter-spacing:.08em;color:var(--ink-3);padding:4px 0 2px}
.title-slide{justify-content:flex-start}
.title-slide h2{font-size:clamp(1.45rem,6.6vw,2.4rem);max-width:none}
.title-slide .kicker{font-size:.95rem}
.agenda,.agenda.four{grid-template-columns:1fr;gap:0;max-width:none}
.agenda div,.agenda.four div{font-size:.8rem;padding:6px 0}
.checklist{grid-template-columns:1fr}
.slidenum{top:12px;right:14px}
.notes{max-height:none}
.verify{font-size:.8rem}
.bar{flex-wrap:wrap;justify-content:center;gap:8px}.bar .hint{display:none}
button.ghost{padding:10px 16px;font-size:.8rem}
}
@media (max-width:420px){.gfx svg{width:560px;min-width:560px}}
"""

# --------------------------------------------------------------------------- graphics
# Each returns an inline SVG. Colours come from the page tokens so dark mode follows.

def g_agent_loop() -> str:
    """One agentic turn: prompt → model → tool call → permission → tool result → model, repeated."""
    return """<svg viewBox="0 0 640 400" role="img" aria-label="One agentic turn: a prompt and context go to the model at the vendor API or a hyperscaler region; the model either answers or calls a tool; a permission gate sits in front of every tool call; the tool result returns to the model; the loop repeats until the model answers. Hooks observe before and after each tool call.">
<defs><marker id="al" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="var(--ink-3)"/></marker></defs>
<rect x="20" y="30" width="190" height="78" rx="10" fill="var(--surface-2)" stroke="var(--border-strong)"/>
<text x="115" y="60" text-anchor="middle" font-size="14" font-weight="800" fill="var(--ink)">Prompt + context</text>
<text x="115" y="82" text-anchor="middle" font-size="11" fill="var(--ink-2)">memory file · files · skills · history</text>
<rect x="250" y="20" width="200" height="98" rx="12" fill="var(--accent-wash)" stroke="var(--accent)" stroke-width="1.6"/>
<text x="350" y="56" text-anchor="middle" font-size="16" font-weight="900" fill="var(--ink)">Model</text>
<text x="350" y="78" text-anchor="middle" font-size="11" fill="var(--ink-2)">answer, or ask for a tool</text>
<text x="350" y="96" text-anchor="middle" font-size="10.5" fill="var(--ink-3)">the vendor API, or a hyperscaler region</text>
<rect x="490" y="40" width="130" height="58" rx="10" fill="var(--good-wash)" stroke="var(--good)"/>
<text x="555" y="64" text-anchor="middle" font-size="13" font-weight="800" fill="var(--ink)">Final answer</text>
<text x="555" y="84" text-anchor="middle" font-size="10.5" fill="var(--ink-2)">text, files, a commit</text>
<line x1="210" y1="69" x2="246" y2="69" stroke="var(--ink-3)" stroke-width="2" marker-end="url(#al)"/>
<line x1="450" y1="69" x2="486" y2="69" stroke="var(--ink-3)" stroke-width="2" marker-end="url(#al)"/>
<path d="M350 118 V150" stroke="var(--ink-3)" stroke-width="2" marker-end="url(#al)"/>
<rect x="240" y="154" width="220" height="56" rx="28" fill="var(--violet-wash)" stroke="var(--violet)" stroke-width="1.6"/>
<text x="350" y="178" text-anchor="middle" font-size="13" font-weight="800" fill="var(--ink)">Permission gate</text>
<text x="350" y="196" text-anchor="middle" font-size="10.5" fill="var(--ink-2)">mode · allow rules · classifier · a person</text>
<path d="M350 210 V242" stroke="var(--ink-3)" stroke-width="2" marker-end="url(#al)"/>
<rect x="190" y="246" width="320" height="70" rx="10" fill="var(--surface)" stroke="var(--border-strong)" stroke-width="1.4"/>
<text x="350" y="272" text-anchor="middle" font-size="14" font-weight="800" fill="var(--ink)">Tool call</text>
<text x="350" y="292" text-anchor="middle" font-size="10.5" fill="var(--ink-2)">Read · Edit · Bash · Grep · MCP server · subagent · browser</text>
<text x="350" y="308" text-anchor="middle" font-size="10" fill="var(--ink-3)">hooks run before and after; results are untrusted data</text>
<path d="M190 281 H120 V118 H250" fill="none" stroke="var(--accent)" stroke-width="2.4" stroke-dasharray="6 5" marker-end="url(#al)"/>
<text x="110" y="200" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--accent-ink)" transform="rotate(-90 110 200)">tool result back to the model</text>
<rect x="20" y="340" width="600" height="44" rx="8" fill="var(--surface-2)" stroke="var(--border)"/>
<text x="320" y="367" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--ink)">The loop repeats until the model stops asking for tools. Every arrow is a seam you can log, gate or cut.</text>
</svg>"""


def g_architecture() -> str:
    """The agent harness suite (Claude Code) in one picture."""
    return """<svg viewBox="0 0 640 420" role="img" aria-label="The agent harness suite (Claude Code): surfaces on top (CLI, IDE, hosted web sessions, CI runners, an SDK); the harness in the middle (tools, subagents, workflows, permissions, compaction, hooks); the extension layer (a project memory file, skills, MCP servers, plugins, hosted pages, schedules); and model providers at the base.">
<rect x="14" y="14" width="612" height="66" rx="10" fill="var(--surface-2)" stroke="var(--border-strong)"/>
<text x="28" y="36" font-size="10.5" font-weight="700" letter-spacing="1.4" fill="var(--ink-3)">SURFACES</text>
<g font-size="12" font-weight="700" fill="var(--ink)" text-anchor="middle">
<rect x="28" y="44" width="104" height="26" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="80" y="62">Terminal CLI</text>
<rect x="142" y="44" width="104" height="26" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="194" y="62">IDE extension</text>
<rect x="256" y="44" width="134" height="26" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="323" y="62">Hosted web sessions</text>
<rect x="400" y="44" width="110" height="26" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="455" y="62">CI runners</text>
<rect x="520" y="44" width="92" height="26" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="566" y="62">An SDK</text>
</g>
<rect x="14" y="96" width="612" height="118" rx="10" fill="var(--accent-wash)" stroke="var(--accent)" stroke-width="1.4"/>
<text x="28" y="118" font-size="10.5" font-weight="700" letter-spacing="1.4" fill="var(--accent-ink)">THE HARNESS — THE AGENTIC LOOP</text>
<g font-size="11.5" fill="var(--ink)" text-anchor="middle">
<rect x="28" y="128" width="110" height="34" rx="6" fill="var(--surface)" stroke="var(--border-strong)"/><text x="83" y="149" font-weight="700">Built-in tools</text>
<rect x="148" y="128" width="110" height="34" rx="6" fill="var(--surface)" stroke="var(--border-strong)"/><text x="203" y="149" font-weight="700">Subagents</text>
<rect x="268" y="128" width="110" height="34" rx="6" fill="var(--surface)" stroke="var(--border-strong)"/><text x="323" y="149" font-weight="700">Workflows</text>
<rect x="388" y="128" width="110" height="34" rx="6" fill="var(--surface)" stroke="var(--border-strong)"/><text x="443" y="149" font-weight="700">Permissions</text>
<rect x="508" y="128" width="104" height="34" rx="6" fill="var(--surface)" stroke="var(--border-strong)"/><text x="560" y="149" font-weight="700">Hooks</text>
<rect x="28" y="170" width="286" height="32" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="171" y="190" fill="var(--ink-2)" font-size="10.5">context · compaction · prompt caching · memory</text>
<rect x="326" y="170" width="286" height="32" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="469" y="190" fill="var(--ink-2)" font-size="10.5">sandbox: your machine, or a managed container</text>
</g>
<rect x="14" y="230" width="612" height="92" rx="10" fill="var(--steel-wash)" stroke="var(--steel)"/>
<text x="28" y="252" font-size="10.5" font-weight="700" letter-spacing="1.4" fill="var(--steel)">EXTENSION LAYER — WHAT YOU ADD</text>
<g font-size="11.5" font-weight="700" fill="var(--ink)" text-anchor="middle">
<rect x="28" y="262" width="92" height="46" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="74" y="281">Memory file</text><text x="74" y="297" font-size="9.5" font-weight="400" fill="var(--ink-3)">(CLAUDE.md)</text>
<rect x="128" y="262" width="92" height="46" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="174" y="281">Skills</text><text x="174" y="297" font-size="9.5" font-weight="400" fill="var(--ink-3)">SKILL.md · /slash</text>
<rect x="228" y="262" width="92" height="46" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="274" y="281">MCP servers</text><text x="274" y="297" font-size="9.5" font-weight="400" fill="var(--ink-3)">git host, drive, yours</text>
<rect x="328" y="262" width="92" height="46" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="374" y="281">Plugins</text><text x="374" y="297" font-size="9.5" font-weight="400" fill="var(--ink-3)">bundles of the above</text>
<rect x="428" y="262" width="92" height="46" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="474" y="281">Hosted pages</text><text x="474" y="297" font-size="9.5" font-weight="400" fill="var(--ink-3)">(Artifacts)</text>
<rect x="528" y="262" width="84" height="46" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="570" y="281">Schedules</text><text x="570" y="297" font-size="9.5" font-weight="400" fill="var(--ink-3)">(Routines)</text>
</g>
<rect x="14" y="338" width="612" height="68" rx="10" fill="var(--surface-2)" stroke="var(--border-strong)"/>
<text x="28" y="360" font-size="10.5" font-weight="700" letter-spacing="1.4" fill="var(--ink-3)">MODEL PROVIDERS — WHERE THE TOKENS GO</text>
<g font-size="11.5" font-weight="700" fill="var(--ink)" text-anchor="middle">
<rect x="28" y="370" width="140" height="26" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="98" y="388" font-size="10.5">Vendor API (Anthropic)</text>
<rect x="176" y="370" width="140" height="26" rx="6" fill="var(--surface)" stroke="var(--good)" stroke-width="1.6"/><text x="246" y="388" font-size="10.5">Gov region (Bedrock)</text>
<rect x="324" y="370" width="140" height="26" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="394" y="388" font-size="10.5">Cloud region (Vertex AI)</text>
<rect x="472" y="370" width="140" height="26" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="542" y="388" font-size="10.5">Cloud region (Foundry)</text>
</g>
</svg>"""


def g_boundary() -> str:
    """Three ways to run an agent, by where the data and the model sit."""
    return """<svg viewBox="0 0 640 400" role="img" aria-label="Three deployment shapes. Left: the vendor's commercial SaaS (claude.ai web sessions, hosted pages and connectors), data and model both outside the agency boundary. Middle: the harness CLI (Claude Code) on an agency workstation calling the model through a hyperscaler's authorized region (Amazon Bedrock in AWS GovCloud), the model inside an authorized boundary, the harness on your machine. Right: the AI Factory pattern, an open-source harness and an open model on OpenShift AI inside the agency's own enclave, including air-gapped.">
<defs><marker id="bl" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="var(--ink-3)"/></marker></defs>
<g>
<rect x="14" y="14" width="196" height="330" rx="12" fill="var(--surface)" stroke="var(--border-strong)" stroke-width="1.4"/>
<rect x="14" y="14" width="196" height="40" rx="12" fill="var(--amber-wash)"/><rect x="14" y="40" width="196" height="14" fill="var(--amber-wash)"/>
<text x="112" y="40" text-anchor="middle" font-size="12.5" font-weight="800" fill="var(--ink)">Vendor SaaS</text>
<text x="112" y="78" text-anchor="middle" font-size="10.5" fill="var(--ink-2)">vendor web app (claude.ai)</text>
<text x="112" y="94" text-anchor="middle" font-size="10" fill="var(--ink-2)">hosted sessions, pages, schedules</text>
<rect x="34" y="112" width="156" height="60" rx="8" fill="var(--amber-wash)" stroke="var(--amber)"/>
<text x="112" y="136" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--ink)">model + sandbox</text>
<text x="112" y="154" text-anchor="middle" font-size="10" fill="var(--ink-2)">vendor-managed (Anthropic)</text>
<rect x="34" y="186" width="156" height="40" rx="8" fill="var(--surface-2)" stroke="var(--border)"/>
<text x="112" y="210" text-anchor="middle" font-size="10.5" fill="var(--ink-2)">your repo is cloned in</text>
<text x="112" y="258" text-anchor="middle" font-size="11" font-weight="700" fill="var(--amber)">built THIS kit</text>
<text x="112" y="276" text-anchor="middle" font-size="10" fill="var(--ink-2)">public, open-source content</text>
<text x="112" y="306" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--accent-ink)">not for CUI · FTI · IL4+</text>
<text x="112" y="324" text-anchor="middle" font-size="9.5" fill="var(--ink-3)">data leaves the agency boundary</text>
</g>
<g>
<rect x="222" y="14" width="196" height="330" rx="12" fill="var(--surface)" stroke="var(--good)" stroke-width="1.6"/>
<rect x="222" y="14" width="196" height="40" rx="12" fill="var(--good-wash)"/><rect x="222" y="40" width="196" height="14" fill="var(--good-wash)"/>
<text x="320" y="40" text-anchor="middle" font-size="12.5" font-weight="800" fill="var(--ink)">Authorized cloud</text>
<text x="320" y="78" text-anchor="middle" font-size="10" fill="var(--ink-2)">the harness CLI on your workstation</text>
<text x="320" y="94" text-anchor="middle" font-size="10" fill="var(--ink-2)">to a cloud region (Bedrock, Vertex)</text>
<rect x="242" y="112" width="156" height="60" rx="8" fill="var(--good-wash)" stroke="var(--good)"/>
<text x="320" y="136" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--ink)">model in an authorized region</text>
<text x="320" y="154" text-anchor="middle" font-size="10" fill="var(--ink-2)">FedRAMP High · IL4/IL5 as authorized</text>
<rect x="242" y="186" width="156" height="40" rx="8" fill="var(--surface-2)" stroke="var(--border)"/>
<text x="320" y="210" text-anchor="middle" font-size="10.5" fill="var(--ink-2)">harness + files stay with you</text>
<text x="320" y="258" text-anchor="middle" font-size="11" font-weight="700" fill="var(--good)">the usable federal shape</text>
<text x="320" y="276" text-anchor="middle" font-size="10" fill="var(--ink-2)">no web sessions, no hosted pages</text>
<text x="320" y="306" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--accent-ink)">verify the IL for your data</text>
<text x="320" y="324" text-anchor="middle" font-size="9.5" fill="var(--ink-3)">still no air gap, still a vendor model</text>
</g>
<g>
<rect x="430" y="14" width="196" height="330" rx="12" fill="var(--surface)" stroke="var(--steel)" stroke-width="1.6"/>
<rect x="430" y="14" width="196" height="40" rx="12" fill="var(--steel-wash)"/><rect x="430" y="40" width="196" height="14" fill="var(--steel-wash)"/>
<text x="528" y="40" text-anchor="middle" font-size="12.5" font-weight="800" fill="var(--ink)">AI Factory, in the enclave</text>
<text x="528" y="78" text-anchor="middle" font-size="10.5" fill="var(--ink-2)">open harness: goose, OpenHands, Aider</text>
<text x="528" y="94" text-anchor="middle" font-size="10.5" fill="var(--ink-2)">open model on OpenShift AI · vLLM</text>
<rect x="450" y="112" width="156" height="60" rx="8" fill="var(--steel-wash)" stroke="var(--steel)"/>
<text x="528" y="136" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--ink)">model on your metal</text>
<text x="528" y="154" text-anchor="middle" font-size="10" fill="var(--ink-2)">Granite, Llama, Qwen, gpt-oss</text>
<rect x="450" y="186" width="156" height="40" rx="8" fill="var(--surface-2)" stroke="var(--border)"/>
<text x="528" y="210" text-anchor="middle" font-size="10.5" fill="var(--ink-2)">MCP · Llama Stack · Ansible</text>
<text x="528" y="258" text-anchor="middle" font-size="11" font-weight="700" fill="var(--steel)">air gap · IL6 · sovereign</text>
<text x="528" y="276" text-anchor="middle" font-size="10" fill="var(--ink-2)">the AI Factory pattern</text>
<text x="528" y="306" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--accent-ink)">smaller models, more engineering</text>
<text x="528" y="324" text-anchor="middle" font-size="9.5" fill="var(--ink-3)">you own the evals and the accreditation</text>
</g>
<rect x="14" y="358" width="612" height="34" rx="8" fill="var(--surface-2)" stroke="var(--border)"/>
<text x="320" y="380" text-anchor="middle" font-size="12" font-weight="700" fill="var(--ink)">Same question as the pyramid: where does the data live? That decides the architecture.</text>
</svg>"""


def g_pipeline() -> str:
    """How the kit was synthesized: inputs → sources of truth → generators → verify → CI → site."""
    return """<svg viewBox="0 0 640 400" role="img" aria-label="The build pipeline: inputs (the event abstract, two planning calls, a review transcript, the presenter's script, five graphics) flow into single sources of truth (the deck HTML, the lab run scripts, a ladder map, an inventory JSON), which generators turn into the console, reveal slides, PowerPoint, docs and the adventure page; a render-and-measure loop with Playwright checks every output and feeds fixes back to the sources; the host\'s CI runners (GitHub Actions) run the labs in simulate mode and publish the static site.">
<defs><marker id="pl" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="var(--ink-3)"/></marker><marker id="plr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker></defs>
<g font-size="10.5" fill="var(--ink-2)">
<rect x="14" y="20" width="150" height="130" rx="10" fill="var(--surface-2)" stroke="var(--border-strong)"/>
<text x="89" y="42" text-anchor="middle" font-size="12" font-weight="800" fill="var(--ink)">Inputs</text>
<text x="26" y="64">event abstract</text><text x="26" y="80">two planning calls</text><text x="26" y="96">review transcript</text><text x="26" y="112">presenter's own script</text><text x="26" y="128">five graphics (renders)</text><text x="26" y="144">eight real workflows</text>
<rect x="190" y="20" width="160" height="130" rx="10" fill="var(--accent-wash)" stroke="var(--accent)" stroke-width="1.4"/>
<text x="270" y="42" text-anchor="middle" font-size="12" font-weight="800" fill="var(--ink)">Sources of truth</text>
<text x="202" y="64" font-family="Red Hat Mono" font-size="9.5">slides/deck.html</text><text x="202" y="80" font-family="Red Hat Mono" font-size="9.5">labs/*/run.sh</text><text x="202" y="96" font-family="Red Hat Mono" font-size="9.5">slides/ladder-map.json</text><text x="202" y="112" font-family="Red Hat Mono" font-size="9.5">adventure-inventory.json</text><text x="202" y="128" font-family="Red Hat Mono" font-size="9.5">docs/*.adoc</text><text x="202" y="144" font-size="9.5" fill="var(--ink-3)">change once, regenerate the rest</text>
<rect x="376" y="20" width="250" height="130" rx="10" fill="var(--surface)" stroke="var(--border-strong)"/>
<text x="501" y="42" text-anchor="middle" font-size="12" font-weight="800" fill="var(--ink)">Generators and outputs</text>
<text x="388" y="64">presenter console · patch scripts</text><text x="388" y="80">asciidoctor → docs HTML · PDF</text><text x="388" y="96">asciidoctor-revealjs → reveal deck</text><text x="388" y="112">python-pptx → native PowerPoint</text><text x="388" y="128">build-adventure.py → catalogue page</text><text x="388" y="144">EN/ES text table → one deck, two languages</text>
</g>
<line x1="164" y1="85" x2="186" y2="85" stroke="var(--ink-3)" stroke-width="2" marker-end="url(#pl)"/>
<line x1="350" y1="85" x2="372" y2="85" stroke="var(--ink-3)" stroke-width="2" marker-end="url(#pl)"/>
<path d="M501 150 V192" stroke="var(--ink-3)" stroke-width="2" marker-end="url(#pl)"/>
<path d="M270 196 V156" fill="none" stroke="var(--accent)" stroke-width="2.4" stroke-dasharray="5 4" marker-end="url(#plr)"/>
<text x="282" y="179" font-size="10" font-weight="700" fill="var(--accent-ink)">fixes go back to the source</text>
<rect x="190" y="196" width="436" height="80" rx="10" fill="var(--steel-wash)" stroke="var(--steel)" stroke-width="1.4"/>
<text x="408" y="220" text-anchor="middle" font-size="12" font-weight="800" fill="var(--ink)">Render, measure, fix — every round, both languages, both views</text>
<text x="408" y="242" text-anchor="middle" font-size="10" fill="var(--ink-2)">Playwright + Chromium screenshots · overflow and text-extent checks · Spanish coverage</text>
<text x="408" y="262" text-anchor="middle" font-size="10" fill="var(--ink-2)">LibreOffice + pdftoppm to eyeball the pptx · every lab runs in simulate mode, end to end</text>
<path d="M408 276 V302" stroke="var(--ink-3)" stroke-width="2" marker-end="url(#pl)"/>
<rect x="14" y="306" width="612" height="76" rx="10" fill="var(--good-wash)" stroke="var(--good)" stroke-width="1.4"/>
<text x="320" y="330" text-anchor="middle" font-size="12" font-weight="800" fill="var(--ink)">CI (GitHub Actions): lint → every lab in simulate → build → publish (Pages)</text>
<text x="320" y="352" text-anchor="middle" font-size="10.5" fill="var(--ink-2)">The labs gate the docs. A broken lab blocks the site. Everything public, MIT, one URL.</text>
<text x="320" y="370" text-anchor="middle" font-size="10" fill="var(--ink-3)">plus a vendor-hosted review page, and a presenter console that follows the deck window to window</text>
</svg>"""


def g_toolchain() -> str:
    """The toolchain as five shelves."""
    rows = [
        ('AUTHORING', 'var(--accent)', ['HTML · CSS · JS, one file', 'inline SVG graphics', 'Red Hat fonts', 'EN/ES text table']),
        ('LABS', 'var(--good)', ['bash runtime · step()', 'Python · pgvector', 'Ansible · EDA rulebooks', 'KServe · qna.yaml']),
        ('DOCS + EXPORTS', 'var(--steel)', ['AsciiDoc · Asciidoctor', 'revealjs · pdf backends', 'python-pptx', 'Makefile · container']),
        ('VERIFY', 'var(--violet)', ['Playwright · Chromium', 'measurement scripts', 'LibreOffice · pdftoppm', 'bash -n · py_compile']),
        ('PUBLISH', 'var(--amber)', ['Git · a git host (GitHub)', 'CI runners (Actions)', 'static site (Pages)', 'MIT licence']),
    ]
    out = ['<svg viewBox="0 0 640 400" role="img" aria-label="The toolchain in five shelves: authoring, labs, docs and exports, verification, publishing; every item open source.">']
    y = 14
    for label, colour, items in rows:
        out.append(f'<rect x="14" y="{y}" width="612" height="68" rx="10" fill="var(--surface)" stroke="var(--border-strong)"/>')
        out.append(f'<rect x="14" y="{y}" width="8" height="68" rx="4" fill="{colour}"/>')
        out.append(f'<text x="34" y="{y + 26}" font-size="10.5" font-weight="700" letter-spacing="1.4" fill="{colour}">{label}</text>')
        x = 34
        for it in items:
            w = 14 + int(len(it) * 6.1)
            out.append(f'<rect x="{x}" y="{y + 36}" width="{w}" height="22" rx="11" fill="var(--surface-2)" stroke="var(--border)"/>')
            out.append(f'<text x="{x + w / 2}" y="{y + 51}" text-anchor="middle" font-size="10.5" font-weight="600" fill="var(--ink)">{E(it)}</text>')
            x += w + 8
        y += 76
    out.append('<text x="320" y="396" text-anchor="middle" font-size="10.5" fill="var(--ink-3)">no framework, no build step for the deck itself: open the file, present</text></svg>')
    return '\n'.join(out)


def g_gaps() -> str:
    return _tiles([
        ('Air gap · IL6 outside one cloud', 'no on-prem or weights offer; AWS classified regions only'),
        ('The DoD designation', 'blocks DoW contract work regardless of technology'),
        ('CUI / FTI boundary', 'hosted sessions and pages are vendor SaaS'),
        ('Supply chain', 'plugins, skills, MCP servers: pin, mirror, sign'),
        ('Prompt injection', 'tool results are untrusted; no system is immune'),
        ('Classifier as control', 'a model decides (17% misses); keep deny rules'),
        ('Limits and compaction', 'work stops or is summarised; checkpoint to git'),
        ('Audit, identity, 508', 'OTel opt-in; no PIV/CAC; ACRs cover the tool only'),
    ], 'var(--accent)', 'Eight places the agent harness (Claude Code) fails to perform for federal customers, each with the mitigation: air gap and classified networks outside one cloud, the DoD designation, the CUI and FTI boundary, supply chain, prompt injection, the classifier as a control, limits and compaction, and audit, identity and Section 508.')


def g_pyramid() -> str:
    """The kit's pyramid, small, with the three rules."""
    return """<svg viewBox="0 0 640 400" role="img" aria-label="The data-to-judgement pyramid beside three rules: solve a problem someone has; keep judgement human; right tool, right time.">
<g><polygon points="160,30 300,330 20,330" fill="none" stroke="var(--border-strong)"/>
<polygon points="160,32 221,164 99,164" fill="var(--violet)"/>
<polygon points="97,168 223,168 231,186 89,186" fill="#1D4ED8"/>
<polygon points="88,190 232,190 262,254 58,254" fill="var(--good)"/>
<polygon points="56,258 264,258 271,272 49,272" fill="#D99A00"/>
<polygon points="48,276 272,276 291,316 29,316" fill="#C2410C"/>
<polygon points="27,320 293,320 298,330 22,330" fill="var(--accent)"/>
<text x="160" y="112" text-anchor="middle" font-size="12" font-weight="700" fill="#fff">04</text>
<text x="160" y="230" text-anchor="middle" font-size="12" font-weight="700" fill="#fff">03</text>
<text x="160" y="302" text-anchor="middle" font-size="12" font-weight="700" fill="#fff">02</text>
<text x="160" y="352" text-anchor="middle" font-size="9.5" font-weight="700" letter-spacing=".8" fill="var(--ink-3)">DATA · INFORMATION · KNOWLEDGE · JUDGEMENT</text></g>
<g font-size="12" fill="var(--ink-2)">
<rect x="330" y="40" width="296" height="90" rx="10" fill="var(--accent-wash)" stroke="var(--accent)"/>
<text x="348" y="68" font-size="14" font-weight="800" fill="var(--ink)">Solve a problem someone has</text>
<text x="348" y="90" font-size="11">Every lab started from a queue, a pager or an</text><text x="348" y="108" font-size="11">accreditation question. Nothing else got in.</text>
<rect x="330" y="146" width="296" height="90" rx="10" fill="var(--violet-wash)" stroke="var(--violet)"/>
<text x="348" y="174" font-size="14" font-weight="800" fill="var(--ink)">Keep judgement human</text>
<text x="348" y="196" font-size="11">The agent drafted, measured and proposed;</text><text x="348" y="214" font-size="11">a person read every diff and signed off.</text>
<rect x="330" y="252" width="296" height="90" rx="10" fill="var(--good-wash)" stroke="var(--good)"/>
<text x="348" y="280" font-size="14" font-weight="800" fill="var(--ink)">Right tool, right time</text>
<text x="348" y="302" font-size="11">A frontier model in the cloud for public content;</text><text x="348" y="320" font-size="11">the AI Factory pattern inside the enclave for the data.</text>
</g>
<text x="320" y="384" text-anchor="middle" font-size="11" fill="var(--ink-3)">the same rules that run the deck ran the making of it</text>
</svg>"""


def _tiles(items: list[tuple[str, str]], colour: str, aria: str) -> str:
    """A wall of two-column tiles: a bold line and a smaller line under it."""
    out = [f'<svg viewBox="0 0 640 400" role="img" aria-label="{E(aria)}">']
    rows = (len(items) + 1) // 2
    h = min(80, int((372 - (rows - 1) * 12) / rows))
    for i, (t, m) in enumerate(items):
        col, row = i % 2, i // 2
        x, y = 14 + col * 310, 14 + row * (h + 12)
        out.append(f'<rect x="{x}" y="{y}" width="298" height="{h}" rx="10" fill="var(--surface)" stroke="var(--border-strong)" stroke-width="1.3"/>')
        out.append(f'<rect x="{x}" y="{y + 12}" width="6" height="{h - 24}" rx="3" fill="{colour}"/>')
        out.append(f'<text x="{x + 20}" y="{y + 31}" font-size="13.5" font-weight="800" fill="var(--ink)">{E(t)}</text>')
        out.append(f'<text x="{x + 20}" y="{y + 54}" font-size="10" fill="var(--ink-2)">→ {E(m)}</text>')
    out.append('</svg>')
    return '\n'.join(out)


def g_hurt() -> str:
    return _tiles([
        ('Usage limits mid-task', 'checkpoint early; every agent output is a file'),
        ('Context compaction, twice', 'the repo and commit messages are the memory'),
        ('Permission classifier', 'a push refused, then allowed; keep a human fallback'),
        ('Scratchpad cleared', 'the check scripts vanished; commit the harness'),
        ('Egress policy', 'no path to the live site; verified via the API'),
        ('Account-level actions', 'no repo creation; people create, agents prepare'),
    ], 'var(--amber)', 'Six things that hurt while building the kit, each with the lesson: usage limits mid-task, context compaction, the permission classifier, the cleared scratchpad, the egress policy, and account-level actions the agent could not take.')


def g_faces() -> str:
    """One repository, six faces."""
    tiles = [
        (14, 14, 'Interactive deck', '18 slides · EN/ES · Show/Tell · one 731 KB file'),
        (330, 14, 'Eight labs', '43 real commands with expected output · simulate or live'),
        (14, 98, 'Presenter console', '26 sections that follow the deck window to window'),
        (330, 98, 'Docs book', '11 AsciiDoc modules · HTML and PDF'),
        (14, 182, 'reveal.js + PowerPoint', '18 slides with notes · 11 native pptx slides'),
        (330, 182, 'Adventure catalogue', '57 items · 6 reading paths by job'),
    ]
    out = ['<svg viewBox="0 0 640 400" role="img" aria-label="One git repository renders six faces: the interactive deck, eight labs, the presenter console, the docs book, reveal.js and PowerPoint cuts, and the adventure catalogue; the host\'s CI runners (GitHub Actions) test the labs and publish the static site.">']
    for x, y, t, m in tiles:
        out.append(f'<rect x="{x}" y="{y}" width="296" height="70" rx="10" fill="var(--surface)" stroke="var(--border-strong)" stroke-width="1.3"/>')
        out.append(f'<text x="{x + 16}" y="{y + 29}" font-size="14" font-weight="800" fill="var(--ink)">{E(t)}</text>')
        out.append(f'<text x="{x + 16}" y="{y + 51}" font-size="10.5" fill="var(--ink-2)">{E(m)}</text>')
    out.append('<rect x="14" y="268" width="612" height="52" rx="10" fill="var(--accent-wash)" stroke="var(--accent)" stroke-width="1.4"/>')
    out.append('<text x="320" y="291" text-anchor="middle" font-size="14" font-weight="900" fill="var(--ink)">one git repository · MIT · no framework, no build step for the deck</text>')
    out.append('<text x="320" y="309" text-anchor="middle" font-size="10.5" fill="var(--ink-2)">sources of truth: deck.html · labs/*/run.sh · ladder-map.json · adventure-inventory.json · docs/*.adoc</text>')
    out.append('<rect x="14" y="334" width="612" height="52" rx="10" fill="var(--good-wash)" stroke="var(--good)" stroke-width="1.4"/>')
    out.append('<text x="320" y="357" text-anchor="middle" font-size="13" font-weight="800" fill="var(--ink)">CI (GitHub Actions): lint → run all eight labs → build → publish (Pages)</text>')
    out.append('<text x="320" y="375" text-anchor="middle" font-size="10.5" fill="var(--ink-2)">nommsweymx.github.io/redhat-ai-tax-labs · a vendor-hosted review page after every round</text>')
    out.append('</svg>')
    return '\n'.join(out)


def g_matrix() -> str:
    """Where the agent harness (Claude Code) fits by data category, limited to what was read on the vendor's pages (Anthropic) on 2026-11-19."""
    cols = ['Public content', 'CUI · FTI', 'IL4 · IL5', 'IL6 · TS']
    rows = [
        ('Vendor API and web app (Anthropic)', ['Y', 'N', 'N', 'N'], 'hosted sessions, pages, connectors, schedules'),
        ('Hyperscaler gov region (Bedrock)', ['Y', 'Y', 'Y', 'N'], 'AWS GovCloud · FedRAMP High · IL4/5 announced Jun 2025 · per model'),
        ('Hyperscaler gov region (Vertex AI)', ['Y', 'Y', 'D', 'N'], 'Assured Workloads · FedRAMP High · IL2 announced Apr 2025'),
        ('Vendor gov offering (Claude for Gov)', ['Y', 'Y', 'D', 'N'], 'GA 30 Sep 2026 · FedRAMP High environment · harness in early access'),
        ('Classified regions (AWS Secret, TS)', ['D', 'D', 'D', 'Y'], 'via the hyperscaler (Bedrock) · harness not stated'),
        ('Hyperscaler cloud (Microsoft Foundry)', ['Y', 'D', 'D', 'N'], 'no federal authorization read'),
    ]
    sym = {'Y': ('✓', 'var(--good)', 'var(--good-wash)'), 'N': ('✗', 'var(--accent-ink)', 'var(--accent-wash)'), 'D': ('—', 'var(--ink-3)', 'var(--surface-2)')}
    out = ['<svg viewBox="0 0 640 400" role="img" aria-label="Where the agent harness (Claude Code) fits by data category, as read on the vendor\'s pages (Anthropic) on 19 November 2026: the vendor API and web app for public content only; a hyperscaler gov region (Bedrock in AWS GovCloud) for FedRAMP High and IL4 and IL5 workloads; another (Vertex AI with Assured Workloads) for FedRAMP High and IL2; the vendor\'s government offering (Claude for Government) in a FedRAMP High environment; classified regions (AWS Secret and Top Secret via Bedrock); a third hyperscaler cloud (Microsoft Foundry) with no federal authorization read. The DoD note on the vendor\'s page is shown separately.">']
    x0, y0, lw, cw, rh = 14, 14, 262, 90, 44
    out.append(f'<text x="{x0}" y="{y0 + 20}" font-size="10.5" font-weight="700" letter-spacing="1.2" fill="var(--ink-3)">PATH</text>')
    for j, c in enumerate(cols):
        out.append(f'<text x="{x0 + lw + j * cw + cw / 2}" y="{y0 + 20}" text-anchor="middle" font-size="10.5" font-weight="700" letter-spacing="1" fill="var(--ink-3)">{E(c.upper())}</text>')
    y = y0 + 30
    for name, cells, note in rows:
        out.append(f'<rect x="{x0}" y="{y}" width="{lw + cw * 4}" height="{rh}" rx="8" fill="var(--surface)" stroke="var(--border)"/>')
        out.append(f'<text x="{x0 + 12}" y="{y + 19}" font-size="12" font-weight="800" fill="var(--ink)">{E(name)}</text>')
        out.append(f'<text x="{x0 + 12}" y="{y + 36}" font-size="9.5" fill="var(--ink-3)">{E(note)}</text>')
        for j, c in enumerate(cells):
            ch, fg, bg = sym[c]
            cx = x0 + lw + j * cw + cw / 2
            out.append(f'<rect x="{cx - 16}" y="{y + 9}" width="32" height="28" rx="6" fill="{bg}"/>')
            out.append(f'<text x="{cx}" y="{y + 29}" text-anchor="middle" font-size="16" font-weight="800" fill="{fg}">{ch}</text>')
        y += rh + 5
    out.append(f'<rect x="{x0}" y="{y + 2}" width="{lw + cw * 4}" height="40" rx="8" fill="var(--accent-wash)" stroke="var(--accent)"/>')
    out.append(f'<text x="{x0 + 12}" y="{y + 19}" font-size="11" font-weight="800" fill="var(--accent-ink)">DoD: a supply-chain-risk note on the vendor\'s own government page (Anthropic, read 2026-11-19)</text>')
    out.append(f'<text x="{x0 + 12}" y="{y + 34}" font-size="9.5" fill="var(--ink-2)">"applies to the use of Claude as a direct part of DoW contracts and subcontracts"</text>')
    out.append(f'<text x="{x0}" y="396" font-size="9.5" fill="var(--ink-3)">✓ stated on a vendor page (Anthropic) read on 2026-11-19 · — not stated · ✗ no authorization found · each model is authorized separately</text>')
    out.append('</svg>')
    return '\n'.join(out)


# --------------------------------------------------------------------------- history-driven graphics
# The timeline and growth panels read the per-commit metrics that bin/mine-history.py writes,
# so every number in them can be re-derived from the git tree.

HISTORY_PATH = Path(__file__).resolve().parent.parent / 'slides' / 'how-it-was-built-history.json'
_HISTORY: list[dict] | None = None


def history() -> list[dict]:
    global _HISTORY
    if _HISTORY is None:
        _HISTORY = json.loads(HISTORY_PATH.read_text(encoding='utf-8'))['commits'] if HISTORY_PATH.exists() else []
    return _HISTORY


def _day(c: dict) -> float:
    """Days since 26 August 2026, with the time of day as a fraction."""
    from datetime import date
    d = date.fromisoformat(c['date'])
    h, m = (int(x) for x in c['time'].split(':'))
    return (d - date(2026, 8, 26)).days + (h * 60 + m) / 1440


def _wrap(text: str, width: int) -> list[str]:
    lines, cur = [], ''
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f'{cur} {w}'.strip()
    if cur:
        lines.append(cur)
    return lines


def _lines(x: float, y: float, lines: list[str], size: float, fill: str, lh: float | None = None, anchor: str = 'start', weight: str = '400') -> str:
    lh = lh or size * 1.3
    return ''.join(f'<text x="{x}" y="{y + i * lh:.1f}" text-anchor="{anchor}" font-size="{size}" font-weight="{weight}" fill="{fill}">{E(l)}</text>' for i, l in enumerate(lines))


def _label(x: float, y: float, lines: list[str], anchor: str = 'start', size: float = 9.5, lh: float = 12) -> str:
    """A small caption whose first line is bold."""
    out = [f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" font-weight="800" fill="var(--ink)">{E(lines[0])}</text>']
    out.append(_lines(x, y + lh, lines[1:], size, 'var(--ink-2)', lh, anchor=anchor))
    return ''.join(out)


def g_brief() -> str:
    """The original ask: the event, the five outcomes, and the rules the builder set."""
    outcomes = ['Modernize operations', 'Serve a model inside the boundary', 'Ground answers in agency guidance', 'Prove it to the security office', 'Survive filing season']
    rules = [('Everything public, open source', 'one repo, MIT, no secrets'), ('No model names in the files', 'the kit outlives any model'),
             ('Every claim runs in a shell', 'a slide line is a lab step'), ('Laptop first, cluster when real', 'simulate mode, then live mode'),
             ('A console the audience never sees', 'notes follow the deck window to window'), ('End hands-on', 'not with a thank-you slide')]
    out = ['<svg viewBox="0 0 640 400" role="img" aria-label="The original ask: a one-hour virtual event on 17 September 2026 for about 56 IRS and adjacent-agency registrants, hosted by Carahsoft with Four Inc. and presented by Red Hat; an abstract naming five outcomes; and six standing rules the builder set on day one.">']
    out.append('<rect x="14" y="14" width="300" height="196" rx="10" fill="var(--surface)" stroke="var(--border-strong)" stroke-width="1.3"/>')
    out.append('<text x="30" y="38" font-size="10.5" font-weight="700" letter-spacing="1.4" fill="var(--accent-ink)">THE EVENT</text>')
    out.append(_lines(30, 62, ['AI foundations for intelligent', 'tax administration'], 15, 'var(--ink)', 19, weight='800'))
    out.append(_lines(30, 108, ['17 September 2026 · 1:00 to 2:00 PM Eastern · virtual', 'Carahsoft hosting · Four Inc. distributing', 'Red Hat presenting: two solution architects',
                                'about 56 registrants, IRS and adjacent agencies,', 'most of them new to Red Hat'], 10.5, 'var(--ink-2)', 16))
    out.append('<text x="30" y="198" font-size="10" font-style="italic" fill="var(--ink-3)">the brief was one abstract and one wish</text>')
    out.append('<rect x="330" y="14" width="296" height="196" rx="10" fill="var(--accent-wash)" stroke="var(--accent)" stroke-width="1.3"/>')
    out.append('<text x="346" y="38" font-size="10.5" font-weight="700" letter-spacing="1.4" fill="var(--accent-ink)">FIVE OUTCOMES IN THE ABSTRACT</text>')
    for i, o in enumerate(outcomes):
        y = 52 + i * 30
        out.append(f'<rect x="346" y="{y}" width="264" height="24" rx="12" fill="var(--surface)" stroke="var(--border)"/>')
        out.append(f'<text x="360" y="{y + 16}" font-size="10.5" font-weight="700" fill="var(--accent-ink)">0{i + 1}</text>')
        out.append(f'<text x="382" y="{y + 16}" font-size="11" font-weight="600" fill="var(--ink)">{E(o)}</text>')
    out.append('<rect x="14" y="224" width="612" height="162" rx="10" fill="var(--surface-2)" stroke="var(--border-strong)"/>')
    out.append('<text x="30" y="248" font-size="10.5" font-weight="700" letter-spacing="1.4" fill="var(--ink-3)">STANDING RULES, SET ON DAY ONE AND NEVER RELAXED</text>')
    for i, (t, m) in enumerate(rules):
        col, row = i % 3, i // 3
        x, y = 30 + col * 200, 262 + row * 58
        out.append(f'<rect x="{x}" y="{y}" width="188" height="48" rx="8" fill="var(--surface)" stroke="var(--border)"/>')
        out.append(f'<rect x="{x}" y="{y + 10}" width="4" height="28" rx="2" fill="var(--accent)"/>')
        out.append(f'<text x="{x + 14}" y="{y + 21}" font-size="10.5" font-weight="800" fill="var(--ink)">{E(t)}</text>')
        out.append(f'<text x="{x + 14}" y="{y + 38}" font-size="9.5" fill="var(--ink-2)">{E(m)}</text>')
    out.append('</svg>')
    return '\n'.join(out)


def g_timeline() -> str:
    """Forty-four commits on main, grouped into the rounds that landed, on one date axis."""
    x0, x1, ay = 40, 520, 200
    def X(day: float) -> float:
        return x0 + day / 22 * (x1 - x0)
    # (sha of the round's first commit, above?, level, lines); the marker sits at that commit's UTC time
    by_sha = {c['sha']: c for c in history()}
    def day_of(sha: str, fallback: float) -> float:
        return _day(by_sha[sha]) if sha in by_sha else fallback
    rounds = [
        (day_of('5d88c73', 0.72), True, 0, ['26 Aug · first commit', 'deck, six labs, docs,', 'Makefile and CI already in']),
        (day_of('e87b5ce', 1.38), False, 0, ['27 Aug · demo mode', 'labs play themselves,', 'first graphics']),
        (day_of('d81a33f', 7.7), True, 1, ['2 Sep · foundations', 'current AI stack, Lab 07,', 'presenter console']),
        (day_of('ea0730a', 8.79), False, 1, ['3 Sep · planning notes', 'folded in; audit finds', 'six gaps, fixed same day']),
        (day_of('039564c', 13.68), True, 0, ['8 Sep · the ladder', 'ladder-map.json, catalogue', 'page, portraits']),
        (day_of('78ac752', 15.27), False, 0, ['10 Sep · English/Spanish', '453 strings, dark theme,', 'theory panels, glossary']),
        (day_of('1a25b61', 19.69), True, 1, ['14 Sep · step cards', 'what, why, the seam,', 'on every lab step']),
        (day_of('d2cb6d8', 21.29), False, 1, ['16 Sep · pyramid icon,', 'pop-outs, the review', 'transcript mined']),
        (day_of('7dd52f2', 22.6), False, 0, ['17 Sep · event day', 'Lab 08, Show/Tell, the', 'layered title pyramid']),
    ]
    out = ['<svg viewBox="0 0 640 400" role="img" aria-label="A timeline of the kit from 26 August to 17 September 2026: 44 commits on main as ticks, nine rounds labelled by date, the event marker at 1 PM Eastern on 17 September with the last merge 38 minutes before, and the November briefing after a break in the axis.">']
    out.append(f'<line x1="{x0 - 12}" y1="{ay}" x2="{x1 + 14}" y2="{ay}" stroke="var(--border-strong)" stroke-width="1.5"/>')
    out.append(f'<line x1="{x1 + 30}" y1="{ay}" x2="626" y2="{ay}" stroke="var(--border-strong)" stroke-width="1.5"/>')
    out.append(f'<path d="M{x1 + 16} {ay - 6} l6 12 M{x1 + 24} {ay - 6} l6 12" stroke="var(--border-strong)" stroke-width="1.5" fill="none"/>')
    for c in history():
        x = X(_day(c))
        out.append(f'<line x1="{x:.1f}" y1="{ay - 7}" x2="{x:.1f}" y2="{ay + 7}" stroke="var(--ink-3)" stroke-width="1" opacity=".8"><title>{E(c["date"] + " " + c["time"] + " UTC · " + c["subject"])}</title></line>')
    for day, lab in [(0, '26 Aug'), (7, '2 Sep'), (14, '9 Sep'), (21, '16 Sep')]:
        out.append(f'<text x="{X(day):.1f}" y="{ay + 22}" text-anchor="middle" font-size="9.5" fill="var(--ink-3)">{lab}</text>')
    out.append(f'<text x="590" y="{ay + 22}" text-anchor="middle" font-size="9.5" fill="var(--ink-3)">19 to 20 Nov</text>')
    for day, above, level, lines in rounds:
        x = X(day)
        ly = (ay - 50 - level * 50) if above else (ay + 52 + level * 50)
        anchor = 'middle'
        tx = x
        if day < 0.8:
            anchor, tx = 'start', x - 26
        if day > 22:
            anchor, tx = 'start', x + 8
        out.append(f'<line x1="{x:.1f}" y1="{ay}" x2="{x:.1f}" y2="{ly:.1f}" stroke="var(--accent)" stroke-width="1" opacity=".55"/>')
        out.append(f'<circle cx="{x:.1f}" cy="{ay}" r="5.5" fill="var(--accent)" stroke="var(--surface)" stroke-width="2"/>')
        ty = ly - 6 - 12 * (len(lines) - 1) if above else ly + 12
        out.append(_label(tx, ty, lines, anchor))
    ex = X(22 + 17 / 24)
    out.append(f'<line x1="{ex:.1f}" y1="{ay}" x2="{ex:.1f}" y2="{ay - 86}" stroke="var(--good)" stroke-width="1.5" stroke-dasharray="4 3"/>')
    out.append(f'<path d="M{ex:.1f} {ay - 8} l7 8 l-7 8 l-7 -8 z" fill="var(--surface)" stroke="var(--good)" stroke-width="2"><title>Event opens: 17 Sep 2026, 1:00 PM Eastern (17:00 UTC)</title></path>')
    out.append(f'<text x="{ex + 6:.1f}" y="{ay - 78}" font-size="9.5" font-weight="800" fill="var(--good)">event opens</text>')
    out.append(_lines(ex + 6, ay - 66, ['1:00 PM Eastern', 'last merge to main', '38 minutes before'], 9.5, 'var(--ink-2)', 12))
    out.append(f'<circle cx="590" cy="{ay}" r="5.5" fill="var(--steel)" stroke="var(--surface)" stroke-width="2"/>')
    out.append(f'<line x1="590" y1="{ay}" x2="590" y2="{ay - 100}" stroke="var(--steel)" stroke-width="1" opacity=".55"/>')
    out.append(_label(626, ay - 142, ['this briefing', '39-agent research,', 'a deck, a handout,', 'this talk, an essay'], 'end'))
    out.append('<text x="320" y="392" text-anchor="middle" font-size="10" fill="var(--ink-3)">44 commits on main, each a tick · nine rounds, each a request in plain language · times from the git log, normalised to UTC</text>')
    out.append('</svg>')
    return '\n'.join(out)


def g_growth() -> str:
    """Six small multiples of the kit's size over the 23 days, one scale per panel."""
    panels = [('deck_kb', 'Deck size, KB'), ('slides', 'Slides'), ('labs', 'Labs'),
              ('es_keys', 'Spanish strings'), ('svgs', 'Inline SVG graphics'), ('console_sections', 'Presenter-console sections')]
    H = [c for c in history() if c.get('first_parent', True)]
    out = ['<svg viewBox="0 0 640 400" role="img" aria-label="Six small charts of growth from 26 August to 17 September 2026, each with its own scale: deck size 84 to 718 KB, slides 9 to 18, labs 6 to 8, Spanish strings 0 to 575, inline SVG graphics 1 to 19, presenter-console sections 0 to 26.">']
    out.append('<defs><clipPath id="gclip"><rect x="0" y="0" width="640" height="400"/></clipPath></defs>')
    for i, (key, title) in enumerate(panels):
        col, row = i % 3, i // 3
        px, py, pw, ph = 14 + col * 208, 14 + row * 184, 196, 168
        out.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="10" fill="var(--surface)" stroke="var(--border)"/>')
        out.append(f'<text x="{px + 12}" y="{py + 20}" font-size="11.5" font-weight="800" fill="var(--ink)">{E(title)}</text>')
        gx0, gx1, gy0, gy1 = px + 12, px + pw - 40, py + 36, py + ph - 26
        pts = []
        xprev = gx0
        vmax = max(c[key] for c in H) or 1
        for c in H:
            x = gx0 + _day(c) / 22.75 * (gx1 - gx0)
            x = max(x, xprev)
            xprev = x
            y = gy1 - c[key] / (vmax * 1.08) * (gy1 - gy0)
            pts.append((x, y, c))
        d = f'M{pts[0][0]:.1f} {pts[0][1]:.1f}'
        for (xa, ya, _), (xb, yb, _) in zip(pts, pts[1:]):
            d += f' H{xb:.1f} V{yb:.1f}'
        d += f' H{gx1 + 6:.1f}'
        out.append(f'<line x1="{gx0}" y1="{gy1}" x2="{gx1 + 6}" y2="{gy1}" stroke="var(--border)" stroke-width="1"/>')
        out.append(f'<path d="{d} V{gy1} H{gx0} Z" fill="var(--accent)" opacity=".1"/>')
        out.append(f'<path d="{d}" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
        first, last = pts[0], pts[-1]
        out.append(f'<circle cx="{gx1 + 6}" cy="{last[1]:.1f}" r="4" fill="var(--accent)" stroke="var(--surface)" stroke-width="2"><title>{E(f"{last[2][key]:,} on " + last[2]["date"])}</title></circle>')
        out.append(f'<text x="{gx1 + 14}" y="{last[1] + 4:.1f}" font-size="11" font-weight="800" fill="var(--ink)">{last[2][key]:,}</text>')
        out.append(f'<text x="{gx0}" y="{min(first[1] - 6, gy1 - 6):.1f}" font-size="9.5" fill="var(--ink-3)">{first[2][key]:,}</text>')
        out.append(f'<text x="{gx0}" y="{gy1 + 14}" font-size="8.5" fill="var(--ink-3)">26 Aug</text>')
        out.append(f'<text x="{gx1 + 6}" y="{gy1 + 14}" text-anchor="end" font-size="8.5" fill="var(--ink-3)">17 Sep</text>')
    out.append('<text x="320" y="392" text-anchor="middle" font-size="10" fill="var(--ink-3)">one scale per panel · the state of main after each of its commits, read from the git tree · bin/mine-history.py regenerates the data</text>')
    out.append('</svg>')
    return '\n'.join(out)


def g_where() -> str:
    """Where everything ran: the person, the managed container and model, the git host, the audience, the labs."""
    out = ['<svg viewBox="0 0 640 400" role="img" aria-label="Where it ran. A person on a laptop and a phone used the vendor\'s hosted agent sessions (Claude Code on the web). Each session ran in a vendor-managed (Anthropic) ephemeral container with a fresh clone, a shell, Python, node, Playwright with Chromium and LibreOffice, behind an allow-listed egress proxy, talking to the model at the API endpoint. The container pushed to GitHub, whose Actions runners ran the labs, built the docs and published to Pages; the audience loaded the deck from Pages. A hosted artifact copy lived on claude.ai. The labs ran on attendee laptops in simulate mode or on OpenShift AI, RHEL AI, Ansible Automation Platform and pgvector in live mode.">',
           '<defs><marker id="wl" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="var(--ink-3)"/></marker></defs>']
    # people
    out.append('<rect x="14" y="14" width="164" height="226" rx="10" fill="var(--surface)" stroke="var(--border-strong)" stroke-width="1.3"/>')
    out.append('<text x="28" y="36" font-size="10.5" font-weight="700" letter-spacing="1.4" fill="var(--ink-3)">THE PERSON</text>')
    out.append('<rect x="28" y="48" width="64" height="40" rx="4" fill="var(--surface-2)" stroke="var(--border-strong)"/><rect x="22" y="88" width="76" height="5" rx="2" fill="var(--border-strong)"/>')
    out.append('<rect x="108" y="46" width="26" height="46" rx="5" fill="var(--surface-2)" stroke="var(--border-strong)"/><circle cx="121" cy="86" r="2" fill="var(--border-strong)"/>')
    out.append(_lines(28, 116, ['hosted agent sessions', '(Claude Code on the web)', 'laptop and phone'], 11, 'var(--ink)', 14, weight='800'))
    out.append(_lines(28, 164, ['requests in plain language', 'notes, a transcript, graphics', 'every diff read by a person', 'before it merged'], 10, 'var(--ink-2)', 14))
    # anthropic boundary
    out.append('<rect x="194" y="14" width="300" height="226" rx="12" fill="none" stroke="var(--amber)" stroke-width="1.4" stroke-dasharray="6 4"/>')
    out.append('<text x="208" y="34" font-size="10" font-weight="700" letter-spacing="1.2" fill="var(--amber)">VENDOR-MANAGED (ANTHROPIC) · EPHEMERAL</text>')
    out.append('<rect x="206" y="44" width="172" height="148" rx="8" fill="var(--amber-wash)" stroke="var(--amber)"/>')
    out.append('<text x="216" y="62" font-size="11.5" font-weight="800" fill="var(--ink)">Session container</text>')
    out.append(_lines(216, 80, ['fresh clone of the repo', 'bash · git · Python · node', 'Playwright + Chromium', 'LibreOffice · pdftoppm', 'scratch dir, not kept', 'MCP: git host, session tools'], 9.8, 'var(--ink-2)', 13.5))
    out.append('<rect x="390" y="44" width="92" height="148" rx="8" fill="var(--accent-wash)" stroke="var(--accent)" stroke-width="1.4"/>')
    out.append('<text x="436" y="64" text-anchor="middle" font-size="12" font-weight="900" fill="var(--ink)">Model</text>')
    out.append(_lines(436, 84, ['vendor API', 'context in,', 'tokens out', '', 'every excerpt,', 'output and', 'screenshot', 'goes here'], 9.5, 'var(--ink-2)', 13, anchor='middle'))
    out.append('<line x1="378" y1="100" x2="386" y2="100" stroke="var(--ink-3)" stroke-width="2" marker-end="url(#wl)"/><line x1="390" y1="130" x2="382" y2="130" stroke="var(--ink-3)" stroke-width="2" marker-end="url(#wl)"/>')
    out.append('<rect x="206" y="202" width="276" height="30" rx="6" fill="var(--surface)" stroke="var(--border-strong)"/>')
    out.append('<text x="344" y="215" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--ink)">egress proxy, allow-list</text>')
    out.append('<text x="344" y="227" text-anchor="middle" font-size="9" fill="var(--ink-2)">the git host and fonts: yes · the published site, google.com: no</text>')
    # github
    out.append('<rect x="510" y="14" width="116" height="226" rx="10" fill="var(--good-wash)" stroke="var(--good)" stroke-width="1.3"/>')
    out.append('<text x="524" y="36" font-size="10.5" font-weight="700" letter-spacing="1.4" fill="var(--good)">GIT HOST</text>')
    out.append(_lines(524, 58, ['repo (GitHub)', 'two PRs, 44 merges'], 10, 'var(--ink)', 13, weight='700'))
    out.append(_lines(524, 96, ['CI runners (Actions)', 'ubuntu and the', 'asciidoctor image:', 'lint · 8 labs simulate', '· docs · slides · PDF'], 9.6, 'var(--ink-2)', 13))
    out.append(_lines(524, 176, ['static site (Pages)', 'one public URL', 'for everything'], 9.8, 'var(--ink)', 13, weight='700'))
    # arrows top row
    out.append('<line x1="178" y1="120" x2="190" y2="120" stroke="var(--ink-3)" stroke-width="2" marker-end="url(#wl)"/>')
    out.append('<line x1="494" y1="120" x2="506" y2="120" stroke="var(--ink-3)" stroke-width="2" marker-end="url(#wl)"/>')
    out.append('<text x="500" y="112" text-anchor="middle" font-size="8" fill="var(--ink-3)">push</text>')
    # bottom row
    boxes = [(14, 'HOSTED COPY', 'var(--amber)', 'var(--surface)', ['a vendor-hosted review page', '(a claude.ai artifact), republished', 'after every round, on any device']),
             (218, 'THE AUDIENCE', 'var(--good)', 'var(--surface)', ['browsers load the deck from the', 'static site; the presenter opens a', 'second window, the console']),
             (422, 'THE LABS', 'var(--steel)', 'var(--steel-wash)', ['attendee laptop: simulate mode,', 'nothing installed · live mode:', 'OpenShift AI, RHEL AI, Ansible', 'Automation Platform, pgvector'])]
    for x, t, colour, fill, lines in boxes:
        out.append(f'<rect x="{x}" y="262" width="204" height="98" rx="10" fill="{fill}" stroke="{colour}" stroke-width="1.3"/>')
        out.append(f'<text x="{x + 14}" y="{284}" font-size="10.5" font-weight="700" letter-spacing="1.4" fill="{colour}">{E(t)}</text>')
        out.append(_lines(x + 14, 304, lines, 9.5, 'var(--ink-2)', 14))
    out.append('<path d="M300 240 V258" stroke="var(--ink-3)" stroke-width="1.5" stroke-dasharray="3 3"/><path d="M116 240 V258" stroke="var(--ink-3)" stroke-width="1.5" stroke-dasharray="3 3"/><path d="M568 240 V250 H320 V258" fill="none" stroke="var(--ink-3)" stroke-width="1.5" marker-end="url(#wl)"/>')
    out.append('<text x="320" y="376" text-anchor="middle" font-size="11" font-weight="700" fill="var(--ink)">The agent never ran on a laptop and never inside an agency. Public content only, which is why this shape was acceptable.</text>')
    out.append('<text x="320" y="392" text-anchor="middle" font-size="9.5" fill="var(--ink-3)">two months later the container was new and the scratch directory was empty; only what was committed survived</text>')
    out.append('</svg>')
    return '\n'.join(out)


def g_trace() -> str:
    """One ordinary round, as the tool calls the agent actually made."""
    steps = [
        ('person', 'var(--ink-3)', 'Request', 'A sentence or two in plain language, sometimes with a file attached.'),
        ('search', 'var(--steel)', 'Grep', 'Search the 700 KB deck for the markers to change instead of reading it whole.'),
        ('read', 'var(--steel)', 'Read', 'Read 40 to 80 line excerpts around each match. Each excerpt enters the context.'),
        ('write', 'var(--violet)', 'Write', 'Write a Python patch script. Every replacement asserts exactly one match first.'),
        ('shell', 'var(--violet)', 'Bash', 'Run it. A permission gate sits in front of every shell command.'),
        ('browser', 'var(--good)', 'Playwright', 'Screenshot the touched slides in EN and ES, Show and Tell; measure text against its box.'),
        ('image', 'var(--good)', 'Look', 'The model reads the screenshots as images and fixes what overflows. Repeat.'),
        ('shell', 'var(--violet)', 'Bash', 'Overflow check on all 18 slides; every lab in simulate mode; bash -n; py_compile.'),
        ('git', 'var(--accent)', 'git', 'Commit on the branch with the fixed trailer; merge to main; push through the proxy.'),
        ('api', 'var(--amber)', 'Git host MCP', "Watch the CI run finish (GitHub's MCP server); the site is unreachable from the sandbox."),
        ('host', 'var(--amber)', 'Hosted page', 'Republish the vendor-hosted review page (artifact) so the presenter can check it anywhere.'),
        ('person', 'var(--ink-3)', 'Reply', 'What changed, what was verified, what was not. A person reads the diff.'),
    ]
    out = ['<svg viewBox="0 0 640 400" role="img" aria-label="One ordinary round as twelve steps: request, grep the deck, read excerpts, write a patch script, run it behind the permission gate, screenshot and measure with Playwright, look at the screenshots and fix, run the overflow check and the labs, commit merge and push, watch the CI run through the git host\'s MCP server, republish the vendor-hosted review page, reply.">']
    for i, (kind, colour, tool, text) in enumerate(steps):
        col, row = i // 6, i % 6
        x, y = 14 + col * 312, 14 + row * 58
        out.append(f'<rect x="{x}" y="{y}" width="300" height="50" rx="8" fill="var(--surface)" stroke="var(--border)"/>')
        out.append(f'<circle cx="{x + 20}" cy="{y + 25}" r="12" fill="{colour}"/>')
        out.append(f'<text x="{x + 20}" y="{y + 29}" text-anchor="middle" font-size="10.5" font-weight="800" fill="#fff">{i + 1}</text>')
        out.append(f'<text x="{x + 40}" y="{y + 19}" font-size="11" font-weight="800" fill="var(--ink)">{E(tool)}</text>')
        out.append(f'<text x="{x + 40 + len(tool) * 7 + 8}" y="{y + 19}" font-size="8.5" font-weight="700" letter-spacing="1" fill="{colour}">{E(kind.upper())}</text>')
        out.append(_lines(x + 40, y + 33, _wrap(text, 50)[:2], 9.3, 'var(--ink-2)', 11.5))
    out.append('<rect x="14" y="366" width="612" height="24" rx="6" fill="var(--surface-2)" stroke="var(--border)"/>')
    out.append('<text x="320" y="382" text-anchor="middle" font-size="10" fill="var(--ink-2)">a typical round: 20 to 60 tool calls · every result returns to the model as text or an image · nothing runs without the gate</text>')
    out.append('</svg>')
    return '\n'.join(out)


def g_context() -> str:
    """What the model sees on a turn: the context window, the cached prefix, and compaction."""
    segs = [('System prompt and tool definitions', 15, 'var(--surface-2)', 'var(--ink-2)'), ('Standing rules', 5, 'var(--accent-wash)', 'var(--accent-ink)'),
            ('Conversation so far', 13, 'var(--steel-wash)', 'var(--steel)'), ('Tool results: file excerpts, command output, screenshots', 55, 'var(--amber-wash)', 'var(--amber)'),
            ('Reply', 5, 'var(--good-wash)', 'var(--good)'), ('free', 7, 'var(--surface)', 'var(--ink-3)')]
    out = ['<svg viewBox="0 0 640 400" role="img" aria-label="The context window on one turn: a bar split into the system prompt and tool definitions, the standing rules, the conversation so far, tool results which take most of the room, the reply, and free space. The first parts repeat every turn and are cached. When the window fills, the model writes a summary and continues from it; this session was compacted twice. Below: what is in the window versus what is not.">']
    out.append('<text x="14" y="22" font-size="12.5" font-weight="800" fill="var(--ink)">One turn, as the model sees it</text>')
    out.append('<text x="626" y="22" text-anchor="end" font-size="9.5" fill="var(--ink-3)">proportions illustrative; they change every turn</text>')
    total, by, bh = 612, 60, 44
    cw = total * 0.33
    out.append(f'<path d="M14 {by - 8} V{by - 14} H{14 + cw:.1f} V{by - 8}" fill="none" stroke="var(--violet)" stroke-width="1.5"/>')
    out.append(f'<text x="{14 + cw / 2:.1f}" y="{by - 18}" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--violet)">repeated every turn, cached, cheap</text>')
    out.append(f'<path d="M{14 + cw + 4:.1f} {by - 8} V{by - 14} H626 V{by - 8}" fill="none" stroke="var(--amber)" stroke-width="1.5"/>')
    out.append(f'<text x="{(14 + cw + 4 + 626) / 2:.1f}" y="{by - 18}" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--amber)">new this turn: what the tools returned</text>')
    x = 14
    for i, (label, pct, fill, ink) in enumerate(segs):
        w = total * pct / 100 - 2
        out.append(f'<rect x="{x:.1f}" y="{by}" width="{w:.1f}" height="{bh}" rx="6" fill="{fill}" stroke="var(--border-strong)"/>')
        if pct >= 13:
            lines = _wrap(label, int(w / 5.6))[:2]
            size = 9.5 if pct < 20 else 10.5
            out.append(_lines(x + w / 2, by + bh / 2 + (4 if len(lines) == 1 else -2), lines, size, ink, 12, anchor='middle', weight='700'))
        else:
            ty = by + bh + 22 if i % 2 == 0 else by + bh + 36
            out.append(f'<line x1="{x + w / 2:.1f}" y1="{by + bh}" x2="{x + w / 2:.1f}" y2="{ty - 10}" stroke="var(--border-strong)" stroke-width="1"/>')
            out.append(f'<text x="{x + w / 2:.1f}" y="{ty}" text-anchor="middle" font-size="9.5" font-weight="700" fill="{ink}">{E(label)}</text>')
        x += w + 2
    out.append('<rect x="14" y="152" width="612" height="62" rx="8" fill="var(--surface)" stroke="var(--border-strong)"/>')
    out.append('<text x="28" y="173" font-size="11" font-weight="800" fill="var(--ink)">When the window fills: compaction</text>')
    out.append(_lines(28, 190, ['The model writes a summary of the conversation and continues from it. This session was compacted twice.',
                                'Details survived because they were in files and commit messages, not because the model remembered them.'], 9.8, 'var(--ink-2)', 13))
    out.append('<rect x="14" y="228" width="300" height="148" rx="8" fill="var(--good-wash)" stroke="var(--good)"/>')
    out.append('<text x="28" y="250" font-size="10.5" font-weight="700" letter-spacing="1.2" fill="var(--good)">IN THE WINDOW</text>')
    out.append(_lines(28, 270, ['the rules it was given, every turn', 'the excerpts it chose to read', 'the output of the commands it ran', 'the screenshots it asked for', 'the summary of what came before'], 10, 'var(--ink-2)', 18))
    out.append('<rect x="326" y="228" width="300" height="148" rx="8" fill="var(--accent-wash)" stroke="var(--accent)"/>')
    out.append('<text x="340" y="250" font-size="10.5" font-weight="700" letter-spacing="1.2" fill="var(--accent-ink)">NOT IN THE WINDOW</text>')
    out.append(_lines(340, 270, ['the rest of the repository', "last round's screenshots", 'the scratch directory after a reset', 'anything nobody wrote down', 'your intent, unless you said it'], 10, 'var(--ink-2)', 18))
    out.append('<text x="320" y="394" text-anchor="middle" font-size="10" fill="var(--ink-3)">so the method follows: write it down, keep it in the repo, make every check a script</text>')
    out.append('</svg>')
    return '\n'.join(out)


def g_fanout() -> str:
    """The research workflow behind this briefing: research, verify, synthesize."""
    out = ['<svg viewBox="0 0 640 400" role="img" aria-label="The research workflow behind this briefing: the brief fans out to four researchers in parallel (architecture, federal, open source, inventory); their high-stakes claims fan out to 33 verifiers, one claim each, of which 31 came back unclear because pages were unreachable and 2 refuted; a synthesizer and a completeness critic produce the outline. 39 agents, 301 tool calls, 36.7 minutes, 1.71 million tokens.">',
           '<defs><marker id="fl" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="var(--ink-3)"/></marker></defs>']
    for x, t in [(150, 'RESEARCH · 4 IN PARALLEL'), (352, 'VERIFY · 33, ONE CLAIM EACH'), (546, 'SYNTHESIZE · 1 + A CRITIC')]:
        out.append(f'<text x="{x}" y="24" text-anchor="middle" font-size="9.5" font-weight="700" letter-spacing="1.2" fill="var(--ink-3)">{t}</text>')
    out.append('<rect x="14" y="124" width="70" height="56" rx="8" fill="var(--surface-2)" stroke="var(--border-strong)"/>')
    out.append(_lines(49, 148, ['the brief', 'in a script'], 10, 'var(--ink)', 13, anchor='middle', weight='700'))
    names = ['architecture', 'federal fit', 'open source', 'kit inventory']
    for i, n in enumerate(names):
        y = 36 + i * 58
        out.append(f'<rect x="100" y="{y}" width="100" height="46" rx="8" fill="var(--steel-wash)" stroke="var(--steel)"/>')
        out.append(f'<text x="150" y="{y + 20}" text-anchor="middle" font-size="10.5" font-weight="800" fill="var(--ink)">{E(n)}</text>')
        out.append(f'<text x="150" y="{y + 35}" text-anchor="middle" font-size="9" fill="var(--ink-2)">reads docs, writes claims</text>')
        out.append(f'<path d="M84 152 C92 152, 92 {y + 23}, 98 {y + 23}" fill="none" stroke="var(--ink-3)" stroke-width="1.2" marker-end="url(#fl)"/>')
        out.append(f'<path d="M200 {y + 23} C218 {y + 23}, 218 152, 230 152" fill="none" stroke="var(--ink-3)" stroke-width="1.2"/>')
    gx, gy = 244, 118
    for k in range(33):
        c, r = k % 11, k // 11
        cx, cy = gx + c * 21, gy + r * 34
        refuted = k in (7, 23)
        fill = 'var(--accent)' if refuted else 'var(--border-strong)'
        out.append(f'<circle cx="{cx}" cy="{cy}" r="7" fill="{fill}" stroke="var(--surface)" stroke-width="2"><title>{"refuted by page text" if refuted else "unclear: page unreachable from the sandbox"}</title></circle>')
    out.append(_lines(352, 212, ['each verifier reads the primary page', 'and tries to refute its claim'], 9.5, 'var(--ink-2)', 12, anchor='middle'))
    out.append('<circle cx="244" cy="248" r="5" fill="var(--border-strong)"/><text x="254" y="252" font-size="9.5" fill="var(--ink-2)">31 unclear: page unreachable</text>')
    out.append('<circle cx="398" cy="248" r="5" fill="var(--accent)"/><text x="408" y="252" font-size="9.5" fill="var(--ink-2)">2 refuted · 0 confirmed</text>')
    out.append('<path d="M468 152 H486" stroke="var(--ink-3)" stroke-width="1.5" marker-end="url(#fl)"/>')
    out.append('<rect x="490" y="96" width="112" height="52" rx="8" fill="var(--violet-wash)" stroke="var(--violet)"/>')
    out.append(_lines(546, 118, ['synthesizer', 'drafts the outline'], 10, 'var(--ink)', 13, anchor='middle', weight='700'))
    out.append('<path d="M546 148 V166" stroke="var(--ink-3)" stroke-width="1.5" marker-end="url(#fl)"/>')
    out.append('<rect x="490" y="170" width="112" height="52" rx="8" fill="var(--violet-wash)" stroke="var(--violet)"/>')
    out.append(_lines(546, 192, ['critic', 'what is missing?'], 10, 'var(--ink)', 13, anchor='middle', weight='700'))
    out.append('<rect x="14" y="276" width="612" height="56" rx="8" fill="var(--accent-wash)" stroke="var(--accent)" stroke-width="1.3"/>')
    out.append('<text x="320" y="298" text-anchor="middle" font-size="11.5" font-weight="800" fill="var(--ink)">Rule that fell out of it: only sentences confirmed from page text went on the federal slides.</text>')
    out.append('<text x="320" y="318" text-anchor="middle" font-size="10" fill="var(--ink-2)">Everything else moved to an appendix marked verify before quoting. The refuted claims never appeared.</text>')
    stats = [('39', 'agents'), ('301', 'tool calls'), ('36.7', 'minutes'), ('1.71M', 'tokens'), ('8', 'subagents wrote the step cards, earlier')]
    x = 14
    for v, l in stats:
        w = 70 if len(l) < 12 else 262
        out.append(f'<rect x="{x}" y="346" width="{w}" height="44" rx="8" fill="var(--surface)" stroke="var(--border)"/>')
        out.append(f'<text x="{x + 10}" y="366" font-size="14" font-weight="800" fill="var(--ink)">{v}</text>')
        out.append(f'<text x="{x + 10}" y="382" font-size="9" fill="var(--ink-3)">{E(l)}</text>')
        x += w + 8
    out.append('</svg>')
    return '\n'.join(out)


# --------------------------------------------------------------------------- data-driven graphics for the adaptation slides
# These read `graphic_data` from the outline (or essay) JSON, so the chapter's verified
# recipes and the pictures share one source.

DATA: dict = {}

RUNG_COLOUR = {'data': 'var(--accent)', 'information': '#C2410C', 'knowledge': 'var(--good)', 'judgement': 'var(--violet)'}


def _rung_colour(rung: str) -> str:
    r = rung.lower()
    for name in ('judgement', 'knowledge', 'information', 'data'):
        if r.rstrip().endswith(name) or (name in r and '→' not in r):
            return RUNG_COLOUR[name]
    for name in ('judgement', 'knowledge', 'information', 'data'):
        if name in r:
            return RUNG_COLOUR[name]
    return 'var(--ink-3)'


def g_knobs() -> str:
    """The extension points: area, file, what you change."""
    rows = DATA.get('knobs') or [
        {'area': 'Slides', 'file': 'slides/deck.html', 'change': 'one <section class="slide"> each'},
        {'area': 'Spanish', 'file': 'slides/deck.html ES_TEXT', 'change': 'one entry per string'},
        {'area': 'Labs', 'file': 'labs/labNN/run.sh', 'change': 'step() + expected output'},
        {'area': 'Docs', 'file': 'docs/NN-lab-*.adoc', 'change': 'header table + sections'},
        {'area': 'Catalogue', 'file': 'bin/adventure-inventory.json', 'change': 'one item per thing'},
        {'area': 'Ladder', 'file': 'slides/ladder-map.json', 'change': 'rung per slide and lab'},
        {'area': 'Console', 'file': 'slides/presenter-notes.html', 'change': 'a section per slide'},
        {'area': 'PowerPoint', 'file': 'bin/build-pptx.py', 'change': 'slide list, block order'},
        {'area': 'Graphics', 'file': 'slides/assets/graphics/', 'change': 'drop in by filename'},
        {'area': 'Gates', 'file': '.github/workflows/docs.yml', 'change': 'labs run before docs build'},
    ]
    rows = rows[:10]
    out = ['<svg viewBox="0 0 640 400" role="img" aria-label="The kit\'s extension points: for each area, the file that owns it and what you change there.">']
    n = (len(rows) + 1) // 2
    h = min(66, int((376 - (n - 1) * 8) / n))
    for i, r in enumerate(rows):
        col, row = i % 2, i // 2
        x, y = 14 + col * 310, 14 + row * (h + 8)
        out.append(f'<rect x="{x}" y="{y}" width="298" height="{h}" rx="9" fill="var(--surface)" stroke="var(--border-strong)" stroke-width="1.2"/>')
        out.append(f'<rect x="{x}" y="{y + 10}" width="5" height="{h - 20}" rx="2.5" fill="var(--steel)"/>')
        out.append(f'<text x="{x + 16}" y="{y + 20}" font-size="12" font-weight="800" fill="var(--ink)">{E(r["area"])}</text>')
        out.append(f'<text x="{x + 16}" y="{y + 36}" font-size="9.5" font-family="Red Hat Mono, monospace" fill="var(--steel)">{E(r["file"])}</text>')
        out.append(f'<text x="{x + 16}" y="{y + 52}" font-size="9.5" fill="var(--ink-2)">{E(r["change"])}</text>')
    out.append('</svg>')
    return '\n'.join(out)


def g_newlab() -> str:
    """A new use case as a lab, as an ordered flow of up to ten steps."""
    steps = (DATA.get('newlab') or [
        'Name the problem owner and the queue', 'Place it on a rung of the ladder', 'Pick the product that serves that rung',
        'Write the expected output first', 'Write run.sh with one step() per command', 'Run it in simulate mode on a laptop',
        'Add the docs chapter and the catalogue entry', 'Add the ladder-map rung and the deck preview', 'Let CI run every lab before the docs build',
        'Run it live; a divergence is the finding'])[:10]
    out = ['<svg viewBox="0 0 640 400" role="img" aria-label="A new use case becomes a lab in ordered steps: from naming the problem owner and the rung, through writing the expected output and the run script, to the docs, catalogue, deck, CI and a live run.">',
           '<defs><marker id="nl" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="var(--ink-3)"/></marker></defs>']
    per_row = 5
    bw, bh, gap = 112, 112, 13
    for i, s in enumerate(steps):
        row, col = i // per_row, i % per_row
        if row % 2 == 1:
            col = per_row - 1 - col  # snake back so the arrows stay short
        x, y = 14 + col * (bw + gap), 24 + row * (bh + 56)
        colour = 'var(--steel)' if i < 4 else ('var(--good)' if i < 7 else 'var(--violet)')
        out.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="10" fill="var(--surface)" stroke="{colour}" stroke-width="1.4"/>')
        out.append(f'<circle cx="{x + 18}" cy="{y + 18}" r="11" fill="{colour}"/>')
        out.append(f'<text x="{x + 18}" y="{y + 22}" text-anchor="middle" font-size="10.5" font-weight="800" fill="#fff">{i + 1}</text>')
        out.append(_lines(x + 10, y + 46, _wrap(s, 19)[:4], 9.8, 'var(--ink)', 13.5, weight='600'))
        nxt = i + 1
        if nxt < len(steps):
            nrow = nxt // per_row
            if nrow == row:
                dx = 1 if row % 2 == 0 else -1
                x1 = x + bw if dx == 1 else x
                x2 = x1 + dx * (gap - 2)
                out.append(f'<line x1="{x1}" y1="{y + bh / 2}" x2="{x2}" y2="{y + bh / 2}" stroke="var(--ink-3)" stroke-width="1.6" marker-end="url(#nl)"/>')
            else:
                out.append(f'<line x1="{x + bw / 2}" y1="{y + bh}" x2="{x + bw / 2}" y2="{y + bh + 52}" stroke="var(--ink-3)" stroke-width="1.6" marker-end="url(#nl)"/>')
    labels = [('var(--steel)', 'decide'), ('var(--good)', 'build and check'), ('var(--violet)', 'ship and run live')]
    x = 14
    for colour, text in labels:
        out.append(f'<rect x="{x}" y="372" width="10" height="10" rx="3" fill="{colour}"/><text x="{x + 16}" y="381" font-size="9.5" fill="var(--ink-2)">{E(text)}</text>')
        x += 20 + len(text) * 5.6 + 18
    out.append('<text x="626" y="381" text-anchor="end" font-size="9.5" fill="var(--ink-3)">the expected output is the acceptance criterion</text>')
    out.append('</svg>')
    return '\n'.join(out)


def g_usecases() -> str:
    """Eight specific use cases against the labs that already cover them."""
    rows = (DATA.get('usecases') or [
        {'use_case': 'Correspondence triage', 'agency': 'IRS', 'rung': 'information', 'labs': 'Lab 04 + 02', 'change': 'new lab from the RAG pattern'},
        {'use_case': 'Refund fraud scoring', 'agency': 'State revenue', 'rung': 'information', 'labs': 'Lab 03 + 06', 'change': 'serve a scorer, prove it'},
        {'use_case': 'Claims backlog assist', 'agency': 'SSA / VA', 'rung': 'knowledge', 'labs': 'Lab 04', 'change': 'swap corpus and threshold'},
        {'use_case': 'Call-centre answer drafts', 'agency': 'CMS', 'rung': 'knowledge', 'labs': 'Lab 04 + 06', 'change': 'cite guidance, human send'},
        {'use_case': 'Batch-window incidents', 'agency': 'IRS mainframe', 'rung': 'data → info', 'labs': 'Lab 07 + 08', 'change': 'point at your logs'},
        {'use_case': 'Entry classification', 'agency': 'CBP', 'rung': 'information', 'labs': 'Lab 02 + 03', 'change': 'tune on your taxonomy'},
        {'use_case': 'Readiness reporting', 'agency': 'DoD logistics', 'rung': 'data → info', 'labs': 'Lab 05 + 07', 'change': 'rulebooks, your telemetry'},
        {'use_case': 'Audit evidence packs', 'agency': 'DoD finance', 'rung': 'knowledge', 'labs': 'Lab 04 + 06', 'change': 'TrustyAI reports per run'},
    ])[:8]
    cols = [('USE CASE', 14, 158), ('AGENCY', 172, 96), ('RUNG', 268, 104), ('LABS', 372, 92), ('WHAT CHANGES', 464, 162)]
    out = ['<svg viewBox="0 0 640 400" role="img" aria-label="Eight specific use cases across the IRS, other federal civilian agencies, state revenue and DoD business systems, each with its rung, the closest existing labs and what changes.">']
    for name, x, w in cols:
        out.append(f'<text x="{x + 8}" y="26" font-size="9.5" font-weight="700" letter-spacing="1.2" fill="var(--ink-3)">{name}</text>')
    y = 36
    rh = 41
    for r in rows:
        out.append(f'<rect x="14" y="{y}" width="612" height="{rh - 4}" rx="7" fill="var(--surface)" stroke="var(--border)"/>')
        out.append(f'<text x="22" y="{y + 23}" font-size="11" font-weight="800" fill="var(--ink)">{E(r["use_case"])}</text>')
        out.append(f'<text x="180" y="{y + 23}" font-size="10" fill="var(--ink-2)">{E(r["agency"])}</text>')
        rc = _rung_colour(r['rung'])
        out.append(f'<rect x="276" y="{y + 10}" width="88" height="18" rx="9" fill="{rc}" opacity=".14"/>')
        out.append(f'<circle cx="286" cy="{y + 19}" r="3.5" fill="{rc}"/>')
        out.append(f'<text x="294" y="{y + 23}" font-size="9.5" font-weight="700" fill="var(--ink)">{E(r["rung"])}</text>')
        out.append(f'<text x="380" y="{y + 23}" font-size="10" font-family="Red Hat Mono, monospace" fill="var(--steel)">{E(r["labs"])}</text>')
        out.append(f'<text x="472" y="{y + 23}" font-size="9.8" fill="var(--ink-2)">{E(r["change"])}</text>')
        y += rh
    out.append(f'<text x="320" y="392" text-anchor="middle" font-size="9.5" fill="var(--ink-3)">the full catalogue is in the docs chapter · in every row the determination stays with a person</text>')
    out.append('</svg>')
    return '\n'.join(out)

def g_afternoon() -> str:
    """The one-page lab brief filled in the room, the time boxes and the gates."""
    fields = [('a', 'Problem owner: role and team, never a name'), ('b', 'Trigger: queue, pager or accreditation question'),
              ('c', 'Data: system, boundary it must not leave, who may read it'), ('d', 'Rung this lab proves; who climbs the next one'),
              ('e', 'Product that serves the rung; the chip string'), ('f', 'Success output: the exact lines the last command prints'),
              ('g', 'Who signs: the lab ends on their screen'), ('h', 'Nearest existing lab to copy from'),
              ('i', 'Live inputs: ${VAR:-default} knobs, CLI tools'), ('j', 'Sample data allowed in the repo; what stays out')]
    boxes = [('0:00', 'conversation'), ('0:30', 'ladder and product'), ('0:45', 'expected output'), ('1:30', 'run.sh'),
             ('2:15', 'gates'), ('2:20', 'docs chapter'), ('2:50', 'register, make adventure'), ('3:15', 'review and commit')]
    out = ['<svg viewBox="0 0 640 400" role="img" aria-label="The lab brief: ten fields filled in the room (problem owner, trigger, data location, rung, product, success output, who signs, nearest lab, live inputs, sample data), eight time boxes from the conversation at 0:00 to review and commit at 3:15, and the gates that run before anyone sees a slide.">']
    out.append('<rect x="14" y="14" width="400" height="348" rx="10" fill="var(--surface)" stroke="var(--border-strong)" stroke-width="1.3"/>')
    out.append('<text x="30" y="38" font-size="10.5" font-weight="700" letter-spacing="1.4" fill="var(--accent-ink)">LAB BRIEF · ONE PAGE, FILLED IN THE ROOM</text>')
    for i, (k, label) in enumerate(fields):
        y = 54 + i * 30
        hot = k in ('f', 'g')
        out.append(f'<rect x="30" y="{y}" width="20" height="20" rx="5" fill="{"var(--accent)" if hot else "var(--surface-2)"}" stroke="{"var(--accent)" if hot else "var(--border-strong)"}"/>')
        out.append(f'<text x="40" y="{y + 14}" text-anchor="middle" font-size="10" font-weight="800" fill="{"#fff" if hot else "var(--ink-2)"}">{k}</text>')
        out.append(f'<text x="58" y="{y + 14}" font-size="10.5" font-weight="{"700" if hot else "500"}" fill="var(--ink)">{E(label)}</text>')
        out.append(f'<line x1="58" y1="{y + 24}" x2="398" y2="{y + 24}" stroke="var(--border)" stroke-width="1" stroke-dasharray="2 3"/>')
    out.append('<rect x="430" y="14" width="196" height="214" rx="10" fill="var(--steel-wash)" stroke="var(--steel)" stroke-width="1.3"/>')
    out.append('<text x="446" y="38" font-size="10.5" font-weight="700" letter-spacing="1.4" fill="var(--steel)">TIME BOXES · FOUR HOURS</text>')
    for i, (tm, what) in enumerate(boxes):
        y = 60 + i * 21
        out.append(f'<text x="446" y="{y}" font-size="10.5" font-weight="800" font-family="Red Hat Mono, monospace" fill="var(--ink)">{tm}</text>')
        out.append(f'<text x="486" y="{y}" font-size="10.5" fill="var(--ink-2)">{E(what)}</text>')
    out.append('<rect x="430" y="242" width="196" height="120" rx="10" fill="var(--good-wash)" stroke="var(--good)" stroke-width="1.3"/>')
    out.append('<text x="446" y="266" font-size="10.5" font-weight="700" letter-spacing="1.4" fill="var(--good)">GATES BEFORE ANY SLIDE</text>')
    out.append(_lines(446, 284, ['bash -n · step count matches', 'make lint · run-all-labs · make test', 'model-name grep · asset presence', 'inventory fields · ladder-map chip', 'equals the docs Rung row', 'make adventure comes back clean'], 9.8, 'var(--ink-2)', 13))
    out.append('<text x="320" y="388" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--ink)">Stop the conversation only when (f) and (g) are written down. Nothing reaches a slide until a lab prints it.</text>')
    out.append('</svg>')
    return '\n'.join(out)


GRAPHICS = {
    'agent-loop': g_agent_loop, 'architecture': g_architecture, 'boundary': g_boundary,
    'pipeline': g_pipeline, 'toolchain': g_toolchain, 'gaps': g_gaps, 'pyramid': g_pyramid,
    'hurt': g_hurt, 'faces': g_faces, 'matrix': g_matrix,
    'brief': g_brief, 'timeline': g_timeline, 'growth': g_growth, 'where': g_where,
    'trace': g_trace, 'context': g_context, 'fanout': g_fanout,
    'knobs': g_knobs, 'newlab': g_newlab, 'usecases': g_usecases, 'afternoon': g_afternoon,
}

# --------------------------------------------------------------------------- page

def inline(text: str) -> str:
    """Escape, then turn **bold** spans into <b>."""
    parts = re.split(r'\*\*(.+?)\*\*', text)
    return ''.join(E(part) if i % 2 == 0 else f'<b>{E(part)}</b>' for i, part in enumerate(parts))


def render_bullets(bullets: list[str]) -> str:
    return '\n'.join(f'<li>{inline(b)}</li>' for b in bullets)


def render_slide(s: dict, i: int, total: int, outline: dict) -> str:
    n = i + 1
    notes = E(s.get('notes', ''))
    srcs = ''.join(f'<span class="src">{E(u)}</span>' for u in s.get('sources', []))
    kind = s.get('kind', 'standard')
    if kind == 'title':
        timed = [x for x in outline['slides'] if x.get('kind') != 'title' and x.get('minutes', 0) > 0]
        agenda = ''.join(
            f'<div><i>{j + 1:02d}</i><span>{E(x["title"])}</span><span class="m">{x["minutes"]:g} min</span></div>'
            for j, x in enumerate(timed))
        body = f'''
          <span class="eyebrow">{E(s.get('eyebrow', ''))}</span>
          <h2>{E(s['title'])}</h2>
          <p class="kicker">{E(s.get('lede', ''))}</p>
          <div class="hosts">{''.join(f'<span class="host">{E(h)}</span>' for h in s.get('hosts', []))}</div>
          <div class="agenda{' four' if len(timed) > 18 else ''}">{agenda}</div>'''
        return f'''<article class="slide title-slide" data-title="{E(s['title'])}" data-notes="{notes}" data-sources="{E(" ".join(s.get('sources', [])))}">
          <div class="rule"></div>{body}
          <span class="slidenum">{n:02d} / {total}</span>
        </article>'''
    gfx_key = s.get('graphic_key')
    gfx = GRAPHICS[gfx_key]() if gfx_key in GRAPHICS else ''
    if kind == 'checklist':
        content = '<div class="checklist">' + ''.join(f'<div>{E(b)}</div>' for b in s['bullets']) + '</div>'
        body_cls = 'body nogfx'
        cols = content
    else:
        body_cls = 'body' + ('' if gfx else ' nogfx') + (' wide' if s.get('wide') else '')
        cols = f'<ul class="pts">{render_bullets(s["bullets"])}</ul>' + (f'<div class="gfx">{gfx}</div>' if gfx else '')
    verify = ''
    if s.get('verify'):
        verify = '<div class="verify"><b>Verify before quoting</b> · ' + E(s['verify']) + '</div>'
    return f'''<article class="slide" data-title="{E(s['title'])}" data-notes="{notes}" data-sources="{E(" ".join(s.get('sources', [])))}">
          <div class="rule"></div>
          <div class="head">
            <div class="meta"><span class="eyebrow">{E(s.get('eyebrow', ''))}</span><span class="min">{s['minutes']:g} min</span></div>
            <h2>{E(s['title'])}</h2>
            {f'<p class="lede">{E(s["lede"])}</p>' if s.get('lede') else ''}
          </div>
          <div class="{body_cls}">{cols}</div>
          {verify}
          <span class="slidenum">{n:02d} / {total}</span>
        </article>'''


def build(outline: dict) -> str:
    global DATA
    DATA = outline.get('graphic_data', {}) or {}
    slides = outline['slides']
    total = len(slides)
    arts = '\n'.join(render_slide(s, i, total, outline) for i, s in enumerate(slides))
    title = outline['title']
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@400;500;700;800;900&family=Red+Hat+Mono:wght@400;500;600;700&family=Red+Hat+Text:wght@400;500;700&display=swap">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="stage" id="stage" tabindex="0">
{arts}
  </div>
  <div class="notes" id="notes" hidden><b>Presenter notes</b><span id="notes-text"></span><span id="notes-src"></span></div>
  <div class="bar">
    <span class="hint"><kbd>←</kbd> <kbd>→</kbd> move · <kbd>N</kbd> notes · <kbd>F</kbd> full screen · <kbd>D</kbd> dark · {outline['total_minutes']} minutes</span>
    <span class="grp"><button class="ghost" id="prev">← Prev</button><span id="pos"></span><button class="ghost" id="next">Next →</button></span>
  </div>
</div>
<script>
(function(){{
  var slides = Array.prototype.slice.call(document.querySelectorAll('.slide'));
  var cur = 0, notes = document.getElementById('notes'), nt = document.getElementById('notes-text'), ns = document.getElementById('notes-src'), pos = document.getElementById('pos');
  function go(i){{
    cur = Math.max(0, Math.min(slides.length - 1, i));
    slides.forEach(function(s, k){{ s.setAttribute('data-active', k === cur ? 'true' : 'false'); }});
    nt.textContent = slides[cur].dataset.notes || '';
    ns.textContent = slides[cur].dataset.sources ? 'Sources: ' + slides[cur].dataset.sources : '';
    pos.textContent = String(cur + 1).padStart(2, '0') + ' / ' + slides.length;
    try {{ history.replaceState(null, '', '#slide-' + (cur + 1)); }} catch (e) {{}}
    if (window.innerWidth <= 900 || window.innerHeight <= 560) window.scrollTo(0, 0);
  }}
  document.getElementById('prev').addEventListener('click', function(){{ go(cur - 1); }});
  document.getElementById('next').addEventListener('click', function(){{ go(cur + 1); }});
  document.addEventListener('keydown', function(e){{
    if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') {{ e.preventDefault(); go(cur + 1); }}
    else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {{ e.preventDefault(); go(cur - 1); }}
    else if (e.key === 'Home') go(0); else if (e.key === 'End') go(slides.length - 1);
    else if (e.key === 'n' || e.key === 'N') notes.hidden = !notes.hidden;
    else if (e.key === 'd' || e.key === 'D') document.documentElement.setAttribute('data-theme', document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
    else if (e.key === 'f' || e.key === 'F') {{ var st = document.getElementById('stage'); if (document.fullscreenElement) document.exitFullscreen(); else if (st.requestFullscreen) st.requestFullscreen(); }}
  }});
  var m = /^#slide-(\\d+)$/.exec(location.hash || '');
  go(m ? parseInt(m[1], 10) - 1 : 0);
  window.__go = go;
  // Swipe left or right to move; a drag that starts on a graphic pans it instead.
  var st = document.getElementById('stage'), sx = null, sy = null, onGfx = false;
  st.addEventListener('touchstart', function(e){{ var t = e.touches[0]; sx = t.clientX; sy = t.clientY; onGfx = !!(e.target.closest && e.target.closest('.gfx')); }}, {{passive: true}});
  st.addEventListener('touchend', function(e){{
    if (sx === null || onGfx) {{ sx = null; return; }}
    var t = e.changedTouches[0], dx = t.clientX - sx, dy = t.clientY - sy; sx = null;
    if (Math.abs(dx) > 60 && Math.abs(dx) > 2 * Math.abs(dy)) {{ go(cur + (dx < 0 ? 1 : -1)); window.scrollTo(0, 0); }}
  }}, {{passive: true}});
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) document.documentElement.setAttribute('data-theme', 'dark');
}})();
</script>
</body>
</html>
'''


# --------------------------------------------------------------------------- essay, AsciiDoc and standalone graphics

ESSAY_CSS = r"""
.essay{width:100%;max-width:860px;min-width:0;margin:0 auto;padding:36px 24px 64px}
.essay header{padding-bottom:22px;border-bottom:1px solid var(--border);margin-bottom:28px}
.essay h1{font-size:clamp(1.9rem,4vw,3rem);font-weight:900;letter-spacing:-.03em;max-width:24ch;margin-top:10px}
.essay .standfirst{font-size:clamp(1.05rem,1.5vw,1.25rem);color:var(--ink-2);max-width:64ch;margin-top:14px;line-height:1.5}
.essay .meta{display:flex;flex-wrap:wrap;gap:8px 18px;margin-top:16px;font-family:"Red Hat Mono",monospace;font-size:.7rem;color:var(--ink-3);letter-spacing:.04em}
.essay nav.toc{border:1px solid var(--border);border-radius:10px;background:var(--surface);padding:14px 18px;margin:0 0 30px;box-shadow:var(--shadow)}
.essay nav.toc b{display:block;font-family:"Red Hat Mono",monospace;font-size:.66rem;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3);margin-bottom:8px}
.essay nav.toc ol{margin:0;padding-left:1.4em;columns:2;column-gap:28px;font-size:.9rem;color:var(--ink-2)}
.essay nav.toc li{padding:2px 0;break-inside:avoid}
.essay nav.toc a{color:var(--ink-2);text-decoration:none}.essay nav.toc a:hover{color:var(--accent-ink)}
.essay section{margin:0 0 40px;scroll-margin-top:16px}
.essay h2{font-size:clamp(1.3rem,2.2vw,1.8rem);font-weight:800;max-width:30ch;margin-bottom:14px}
.essay h2 small{display:block;font-family:"Red Hat Mono",monospace;font-size:.66rem;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--accent-ink);margin-bottom:8px}
.essay p{max-width:70ch;font-size:1.02rem;line-height:1.62;margin:0 0 14px;color:var(--ink)}
.essay figure{margin:22px 0 24px;border:1px solid var(--border);border-radius:10px;background:var(--surface);padding:14px 16px 10px;box-shadow:var(--shadow)}
.essay figure svg{width:100%;height:auto;display:block}
.essay figure svg text{font-family:"Red Hat Text",system-ui,sans-serif}
.essay figcaption{margin-top:10px;font-size:.84rem;color:var(--ink-2);line-height:1.45}
.essay figcaption b{font-family:"Red Hat Mono",monospace;font-size:.64rem;letter-spacing:.12em;text-transform:uppercase;color:var(--ink-3);margin-right:8px}
.essay blockquote.pull{margin:22px 0;padding:6px 0 6px 20px;border-left:4px solid var(--accent);font-family:"Red Hat Display","Red Hat Text",sans-serif;font-size:clamp(1.15rem,1.8vw,1.45rem);font-weight:700;line-height:1.3;letter-spacing:-.01em;color:var(--ink);max-width:40ch}
.essay table{border-collapse:collapse;width:100%;min-width:760px;font-size:.8rem;margin:10px 0 6px}
.essay th,.essay td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--border);vertical-align:top}
.essay th{font-family:"Red Hat Mono",monospace;font-size:.62rem;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3);font-weight:600}
.essay td.n,.essay th.n{text-align:right;font-variant-numeric:tabular-nums;font-family:"Red Hat Mono",monospace;font-size:.74rem;white-space:nowrap}
.essay td.s{color:var(--ink-2)}
.essay .tablewrap{overflow-x:auto;border:1px solid var(--border);border-radius:10px;background:var(--surface);padding:4px 10px}
.essay .appendix{border-top:1px solid var(--border);padding-top:24px}
.essay .appendix h2{font-size:1.25rem}
.essay footer{border-top:1px solid var(--border);margin-top:40px;padding-top:18px;font-size:.84rem;color:var(--ink-2);display:flex;flex-wrap:wrap;gap:10px 22px;align-items:center}
.essay footer a{color:var(--accent-ink);text-decoration:none;font-weight:600}
.essay .topbar{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:12px}
.essay .topbar a{font-family:"Red Hat Mono",monospace;font-size:.7rem;color:var(--ink-3);text-decoration:none}
.essay .topbar a:hover{color:var(--accent-ink)}
.essay .verifybox{border:1px dashed var(--border-strong);border-radius:10px;padding:12px 16px;font-size:.86rem;color:var(--ink-2);background:var(--surface-2);max-width:70ch}
.essay .verifybox b{color:var(--amber);font-family:"Red Hat Mono",monospace;font-size:.62rem;letter-spacing:.1em;text-transform:uppercase;display:block;margin-bottom:4px}
@media print{.essay{max-width:none;padding:0}.essay figure,.essay section{break-inside:avoid}.essay .topbar,.essay nav.toc{display:none}body{background:#fff}}
@media (max-width:640px){.essay nav.toc ol{columns:1}.essay p{font-size:.98rem}}
"""


def _reading_minutes(words: int) -> int:
    return max(1, round(words / 230))


def _word_count(essay: dict) -> int:
    n = len(essay.get('standfirst', '').split())
    for s in essay['sections']:
        n += sum(len(p.split()) for p in s['paragraphs'])
    return n


def history_table_html(rows: list[dict]) -> str:
    head = '<tr><th>Date</th><th>UTC</th><th>What landed</th><th class="n">Deck KB</th><th class="n">Slides</th><th class="n">Labs</th><th class="n">ES</th><th class="n">SVG</th><th class="n">Console</th><th class="n">Files</th></tr>'
    body = ''.join(
        f'<tr><td class="n">{E(c["date"][5:])}</td><td class="n">{E(c["time"])}</td><td class="s">{E(c["subject"])}</td>'
        f'<td class="n">{c["deck_kb"]}</td><td class="n">{c["slides"]}</td><td class="n">{c["labs"]}</td><td class="n">{c["es_keys"]}</td>'
        f'<td class="n">{c["svgs"]}</td><td class="n">{c["console_sections"]}</td><td class="n">{c["files"]}</td></tr>' for c in rows)
    return f'<div class="tablewrap"><table><thead>{head}</thead><tbody>{body}</tbody></table></div>'


def build_essay(essay: dict, links: dict) -> str:
    words = essay.get('word_count') or _word_count(essay)
    toc = ''.join(f'<li><a href="#{E(s["id"])}">{E(s["heading"])}</a></li>' for s in essay['sections'])
    parts = []
    for i, s in enumerate(essay['sections']):
        paras = ''.join(f'<p>{inline(p)}</p>' for p in s['paragraphs'])
        fig = ''
        key = s.get('graphic') or ''
        if key in GRAPHICS:
            fig = f'<figure>{GRAPHICS[key]()}<figcaption><b>Figure {i + 1}</b>{E(s.get("graphic_caption", ""))}</figcaption></figure>'
        pull = f'<blockquote class="pull">{E(s["pullquote"])}</blockquote>' if s.get('pullquote') else ''
        # put the figure after the first two paragraphs where there are enough, else at the end
        ps = [f'<p>{inline(p)}</p>' for p in s['paragraphs']]
        if len(ps) >= 4:
            body = ''.join(ps[:2]) + fig + ''.join(ps[2:4]) + pull + ''.join(ps[4:])
        else:
            body = ''.join(ps) + fig + pull
        parts.append(f'<section id="{E(s["id"])}"><h2><small>{i + 1:02d}</small>{E(s["heading"])}</h2>{body}</section>')
    states = [c for c in history() if c.get('first_parent', True)]
    appendix = f'''<section class="appendix" id="appendix-history">
      <h2><small>Appendix A</small>The numbers, from the git log</h2>
      <p>The growth figures above are drawn from this table: the state of the main branch after each of its {len(states)} commits, read from the git tree by <code>bin/mine-history.py</code>. Times are UTC. ES is the count of Spanish strings, SVG the count of inline vector graphics in the deck, Console the sections in the presenter console.</p>
      {history_table_html(states)}
    </section>
    <section class="appendix" id="appendix-sources">
      <h2><small>Appendix B</small>What this essay rests on</h2>
      <p>Dates, counts and sizes come from the repository and can be re-derived. The account of what the agent did, where it ran and what hurt is the builder's recollection of the session, written down the same week. Where the essay repeats a federal or product claim it uses only the wording of the 15-minute briefing and its handout, which were limited to what was read on the model vendor's own pages (Anthropic's) on 19 November 2026.</p>
      <div class="verifybox"><b>Verify before quoting</b>The briefing's appendix lists the claims that could not be read from a primary page that week. Re-check them from a workstation with normal egress before repeating them to a customer.</div>
    </section>'''
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(essay['title'])}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@400;500;700;800;900&family=Red+Hat+Mono:wght@400;500;600;700&family=Red+Hat+Text:wght@400;500;700&display=swap">
<style>{CSS}{ESSAY_CSS}</style>
</head>
<body>
<main class="essay">
  <div class="topbar"><a href="{E(links.get('talk', 'how-it-was-built-talk.html'))}">← the talk</a><a href="#" id="theme">dark / light</a></div>
  <header>
    <span class="eyebrow">Red Hat · how it was built · the long form</span>
    <h1>{E(essay['title'])}</h1>
    <p class="standfirst">{inline(essay['standfirst'])}</p>
    <div class="meta"><span>{words:,} words</span><span>about {_reading_minutes(words)} minute{'' if _reading_minutes(words) == 1 else 's'}</span><span>November 2026</span><span>companion to a {links.get('talk_minutes', 28)}-minute talk</span></div>
  </header>
  <nav class="toc"><b>Contents</b><ol>{toc}</ol></nav>
  {''.join(parts)}
  {appendix}
  <footer>
    <a href="{E(links.get('talk', 'how-it-was-built-talk.html'))}">The talk</a>
    <a href="{E(links.get('brief', 'how-it-was-built.html'))}">The 15-minute briefing</a>
    <a href="{E(links.get('handout', 'docs/#_how_the_kit_was_built'))}">The handout</a>
    <a href="{E(links.get('repo', 'https://github.com/nommsweyMX/redhat-ai-tax-labs'))}">The repository</a>
    <span>MIT. Generated by bin/build-brief.py from the essay's JSON.</span>
  </footer>
</main>
<script>
(function(){{
  var r=document.documentElement;
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) r.setAttribute('data-theme','dark');
  document.getElementById('theme').addEventListener('click',function(e){{e.preventDefault();r.setAttribute('data-theme',r.getAttribute('data-theme')==='dark'?'light':'dark');}});
}})();
</script>
</body>
</html>
'''


def _adoc_inline(text: str) -> str:
    """**bold** → *bold*; escape nothing else (the essay is plain prose)."""
    return re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)


def build_essay_adoc(essay: dict, image_prefix: str) -> str:
    # Level-1 title and level-2 sections: docs/index.adoc includes the chapters inside a +1 level offset.
    out = [f'// Generated by bin/build-brief.py from slides/how-it-was-built-essay.json. Edit the JSON, not this file.',
           f'[#how-it-was-built-essay]', f'= {essay["title"]}', '', '[.lead]', _adoc_inline(essay['standfirst']), '']
    for i, s in enumerate(essay['sections']):
        out.append(f'[#{s["id"]}]')
        out.append(f'== {s["heading"]}')
        out.append('')
        ps = s['paragraphs']
        key = s.get('graphic') or ''
        fig = []
        if key in GRAPHICS:
            fig = [f'.{s.get("graphic_caption", "").rstrip(".")}', f'image::{image_prefix}{key}.png[{key.replace("-", " ")}, pdfwidth=100%]', '']
        pull = ['[quote]', '____', s['pullquote'], '____', ''] if s.get('pullquote') else []
        if len(ps) >= 4:
            out += [_adoc_inline(p) + '\n' for p in ps[:2]] + fig + [_adoc_inline(p) + '\n' for p in ps[2:4]] + pull + [_adoc_inline(p) + '\n' for p in ps[4:]]
        else:
            out += [_adoc_inline(p) + '\n' for p in ps] + fig + pull
    states = [c for c in history() if c.get('first_parent', True)]
    out += ['[#how-it-was-built-numbers]', '== The numbers, from the git log', '',
            f'The state of the main branch after each of its {len(states)} commits, read from the git tree by `bin/mine-history.py`. Times are UTC. ES is the count of Spanish strings, SVG the count of inline vector graphics in the deck, Console the sections in the presenter console.', '',
            '.Main, commit by commit', '[cols="1,1,5,1,1,1,1,1,1", options="header"]', '|===', '| Date | UTC | What landed | Deck KB | Slides | Labs | ES | SVG | Console', '']
    for c in states:
        out.append(f'| {c["date"][5:]} | {c["time"]} | {c["subject"].replace("|", "¦")} | {c["deck_kb"]} | {c["slides"]} | {c["labs"]} | {c["es_keys"]} | {c["svgs"]} | {c["console_sections"]}')
    out += ['|===', '', '== What this essay rests on', '',
            'Dates, counts and sizes come from the repository and can be re-derived. The account of what the agent did, where it ran and what hurt is the builder\'s recollection of the session, written down the same week. Where the essay repeats a federal or product claim it uses only the wording of the methods briefing in the previous chapter, which was limited to what was read on the model vendor\'s own pages (Anthropic\'s) on 19 November 2026; re-check anything in that chapter\'s verify-before-quoting list before repeating it to a customer.', '']
    return '\n'.join(out)


def standalone_svg(key: str) -> str:
    """The graphic as a file of its own: namespace, the light-theme tokens, a surface background."""
    tokens = re.search(r':root\{([^}]*)\}', CSS).group(1)
    svg = GRAPHICS[key]()
    style = f'<style>:root{{{tokens}}}text{{font-family:"Red Hat Text",system-ui,sans-serif}}</style><rect width="640" height="400" fill="var(--surface)"/>'
    return svg.replace('<svg viewBox', '<svg xmlns="http://www.w3.org/2000/svg" viewBox', 1).replace('>', '>' + style, 1)


def write_svgs(folder: Path) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    written = []
    for key in GRAPHICS:
        p = folder / f'{key}.svg'
        p.write_text(standalone_svg(key) + '\n', encoding='utf-8')
        written.append(p)
    return written

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--outline', type=Path, help='slide outline JSON → a deck (default mode)')
    ap.add_argument('--essay', type=Path, help='essay JSON → a long-form page')
    ap.add_argument('--adoc', type=Path, help='with --essay: also write this AsciiDoc chapter')
    ap.add_argument('--image-prefix', default='built/', help='with --adoc: path prefix for the figure PNGs, relative to imagesdir')
    ap.add_argument('--svg-dir', type=Path, help='write every graphic as a standalone SVG into this folder')
    ap.add_argument('--history', type=Path, help='per-commit metrics JSON from bin/mine-history.py')
    ap.add_argument('--out', type=Path, help='output HTML')
    a = ap.parse_args()
    global HISTORY_PATH
    if a.history:
        HISTORY_PATH = a.history
    did = False
    global DATA
    if a.svg_dir:
        if a.outline and a.outline.exists():
            DATA = json.loads(a.outline.read_text(encoding='utf-8')).get('graphic_data', {}) or {}
        for p in write_svgs(a.svg_dir):
            print(f'Wrote {p}')
        did = True
    if a.essay:
        essay = json.loads(a.essay.read_text(encoding='utf-8'))
        out = a.out or Path('slides/how-it-was-built-essay.html')
        DATA = essay.get('graphic_data', {}) or {}
        out.write_text(build_essay(essay, essay.get('links', {})), encoding='utf-8')
        print(f'Wrote {out} ({out.stat().st_size:,} bytes, {len(essay["slides"]) if "slides" in essay else len(essay["sections"])} sections, {essay.get("word_count") or _word_count(essay):,} words)')
        if a.adoc:
            a.adoc.write_text(build_essay_adoc(essay, a.image_prefix), encoding='utf-8')
            print(f'Wrote {a.adoc}')
        did = True
    if a.outline or not did:
        outline_path = a.outline or Path('slides/how-it-was-built.json')
        out = a.out or Path('slides/how-it-was-built.html')
        outline = json.loads(outline_path.read_text(encoding='utf-8'))
        out.write_text(build(outline), encoding='utf-8')
        print(f'Wrote {out} ({out.stat().st_size:,} bytes, {len(outline["slides"])} slides)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
