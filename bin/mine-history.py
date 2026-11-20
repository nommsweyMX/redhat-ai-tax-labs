#!/usr/bin/env python3
"""Mine the repository's own history for the how-it-was-built talk.

    python3 bin/mine-history.py --ref origin/main --out slides/how-it-was-built-history.json

For every commit on the ref, oldest first, record the date, the subject and a few sizes
that the growth graphics plot: deck bytes, slide count, lab count, inline SVG count,
Spanish string count, presenter-console section count and the file count. Everything is
read from the tree at that commit, so the numbers can be checked by anyone with a clone."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


def git(*args: str) -> str:
    return subprocess.run(['git', *args], check=True, capture_output=True, text=True).stdout


def show(sha: str, path: str) -> str:
    r = subprocess.run(['git', 'show', f'{sha}:{path}'], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ''


def tree(sha: str) -> list[str]:
    return git('ls-tree', '-r', '--name-only', sha).split()


def metrics(sha: str) -> dict:
    deck = show(sha, 'slides/deck.html')
    console = show(sha, 'slides/presenter-notes.html')
    files = tree(sha)
    return {
        'deck_kb': round(len(deck.encode('utf-8')) / 1024),
        'slides': len(re.findall(r'<section class="slide\b|<section\s+class="slide ', deck)) or len(re.findall(r'class="slide[ "]', deck)),
        'labs': len([f for f in files if re.match(r'labs/lab\d+[^/]*/run\.sh$', f)]),
        'svgs': len(re.findall(r'<svg\b', deck)),
        'es_keys': len(re.findall(r'^\s*"[^"\n]+"\s*:\s*"', deck[deck.find('ES_TEXT'):], re.M)) if 'ES_TEXT' in deck else 0,
        'console_sections': len(re.findall(r'<section\b', console)),
        'files': len(files),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--ref', default='origin/main')
    ap.add_argument('--out', type=Path, default=Path('slides/how-it-was-built-history.json'))
    a = ap.parse_args()
    first_parent = set(git('rev-list', '--first-parent', a.ref).split())
    rows = []
    for line in git('log', '--reverse', '--date=iso-strict', '--format=%H%x09%ad%x09%s', a.ref).splitlines():
        sha, date, subject = line.split('\t', 2)
        m = metrics(sha)
        # first_parent marks the commits that are the state of the branch itself (merges and direct
        # commits), as opposed to work on a side branch before it merged; growth is plotted on those.
        rows.append({'sha': sha[:7], 'date': date[:10], 'time': date[11:16], 'tz': date[19:], 'subject': subject,
                     'first_parent': sha in first_parent, **m})
    out = {
        '_comment': f'Mined from git log {a.ref} by bin/mine-history.py; sizes are read from the tree at each commit.',
        'ref': a.ref, 'commits': rows,
    }
    a.out.write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {a.out}: {len(rows)} commits, {rows[0]["date"]} to {rows[-1]["date"]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
