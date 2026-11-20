#!/usr/bin/env node
// Regenerate the title pyramid from the deck's own renderer (TITLE_LAYERS, TITLE_STR and
// titlePyramidSVG in slides/deck.html), so the frozen copies never drift from the deck.
//
//   node bin/regen-title-pyramid.js en > slides/assets/graphics/title-pyramid.svg   # theme colours made literal (light)
//   node bin/regen-title-pyramid.js en --tokens                                        # var(--token) colours kept, for the console's inline copy
//
// Run from the repository root. The first argument is the language position ('en' or 'es').
const fs=require('fs');const L=fs.readFileSync('slides/deck.html','utf8').split('\n');const a=L.findIndex(l=>l.startsWith('  var TITLE_LAYERS = ['));const b=L.findIndex(l=>l.startsWith('  function titlePyramidSVG()'));let e=b;while(!L[e].startsWith('  }'))e++;const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');let svg=new Function('lang','esc',L.slice(a,e+1).join('\n')+'\nreturn titlePyramidSVG();')(process.argv[2]||'en',esc);if(!process.argv.includes('--tokens')){const LIGHT={'r-judge':'#5B2E91','rb-blue':'#1D4ED8','r-know':'#1E7A55','rb-yellow':'#D99A00','r-info':'#C2410C','r-data':'#CC0000','ink':'#1B1211','ink-2':'#54423E','ink-3':'#7E6A64','border-strong':'#CFC2BE','border':'#E6DDDA','surface-2':'#F4EFED','accent':'#CC0000'};svg=svg.replace(/var\(--([a-z0-9-]+)\)/g,(m,k)=>{if(!(k in LIGHT))throw new Error('no literal for --'+k);return LIGHT[k];});svg='<?xml version="1.0" encoding="UTF-8"?>\n'+svg;}process.stdout.write(svg+'\n');
