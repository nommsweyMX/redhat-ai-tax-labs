#!/usr/bin/env python3
"""Cross-check the slide chain: deck.html articles vs CHAPTERS, TITLES_ES, SLIDE_GFX, data-title CSS,
build-pptx.py DECK_RUNGS, ladder-map.json, adventure-inventory.json, presenter-notes.html, slides.adoc,
plus the count words in README/build-adventure.py. Read-only. Exit 1 on any finding.
   python3 bin/check-chain.py [repo-root]"""
import json, re, sys
from pathlib import Path
R = Path(sys.argv[1] if len(sys.argv) > 1 else '.')
deck = (R / 'slides/deck.html').read_text(encoding='utf-8')
con = (R / 'slides/presenter-notes.html').read_text(encoding='utf-8')
pptx = (R / 'bin/build-pptx.py').read_text(encoding='utf-8')
adoc = (R / 'slides/slides.adoc').read_text(encoding='utf-8')
ladder = json.loads((R / 'slides/ladder-map.json').read_text(encoding='utf-8'))
inv = json.loads((R / 'bin/adventure-inventory.json').read_text(encoding='utf-8'))['items']
bad = []
def flag(msg): bad.append(msg); print('FAIL', msg)
# 1. articles in DOM order, each with its slidenum span
arts = re.findall(r'<article class="slide[^"]*" data-title="([^"]*)" data-rungs="([^"]*)"', deck)
titles = [t for t, _ in arts]; rungs = {t: tuple(x.strip() for x in r.split(',')) for t, r in arts}; N = len(titles)
body = deck[deck.find('id="stage"'):deck.find('<section id="labs"')]
for chunk, t in zip(re.split(r'<article class="slide', body)[1:], titles):
    if '<span class="slidenum"></span>' not in chunk: flag(f'{t}: no <span class="slidenum"></span> (slidenum loop throws, deck does not start)')
if len(set(titles)) != N: flag('duplicate data-title')
# 2. CHAPTERS: every title in exactly one chapter, chapters contiguous in DOM order
chap = re.search(r'var CHAPTERS = \[(.*?)\n  \];', deck, re.S).group(1)
chapters = [(int(n), en, re.findall(r'"([^"]*)"', sl)) for n, en, sl in re.findall(r'\{n:(\d+), en:"([^"]*)", es:"[^"]*", slides:\[([^\]]*)\]\}', chap)]
seen = [t for _, _, sl in chapters for t in sl]
for t in titles:
    if seen.count(t) != 1: flag(f'{t}: in {seen.count(t)} CHAPTERS entries (needs exactly 1)')
for t in seen:
    if t not in titles: flag(f'CHAPTERS names unknown slide {t!r}')
order = [next((n for n, _, sl in chapters if t in sl), None) for t in titles]
runs = [k for i, k in enumerate(order) if i == 0 or k != order[i-1]]
if len(runs) != len(set(runs)): flag(f'a chapter is not contiguous in DOM order: chapter sequence {order} (rail gets a duplicate header)')
# 3. TITLES_ES, SLIDE_GFX, CSS/JS selectors keyed on data-title
tes = dict(re.findall(r"'([^']*)':'([^']*)'", re.search(r'var TITLES_ES = \{(.*?)\};', deck, re.S).group(1)))
for t in titles:
    if t not in tes: flag(f'{t}: no TITLES_ES entry (rail shows English in ES)')
for k in re.findall(r"'([^']*)':'[^']*'", re.search(r'var SLIDE_GFX = \{(.*?)\};', deck, re.S).group(1)):
    if k not in titles: flag(f'SLIDE_GFX key {k!r} is not a slide')
for k in sorted(set(re.findall(r'\.slide\[data-title="([^"]*)"\]', deck))):
    if k not in titles: flag(f'selector .slide[data-title="{k}"] matches no slide (dead Show/Tell face or renderer)')
# 4. build-pptx.py
dr = dict((k, tuple(re.findall(r'"([a-z]+)"', v))) for k, v in re.findall(r'^\s+"([^"]+)": \(([^)]*)\),', pptx[pptx.find('DECK_RUNGS = {'):], re.M))
for t in titles:
    if t not in dr: flag(f'{t}: no DECK_RUNGS entry (add_spine KeyError)')
    elif dr[t] != rungs[t]: flag(f'{t}: data-rungs {rungs[t]} != DECK_RUNGS {dr[t]}')
for t in re.findall(r'add_spine\(s, "([^"]*)"\)', pptx):
    if t not in dr: flag(f'add_spine(s, "{t}") has no DECK_RUNGS entry')
# 5. ladder-map.json
lm = [(s['n'], s['title']) for s in ladder['slides']]
if lm != list(enumerate(titles, 1)): flag(f'ladder-map slides[] != deck order: {lm}')
lc = [(c['n'], c['title'], c['slides']) for c in ladder['chapters']]
if lc != chapters: flag(f'ladder-map chapters[] != deck CHAPTERS')
for s in ladder['slides']:
    if tuple(s.get('rungs', [])) != rungs.get(s['title']): flag(f"ladder-map slide {s['n']} {s['title']!r} rungs {s.get('rungs')} != data-rungs {rungs.get(s['title'])}")
# 5b. build-adventure.py: positional slide ids in PATHS and hard-coded ./#slide-N hashes must exist (re-mapping them is manual)
adv = (R / 'bin/build-adventure.py').read_text(encoding='utf-8')
for k in sorted(set(re.findall(r'"slide-(\d\d)"', adv)) | set(re.findall(r'\./#slide-(\d+)"', adv))):
    if not 1 <= int(k) <= N: flag(f'build-adventure.py names slide {k}; deck has {N}')
# 6. inventory: positional ids, anchors, next targets
ids = {i['id'] for i in inv}
sl = sorted((i for i in inv if i['kind'] == 'slide'), key=lambda i: i['id'])
if [i['id'] for i in sl] != [f'slide-{k:02d}' for k in range(1, N + 1)]: flag(f'inventory slide ids not slide-01..slide-{N:02d}')
for k, it in enumerate(sl, 1):
    want = f'data-title="{titles[k-1]}"'
    if want not in it.get('anchors', []): flag(f'{it["id"]}: anchors lack {want} (is it the slide at position {k}?)')
    if f'console step: Slide {k:02d} / {N}' not in it.get('anchors', []): flag(f'{it["id"]}: anchors lack "console step: Slide {k:02d} / {N}"')
for it in inv:
    for nx in it.get('next', []):
        if re.fullmatch(r'[a-z0-9-]+', nx) and nx not in ids: flag(f'{it["id"]}: next -> unknown id {nx}')
# 7. presenter console: labels, SLIDE_N, data-goto
labels = re.findall(r'data-label="Slide (\d\d) / (\d+)"', con)
if [int(a) for a, _ in labels] != list(range(1, N + 1)) or any(int(b) != N for _, b in labels): flag(f'console data-labels are {labels[:2]}..{labels[-1:]}, deck has {N}')
if f'id="pos">Slide 01 / {N}<' not in con: flag(f'console #pos default is not "Slide 01 / {N}"')
sn = int(re.search(r'var SLIDE_N = (\d+);', con).group(1))
if sn != N: flag(f'console SLIDE_N = {sn}, deck has {N} slides (every lab step lands {N-sn:+d})')
steps = len(re.findall(r'<section class="step"', con))
for v, txt in re.findall(r'data-goto="(\d+)">([^<]*)<', con):
    m = re.search(r'(Lab|Slide) (\d+)', txt); v = int(v)
    want = (sn + int(m.group(2)) - 1) if m and m.group(1) == 'Lab' else (int(m.group(2)) - 1 if m else None)
    if v >= steps or (want is not None and v != want): flag(f'data-goto="{v}" labelled {txt.strip()!r} should be {want} (0-based step index)')
# 8. slides.adoc and count words
h = len(re.findall(r'^== ', adoc, re.M)); nb = len(re.findall(r'^\[\.notes\]', adoc, re.M))
if h != N or nb != N: flag(f'slides.adoc has {h} "== " slides and {nb} [.notes] blocks; deck has {N}')
words = {16: 'sixteen', 17: 'seventeen', 18: 'eighteen', 19: 'nineteen', 20: 'twenty'}
for f in ('README.adoc', 'bin/build-adventure.py'):
    txt = (R / f).read_text(encoding='utf-8').lower()
    for w in re.findall(r'\b(\w+) slides\b', txt):
        if w in words.values() and w != words.get(N): flag(f'{f} says "{w} slides"; deck has {N}')
print(f'{N} slides, {len(chapters)} chapters, {steps} console steps checked: {len(bad)} finding(s)')
sys.exit(1 if bad else 0)
