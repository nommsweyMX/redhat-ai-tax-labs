#!/usr/bin/env python3
"""Find ES_TEXT keys in slides/deck.html whose English text no longer occurs in the deck
(outside the ES_TEXT block itself). An edited English string orphans its translation silently
(setLang looks the key up by exact innerHTML). Usage: check-es-keys.py <repo-root>"""
import re, sys, os, html
deck = open(os.path.join(sys.argv[1], 'slides/deck.html'), encoding='utf-8').read()
s = deck.index('var ES_TEXT = {'); e = deck.index('\n  };', s)
block = deck[s:e]
rest = deck[:s] + deck[e:]
rest_ws = re.sub(r'\s+', ' ', rest)
rest_plain = html.unescape(rest_ws)
keys = re.findall(r'^\s*"((?:[^"\\]|\\.)+)"\s*:\s*"', block, re.M)
orphans = []
for k in keys:
    kk = k.replace('\\"', '"').replace('\\\\', '\\')
    if kk in rest_ws or kk in rest_plain or html.unescape(kk) in rest_plain:
        continue
    orphans.append(kk)
print(f'{len(keys)} ES_TEXT keys, {len(orphans)} not found in the deck source')
for o in orphans: print('  orphan:', o[:120])
sys.exit(1 if orphans else 0)
