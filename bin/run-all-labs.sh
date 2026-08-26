#!/usr/bin/env bash
# Walk every lab end to end. Used by CI as a smoke test and by facilitators
# rehearsing the session.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

: "${LAB_MODE:=simulate}"
export LAB_MODE

failed=0
for script in labs/lab*/run.sh; do
  lab="$(basename "$(dirname "$script")")"
  printf '\n>>> %s\n' "$lab"
  ( cd "$(dirname "$script")" && bash run.sh ) || {
    printf '!!! %s exited %d\n' "$lab" "$?"
    failed=$((failed + 1))
  }
done

if [[ $failed -gt 0 ]]; then
  printf '\n%d lab(s) failed.\n' "$failed"
  exit 1
fi
printf '\nAll labs completed.\n'
