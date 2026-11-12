"""Promote verified migration state into lazily readable native S3 objects."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import tarfile
import boto3
from s3_runtime import BUCKET, PREFIX, CURRENT, CONFIG, put_verified_json, read_index

ARCHIVES = 'research-data/server-migrations/2026-10-20/ip-172-31-47-178/'


class Stream:
    """Intentionally non-seekable: tar member data is uploaded with bounded RAM."""
    def __init__(self, source):
        self.source = source
        self.sha256 = hashlib.sha256()
        self.size = 0
    def read(self, amount=-1):
        value = self.source.read(amount)
        self.sha256.update(value)
        self.size += len(value)
        return value


def main():
    s3 = boto3.client('s3', region_name='us-east-1')
    try:
        s3.head_object(Bucket=BUCKET, Key=CURRENT)
    except s3.exceptions.ClientError as exc:
        if exc.response['Error']['Code'] not in {'404', 'NoSuchKey'}:
            raise
    else:
        print('Runtime already seeded; retaining current checkpoint', flush=True)
        return
    paths = {}
    for group in ('root-data', 'reference-data', 'reports'):
        receipt = json.loads(s3.get_object(Bucket=BUCKET, Key=ARCHIVES + group + '.result.json')['Body'].read())
        assert receipt['full_s3_readback_verified']
        response = s3.get_object(Bucket=BUCKET, Key=ARCHIVES + group + '.tar.gz')
        try:
            with tarfile.open(fileobj=response['Body'], mode='r|gz') as archive:
                for member in archive:
                    if member.islnk():
                        if member.linkname not in paths:
                            raise ValueError('Unresolved archive hardlink: ' + member.name)
                        paths[member.name] = dict(paths[member.linkname])
                        continue
                    if not member.isfile():
                        continue
                    if member.name.startswith('/') or '..' in member.name.split('/'):
                        raise ValueError('Unsafe archived path')
                    key = PREFIX + '/snapshots/migration-seed/' + member.name
                    source = Stream(archive.extractfile(member))
                    s3.upload_fileobj(source, BUCKET, key, ExtraArgs={'ServerSideEncryption': 'AES256'}, Config=CONFIG)
                    if source.size != member.size:
                        raise ValueError('Seed size mismatch')
                    remote = hashlib.sha256()
                    count = 0
                    downloaded = s3.get_object(Bucket=BUCKET, Key=key)
                    with closing(downloaded['Body']) as handle:
                        for chunk in handle.iter_chunks(chunk_size=1024 * 1024):
                            remote.update(chunk)
                            count += len(chunk)
                    if (remote.hexdigest(), count) != (source.sha256.hexdigest(), member.size):
                        raise ValueError('Seed readback mismatch: ' + member.name)
                    paths[member.name] = {'key': key, 'sha256': source.sha256.hexdigest(), 'bytes': member.size}
                    if len(paths) % 100 == 0 or member.size > 100 * 1024**2:
                        print(json.dumps({'seeded': len(paths), 'latest': member.name, 'bytes': member.size}), flush=True)
        finally:
            response['Body'].close()
        print('SEEDED_GROUP', group, len(paths), flush=True)
    state = {'schema_version': 1, 'paths': paths, 'run_id': 'migration-seed',
             'checkpointed_at': datetime.now(timezone.utc).isoformat(), 'source': ARCHIVES}
    put_verified_json(s3, PREFIX + '/manifests/migration-seed.json', state, create=True)
    put_verified_json(s3, CURRENT, state, create=True)
    print(json.dumps({'status': 'seed_verified', 'paths': len(paths), 'bytes': sum(p['bytes'] for p in paths.values())}), flush=True)


def repair_aliases():
    s3 = boto3.client('s3', region_name='us-east-1')
    state, etag = read_index(s3)
    added = 0
    response = s3.get_object(Bucket=BUCKET, Key=ARCHIVES + 'reports.tar.gz')
    try:
        with tarfile.open(fileobj=response['Body'], mode='r|gz') as archive:
            for member in archive:
                if member.islnk() and member.name not in state['paths']:
                    if member.linkname not in state['paths']:
                        raise ValueError('Unresolved archived alias')
                    state['paths'][member.name] = dict(state['paths'][member.linkname])
                    added += 1
    finally:
        response['Body'].close()
    state['seed_aliases_repaired_at'] = datetime.now(timezone.utc).isoformat()
    put_verified_json(s3, CURRENT, state, etag=etag)
    print(json.dumps({'archive_aliases_added':added,'total_paths':len(state['paths'])}))


if __name__ == '__main__':
    import sys
    repair_aliases() if '--repair-aliases' in sys.argv else main()
