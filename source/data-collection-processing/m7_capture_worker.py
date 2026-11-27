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
LANES={'large':1,'light':4}
LARGE_JOBS={'edinet-documents-daily'}

def lane_for(job):
    return 'large' if job in LARGE_JOBS else 'light'

def memory_admission_threshold(job):
    # The resized capture slice has a 20 GiB hard cap.  A new payload is not
    # admitted once the pool is close to that cap; its lane lock then bounds
    # the remaining concurrent payloads to one large or two light jobs.
    return int(17*1024**3)

def pool_memory_path():
    entry=next(line.split(':',2)[2]for line in Path('/proc/self/cgroup').read_text().splitlines()if line.startswith('0::'))
    path=Path('/sys/fs/cgroup')/entry.lstrip('/')
    for parent in (path,*path.parents):
        if parent.name=='constellation-workers-capture.slice':return parent/'memory.current'
        if parent.name=='constellation-workers.slice':return parent/'memory.current'
    raise RuntimeError('Capture must run inside constellation-workers.slice')

def wait_for_memory(path,threshold=int(4.5*1024**3),seconds=900):
    deadline=time.monotonic()+seconds
    while int(path.read_text())>threshold:
        if time.monotonic()>=deadline:return False
        time.sleep(2)
    return True

def acquire_lane_slot(lane, deadline):
    """Claim an available bounded lane without serializing unrelated work."""
    locks=[]
    while time.monotonic()<deadline:
        for number in range(LANES[lane]):
            lock=(BASE/(f'capture-{lane}-{number}.lock')).open('a')
            try:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                return lock
            except BlockingIOError:
                lock.close()
        time.sleep(1)
    return None

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--job',choices=sorted(JOBS),required=True);args=parser.parse_args()
    BASE.mkdir(exist_ok=True)
    lane=lane_for(args.job)
    print(json.dumps({'stage':'waiting_for_capture_slot','job':args.job,'lane':lane}),flush=True)
    path=pool_memory_path();threshold=memory_admission_threshold(args.job);deadline=time.monotonic()+900
    if not wait_for_memory(path,threshold=threshold,seconds=max(0,deadline-time.monotonic())):
        print(json.dumps({'status':'deferred','reason':'worker_pool_memory_busy','job':args.job}),flush=True);return 75
    lock=acquire_lane_slot(lane,deadline)
    if lock is None:
        print(json.dumps({'status':'deferred','reason':'capture_lane_busy','job':args.job,'lane':lane}),flush=True);return 75
    with lock:
        # A wait for a lane does not reserve memory.  Recheck after the claim
        # so the hard slice cap remains the final backstop under races.
        if int(path.read_text())>threshold:
            print(json.dumps({'status':'deferred','reason':'worker_pool_memory_busy','job':args.job}),flush=True);return 75
        print(json.dumps({'stage':'capture_started','job':args.job,'lane':lane}),flush=True)
        return subprocess.call(['/usr/bin/timeout','--signal=INT','--kill-after=120s','15m',sys.executable,'-B',*JOBS[args.job]])

if __name__=='__main__':raise SystemExit(main())
