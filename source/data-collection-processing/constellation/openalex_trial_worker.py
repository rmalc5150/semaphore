"""Run the temporary Arm worker's OpenAlex and OpenDART jobs serially."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

SOURCE = 'openalex_scholarly_graph'
ROOT = Path(__file__).resolve().parents[1]
WINDOW = Path('/opt/constellation/trial-window')
STATE = Path('/opt/constellation/tmp/openalex-trial-tasks.json')
HANDOFF = Path('/opt/constellation/openalex-trial-ready')
SNAPSHOT_HANDOFF = Path('/opt/constellation/openalex-trial-snapshot-ready')
METADATA_PAUSE = Path('/opt/constellation/metadata-processing-paused')


def time_left():
    try:
        return int(WINDOW.read_text()) - time.time()
    except (OSError, ValueError):
        return 0


def execute(module, *arguments):
    if module.startswith('metadata_engine.') and METADATA_PAUSE.exists():
        return 0
    command = [sys.executable, '-B', '-m', module, *arguments]
    return subprocess.run(command, cwd=ROOT, timeout=900).returncode


def release(exact=None):
    if METADATA_PAUSE.exists():
        return
    from metadata_engine.controller import publish
    from metadata_engine.runtime_db import Database

    config = json.loads((ROOT / 'config/metadata-engine.json').read_text())
    count = publish(Database(config), source_key=SOURCE, job_ids=exact)
    print(json.dumps({'source': SOURCE, 'published_batches': count}), flush=True)


def due(state, name, interval, time_budget, fn, *, trial_limited=True):
    now = time.time()
    if now - state.get(name, 0) < interval or (trial_limited and time_left() < time_budget):
        return
    try:
        status = fn()
        if status:
            print(json.dumps({'trial_task': name, 'exit_status': status}), flush=True)
    except Exception as error:
        print(json.dumps({'trial_task': name, 'error': type(error).__name__, 'detail': str(error)[:180]}), flush=True)
    finally:
        state[name] = time.time()
        temporary = STATE.with_suffix('.tmp')
        temporary.write_text(json.dumps(state))
        temporary.replace(STATE)


def run_metadata(state):
    if HANDOFF.exists() and time_left() > 330:
        execute('metadata_engine.worker', '--source', SOURCE, '--max-jobs', '12', '--max-seconds', '125')
        if time_left() > 200:
            execute('metadata_engine.streaming_worker', '--source', SOURCE, '--max-jobs', '1')
    due(state, 'dart_originals', 420, 480, lambda: execute(
        'metadata_engine.dart_repair_queue', '--max-receipts', '4', '--max-seconds', '120'))
    due(state, 'dart_streaming', 420, 420, lambda: execute(
        'metadata_engine.streaming_worker', '--lane', 'opendart', '--max-jobs', '4'))
    if HANDOFF.exists():
        due(state, 'openalex_publication', 300, 180, release)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish-exact')
    args = parser.parse_args()
    if args.publish_exact:
        if METADATA_PAUSE.exists():
            print(json.dumps({'status': 'metadata_processing_paused'}), flush=True)
            return 2
        release([args.publish_exact])
        return 0
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    if not METADATA_PAUSE.exists():
        run_metadata(state)
    if SNAPSHOT_HANDOFF.exists():
        from constellation.trial_historical_access import configured_for
        due(state, 'openalex_snapshot', 1800, 2400, lambda: execute(
            'constellation.research_feeds', SOURCE, 'historical', '--budget', '1'),
            trial_limited=not configured_for(SOURCE))


if __name__ == '__main__':
    raise SystemExit(main())
