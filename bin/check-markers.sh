#!/usr/bin/env bash
# Old-mission and old-event markers that must be gone after a retarget (methods pages excluded: they are history).
# Usage: check-markers.sh <repo-root> [extra regex]
cd "$1" || exit 2
EXTRA="${2:-}"
PAT='taxpayer|filing[- ]season|filing lifecycle|\bIRS\b|\bFTI\b|Carahsoft|Four Inc|Scalio|Keam|Ted Craig|bscalio|jkeam|September 17|tax administration|tax agenc|tax-inference|tax-classifier|granite-8b-tax-v1|tax_guidance|tax-loop|CR-8841|CP2000|CP14|Form 8822|agency\.gov|redhat-ai-tax|nommsweymx'
[[ -n "$EXTRA" ]] && PAT="$PAT|$EXTRA"
git grep -n -i -E "$PAT" -- . \
  ':!slides/how-it-was-built*' ':!docs/95-*' ':!docs/96-*' ':!slides/assets/graphics/built' ':!bin/build-brief.py' ':!bin/mine-history.py' ':!LICENSE' \
  | cut -c1-140
n=$(git grep -c -i -E "$PAT" -- . ':!slides/how-it-was-built*' ':!docs/95-*' ':!docs/96-*' ':!slides/assets/graphics/built' ':!bin/build-brief.py' ':!bin/mine-history.py' ':!LICENSE' | awk -F: '{s+=$2} END{print s+0}')
echo "lines still carrying old-mission markers: $n"
[[ "$n" -eq 0 ]]
