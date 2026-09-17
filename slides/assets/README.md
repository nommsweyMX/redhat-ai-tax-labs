# Assets

Files dropped here are picked up automatically by the contact slide, the
adventure page and the site build (`slides/assets/` is published at
`/assets/`).

Partner logos — shown as wordmarks until the files exist:

    slides/assets/logo-redhat.svg
    slides/assets/logo-four-inc.svg
    slides/assets/logo-carahsoft.svg

SVG is preferred; keep the filenames exactly as above. Run
`make adventure` after adding them so the catalogue page embeds them too.

## Illustrated graphics (pop-outs)

Drop the full-resolution renders into `graphics/` with these exact
filenames and the deck's pop-outs show them instead of the built-in vector
renditions (nothing else to change):

| file | graphic |
| --- | --- |
| `graphics/choose-your-path.png` | Choose your path. Explore the labs by role, mission, or outcome. |
| `graphics/data-to-judgement.png` | AI foundations for intelligent tax administration. From data to judgement. |
| `graphics/one-foundation.png` | One foundation, from bare metal to the taxpayer. |
| `graphics/filing-lifecycle.png` | Where AI actually lands in the filing lifecycle. |
| `graphics/ffs-portal.png` | AI for Federal Financial Services (the site map). |

`graphics/one-foundation-base.webp` is the unlabeled isometric base of the
architecture graphic and is already checked in; the deck also embeds it.

`graphics/title-pyramid.svg` is the title slide's layered pyramid as the
reveal.js source (`slides/slides.adoc`) shows it. It is generated from the
deck's own renderer (`titlePyramidSVG` in `slides/deck.html`) with the theme
colours made literal; change the layers in the deck, then regenerate it,
rather than editing the file by hand.
PNG or WebP, 1672x941 or any 16:9 render; keep them under 1.5 MB each.
