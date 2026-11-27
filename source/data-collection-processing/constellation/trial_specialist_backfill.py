"""Run delegated historical collectors with the existing priority lanes first."""
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from constellation.trial_historical_access import OPENDART, OPENDART_OWNER

ROOT = Path('/opt/constellation')
SOURCES = {'imf_portwatch_shipping_activity': (3, 150),
           'copernicus_era5_era5_land': (1, 210)}  # pages, minimum seconds between runs
SLICE_SECONDS = 100
CONTENDED_GRACE = 12
GUARD_SECONDS = 220
STATE = ROOT / 'tmp/trial-specialist-progress.json'
HANDOFF = ROOT / 'trial-specialists/assigned.json'
PRIORITY = ROOT / 'tmp/openalex-trial-tasks.json'
PRIORITY_INTERVAL = 1800
OPENDART_INTERVAL = 40
OPENDART_PAGES = 16  # The OpenDART collector converts this to two eight-filing commits.


def read(path):
    return json.loads(path.read_text()) if path.is_file() else {}


def snapshot_busy():
    # The arm dispatcher runs frequently even when it has no work. Check for its
    # real historical subprocess, not for the periodic launcher itself.
    cgroup = Path('/sys/fs/cgroup/system.slice/optima-opendart-arm.service/cgroup.procs')
    try:
        pids = cgroup.read_text().split()
    except FileNotFoundError:
        return False
    for pid in pids:
        try:
            args = (Path('/proc') / pid / 'cmdline').read_bytes().split(b'\0')
        except FileNotFoundError:
            continue
        except PermissionError:
            return True
        if (b'constellation.research_feeds' in args or
                any(arg.startswith(b'metadata_engine.') for arg in args)):
            return True
    return False


def priority_window(now, priority, trial_until, mem_mib, busy):
    last = priority.get('openalex_snapshot')
    # An unknown or overdue priority schedule is not idle capacity.
    return (not busy and mem_mib >= 850 and isinstance(last, (int, float))
            and last <= now < last + PRIORITY_INTERVAL - GUARD_SECONDS
            and now + GUARD_SECONDS < trial_until)


def read_trial_schedule():
    mem = next(int(line.split()[1]) // 1024 for line in Path('/proc/meminfo').read_text().splitlines()
               if line.startswith('MemAvailable:'))
    from constellation.trial_historical_access import configured_for
    until = float('inf') if all(configured_for(source) for source in SOURCES) else int((ROOT / 'trial-window').read_text())
    return read(PRIORITY), until, mem


def can_start():
    return ((ROOT / 'openalex-trial-snapshot-ready').is_file()
            and (ROOT / 'metadata-processing-paused').is_file()
            and not (ROOT / 'batch-paused').exists()
            and priority_window(time.time(), *read_trial_schedule(), snapshot_busy()))


def run_scoped(source, cwd, *, prefer_bridge=False, yield_at=None):
    unit = 'constellation-specialist-' + source + '.service'
    env = dict(os.environ, CONSTELLATION_ROLE='worker', CONSTELLATION_SHARED_HTTP_LIMITS='1',
               PYTHONPATH=str(cwd) + ':' + str(ROOT / 'trial-specialists/deps'),
               AWS_DEFAULT_REGION='us-east-1', PYTHONDONTWRITEBYTECODE='1',
               CONSTELLATION_SPECIALIST_PREFER_INFLIGHT='1',
               CONSTELLATION_SPECIALIST_MODE='historical',
               CONSTELLATION_SPECIALIST_PLAN=str(cwd / 'config/constellation-specialist-historical.json'),
               CONSTELLATION_SPECIALIST_SCHEDULER_PREFIX='constellation-backfill/specialist-schedulers/' + unit,
               CONSTELLATION_SPECIALIST_DISCOVERY_PREFIX='constellation-backfill/specialist-discovered-jobs/',
               CONSTELLATION_SPECIALIST_PUBLICATION_PREFIX='constellation-backfill/specialist-publication-queue/',
               CONSTELLATION_OPERATION_RECEIPT_PREFIX='constellation-backfill/legacy-operation-receipts/' + unit)
    if source=='copernicus_era5_era5_land':
        env['PYTHONPATH'] += ':' + str(ROOT/'trial-specialists/netcdf-deps')
        env['CONSTELLATION_CDS_VERIFY_NETCDF']='1'
        if (ROOT/'trial-specialists/cds-retrieve-only').is_file():
            env['CONSTELLATION_CDS_RETRIEVE_ONLY']='1'
    if source == OPENDART and prefer_bridge:
        env['CONSTELLATION_OPENDART_PREFER_BRIDGE'] = '1'
    pages = OPENDART_PAGES if source == OPENDART else SOURCES[source][0]
    argv = [sys.executable, '-B', 'specialist_inputs.py', '--mode', 'historical', '--lane', 'default',
            '--source', source, '--max-jobs', '1', '--pages', str(pages), '--publish', '0']
    process = subprocess.Popen(argv, cwd=cwd, env=env, start_new_session=True)
    end = time.monotonic() + SLICE_SECONDS
    reason = None
    while process.poll() is None:
        if snapshot_busy() or not HANDOFF.is_file():
            reason = 'yielded_to_priority'
        elif source == OPENDART and (not OPENDART_OWNER.is_file()
                                    or yield_at is not None and time.time() >= yield_at):
            reason = 'yielded_to_existing_history'
        elif time.monotonic() >= end:
            reason = 'bounded_slice_finished'
        if reason:
            try:
                os.killpg(process.pid, signal.SIGINT)
            except ProcessLookupError:
                process.wait()
                break
            try:
                process.wait(timeout=CONTENDED_GRACE)
            except subprocess.TimeoutExpired:
                try:os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:pass
                process.wait(timeout=5)
            break
        time.sleep(1)
    print(json.dumps({'source': source, 'status': reason or 'invocation_finished',
                      'exit_code': process.returncode}), flush=True)


def select_source(state, unpaused, now, opendart_ready):
    priority_due = {s: state.get(s, 0) + SOURCES[s][1] for s in unpaused}
    due = [s for s, at in priority_due.items() if now >= at]
    if due:
        return min(due, key=lambda s: (state.get(s, 0), s)), None
    next_due = min(priority_due.values(), default=float('inf'))
    if (opendart_ready and now >= state.get(OPENDART, 0) + OPENDART_INTERVAL
            and next_due - now >= 15):
        return OPENDART, next_due
    return None, None


def main():
    from constellation.control import Control
    from constellation.trial_historical_access import allowed as historical_allowed
    from source_pauses import is_paused

    if not HANDOFF.is_file() or not can_start():
        return
    control = Control()
    scope = read(HANDOFF)
    if set(scope.get('sources', ())) != set(SOURCES):
        raise ValueError('Wrong delegated source scope')
    with (ROOT / 'tmp/trial-specialists.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        state = read(STATE)
        now = time.time()
        unpaused = {s for s in SOURCES if not is_paused(s)}
        dart_ready = OPENDART_OWNER.is_file() and not is_paused(OPENDART)
        source, yield_at = select_source(state, unpaused, now, dart_ready)
        if not source or not can_start():
            return
        if not historical_allowed(control, source):
            return
        trial = ROOT / 'trial-specialists'
        dart_runs = int(state.get('opendart_invocations', 0))
        try:
            if source == OPENDART:
                run_scoped(source, trial / 'opendart-current', prefer_bridge=dart_runs % 3 == 2,
                           yield_at=yield_at)
            else:
                run_scoped(source, trial / 'current' / source)
        finally:
            state[source] = time.time()
            if source == OPENDART:
                state['opendart_invocations'] = dart_runs + 1
            tmp = STATE.with_suffix('.new')
            tmp.write_text(json.dumps(state) + '\n')
            tmp.replace(STATE)


if __name__ == '__main__':
    main()
