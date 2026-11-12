"""Check archived SQLite databases using temporary RAM storage, one at a time."""
import hashlib
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tarfile
import tempfile
from datetime import datetime, timezone
import boto3

BUCKET = 'data-collection-059416028963-us-east-1-an'
PREFIX = 'research-data/server-migrations/2026-10-20/ip-172-31-47-178/'


def verify(groups=('root-data', 'ted-package-cache', 'reports')):
    s3 = boto3.client('s3', region_name='us-east-1')
    all_results = []
    for group in groups:
        results = []
        response = s3.get_object(Bucket=BUCKET, Key=PREFIX + group + '.tar.gz')
        try:
            with tarfile.open(fileobj=response['Body'], mode='r|gz') as archive:
                for member in archive:
                    if not member.name.endswith('.sqlite3'):
                        continue
                    checksum = hashlib.sha256()
                    with tempfile.NamedTemporaryFile(dir='/tmp', suffix='.sqlite3') as tmp:
                        source = archive.extractfile(member)
                        with source:
                            while True:
                                chunk = source.read(1024 * 1024)
                                if not chunk:
                                    break
                                tmp.write(chunk)
                                checksum.update(chunk)
                        tmp.flush()
                        try:
                            with closing(sqlite3.connect(Path(tmp.name).as_uri() + '?mode=ro&immutable=1', uri=True)) as db:
                                check = [r[0] for r in db.execute('PRAGMA quick_check')]
                            item = {'member': member.name, 'sha256': checksum.hexdigest(), 'quick_check': check}
                        except Exception as exc:
                            item = {'member': member.name, 'sha256': checksum.hexdigest(), 'error': str(exc)}
                        results.append(item)
                        print('CHECKED', group, member.name, item.get('quick_check', item.get('error')), flush=True)
        finally:
            response['Body'].close()
        report = {'group': group, 'checked_at': datetime.now(timezone.utc).isoformat(), 'results': results}
        body = (json.dumps(report, indent=2) + '\n').encode()
        key = PREFIX + group + '.sqlite-integrity.json'
        s3.put_object(Bucket=BUCKET, Key=key, Body=body, ContentType='application/json', ServerSideEncryption='AES256')
        if s3.get_object(Bucket=BUCKET, Key=key)['Body'].read() != body:
            raise RuntimeError('Verification report readback mismatch')
        all_results.extend(results)
        print('GROUP_COMPLETE', group, len(results), flush=True)
    issues = [r for r in all_results if r.get('quick_check') != ['ok']]
    print('COMPLETE', len(all_results), 'issues', json.dumps(issues), flush=True)
    return 1 if issues else 0


if __name__ == '__main__':
    raise SystemExit(verify())
