"""Dispatch reviewed large daily files through the shared worker lifecycle."""
import argparse,fcntl,json
from pathlib import Path
from constellation.control import Control
from constellation.m7_capture_plan import PUBLIC_FILE_JOBS
from source_pauses import is_paused
from constellation import m7_lifecycle

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--job',choices=sorted(PUBLIC_FILE_JOBS),required=True);args=parser.parse_args();source=PUBLIC_FILE_JOBS[args.job];control=Control()
 if not control.daily_allowed()or is_paused(source):
  print(json.dumps({'status':'daily_capture_paused','source':source}));return 0
 config=json.loads((Path(__file__).resolve().parents[1]/'config/constellation-public-sources.json').read_text());spec=next(r for r in config['sources']if r['source']==source)
 if not spec.get('enabled',True):
  print(json.dumps({'status':'source_disabled','source':source}));return 0
 with (m7_lifecycle.STATE.parent/'m7-lifecycle.lock').open('a')as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);m7_lifecycle.dispatch('optima-m7-capture-'+args.job+'.service')
 return 0

if __name__=='__main__':raise SystemExit(main())
