#!/usr/bin/env python3
"""Run bounded personnel-source capture and archive retrieval independently."""
import json
import argparse
from pathlib import Path
import subprocess
import sys


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lane', choices=['daily','historical','all'], default='all')
    parser.add_argument('--publish',action='store_true',help='Opt in to inline publication on a worker; normal capture queues publication for m7')
    args=parser.parse_args(argv)
    root = Path(__file__).resolve().parent
    outcomes = []
    for name, arguments in [('feeds', ['people_social_collection.py', '--feeds-only']),
                            ('archives', ['personnel_archive.py', '--max-windows', '8']),
                            ('publication', ['research_publication.py', '--owners', 'people', '--max-windows', '12'])]:
        if name=='publication'and not args.publish:continue
        if args.lane == 'historical' and name != 'archives':continue
        if name == 'archives' and args.lane != 'all':arguments += ['--mode',args.lane]
        result = subprocess.run([sys.executable, '-B', *arguments], cwd=root)
        outcomes.append({'lane': name, 'exit_code': result.returncode})
    print(json.dumps({'lanes': outcomes}), flush=True)
    return int(any(row['exit_code'] not in {0, 2} for row in outcomes))


if __name__ == '__main__':
    raise SystemExit(main())
