"""Serialize bounded capture passes within the shared m7 memory envelope."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from constellation.m7_capture_plan import JOBS

BASE=Path('/opt/constellation/capture-workers')
def pool_memory_path():
    entry=next(line.split(':',2)[2]for line in Path('/proc/self/cgroup').read_text().splitlines()if line.startswith('0::'))
    path=Path('/sys/fs/cgroup')/entry.lstrip('/')
    for parent in (path,*path.parents):
        if parent.name=='constellation-workers.slice':return parent/'memory.current'
    raise RuntimeError('Capture must run inside constellation-workers.slice')

def wait_for_memory(path,threshold=int(4.5*1024**3),seconds=900):
    deadline=time.monotonic()+seconds
    while int(path.read_text())>threshold:
        if time.monotonic()>=deadline:return False
        time.sleep(2)
    return True

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--job',choices=sorted(JOBS),required=True);args=parser.parse_args()
    BASE.mkdir(exist_ok=True)
    with (BASE/'capture.lock').open('a')as lock:
        print(json.dumps({'stage':'waiting_for_capture_slot','job':args.job}),flush=True)
        fcntl.flock(lock,fcntl.LOCK_EX)
        if not wait_for_memory(pool_memory_path()):
            print(json.dumps({'status':'deferred','reason':'worker_pool_memory_busy','job':args.job}),flush=True);return 75
        print(json.dumps({'stage':'capture_started','job':args.job}),flush=True)
        return subprocess.call(['/usr/bin/timeout','--signal=INT','--kill-after=120s','15m',sys.executable,'-B',*JOBS[args.job]])

if __name__=='__main__':raise SystemExit(main())
