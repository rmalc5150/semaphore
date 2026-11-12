"""Shared OASIS request pacing across normal collection and S57 workers."""
import fcntl
import time
from research_contract import ROOT


def throttle():
 with (ROOT/'.caiso-request.lock').open('a+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  path=ROOT/'reports/caiso-last-request.txt'
  previous=float(path.read_text()) if path.exists() else 0
  time.sleep(max(0,5-(time.time()-previous)))
  path.write_text(str(time.time()))
