#!/usr/bin/env python3
"""Compare the deck's virtual terminals (var LABS in slides/deck.html) with labs/*/run.sh,
and the deck's step cards (var LAB_CARDS) with those terminals.
For each lab: the step commands (run.sh with its default ${VAR:-...} values substituted),
the expected-output lines (heredoc vs the deck's out[] lines, 'note' lines excluded), and
the card count: the {what: facets under the lab's /* Lab NN */ comment must number
(deck steps + 1 wrap) x 2 languages, or cardShow() returns without a card for the missing step.
Exit 1 if anything differs.
Usage: check-labs-parity.py <repo-root> [--lab NN]
  --lab NN reports that lab only, so a new lab is judged apart from inherited divergences."""
import re, sys, glob, os
args = sys.argv[1:]
only = None
if '--lab' in args:
    only = args[args.index('--lab') + 1].zfill(2)
    del args[args.index('--lab'):args.index('--lab') + 2]
root = args[0] if args else '.'
deck = open(os.path.join(root, 'slides/deck.html'), encoding='utf-8').read()
start = deck.index('var LABS = [')
end = deck.index('var LAB_CARDS = [')
block = deck[start:end]
# split into labs on top-level "title:" occurrences
labs = re.split(r"\n  \{\s*title:", block)[1:]
def js_str(s):
    return s.replace("\\'", "'").replace('\\"', '"')
deck_labs = []
STEP = re.compile(r"""\{\s*cmd:(['"])((?:(?!\1).|\\.)*?)\1(.*?)out:\[(.*?)\]\s*\}""", re.S)
LINE = re.compile(r"""\[\s*(['"])([a-z]*)\1\s*,\s*(['"])((?:(?!\3).|\\.)*?)\3\s*\]""", re.S)
for lab in labs:
    cmds, outs = [], []
    for m in STEP.finditer(lab):
        cmds.append(js_str(m.group(2)))
        outs.append([js_str(t) for _, c, _, t in LINE.findall(m.group(4)) if c != 'note'])
    deck_labs.append((cmds, outs))
# LAB_CARDS: one block per "/* Lab NN ... */" comment, counted by its {what: facets
cards_block = deck[end:end + deck[end:].index('\n  ];')]
cards = {}
for m in re.finditer(r'/\* Lab (\d\d)\b', cards_block):
    nxt = re.search(r'/\* Lab \d\d\b', cards_block[m.end():])
    seg = cards_block[m.end():m.end() + nxt.start()] if nxt else cards_block[m.end():]
    cards[m.group(1)] = len(re.findall(r'\{what:', seg))
rc = 0
seen = 0
for i, script in enumerate(sorted(glob.glob(os.path.join(root, 'labs/lab*/run.sh')))):
    name = os.path.basename(os.path.dirname(script))
    nn = name[3:5]
    if only and nn != only:
        continue
    seen += 1
    src = open(script, encoding='utf-8').read()
    defaults = dict(re.findall(r'^([A-Z_]+)="\$\{\1:-([^}]*)\}"', src, re.M))
    def sub(s):
        for k, v in defaults.items():
            s = s.replace('$' + k, v).replace('${' + k + '}', v)
        return s.replace('\\"', '"').replace('\\$', '$')
    steps = re.findall(r'^step "((?:[^"\\]|\\.)*)" <<\'OUT\'\n(.*?)\nOUT$', src, re.M | re.S)
    if i >= len(deck_labs):
        print(f'{name}: no LABS entry in the deck'); rc = 1; continue
    dcmds, douts = deck_labs[i]
    if len(steps) != len(dcmds):
        print(f'{name}: run.sh has {len(steps)} steps, deck has {len(dcmds)} cmds'); rc = 1
    for n, (cmd, out) in enumerate(steps):
        if n < len(dcmds) and sub(cmd) != dcmds[n]:
            print(f'{name} step {n+1}: cmd differs\n   run.sh: {sub(cmd)}\n   deck  : {dcmds[n]}'); rc = 1
        if n < len(douts):
            a = [l.rstrip() for l in out.split('\n')]
            b = [l.rstrip() for l in douts[n]]
            if a != b:
                diff = [(x, y) for x, y in zip(a, b) if x != y]
                print(f'{name} step {n+1}: output differs ({len(a)} vs {len(b)} lines){"; first diff: " + repr(diff[0]) if diff else ""}'); rc = 1
    want = (len(dcmds) + 1) * 2
    have = cards.get(nn)
    if have is None:
        print(f'{name}: no /* Lab {nn} */ block in LAB_CARDS'); rc = 1
    elif have != want:
        print(f'{name}: LAB_CARDS has {have} facets, deck steps + wrap want {want}'); rc = 1
if only and seen == 0:
    print(f'no labs/lab{only}-*/run.sh'); rc = 1
scope = f'lab {only}' if only else f'{len(deck_labs)} deck labs vs run.sh scripts'
print(f'labs/deck parity ({scope}):', 'OK' if rc == 0 else 'DIVERGENCES FOUND')
sys.exit(rc)
