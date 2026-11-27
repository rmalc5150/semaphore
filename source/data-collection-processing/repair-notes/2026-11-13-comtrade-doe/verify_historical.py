"""Read-only validation of early historical inputs and their commit evidence."""
import json
from metadata_engine.runtime_db import Database
from metadata_engine.worker import load_input
from metadata_engine.evidence import evidence_for

cfg = json.load(open('config/metadata-engine.json'));db = Database(cfg)
s3 = db.session.client('s3');base = 'research-data/constellation-backfill/repairs/comtrade-doe-20261113/'
samples = json.loads(s3.get_object(Bucket=cfg['bucket'], Key=base + 'oldest-samples.json')['Body'].read())
results = []
for source, jobs in samples.items():
    for sample in jobs:
        if sample['input_format'] != 'legacy_batch':
            results.append({'source': source, 'job_id': sample['job_id'], 'status': 'excluded_discovery_receipt',
                            'reason': 'Public archive discovery is not a substantive storage document.'})
            continue
        try:
            with db.tx() as c:
                c.execute('SELECT * FROM engine_jobs WHERE job_id=%s', (sample['job_id'],))
                job = c.fetchone()
            rows, raw, manifest = load_input(s3, cfg['bucket'], job, db)
            for row in rows:
                artifacts = evidence_for(row, cfg['contracts'][source], s3, cfg['bucket'])
                info = artifacts[0]['validation']
                results.append({'source': source, 'job_id': job['job_id'], 'status': 'verified',
                                'input_key': job['input_key'], 'record_type': info['record_type'],
                                'source_period': row['payload']['data'].get('trade', row['payload']['data']).get('period'),
                                'extraction_limits': info.get('extraction_limits'),
                                'original_sha256': artifacts[0]['sha256']})
        except Exception as error:
            results.append({'source': source, 'job_id': sample['job_id'], 'status': 'failed',
                            'reason': type(error).__name__ + ': ' + str(error)})
        print(json.dumps(results[-1]), flush=True)
s3.put_object(Bucket=cfg['bucket'], Key=base + 'historical-validation.json',
              Body=json.dumps(results).encode(), ServerSideEncryption='AES256')
assert all(r['status'] != 'failed' for r in results), results
