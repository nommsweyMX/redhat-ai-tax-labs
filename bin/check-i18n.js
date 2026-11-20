#!/usr/bin/env node
/* Translation coverage check for slides/deck.html.
 *
 *   node bin/check-i18n.js [slides/deck.html] [--lang es] [--allow-missing N] [--json]
 *
 * Opens the deck headless, walks the same elements setLang() walks (I18N_SEL),
 * normalises each element's English innerHTML the same way setLang() does and
 * reports: strings with no dictionary entry (they would stay English), dictionary
 * entries no element uses (dead keys), slides with no rail title, labs / cards /
 * graphics / chapters with no translated sub-object, and slides that overflow
 * after the switch. Exit 1 when anything is missing beyond --allow-missing.
 *
 * Needs node >= 18 and playwright (npm i -g playwright). The deck's own script is
 * one IIFE, so the tables are read from the source text, not from window.
 */
'use strict';
const fs = require('fs'), path = require('path'), vm = require('vm');

const args = process.argv.slice(2);
const flag = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };
const file = path.resolve(args.find(a => a.endsWith('.html')) || 'slides/deck.html');
const LANG = flag('--lang', 'es');
const ALLOW = parseInt(flag('--allow-missing', '0'), 10);
const JSON_OUT = args.includes('--json');
const src = fs.readFileSync(file, 'utf8');

/* slice "var NAME = {...};" (or [...];) out of the source and evaluate it */
function table(name, open, close) {
  const start = src.indexOf('var ' + name + ' = ' + open);
  if (start < 0) throw new Error('no ' + name + ' in ' + file);
  const from = start + ('var ' + name + ' = ').length;
  const endRe = new RegExp('^  \\' + close + ';', 'm');
  endRe.lastIndex = from;
  const rest = src.slice(from);
  const m = endRe.exec(rest);
  if (!m) throw new Error(name + ' never closes');
  const text = rest.slice(0, m.index + 3);
  return vm.runInNewContext('(' + text + ')');
}
const DICT_NAME = LANG === 'es' ? 'ES_TEXT' : LANG.toUpperCase() + '_TEXT';
const DICT = table(DICT_NAME, '{', '}');
const TITLES = table(LANG === 'es' ? 'TITLES_ES' : 'TITLES_' + LANG.toUpperCase(), '{', '}');
const CHAPTERS = table('CHAPTERS', '[', ']');
const LABS = table('LABS', '[', ']');
const LAB_CARDS = table('LAB_CARDS', '[', ']');
const selStart = src.indexOf('var I18N_SEL = [');
const selText = src.slice(selStart + 'var I18N_SEL = '.length, src.indexOf("].join(', ');", selStart) + 1);
const I18N_SEL = vm.runInNewContext('(' + selText + ')').join(', ');

/* source-level duplicate keys: a JS object literal keeps the last one silently */
const dictStart = src.indexOf('var ' + DICT_NAME + ' = {');
const dictEnd = src.indexOf('\n  };', dictStart);
const seen = new Map(), dupes = [];
for (const line of src.slice(dictStart, dictEnd).split('\n')) {
  const m = /^\s*"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)"/.exec(line);
  if (!m) continue;
  if (seen.has(m[1]) && seen.get(m[1]) !== m[2]) dupes.push(m[1]);
  seen.set(m[1], m[2]);
}

/* per-object sub-dictionaries */
const labFields = ['title', 'goal', 'rungs', 'youll', 'watch', 'take', 'theory'];
const labsMissing = LABS.map((l, i) => ({ lab: i + 1, missing: labFields.filter(f => l[f] !== undefined && !(l[LANG] && l[LANG][f] !== undefined)) })).filter(x => x.missing.length);
const cardsMissing = [];
LAB_CARDS.forEach((c, i) => {
  const n = LABS[i] ? LABS[i].steps.length : 0;
  if (c.steps.length !== n) cardsMissing.push({ lab: i + 1, note: 'cards ' + c.steps.length + ' vs steps ' + n });
  c.steps.concat([c.wrap]).forEach((card, j) => {
    const miss = ['what', 'why', 'value'].filter(f => !(card[LANG] && card[LANG][f]));
    if (miss.length) cardsMissing.push({ lab: i + 1, card: j < c.steps.length ? j + 1 : 'wrap', missing: miss });
  });
});
if (LABS.length !== LAB_CARDS.length) cardsMissing.push({ note: 'LABS ' + LABS.length + ' entries, LAB_CARDS ' + LAB_CARDS.length });
const chaptersMissing = CHAPTERS.filter(c => !c[LANG]).map(c => c.n);
const gfxMissing = [];
const gfxBlock = src.slice(src.indexOf('/*__GRAPHICS_START__*/'), src.indexOf('/*__GRAPHICS_END__*/'));
gfxBlock.split(/^  (?=GRAPHICS\[")/m).forEach(entry => {
  const m = /^GRAPHICS\["([^"]+)"\]/.exec(entry);
  if (m && !new RegExp('\\b' + LANG + ':\\s*\\{').test(entry)) gfxMissing.push(m[1]);
});

/* strings that stay English on purpose: identifiers, numbers, product names, code.
   Built-in rules plus one literal or /regex/ per line in --keep FILE (default bin/i18n-keep-english.txt). */
const keepFile = flag('--keep', path.join(path.dirname(file), '..', 'bin', 'i18n-keep-english.txt'));
const keepRules = [/^[\d\s·\-–—:+%.,\/()]*$/, /^[A-Z]$/, /^\d+[hm]( \d+m)?$/, /^<tspan /];
if (fs.existsSync(keepFile)) {
  for (const raw of fs.readFileSync(keepFile, 'utf8').split('\n')) {
    const line = raw.trim();
    if (!line || line.startsWith('#')) continue;
    const r = /^\/(.*)\/([a-z]*)$/.exec(line);
    keepRules.push(r ? new RegExp(r[1], r[2]) : { test: s => s === line });
  }
}
const kept = s => keepRules.some(r => r.test(s));
/* a dead key whose English still occurs in the page source sits on an element no I18N_SEL selector matches */
const inMarkup = k => { const i = src.indexOf(k); return i >= 0 && (i < dictStart || i > dictEnd); };

(async () => {
  const { chromium } = require('playwright');
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  await page.goto('file://' + file);
  const keys = Object.keys(DICT);
  /* renderer-owned: redrawn from their own bilingual data (TITLE_LAYERS, LOOP_STATIONS, RUNGN, CHROME), never through the dictionary */
  const SKIP = '#title-pyr, .stagemap, .spine, #gfxbtn';
  const dom = await page.evaluate(({ sel, keys, skip }) => {
    const KEYS = new Set(keys);
    const norm = s => s.replace(/\s+/g, ' ').trim();
    const els = Array.from(document.querySelectorAll(sel));
    const matched = new Set(els);
    const used = new Set(), missing = [];
    for (const el of els) {
      if (el.closest(skip)) continue;                      /* renderer-owned, redrawn from its own EN/ES data */
      const key = norm(el.getAttribute('data-i18n-en') || el.innerHTML);
      if (!key) continue;
      if (KEYS.has(key)) { used.add(key); continue; }
      let anc = el.parentElement, covered = false;         /* parent wins: its innerHTML replacement discards the child */
      while (anc) { if (matched.has(anc) && KEYS.has(norm(anc.getAttribute('data-i18n-en') || anc.innerHTML))) { covered = true; break; } anc = anc.parentElement; }
      if (covered) continue;
      const slide = el.closest('.slide');
      const where = slide ? 'slide "' + slide.dataset.title + '"' : el.closest('#labs') ? 'labs view' : el.closest('#demoview') ? 'demo view' : 'chrome';
      missing.push({ where, el: el.tagName.toLowerCase() + (el.getAttribute('class') ? '.' + el.getAttribute('class').split(' ')[0] : ''), key: key.length > 110 ? key.slice(0, 107) + '...' : key });
    }
    const titles = Array.from(document.querySelectorAll('#stage .slide')).map(s => s.dataset.title);
    /* dead keys that sit on a real element right now (English DOM): the English is there, no selector visits it */
    const DEAD = new Set(keys.filter(k => !used.has(k))), unreachable = {};
    Array.from(document.body.querySelectorAll('*')).forEach(el => {
      if (el.children.length > 3 || el.closest(skip) || el.closest('script, style') || matched.has(el)) return;
      const k = norm(el.innerHTML);
      if (DEAD.has(k)) { const s = el.closest('.slide'); unreachable[k] = (s ? 'slide "' + s.dataset.title + '"' : 'outside the slides') + ' <' + el.tagName.toLowerCase() + '>'; }
    });
    const overflow = [];
    Array.from(document.querySelectorAll('#stage .slide')).forEach(s => {
      s.setAttribute('data-active', 'true');
      if (s.scrollHeight > s.clientHeight + 2) overflow.push(s.dataset.title);
      s.setAttribute('data-active', 'false');
    });
    document.querySelector('#stage .slide').setAttribute('data-active', 'true');
    return { matched: els.length, used: Array.from(used), missing, titles, overflow, unreachable };
  }, { sel: I18N_SEL, keys, skip: SKIP });
  const deadAll = keys.filter(k => !dom.used.includes(k));
  const keptEnglish = dom.missing.filter(m => kept(m.key));
  dom.missing = dom.missing.filter(m => !kept(m.key));
  const titlesMissing = dom.titles.filter(t => !TITLES[t]);

  /* switch and look: lang attribute, still-English elements, dead keys that sit on real elements, overflow per slide */
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.click('#lang-' + LANG);
  const after = await page.evaluate(({ sel, skip, dead }) => {
    const norm = s => s.replace(/\s+/g, ' ').trim();
    const els = Array.from(document.querySelectorAll(sel)).filter(el => !el.closest(skip) && el.getAttribute('data-i18n-en'));
    const unchanged = els.filter(el => norm(el.innerHTML) === norm(el.getAttribute('data-i18n-en'))).length;
    const overflow = [];
    Array.from(document.querySelectorAll('#stage .slide')).forEach(s => {
      s.setAttribute('data-active', 'true');
      if (s.scrollHeight > s.clientHeight + 2) overflow.push(s.dataset.title + ' (+' + (s.scrollHeight - s.clientHeight) + 'px)');
      s.setAttribute('data-active', 'false');
    });
    document.querySelector('#stage .slide').setAttribute('data-active', 'true');
    const undef = (document.body.innerHTML.match(/>undefined<|="undefined/g) || []).length;   /* a renderer indexed past its [en, es, ...] array */
    return { lang: document.documentElement.lang, walked: els.length, unchanged, overflow, undef, rail: Array.from(document.querySelectorAll('#railnav .navitem')).map(b => b.textContent.trim()).slice(0, 3) };
  }, { sel: I18N_SEL, skip: SKIP });
  await browser.close();
  if (after.undef) errors.push(after.undef + ' element(s) render the word "undefined" after the switch');
  after.unreachable = dom.unreachable;
  const unreachable = Object.keys(dom.unreachable);       /* the English is on a real element, but no I18N_SEL selector visits it */
  const stale = deadAll.filter(k => !dom.unreachable[k]);  /* wording changed or the element went away */
  const overflowNew = after.overflow.filter(o => !dom.overflow.includes(o.replace(/ \(\+\d+px\)$/, '')));

  const report = { file: path.relative(process.cwd(), file), lang: LANG, dictionary: DICT_NAME, entries: keys.length, elementsWalked: dom.matched,
    missing: dom.missing, keptEnglish: keptEnglish.map(m => m.key), unreachableKeys: unreachable, staleKeys: stale,
    duplicateKeysWithDifferentValues: dupes, slidesWithoutRailTitle: titlesMissing,
    chaptersWithoutName: chaptersMissing, labsWithoutFields: labsMissing, cardsWithoutFacets: cardsMissing, graphicsWithoutText: gfxMissing,
    afterSwitch: after, overflowOnlyIn: overflowNew };
  if (JSON_OUT) { console.log(JSON.stringify(report, null, 1)); }
  else {
    console.log(`${report.file}: ${DICT_NAME} has ${keys.length} distinct entries; ${dom.matched} elements walked`);
    console.log(`MISSING — prose with no entry, stays English: ${dom.missing.length}`);
    dom.missing.forEach(m => console.log(`  ${m.where} <${m.el}> "${m.key}"`));
    console.log(`kept English on purpose (identifiers, code, names in ${path.basename(keepFile)}): ${keptEnglish.length}`);
    console.log(`UNREACHABLE — entry exists, English is in the deck, but no I18N_SEL selector visits that element: ${unreachable.length}`);
    unreachable.forEach(k => console.log(`  ${after.unreachable[k]} "${k.length > 100 ? k.slice(0, 97) + '...' : k}"`));
    console.log(`JavaScript errors after the switch: ${errors.length}${errors.length ? ' -> ' + errors.join(' | ') : ''}`);
    console.log(`stale — entry whose English no longer occurs in the deck: ${stale.length}`);
    stale.forEach(k => console.log(`  "${k.length > 100 ? k.slice(0, 97) + '...' : k}"`));
    console.log(`duplicate keys with different values (last one wins): ${dupes.length}${dupes.length ? ' -> ' + dupes.join(' | ') : ''}`);
    console.log(`slides without a ${LANG} rail title: ${titlesMissing.length}${titlesMissing.length ? ' -> ' + titlesMissing.join(', ') : ''}`);
    console.log(`chapters without ${LANG}: ${chaptersMissing.length}; labs with untranslated fields: ${labsMissing.length}; cards without facets: ${cardsMissing.length}; graphics without ${LANG}: ${gfxMissing.length}`);
    labsMissing.forEach(x => console.log('  lab', x.lab, x.missing.join(',')));
    cardsMissing.forEach(x => console.log('  card', JSON.stringify(x)));
    console.log(`after click: <html lang="${after.lang}">, ${after.walked - after.unchanged}/${after.walked} walked elements changed, rail starts ${JSON.stringify(after.rail)}`);
    console.log(`slides that scroll at 1600x900: en ${dom.overflow.length}, ${LANG} ${after.overflow.length}${after.overflow.length ? ' -> ' + after.overflow.join('; ') : ''}; only in ${LANG}: ${overflowNew.length}`);
  }
  const problems = dom.missing.length + unreachable.length + titlesMissing.length + chaptersMissing.length + labsMissing.length + cardsMissing.length + gfxMissing.length + dupes.length + errors.length;
  process.exitCode = problems > ALLOW ? 1 : 0;
})().catch(e => { console.error(e.message); process.exitCode = 2; });
