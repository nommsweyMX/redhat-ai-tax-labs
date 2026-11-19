#!/usr/bin/env python3
"""Build the solution-architect briefing deck (how the kit was built, what agentic tooling
adds, where it fails for federal customers) from its JSON outline.

    python3 bin/build-brief.py --outline slides/how-it-was-built.json --out slides/how-it-was-built.html

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
@media (max-width:900px){.body,.body.wide{grid-template-columns:1fr}.gfx{display:none}.agenda,.checklist{grid-template-columns:1fr}}
"""

# --------------------------------------------------------------------------- graphics
# Each returns an inline SVG. Colours come from the page tokens so dark mode follows.

def g_agent_loop() -> str:
    """One agentic turn: prompt → model → tool call → permission → tool result → model, repeated."""
    return """<svg viewBox="0 0 640 400" role="img" aria-label="One agentic turn: a prompt and context go to the model; the model either answers or calls a tool; a permission gate sits in front of every tool call; the tool result returns to the model; the loop repeats until the model answers. Hooks observe before and after each tool call.">
<defs><marker id="al" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="var(--ink-3)"/></marker></defs>
<rect x="20" y="30" width="190" height="78" rx="10" fill="var(--surface-2)" stroke="var(--border-strong)"/>
<text x="115" y="60" text-anchor="middle" font-size="14" font-weight="800" fill="var(--ink)">Prompt + context</text>
<text x="115" y="82" text-anchor="middle" font-size="11" fill="var(--ink-2)">CLAUDE.md · files · skills · history</text>
<rect x="250" y="20" width="200" height="98" rx="12" fill="var(--accent-wash)" stroke="var(--accent)" stroke-width="1.6"/>
<text x="350" y="56" text-anchor="middle" font-size="16" font-weight="900" fill="var(--ink)">Model</text>
<text x="350" y="78" text-anchor="middle" font-size="11" fill="var(--ink-2)">answer, or ask for a tool</text>
<text x="350" y="96" text-anchor="middle" font-size="10.5" fill="var(--ink-3)">Anthropic API · Bedrock · Vertex · Foundry</text>
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
    """The Claude Code suite in one picture."""
    return """<svg viewBox="0 0 640 420" role="img" aria-label="The Claude Code suite: surfaces on top (CLI, IDE, web and cloud sessions, GitHub Actions, Agent SDK); the harness in the middle (tools, subagents, workflows, permissions, compaction, hooks); the extension layer (CLAUDE.md, skills, MCP servers, plugins, artifacts, routines); and model providers at the base.">
<rect x="14" y="14" width="612" height="66" rx="10" fill="var(--surface-2)" stroke="var(--border-strong)"/>
<text x="28" y="36" font-size="10.5" font-weight="700" letter-spacing="1.4" fill="var(--ink-3)">SURFACES</text>
<g font-size="12" font-weight="700" fill="var(--ink)" text-anchor="middle">
<rect x="28" y="44" width="104" height="26" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="80" y="62">Terminal CLI</text>
<rect x="142" y="44" width="104" height="26" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="194" y="62">IDE extension</text>
<rect x="256" y="44" width="134" height="26" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="323" y="62">Web + cloud sessions</text>
<rect x="400" y="44" width="110" height="26" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="455" y="62">GitHub Actions</text>
<rect x="520" y="44" width="92" height="26" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="566" y="62">Agent SDK</text>
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
<rect x="28" y="262" width="92" height="46" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="74" y="281">CLAUDE.md</text><text x="74" y="297" font-size="9.5" font-weight="400" fill="var(--ink-3)">project memory</text>
<rect x="128" y="262" width="92" height="46" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="174" y="281">Skills</text><text x="174" y="297" font-size="9.5" font-weight="400" fill="var(--ink-3)">SKILL.md · /slash</text>
<rect x="228" y="262" width="92" height="46" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="274" y="281">MCP servers</text><text x="274" y="297" font-size="9.5" font-weight="400" fill="var(--ink-3)">GitHub, Drive, yours</text>
<rect x="328" y="262" width="92" height="46" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="374" y="281">Plugins</text><text x="374" y="297" font-size="9.5" font-weight="400" fill="var(--ink-3)">bundles of the above</text>
<rect x="428" y="262" width="92" height="46" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="474" y="281">Artifacts</text><text x="474" y="297" font-size="9.5" font-weight="400" fill="var(--ink-3)">hosted pages</text>
<rect x="528" y="262" width="84" height="46" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="570" y="281">Routines</text><text x="570" y="297" font-size="9.5" font-weight="400" fill="var(--ink-3)">schedules</text>
</g>
<rect x="14" y="338" width="612" height="68" rx="10" fill="var(--surface-2)" stroke="var(--border-strong)"/>
<text x="28" y="360" font-size="10.5" font-weight="700" letter-spacing="1.4" fill="var(--ink-3)">MODEL PROVIDERS — WHERE THE TOKENS GO</text>
<g font-size="11.5" font-weight="700" fill="var(--ink)" text-anchor="middle">
<rect x="28" y="370" width="140" height="26" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="98" y="388" font-size="11">Anthropic API</text>
<rect x="176" y="370" width="140" height="26" rx="6" fill="var(--surface)" stroke="var(--good)" stroke-width="1.6"/><text x="246" y="388" font-size="11">Bedrock · GovCloud</text>
<rect x="324" y="370" width="140" height="26" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="394" y="388" font-size="11">Google Vertex AI</text>
<rect x="472" y="370" width="140" height="26" rx="6" fill="var(--surface)" stroke="var(--border)"/><text x="542" y="388" font-size="11">Microsoft Foundry</text>
</g>
</svg>"""


def g_boundary() -> str:
    """Three ways to run an agent, by where the data and the model sit."""
    return """<svg viewBox="0 0 640 400" role="img" aria-label="Three deployment shapes. Left: Anthropic commercial SaaS — claude.ai web sessions, Artifacts and connectors — data and model both outside the agency boundary. Middle: the Claude Code CLI on an agency workstation calling Claude through Amazon Bedrock in AWS GovCloud — the model inside an authorized boundary, the harness on your machine. Right: an open-source harness and an open model on OpenShift AI inside the agency's own enclave, including air-gapped.">
<defs><marker id="bl" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="var(--ink-3)"/></marker></defs>
<g>
<rect x="14" y="14" width="196" height="330" rx="12" fill="var(--surface)" stroke="var(--border-strong)" stroke-width="1.4"/>
<rect x="14" y="14" width="196" height="40" rx="12" fill="var(--amber-wash)"/><rect x="14" y="40" width="196" height="14" fill="var(--amber-wash)"/>
<text x="112" y="40" text-anchor="middle" font-size="12.5" font-weight="800" fill="var(--ink)">Commercial SaaS</text>
<text x="112" y="78" text-anchor="middle" font-size="10.5" fill="var(--ink-2)">claude.ai web + cloud sessions</text>
<text x="112" y="94" text-anchor="middle" font-size="10.5" fill="var(--ink-2)">Artifacts · connectors · Routines</text>
<rect x="34" y="112" width="156" height="60" rx="8" fill="var(--amber-wash)" stroke="var(--amber)"/>
<text x="112" y="136" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--ink)">model + sandbox</text>
<text x="112" y="154" text-anchor="middle" font-size="10" fill="var(--ink-2)">Anthropic-managed, commercial</text>
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
<text x="320" y="78" text-anchor="middle" font-size="10.5" fill="var(--ink-2)">Claude Code CLI on your workstation</text>
<text x="320" y="94" text-anchor="middle" font-size="10.5" fill="var(--ink-2)">pointed at Bedrock or Vertex</text>
<rect x="242" y="112" width="156" height="60" rx="8" fill="var(--good-wash)" stroke="var(--good)"/>
<text x="320" y="136" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--ink)">model in GovCloud</text>
<text x="320" y="154" text-anchor="middle" font-size="10" fill="var(--ink-2)">FedRAMP High · IL4/IL5 as authorized</text>
<rect x="242" y="186" width="156" height="40" rx="8" fill="var(--surface-2)" stroke="var(--border)"/>
<text x="320" y="210" text-anchor="middle" font-size="10.5" fill="var(--ink-2)">harness + files stay with you</text>
<text x="320" y="258" text-anchor="middle" font-size="11" font-weight="700" fill="var(--good)">the usable federal shape</text>
<text x="320" y="276" text-anchor="middle" font-size="10" fill="var(--ink-2)">no web sessions, no Artifacts</text>
<text x="320" y="306" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--accent-ink)">verify the IL for your data</text>
<text x="320" y="324" text-anchor="middle" font-size="9.5" fill="var(--ink-3)">still no air gap, still a vendor model</text>
</g>
<g>
<rect x="430" y="14" width="196" height="330" rx="12" fill="var(--surface)" stroke="var(--steel)" stroke-width="1.6"/>
<rect x="430" y="14" width="196" height="40" rx="12" fill="var(--steel-wash)"/><rect x="430" y="40" width="196" height="14" fill="var(--steel-wash)"/>
<text x="528" y="40" text-anchor="middle" font-size="12.5" font-weight="800" fill="var(--ink)">Inside the enclave</text>
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
    return """<svg viewBox="0 0 640 400" role="img" aria-label="The build pipeline: inputs (the event abstract, two planning calls, a review transcript, the presenter's script, five graphics) flow into single sources of truth (the deck HTML, the lab run scripts, a ladder map, an inventory JSON), which generators turn into the console, reveal slides, PowerPoint, docs and the adventure page; a render-and-measure loop with Playwright checks every output and feeds fixes back to the sources; GitHub Actions runs the labs in simulate mode and publishes to Pages.">
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
<text x="320" y="330" text-anchor="middle" font-size="12" font-weight="800" fill="var(--ink)">GitHub Actions: lint → run every lab (simulate) → build → publish to Pages</text>
<text x="320" y="352" text-anchor="middle" font-size="10.5" fill="var(--ink-2)">The labs gate the docs. A broken lab blocks the site. Everything public, MIT, one URL.</text>
<text x="320" y="370" text-anchor="middle" font-size="10" fill="var(--ink-3)">plus a hosted artifact for review, and a presenter console that follows the deck window to window</text>
</svg>"""


def g_toolchain() -> str:
    """The toolchain as five shelves."""
    rows = [
        ('AUTHORING', 'var(--accent)', ['HTML · CSS · JS, one file', 'inline SVG graphics', 'Red Hat fonts', 'EN/ES text table']),
        ('LABS', 'var(--good)', ['bash runtime · step()', 'Python · pgvector', 'Ansible · EDA rulebooks', 'KServe · qna.yaml']),
        ('DOCS + EXPORTS', 'var(--steel)', ['AsciiDoc · Asciidoctor', 'revealjs · pdf backends', 'python-pptx', 'Makefile · container']),
        ('VERIFY', 'var(--violet)', ['Playwright · Chromium', 'measurement scripts', 'LibreOffice · pdftoppm', 'bash -n · py_compile']),
        ('PUBLISH', 'var(--amber)', ['Git · GitHub', 'GitHub Actions', 'GitHub Pages', 'MIT licence']),
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
        ('Air gap · IL6 outside AWS', 'no on-prem or weights offer found; AWS Secret/TS only'),
        ('The DoD designation', 'blocks DoW contract work regardless of technology'),
        ('CUI / FTI boundary', 'web sessions and artifacts are commercial SaaS'),
        ('Supply chain', 'plugins, skills, MCP servers: pin, mirror, sign'),
        ('Prompt injection', 'tool results are untrusted; no system is immune'),
        ('Classifier as control', 'a model decides (17% misses); keep deny rules'),
        ('Limits and compaction', 'work stops or is summarised; checkpoint to git'),
        ('Audit, identity, 508', 'OTel opt-in; no PIV/CAC; ACRs cover the tool only'),
    ], 'var(--accent)', 'Eight places Claude Code fails to perform for federal customers, each with the mitigation: air gap and classified networks outside AWS, the DoD designation, the CUI and FTI boundary, supply chain, prompt injection, the classifier as a control, limits and compaction, and audit, identity and Section 508.')


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
<text x="348" y="302" font-size="11">A frontier model in the cloud for public content;</text><text x="348" y="320" font-size="11">an open model inside the enclave for the data.</text>
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
    out = ['<svg viewBox="0 0 640 400" role="img" aria-label="One git repository renders six faces: the interactive deck, eight labs, the presenter console, the docs book, reveal.js and PowerPoint cuts, and the adventure catalogue; GitHub Actions tests the labs and publishes to Pages.">']
    for x, y, t, m in tiles:
        out.append(f'<rect x="{x}" y="{y}" width="296" height="70" rx="10" fill="var(--surface)" stroke="var(--border-strong)" stroke-width="1.3"/>')
        out.append(f'<text x="{x + 16}" y="{y + 29}" font-size="14" font-weight="800" fill="var(--ink)">{E(t)}</text>')
        out.append(f'<text x="{x + 16}" y="{y + 51}" font-size="10.5" fill="var(--ink-2)">{E(m)}</text>')
    out.append('<rect x="14" y="268" width="612" height="52" rx="10" fill="var(--accent-wash)" stroke="var(--accent)" stroke-width="1.4"/>')
    out.append('<text x="320" y="291" text-anchor="middle" font-size="14" font-weight="900" fill="var(--ink)">one git repository · MIT · no framework, no build step for the deck</text>')
    out.append('<text x="320" y="309" text-anchor="middle" font-size="10.5" fill="var(--ink-2)">sources of truth: deck.html · labs/*/run.sh · ladder-map.json · adventure-inventory.json · docs/*.adoc</text>')
    out.append('<rect x="14" y="334" width="612" height="52" rx="10" fill="var(--good-wash)" stroke="var(--good)" stroke-width="1.4"/>')
    out.append('<text x="320" y="357" text-anchor="middle" font-size="13" font-weight="800" fill="var(--ink)">GitHub Actions: lint → run all eight labs → build → publish to GitHub Pages</text>')
    out.append('<text x="320" y="375" text-anchor="middle" font-size="10.5" fill="var(--ink-2)">nommsweymx.github.io/redhat-ai-tax-labs · a hosted artifact for review after every round</text>')
    out.append('</svg>')
    return '\n'.join(out)


def g_matrix() -> str:
    """Where Claude Code fits by data category, limited to what was read on Anthropic pages on 2026-11-19."""
    cols = ['Public content', 'CUI · FTI', 'IL4 · IL5', 'IL6 · TS']
    rows = [
        ('Anthropic API · claude.ai surfaces', ['Y', 'N', 'N', 'N'], 'cloud sessions, artifacts, connectors, routines'),
        ('Bedrock · AWS GovCloud', ['Y', 'Y', 'Y', 'N'], 'FedRAMP High · IL4/5 announced Jun 2025 · per model'),
        ('Vertex AI · Assured Workloads', ['Y', 'Y', 'D', 'N'], 'FedRAMP High · IL2 announced Apr 2025 · IL5 unconfirmed'),
        ('Claude for Government', ['Y', 'Y', 'D', 'N'], 'GA 30 Sep 2026 · FedRAMP High environment · Code early access'),
        ('Bedrock · AWS Secret / Top Secret', ['D', 'D', 'D', 'Y'], 'stated on the page · arrange through AWS · Code not stated'),
        ('Microsoft Foundry', ['Y', 'D', 'D', 'N'], 'no federal authorization read'),
    ]
    sym = {'Y': ('✓', 'var(--good)', 'var(--good-wash)'), 'N': ('✗', 'var(--accent-ink)', 'var(--accent-wash)'), 'D': ('—', 'var(--ink-3)', 'var(--surface-2)')}
    out = ['<svg viewBox="0 0 640 400" role="img" aria-label="Where Claude Code fits by data category, as read on Anthropic pages on 19 November 2026: the commercial API and claude.ai surfaces for public content only; Bedrock in AWS GovCloud for FedRAMP High and IL4 and IL5 workloads; Vertex AI with Assured Workloads for FedRAMP High and IL2; Claude for Government in a FedRAMP High environment; AWS Secret and Top Secret regions via Bedrock for classified; Microsoft Foundry with no federal authorization read. The DoD designation note on Anthropic\'s page is shown separately.">']
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
    out.append(f'<text x="{x0 + 12}" y="{y + 19}" font-size="11" font-weight="800" fill="var(--accent-ink)">DoD: a supply-chain-risk note on Anthropic\'s own government page (read 2026-11-19)</text>')
    out.append(f'<text x="{x0 + 12}" y="{y + 34}" font-size="9.5" fill="var(--ink-2)">"applies to the use of Claude as a direct part of DoW contracts and subcontracts"</text>')
    out.append(f'<text x="{x0}" y="396" font-size="9.5" fill="var(--ink-3)">✓ stated on an Anthropic page we read on 2026-11-19 · — not stated there · ✗ no authorization found · AWS authorizes each model separately</text>')
    out.append('</svg>')
    return '\n'.join(out)


GRAPHICS = {
    'agent-loop': g_agent_loop, 'architecture': g_architecture, 'boundary': g_boundary,
    'pipeline': g_pipeline, 'toolchain': g_toolchain, 'gaps': g_gaps, 'pyramid': g_pyramid,
    'hurt': g_hurt, 'faces': g_faces, 'matrix': g_matrix,
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
        agenda = ''.join(
            f'<div><i>{j + 1:02d}</i><span>{E(x["title"])}</span><span class="m">{x["minutes"]:g} min</span></div>'
            for j, x in enumerate(outline['slides']) if x.get('kind') != 'title' and x.get('minutes', 0) > 0)
        body = f'''
          <span class="eyebrow">{E(s.get('eyebrow', ''))}</span>
          <h2>{E(s['title'])}</h2>
          <p class="kicker">{E(s.get('lede', ''))}</p>
          <div class="hosts">{''.join(f'<span class="host">{E(h)}</span>' for h in s.get('hosts', []))}</div>
          <div class="agenda">{agenda}</div>'''
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
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) document.documentElement.setAttribute('data-theme', 'dark');
}})();
</script>
</body>
</html>
'''


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--outline', type=Path, default=Path('slides/how-it-was-built.json'))
    ap.add_argument('--out', type=Path, default=Path('slides/how-it-was-built.html'))
    a = ap.parse_args()
    outline = json.loads(a.outline.read_text(encoding='utf-8'))
    a.out.write_text(build(outline), encoding='utf-8')
    print(f'Wrote {a.out} ({a.out.stat().st_size:,} bytes, {len(outline["slides"])} slides)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
