"""Release exactly three historical-day pilots, then clear the pilot allowlist."""
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from constellation.control import Control, TERMINAL
from constellation.sources import PROVIDERS, VERSION


def main():
    control = Control()
    state = control.get('control')
    if state['enabled'] or state['pilot_job_ids']:
        raise RuntimeError('Run only while the bulk queue is paused')
    identities = []
    for source in PROVIDERS:
        identities.append(control.register({'source_key': source, 'dataset': PROVIDERS[source]['dataset'],
            'geography': 'global', 'start': '2016-01-04', 'end': '2016-01-05',
            'edition': 'current_retrieval', 'extractor_version': VERSION, 'parameters': {}}))
    results = []
    try:
        control.set_enabled(False, identities)
        deadline = time.monotonic() + 180
        previous = None
        while time.monotonic() < deadline:
            results = [control.get('job#' + identity) for identity in identities]
            statuses = [row['status'] for row in results]
            if statuses != previous:
                print(json.dumps({'pilot_statuses': statuses}), flush=True)
                previous = statuses
            if all(status in TERMINAL for status in statuses):
                break
            if any(status in {'retryable_failed', 'blocked'} for status in statuses):
                raise RuntimeError('Pilot failure: inspect retained job evidence before retrying')
            time.sleep(3)
        if not all(row['status'] == 'succeeded' for row in results):
            raise RuntimeError('Pilot deadline exceeded; collection is paused again')
        receipt = {'checked_at': datetime.now(timezone.utc).isoformat(), 'bulk_collection_enabled': False,
            'results': [{'job_id': r['job_id'], 'source_key': r['source_key'], 'status': r['status'],
                'attempts': r['attempts'], 'worker_id': r['worker_id'],
                'result': json.loads(r['result_json'])} for r in results]}
        (Path(__file__).resolve().parent / 'pilot-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps(receipt), flush=True)
    finally:
        control.set_enabled(False, [])


if __name__ == '__main__':
    main()
