#!/usr/bin/env python3
"""Supervise capture with S3 durable state and a bounded, disk-free workspace.

The global lock serializes jobs to bound RAM and preserve SQLite ownership.
Raw collection commits remain native S3 writes. A completed child (including
failure/interrupt) checkpoints its operational state before releasing RAM.
Uncheckpointed state is retained in RAM and retried before another job starts.
A host loss can repeat an in-flight job; previously committed raw S3 data is
immutable, and the last successful operational checkpoint remains available.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
import uuid
import boto3
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError

ROOT = Path(os.environ.get('OPTIMA_S3_RUNTIME_ROOT', '/home/ec2-user/data-collection-processing/constellation/daily-workspaces/cninfo_mainland_china_company_disclosures/constellation/daily-workspaces/cninfo_mainland_china_company_disclosures/constellation/daily-workspaces/south_korea_fss_opendart'))
BASE = Path(os.environ.get('OPTIMA_S3_RUNTIME_BASE', '/dev/shm/optima-s3'))
WORK = BASE / 'work'
BUCKET = 'data-collection-059416028963-us-east-1-an'
PREFIX = os.environ.get('OPTIMA_S3_RUNTIME_PREFIX', 'research-data/operations/s3-runtime')
CURRENT = PREFIX + '/current.json'
CONFIG = TransferConfig(multipart_threshold=16 * 1024**2, multipart_chunksize=16 * 1024**2,
                        max_concurrency=1, max_io_queue=1, use_threads=False)


def checksum(path):
    digest = hashlib.sha256()
    size = 0
    with open(path, 'rb') as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def read_index(s3):
    try:
        response = s3.get_object(Bucket=BUCKET, Key=CURRENT)
    except ClientError as exc:
        if exc.response['Error']['Code'] not in {'NoSuchKey', '404'}:
            raise
        seed = os.environ.get('OPTIMA_S3_RUNTIME_SEED_KEY')
        if not seed:
            return {'schema_version': 1, 'paths': {}}, None
        response = s3.get_object(Bucket=BUCKET, Key=seed)
        with closing(response['Body']) as body:
            result = json.loads(body.read())
        for rel in result['paths']:
            if Path(rel).is_absolute() or '..' in Path(rel).parts:
                raise ValueError('Unsafe path in S3 runtime seed')
        return result, None
    with closing(response['Body']) as body:
        result = json.loads(body.read())
    for rel in result['paths']:
        if Path(rel).is_absolute() or '..' in Path(rel).parts:
            raise ValueError('Unsafe path in S3 runtime index')
    return result, response['ETag']


def put_verified_json(s3, key, value, etag=None, create=False):
    body = (json.dumps(value, sort_keys=True) + '\n').encode()
    conditional = {'IfMatch': etag} if etag else ({'IfNoneMatch': '*'} if create else {})
    result = s3.put_object(Bucket=BUCKET, Key=key, Body=body, ContentType='application/json',
                           ServerSideEncryption='AES256', **conditional)
    response = s3.get_object(Bucket=BUCKET, Key=key)
    with closing(response['Body']) as handle:
        if handle.read() != body:
            raise ValueError('Runtime checkpoint readback mismatch')
    return result['ETag']


def normalize_databases():
    for path in list(WORK.rglob('*.sqlite3')) + list(WORK.rglob('*.db')):
        if path.is_symlink() or not path.stat().st_size:
            continue
        with closing(sqlite3.connect(path)) as db:
            result = db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
            if result and result[0] not in {0, -1}:
                raise RuntimeError('SQLite checkpoint still locked: ' + str(path))
            check = db.execute('PRAGMA quick_check(1)').fetchone()
            if check != ('ok',):
                raise ValueError('Invalid SQLite operational state: ' + str(path))


def checkpoint(s3, state, etag, unit, run_id):
    normalize_databases()
    updated = dict(state['paths'])
    for marker in (BASE / 'deletions').glob('*.json'):
        updated.pop(json.loads(marker.read_text())['path'], None)
    changed = []
    for path in sorted(WORK.rglob('*')):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(WORK).as_posix()
        if rel.startswith('tmp/') or rel.endswith(('.lock', '-wal', '-shm', '-journal')):
            continue
        digest, size = checksum(path)
        previous = updated.get(rel)
        if previous and (previous['sha256'], previous['bytes']) == (digest, size):
            continue
        key = PREFIX + '/snapshots/' + run_id + '/' + rel
        s3.upload_file(str(path), BUCKET, key, ExtraArgs={'ServerSideEncryption': 'AES256'}, Config=CONFIG)
        response = s3.get_object(Bucket=BUCKET, Key=key)
        remote = hashlib.sha256()
        count = 0
        with closing(response['Body']) as handle:
            for chunk in handle.iter_chunks(chunk_size=1024 * 1024):
                remote.update(chunk)
                count += len(chunk)
        if (remote.hexdigest(), count) != (digest, size):
            raise ValueError('S3 state upload checksum mismatch: ' + rel)
        updated[rel] = {'key': key, 'sha256': digest, 'bytes': size}
        changed.append(rel)
    snapshot = {'schema_version': 1, 'paths': updated, 'unit': unit, 'run_id': run_id,
                'checkpointed_at': datetime.now(timezone.utc).isoformat()}
    put_verified_json(s3, PREFIX + '/manifests/' + run_id + '.json', snapshot, create=True)
    # Advance the durable pointer only after every byte of the snapshot is verified.
    new_etag = put_verified_json(s3, CURRENT, snapshot, etag=etag, create=not etag)
    print(json.dumps({'stage': 's3_checkpoint_verified', 'unit': unit, 'changed_files': len(changed),
                      'run_id': run_id}), flush=True)
    return snapshot, new_etag


def initialize_workspace(state):
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / 'tmp').mkdir(exist_ok=True)
    (BASE / 'locks').mkdir(exist_ok=True)
    deletions = BASE / 'deletions'
    if deletions.exists():
        shutil.rmtree(deletions)
    deletions.mkdir()
    for path in ROOT.iterdir():
        if path.name.endswith('-build') or path.name in {'reports', 'mlperf-evidence-cache', 'ted-package-cache', 'collection-output'}:
            (WORK / path.name).mkdir(parents=True, exist_ok=True)
    (BASE / 'index.json').write_text(json.dumps(state))
    source = ROOT / 'runtime_source_files' / 'reports'
    if source.exists():
        for path in source.rglob('*'):
            if path.is_file() and path.suffix in {'.py', '.sh'}:
                target = WORK / 'reports' / path.relative_to(source)
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    target.symlink_to(path)


def remove_checkpointed_workspace():
    """Cleanup is idempotent after the durable pointer has been verified."""
    try:
        shutil.rmtree(WORK)
    except FileNotFoundError:
        if WORK.exists():
            raise  # Missing children in an existing tree need investigation.


def run(unit, command):
    if not BASE.is_dir():
        raise RuntimeError('S3 runtime RAM mount has not been installed')
    s3 = boto3.client('s3', region_name='us-east-1')
    with (BASE / 'runtime.lock').open('a') as lock:
        print(json.dumps({'stage': 'waiting_for_ram_budget', 'unit': unit}), flush=True)
        fcntl.flock(lock, fcntl.LOCK_EX)
        state, etag = read_index(s3)
        pending_path = BASE / 'pending.json'
        if pending_path.exists():
            pending = json.loads(pending_path.read_text())
            if pending.get('base_etag') != etag and state.get('run_id') != pending['run_id']:
                raise RuntimeError('S3 checkpoint changed since interrupted job; RAM retained for conflict review')
            state, etag = checkpoint(s3, state, etag, pending['unit'], uuid.uuid4().hex)
            remove_checkpointed_workspace()
            pending_path.unlink(missing_ok=True)
        initialize_workspace(state)
        run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S-') + uuid.uuid4().hex
        pending_path.write_text(json.dumps({'unit': unit, 'run_id': run_id, 'base_etag': etag}))
        env = dict(os.environ, OPTIMA_S3_RUNTIME='1', TMPDIR=str(WORK / 'tmp'),
                   PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(ROOT) + os.pathsep + os.environ.get('PYTHONPATH', ''))
        child = subprocess.Popen(command, env=env, start_new_session=True)
        interrupted = []
        def stop(signum, frame):
            if not interrupted:
                interrupted.append(time.monotonic())
                try:
                    os.killpg(child.pid, signal.SIGINT)
                except ProcessLookupError:
                    pass
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, stop)
        while child.poll() is None:
            if interrupted and time.monotonic() - interrupted[0] > 90:
                os.killpg(child.pid, signal.SIGKILL)
            time.sleep(0.5)
        try:
            state, etag = checkpoint(s3, state, etag, unit, run_id)
        except BaseException:
            print(json.dumps({'stage': 'checkpoint_failed_ram_retained', 'unit': unit}), flush=True)
            raise
        remove_checkpointed_workspace()
        pending_path.unlink(missing_ok=True)
        return child.returncode if child.returncode >= 0 else 128 - child.returncode


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--unit', required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('a capture command is required')
    raise SystemExit(run(args.unit, command))
