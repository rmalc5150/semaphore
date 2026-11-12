"""Independently read back all pilot manifests and raw/parsed objects."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from constellation.control import Control, canonical

ROOT = Path(__file__).resolve().parents[1]


def read(s3, uri):
    bucket, key = uri.removeprefix('s3://').split('/', 1)
    response = s3.get_object(Bucket=bucket, Key=key)
    try:
        return response['Body'].read()
    finally:
        response['Body'].close()


def main():
    pilot = json.loads((ROOT / 'constellation/pilot-receipt.json').read_text())
    control = Control()
    state = control.get('control')
    if state['enabled'] or state['pilot_job_ids']:
        raise RuntimeError('Pilot must have returned collection to paused state')
    summaries = []
    for result in pilot['results']:
        body = read(control.s3, result['result']['manifest_uri'])
        if hashlib.sha256(body).hexdigest() != result['result']['manifest_sha256']:
            raise ValueError('Pilot manifest checksum mismatch')
        manifest = json.loads(body)
        identities = set()
        total = 0
        for page in manifest['pages']:
            for field in ('raw', 'records'):
                artifact = read(control.s3, page[field]['uri'])
                if hashlib.sha256(artifact).hexdigest() != page[field]['sha256'] or len(artifact) != page[field]['bytes']:
                    raise ValueError('Pilot artifact checksum/size mismatch')
                if field == 'records':
                    records = [json.loads(line) for line in artifact.splitlines()]
                    if len(records) != page['record_count']:
                        raise ValueError('Pilot page count mismatch')
                    for record in records:
                        if record['source_key'] != result['source_key'] or record['available_to_market_at'] is not None:
                            raise ValueError('Invalid source identity or unsupported historical availability assertion')
                        if record['source_record_id'] in identities:
                            raise ValueError('Duplicate record across pilot pages')
                        identities.add(record['source_record_id'])
                    total += len(records)
        if total != manifest['records'] or total != result['result']['records'] or not manifest['pagination_exhausted']:
            raise ValueError('Pilot manifest record count or pagination mismatch')
        summaries.append({'source_key': result['source_key'], 'records': total, 'pages': len(manifest['pages']),
            'manifest_uri': result['result']['manifest_uri'], 'historical_vintage_verified': False})
    receipt = {'checked_at': datetime.now(timezone.utc).isoformat(), 'status': 'verified',
        'bulk_collection_enabled': False, 'results': summaries, 'total_records': sum(r['records'] for r in summaries)}
    (ROOT / 'constellation/pilot-verification.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
