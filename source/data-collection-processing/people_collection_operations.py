#!/usr/bin/env python3
"""Run bounded personnel-source capture and archive retrieval independently."""
import json
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parent
    outcomes = []
    for name, arguments in [('feeds', ['people_social_collection.py', '--feeds-only']),
                            ('archives', ['personnel_archive.py', '--max-windows', '8']),
                            ('publication', ['research_publication.py', '--owners', 'people', '--max-windows', '12'])]:
        result = subprocess.run([sys.executable, '-B', *arguments], cwd=root)
        outcomes.append({'lane': name, 'exit_code': result.returncode})
    print(json.dumps({'lanes': outcomes}), flush=True)
    return int(any(row['exit_code'] not in {0, 2} for row in outcomes))


if __name__ == '__main__':
    raise SystemExit(main())
