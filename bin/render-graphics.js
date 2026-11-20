#!/usr/bin/env node
// Render the standalone graphics of the how-it-was-built talk to PNG for the docs book.
//
//   node bin/render-graphics.js slides/assets/graphics/built docs/images/built [fonts.css]
//
// Needs Playwright with Chromium (CHROMIUM=/path/to/chromium overrides the executable). Each SVG is
// inlined into a page with the Red Hat fonts and shot at 1280 by 800 pixels.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const [svgDir, pngDir, fontsCss] = process.argv.slice(2);
  if (!svgDir || !pngDir) { console.error('usage: render-graphics.js <svg dir> <png dir> [fonts.css]'); process.exit(2); }
  fs.mkdirSync(pngDir, { recursive: true });
  const opts = process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {};
  const browser = await chromium.launch(opts);
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1 });
  const fontLink = fontsCss
    ? `<style>${fs.readFileSync(fontsCss, 'utf8')}</style>`
    : '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Red+Hat+Display:wght@400;700;800;900&family=Red+Hat+Mono:wght@400;600;700&family=Red+Hat+Text:wght@400;600;700&display=swap">';
  for (const f of fs.readdirSync(svgDir).filter(n => n.endsWith('.svg')).sort()) {
    const svg = fs.readFileSync(path.join(svgDir, f), 'utf8');
    await page.setContent(`<!doctype html><html><head><meta charset="utf-8">${fontLink}<style>html,body{margin:0;background:#fff}svg{width:1280px;height:800px;display:block}text{font-family:"Red Hat Text",system-ui,sans-serif}</style></head><body>${svg}</body></html>`, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(150);
    const out = path.join(pngDir, f.replace(/\.svg$/, '.png'));
    await page.locator('svg').first().screenshot({ path: out });
    console.log('wrote', out);
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
