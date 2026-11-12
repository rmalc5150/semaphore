#!/usr/bin/env python3
"""Guarded maintenance steps. Never stops/resizes the EC2 instance itself."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
STATE = HERE / 'maintenance-state.json'
MARKER = HERE / 'maintenance-active'
READY = HERE / 'ready-to-stop.json'
GIB = 1024**3
GUARD = 'zz-upgrade-maintenance.conf'
LIMIT = 'zz-t3-large-memory.conf'

def command(*args):
    return subprocess.check_output(args, text=True).strip()

def ctl(*args):
    return command('sudo', 'systemctl', *args)

def properties(unit):
    return dict(line.split('=', 1) for line in ctl('show', unit, '-p', 'ActiveState', '-p', 'UnitFileState', '-p', 'Unit').splitlines() if '=' in line)

def units():
    rows = ctl('list-unit-files', 'optima*.timer', 'ec2-code-backup.timer', '--no-legend', '--no-pager').splitlines()
    timers = {r.split()[0]: properties(r.split()[0]) for r in rows if r.strip()}
    workers = sorted({p.get('Unit') or name.replace('.timer','.service') for name,p in timers.items()})
    return timers, workers

def save(path, value):
    temp = path.with_suffix('.pending')
    temp.write_text(json.dumps(value, indent=2) + '\n')
    with temp.open('r') as handle: os.fsync(handle.fileno())
    temp.replace(path)

def install(unit, name, body):
    path = Path('/etc/systemd/system') / (unit + '.d') / name
    staged = HERE / (unit + '.' + name)
    staged.write_text(body)
    if path.exists() and not (HERE / (unit + '.' + name + '.before')).exists():
        (HERE / (unit + '.' + name + '.before')).write_text(path.read_text())
    command('sudo', 'mkdir', '-p', str(path.parent))
    command('sudo', 'install', '-m', '644', str(staged), str(path))

def hardware_ok(kind, memory_bytes):
    return kind == 't3.large' and memory_bytes >= 7 * GIB

def hardware():
    kind = Path('/sys/devices/virtual/dmi/id/product_name').read_text().strip()
    memory = int(next(l for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemTotal:')).split()[1]) * 1024
    return kind, memory

def verify_index():
    # Verify the current pointer against its immutable manifest, without loading
    # all historic state payloads into memory. Runtime verified each upload.
    sys.path.insert(0, str(ROOT))
    import boto3
    from s3_runtime import read_index, BUCKET, PREFIX
    s3 = boto3.client('s3', region_name='us-east-1')
    state, etag = read_index(s3)
    if not etag or not state.get('run_id'): raise RuntimeError('No durable runtime checkpoint')
    response = s3.get_object(Bucket=BUCKET, Key=PREFIX+'/manifests/'+state['run_id']+'.json')
    with response['Body'] as body: manifest = json.loads(body.read())
    if manifest != state: raise RuntimeError('Runtime pointer/manifest mismatch')
    return {'run_id':state['run_id'], 'checkpointed_at':state['checkpointed_at'], 'paths':len(state['paths']), 'etag':etag}

def quiesce():
    if STATE.exists() and not MARKER.exists():
        raise RuntimeError('Prior maintenance state exists; archive it before a new maintenance session')
    READY.unlink(missing_ok=True)
    if not STATE.exists():
        timers, workers = units()
        save(STATE, {'created_at':datetime.now(timezone.utc).isoformat(), 'timers':timers, 'workers':workers})
    state = json.loads(STATE.read_text())
    MARKER.touch()
    # Persistent guard also prevents enabled services restarting after the resize,
    # until the operator has checked hardware and applied limits.
    for unit in state['workers']:
        install(unit, GUARD, '[Unit]\nConditionPathExists=!' + str(MARKER) + '\n')
    ctl('daemon-reload')
    timers = list(state['timers'])
    if timers: ctl('stop', *timers)
    # Graceful service stop invokes existing SIGINT/checkpoint handling. Do not
    # reset failed state or delete RAM when a checkpoint cannot be verified.
    ctl('stop', *state['workers'])
    active = [u for u in state['workers'] if properties(u).get('ActiveState') not in ('inactive','failed')]
    if active: raise RuntimeError('Workers still active: ' + ', '.join(active))
    # Recover any interrupted worker's retained RAM using the existing runtime.
    # Both locks are required; its compare-and-swap detects concurrent changes.
    command('/usr/bin/flock', '--exclusive', '--timeout', '60', '/dev/shm/optima-s3/supervisor.lock',
            str(ROOT/'.venv-athena/bin/python'), '-B', str(ROOT/'s3_runtime.py'),
            '--unit', 'upgrade-checkpoint', '--', '/usr/bin/true')
    if Path('/dev/shm/optima-s3/pending.json').exists(): raise RuntimeError('Uncheckpointed RAM remains')
    evidence = verify_index()
    save(READY, {'status':'ready_to_stop', 'checked_at':datetime.now(timezone.utc).isoformat(), 'checkpoint':evidence})
    print(json.dumps({'status':'ready_to_stop','evidence':str(READY)}))

def apply():
    kind, memory = hardware()
    if not hardware_ok(kind, memory): raise RuntimeError('Requires t3.large with at least 7 GiB visible RAM; limits unchanged')
    if not MARKER.exists() or not READY.exists(): raise RuntimeError('Verified maintenance checkpoint required')
    state = json.loads(STATE.read_text())
    for unit in state['workers']:
        if properties(unit).get('ActiveState') not in ('inactive','failed'):
            raise RuntimeError('Worker active during maintenance: ' + unit)
    install('optima-data.slice', LIMIT, '[Slice]\nMemoryHigh=5G\nMemoryMax=6G\nMemorySwapMax=0\n')
    # One heavy worker at a time. Leave the independent health monitor and code
    # backup limits intact. Allow space under the shared 6 GiB cap for overhead.
    changed=[]
    for unit in state['workers']:
        dropin=Path('/etc/systemd/system')/(unit+'.d')/'99-s3-runtime.conf'
        if unit.startswith('optima-') and dropin.exists() and 's3_runtime.py' in dropin.read_text():
            install(unit, LIMIT, '[Service]\nMemoryHigh=4G\nMemoryMax=5G\nMemorySwapMax=0\n')
            changed.append(unit)
    ctl('daemon-reload')
    if ctl('show','optima-data.slice','-p','MemoryMax','--value') != str(6*GIB):
        raise RuntimeError('Shared limit did not take effect')
    for unit in changed:
        if ctl('show',unit,'-p','MemoryMax','--value') != str(5*GIB):
            raise RuntimeError('Worker limit did not take effect: '+unit)
    save(HERE/'limits-applied.json', {'instance_type':kind,'memory_bytes':memory,'shared_max_bytes':6*GIB,'workers':changed})
    print('Memory limits verified. Maintenance remains active; run resume next.')

def resume():
    if not STATE.exists(): raise RuntimeError('No saved maintenance state')
    # Also serves as abort-before-resize: old limits stay intact on t3.medium.
    kind,_=hardware()
    if kind == 't3.large' and not (HERE/'limits-applied.json').exists():
        raise RuntimeError('Apply and verify t3.large limits first')
    state=json.loads(STATE.read_text())
    MARKER.unlink(missing_ok=True)
    # Empty condition becomes true when marker is absent; retain the guard for
    # reuse without changing normal activation semantics.
    for timer, prior in state['timers'].items():
        if prior.get('ActiveState') == 'active': ctl('restart',timer)
    ctl('start','--no-block','optima-collection-health.service')
    READY.unlink(missing_ok=True)
    print('Previously active timers resumed; verify collection and Athena receipts.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['inspect','quiesce','apply','resume'])
    args=parser.parse_args()
    with (HERE/'operator.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.action=='inspect':
            kind,memory=hardware();timers,workers=units()
            print(json.dumps({'instance_type':kind,'memory_bytes':memory,'active_timers':sum(p.get('ActiveState')=='active' for p in timers.values()),'workers':len(workers),'maintenance':MARKER.exists(),'hardware_ready_for_limits':hardware_ok(kind,memory)},indent=2))
        else: globals()[args.action]()

if __name__=='__main__': main()
