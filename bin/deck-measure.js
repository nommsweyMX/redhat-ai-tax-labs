#!/usr/bin/env node
// Render-and-measure for slides/deck.html: every slide x {en,es} x {tell,show} x {light,dark}.
//   NODE_PATH=/opt/node-tools/node_modules CHROMIUM=/usr/bin/google-chrome \
//   node bin/deck-measure.js slides/deck.html [shots-dir] [W H]
// Reports: slides whose box scrolls (scrollHeight > clientHeight), text elements that end
// below the slide box, and Spanish-mode elements still showing their English innerHTML.
// Exit 1 if any overflow is found. Touches nothing in the repository.
const fs = require('fs'); const path = require('path');
const { chromium } = require('playwright');
(async () => {
  const [deck, shots, W = '1280', H = '800'] = process.argv.slice(2);
  if (!deck) { console.error('usage: deck-measure.js <deck.html> [shots-dir] [W H]'); process.exit(2); }
  if (shots) fs.mkdirSync(shots, { recursive: true });
  const opts = process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {};
  const browser = await chromium.launch(opts);
  const page = await browser.newPage({ viewport: { width: +W, height: +H }, deviceScaleFactor: 1 });
  const errors = []; page.on('pageerror', e => errors.push(String(e)));
  await page.goto('file://' + path.resolve(deck), { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  const n = await page.evaluate(() => document.querySelectorAll('#stage .slide').length);
  let bad = 0;
  for (const lang of ['en', 'es']) {
    await page.click('#lang-' + lang);
    for (const view of ['tell', 'show']) {
      await page.click('#view-' + view);
      for (const theme of ['light', 'dark']) {
        const now = await page.evaluate(() => document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light');
        if (now !== theme) await page.click('#themeToggle');
        for (let i = 1; i <= n; i++) {
          await page.evaluate(k => { location.hash = '#slide-' + k; }, i);
          await page.waitForTimeout(120);
          const r = await page.evaluate(() => {
            const s = document.querySelector('#stage .slide[data-active="true"]');
            const box = s.getBoundingClientRect();
            const past = [], untranslated = [];
            s.querySelectorAll('h2,h3,h4,p,li,td,th,.tag,.rung,.eyebrow,.lede,b,span').forEach(el => {
              if (!el.textContent.trim() || el.closest('.chapstrip,.spine,.slidenum')) return;
              const r = el.getBoundingClientRect();
              if (r.height && r.bottom > box.bottom + 1) past.push(el.tagName.toLowerCase() + ':' + el.textContent.trim().slice(0, 40));
            });
            if (document.documentElement.lang === 'es') s.querySelectorAll('[data-i18n-en]').forEach(el => {
              const en = el.getAttribute('data-i18n-en').replace(/\s+/g, ' ').trim(), now = el.innerHTML.replace(/\s+/g, ' ').trim();
              if (en === now && /[a-z]{3}/i.test(el.textContent) && !el.querySelector('[data-i18n-en]')) untranslated.push(el.textContent.trim().slice(0, 40));
            });
            return { title: s.dataset.title, over: s.scrollHeight - s.clientHeight, wide: s.scrollWidth - s.clientWidth, past, untranslated };
          });
          const tag = `${String(i).padStart(2, '0')} ${r.title} [${lang} ${view} ${theme}]`;
          if (r.over > 1 || r.wide > 1 || r.past.length) { bad++; console.log('OVERFLOW', tag, `+${r.over}px tall +${r.wide}px wide`, r.past.slice(0, 3).join(' | ')); }
          if (r.untranslated.length) console.log('ES-MISSING', tag, r.untranslated.slice(0, 4).join(' | '));
          if (shots) await page.locator('#stage').screenshot({ path: path.join(shots, `${String(i).padStart(2, '0')}-${lang}-${view}-${theme}.png`) });
        }
      }
    }
  }
  console.log(`${n} slides x 8 combos measured; ${bad} overflow(s); ${errors.length} page error(s)`, errors.slice(0, 2));
  await browser.close();
  process.exit(bad || errors.length ? 1 : 0);
})();
