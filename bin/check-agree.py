#!/usr/bin/env python3
"""Cross-file agreement: deck articles vs CHAPTERS, TITLES_ES, SLIDE_GFX, ladder-map slides/chapters/labs,
adventure-inventory slide/lab items, presenter console SLIDE_N and section count, build-pptx DECK_RUNGS,
slides.adoc heading count, docs lab module titles. Usage: check-agree.py <repo-root>"""
import re, sys, os, json
R = sys.argv[1]
rd = lambda p: open(os.path.join(R, p), encoding='utf-8').read()
deck = rd('slides/deck.html'); rc = 0
def bad(m):
    global rc; rc = 1; print('  FAIL', m)
arts = re.findall(r'<article class="slide[^"]*" data-title="([^"]+)" data-rungs="([^"]*)"', deck)
titles = [t for t, _ in arts]
h2s = re.findall(r'<article class="slide[^"]*" data-title="[^"]+"[^>]*>.*?<h2>(.*?)</h2>', deck, re.S)
h2s = [re.sub(r'<[^>]+>', '', h).strip() for h in h2s]
print(f'deck: {len(titles)} slides')
chap = re.search(r'var CHAPTERS = \[(.*?)\n  \];', deck, re.S).group(1)
chap_titles = re.findall(r'"([^"]+)"', chap)
chap_slides = [t for t in chap_titles if t in titles]
if chap_slides != titles: bad(f'CHAPTERS order/set differs from deck articles: {chap_slides}')
tes = re.search(r'var TITLES_ES = \{(.*?)\};', deck, re.S).group(1)
for t in titles:
    if f"'{t}':" not in tes: bad(f'TITLES_ES missing {t!r}')
gfx = re.search(r'var SLIDE_GFX = \{(.*?)\};', deck, re.S).group(1)
for k in re.findall(r"'([^']+)':'", gfx):
    if k not in titles: bad(f'SLIDE_GFX key {k!r} is not a slide')
lm = json.loads(rd('slides/ladder-map.json'))
if [s['title'] for s in lm['slides']] != titles: bad('ladder-map slides[].title order differs from deck')
for s, (t, r) in zip(lm['slides'], arts):
    if s['n'] != titles.index(t) + 1: bad(f'ladder-map slide n {s["n"]} != position of {t!r}')
lm_chap = [(c['title'], c['slides']) for c in lm['chapters']]
deck_chap = re.findall(r'en:"([^"]+)", es:"[^"]+", slides:\[([^\]]*)\]', chap)
deck_chap = [(en, re.findall(r'"([^"]+)"', sl)) for en, sl in deck_chap]
if lm_chap != deck_chap: bad(f'ladder-map chapters differ from deck CHAPTERS')
labs_titles = re.findall(r"\n    title:'((?:[^'\\]|\\.)*)'", deck[deck.index('var LABS = ['):deck.index('var LAB_CARDS')])
labs_titles += re.findall(r'\n  \{title:"([^"]+)"', deck[deck.index('var LABS = ['):deck.index('var LAB_CARDS')])
if [l['title'] for l in lm['labs']] != labs_titles: bad(f'ladder-map labs[].title differs from deck LABS: {labs_titles}')
inv = json.load(open(os.path.join(R, 'bin/adventure-inventory.json')))['items']
inv_slides = sorted((i for i in inv if i['kind'] == 'slide'), key=lambda i: i['id'])
if len(inv_slides) != len(titles): bad(f'inventory has {len(inv_slides)} slide items, deck {len(titles)}')
for n, it in enumerate(inv_slides):
    anchor = [a for a in it['anchors'] if a.startswith('data-title=')]
    if not anchor or anchor[0] != f'data-title="{titles[n]}"': bad(f'{it["id"]} anchors {anchor} != deck slide {n+1} {titles[n]!r}')
    if it['title'] != h2s[n]: bad(f'{it["id"]} title {it["title"]!r} != deck h2 {h2s[n]!r}')
    cs = [a for a in it['anchors'] if a.startswith('console step:')]
    if cs and cs[0] != f'console step: Slide {n+1:02d} / {len(titles)}': bad(f'{it["id"]} {cs[0]!r}')
inv_labs = sorted((i for i in inv if i['kind'] == 'lab'), key=lambda i: i['id'])
for n, it in enumerate(inv_labs):
    if not it['title'].endswith(labs_titles[n]): bad(f'{it["id"]} title {it["title"]!r} vs deck {labs_titles[n]!r}')
    if it['rung'] != lm['labs'][n]['chip']: bad(f'{it["id"]} rung {it["rung"]!r} != ladder-map chip {lm["labs"][n]["chip"]!r}')
pn = rd('slides/presenter-notes.html')
sn = int(re.search(r'var SLIDE_N = (\d+);', pn).group(1))
secs = re.findall(r'<section class="step" data-label="([^"]+)">', pn)
if sn != len(titles): bad(f'presenter SLIDE_N={sn}, deck has {len(titles)} slides')
if len([s for s in secs if s.startswith('Slide')]) != len(titles): bad('presenter slide sections != deck slides')
if len([s for s in secs if s.startswith('Lab')]) != len(labs_titles): bad('presenter lab sections != deck LABS')
for s in secs:
    if s.startswith('Slide') and not s.endswith(f'/ {len(titles)}'): bad(f'presenter label {s!r}')
ph2 = re.findall(r'<section class="step" data-label="Slide[^"]+">\s*<div class="step-head">.*?<h2>(.*?)</h2>', pn, re.S)
for n, h in enumerate(ph2):
    if re.sub(r'<[^>]+>', '', h).strip() != h2s[n]: bad(f'presenter section {n+1} h2 {h!r} != deck h2 {h2s[n]!r}')
pp = rd('bin/build-pptx.py')
dr = re.findall(r'^    "([^"]+)": \(', pp[pp.index('DECK_RUNGS = {'):], re.M)
for t in titles:
    if t not in dr: bad(f'build-pptx DECK_RUNGS missing {t!r}')
for t in re.findall(r'add_spine\(s, "([^"]+)"\)', pp):
    if t not in titles: bad(f'build-pptx add_spine({t!r}) is not a deck slide')
sa = rd('slides/slides.adoc')
heads = re.findall(r'^== (.+)$', sa, re.M)
if len(heads) != len(titles): bad(f'slides.adoc has {len(heads)} slides, deck {len(titles)}')
for n, h in enumerate(heads):
    if h.strip() != h2s[n]: bad(f'slides.adoc slide {n+1} {h!r} != deck h2 {h2s[n]!r}')
import glob
for n, f in enumerate(sorted(glob.glob(os.path.join(R, 'docs/0[1-9]-lab-*.adoc')))):
    m = re.search(r'^= Lab (\d\d) — (.+)$', rd(os.path.relpath(f, R)), re.M)
    if not m or m.group(2).strip() != labs_titles[n]: bad(f'{os.path.basename(f)} title != deck LABS {labs_titles[n]!r}')
    rung = re.search(r'^\| Rung\s*\| (.+)$', rd(os.path.relpath(f, R)), re.M)
    if rung and rung.group(1).strip() != lm['labs'][n]['chip']: bad(f'{os.path.basename(f)} Rung {rung.group(1)!r} != ladder-map chip {lm["labs"][n]["chip"]!r}')
print('cross-file agreement:', 'OK' if rc == 0 else 'MISMATCHES')
sys.exit(rc)
