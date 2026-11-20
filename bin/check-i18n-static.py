#!/usr/bin/env python3
"""Browser-free sanity check of a deck translation dictionary.

    python3 bin/check-i18n-static.py [slides/deck.html] [--lang es]

Reads the source text only, so it cannot know which elements setLang() visits;
bin/check-i18n.js (headless Chromium) is the authoritative check. This one is
cheap enough for `make lint`: it reports duplicate keys whose values differ
(a JS object literal keeps the last one silently), entries whose English no
longer occurs anywhere in the deck (stale after a wording change), slides whose
data-title has no rail title, and labs / cards / graphics without a translated
sub-object. Exit 1 on any finding.
"""
import re, sys

args = sys.argv[1:]
lang = args[args.index('--lang') + 1] if '--lang' in args else 'es'
path = next((a for a in args if a.endswith('.html')), 'slides/deck.html')
src = open(path, encoding='utf-8').read()
dict_name = 'ES_TEXT' if lang == 'es' else lang.upper() + '_TEXT'
titles_name = 'TITLES_' + lang.upper()


def block(name, opener, closer):
    start = src.index('var %s = %s' % (name, opener)) + len('var %s = ' % name)
    end = src.index('\n  %s;' % closer, start)
    return start, end, src[start:end]


d0, d1, dict_text = block(dict_name, '{', '}')
outside = src[:d0] + src[d1:]
pair = re.compile(r'^\s*"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)"', re.M)
entries = pair.findall(dict_text)
seen, dupes = {}, []
for k, v in entries:
    if k in seen and seen[k] != v:
        dupes.append(k)
    seen[k] = v
unesc = lambda s: s.replace('\\"', '"').replace("\\'", "'")
stale = [k for k in seen if unesc(k) not in outside]

slide_titles = re.findall(r'<article class="slide[^"]*" data-title="([^"]+)"', src)
_, _, titles_text = block(titles_name, '{', '}')
rail = set(re.findall(r"'([^']+)'\s*:\s*'", titles_text))
no_rail = [t for t in slide_titles if t not in rail]

l0, l1, labs = block('LABS', '[', ']')
lab_starts = [m.start() for m in re.finditer(r'^\s*\{title:', labs, re.M)]
labs_no_es = [i + 1 for i, s in enumerate(lab_starts)
              if not re.search(r'\b%s:\s*\{' % lang, labs[s:(lab_starts[i + 1] if i + 1 < len(lab_starts) else len(labs))])]
_, _, cards = block('LAB_CARDS', '[', ']')
card_en = len(re.findall(r'\{what:', cards)) - len(re.findall(r'\b%s:\s*\{what:' % lang, cards))
card_lang = len(re.findall(r'\b%s:\s*\{what:' % lang, cards))
gfx = src[src.index('/*__GRAPHICS_START__*/'):src.index('/*__GRAPHICS_END__*/')]
gfx_entries = re.split(r'^  (?=GRAPHICS\[")', gfx, flags=re.M)
gfx_no_lang = [re.match(r'GRAPHICS\["([^"]+)"\]', e).group(1) for e in gfx_entries
               if e.startswith('GRAPHICS[') and not re.search(r'\b%s:\s*\{' % lang, e)]
_, _, chapters = block('CHAPTERS', '[', ']')
chap_no_lang = len(re.findall(r'\{n:', chapters)) - len(re.findall(r'\b%s:"' % lang, chapters))

print('%s: %s has %d entries, %d distinct' % (path, dict_name, len(entries), len(seen)))
print('duplicate keys with different values: %d %s' % (len(dupes), dupes))
print('stale entries (English not in the deck any more): %d' % len(stale))
for k in stale:
    print('  "%s"' % (k if len(k) <= 100 else k[:97] + '...'))
print('slides without a %s rail title: %d %s' % (lang, len(no_rail), no_rail))
print('labs without %s: %d %s; cards %d EN / %d %s; graphics without %s: %d %s; chapters without %s: %d'
      % (lang, len(labs_no_es), labs_no_es, card_en, card_lang, lang, lang, len(gfx_no_lang), gfx_no_lang, lang, chap_no_lang))
bad = len(dupes) + len(stale) + len(no_rail) + len(labs_no_es) + len(gfx_no_lang) + chap_no_lang + (card_en != card_lang)
sys.exit(1 if bad else 0)
