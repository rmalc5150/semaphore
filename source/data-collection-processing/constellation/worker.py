"""Bounded backfill service. Idle while paused; one fenced job per process."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import signal
import socket
import threading
import time
import uuid

from botocore.exceptions import ClientError
import requests

from constellation.control import Control, TERMINAL, canonical, job_id
from constellation.sources import request, parse, identity, observation

STOP = threading.Event()
MAX_BODY = 32 * 1024 * 1024


def emit(event, **fields):
    print(json.dumps({'event': event, 'at': datetime.now(timezone.utc).isoformat(), **fields}), flush=True)


def put_verified(control, key, body, content_type):
    sha = hashlib.sha256(body).hexdigest()
    try:
        control.s3.put_object(Bucket=control.config['bucket'], Key=key, Body=body,
            ContentType=content_type, ServerSideEncryption='AES256', IfNoneMatch='*', Metadata={'sha256': sha})
    except ClientError as exc:
        if exc.response['Error']['Code'] not in {'PreconditionFailed', '412'}:
            raise
    response = control.s3.get_object(Bucket=control.config['bucket'], Key=key)
    try:
        remote = hashlib.sha256()
        for chunk in response['Body'].iter_chunks(1024 * 1024):
            remote.update(chunk)
        if remote.hexdigest() != sha:
            raise ValueError('S3 readback checksum mismatch')
    finally:
        response['Body'].close()
    return {'uri': 's3://' + control.config['bucket'] + '/' + key, 'sha256': sha, 'bytes': len(body)}


def collect(control, spec, token, heartbeat_lost):
    identity_ = job_id(spec)
    attempt = uuid.uuid4().hex
    prefix = control.config['prefix'] + '/jobs/' + identity_ + '/attempts/' + attempt
    cursor = None
    seen = set()
    pages = []
    for page in range(200):
        if STOP.is_set() or heartbeat_lost.is_set():
            raise RuntimeError('worker_stopped_or_lease_lost')
        with control.provider_connection(spec['source_key'],identity_,token):
            control.request_slot(spec['source_key'], identity_, token)
            url, params = request(spec, cursor)
            retrieved_at = datetime.now(timezone.utc).isoformat()
            with requests.get(url, params=params, stream=True, timeout=(10, 30),
                    headers={'User-Agent': 'ConstellationResearch/1.0 (support@optima-holdings.com)'},
                    allow_redirects=False) as response:
                if response.status_code == 429:
                    raise RuntimeError('provider_throttled')
                response.raise_for_status()
                if response.status_code != 200 and not (response.status_code == 204 and spec['source_key'] == 'usgs_earthquakes'):
                    raise ValueError('Unexpected HTTP status')
                chunks = []
                size = 0
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > MAX_BODY:
                        raise ValueError('Response exceeds memory budget; split partition')
                    chunks.append(chunk)
                body = b''.join(chunks)
                # Save the provider response before parsing; malformed payloads remain evidence.
                raw = put_verified(control, prefix + '/raw/' + hashlib.sha256(body).hexdigest(), body,
                    response.headers.get('Content-Type', 'application/octet-stream'))
                metadata = {'request_url': response.url, 'request_parameters': params,
                    'http_status': response.status_code, 'http_headers': dict(response.headers),
                    'retrieved_at': retrieved_at, 'raw': raw, 'cursor': cursor}
                put_verified(control, prefix + '/requests/' + str(page) + '.json', canonical(metadata), 'application/json')
        rows, next_cursor = parse(spec, body, cursor, http_status=response.status_code)
        ids = [identity(spec, row) for row in rows]
        if len(set(ids)) != len(ids) or seen.intersection(ids):
            raise ValueError('Duplicate provider identities; pagination must be reviewed')
        seen.update(ids)
        records = b''.join(canonical(observation(spec, row, raw['uri'], retrieved_at)) + b'\n' for row in rows)
        normalized = put_verified(control, prefix + '/records/' + str(page) + '.jsonl', records, 'application/x-ndjson')
        pages.append({'request_page': page, 'raw': raw, 'records': normalized, 'record_count': len(rows)})
        emit('page_verified', job_id=identity_, page=page, records=len(rows))
        if next_cursor is None:
            control.renew(identity_, token)
            manifest = {'schema_version': 1, 'job_id': identity_, 'spec': spec, 'pages': pages,
                'records': len(seen), 'pagination_exhausted': True, 'coverage_status': 'verified_complete',
                'coverage_scope': 'Requested provider query exhausted; not proof of original vintages, field completeness, or global historical completeness.',
                'historical_vintage_verified': False, 'verified_at': datetime.now(timezone.utc).isoformat()}
            saved = put_verified(control, prefix + '/manifest.json', canonical(manifest), 'application/json')
            return {'manifest_uri': saved['uri'], 'manifest_sha256': saved['sha256'],
                'records': len(seen), 'coverage_status': 'verified_complete', 'historical_vintage_verified': False}
        if next_cursor == cursor:
            raise ValueError('Pagination cursor did not advance')
        cursor = next_cursor
    raise RuntimeError('page_budget_exhausted_split_required')


def process(control, job):
    identity_ = job['job_id']
    if len(identity_) != 64 or any(c not in '0123456789abcdef' for c in identity_):
        raise ValueError('Invalid queue job identity')
    spec = json.loads(job['spec_json'])
    if job_id(spec) != identity_:
        raise ValueError('Stored specification identity mismatch')
    lost = threading.Event()
    done = threading.Event()
    token = job['lease_token']
    def heartbeat():
        while not done.wait(30):
            try:
                control.renew(identity_, token)
            except Exception as exc:
                emit('lease_heartbeat_failed', job_id=identity_, error=type(exc).__name__)
                lost.set()
                return
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        result = collect(control, spec, token, lost)
        if lost.is_set():
            raise RuntimeError('lease_lost')
        control.finish(identity_, token, 'succeeded', result)
        emit('job_succeeded', job_id=identity_, **result)
    except Exception as exc:
        if not lost.is_set() and str(exc)=='historical_daily_budget_exhausted':
            tomorrow=datetime.now(timezone.utc).date()+timedelta(days=1)
            until=int(datetime.combine(tomorrow,datetime.min.time(),timezone.utc).timestamp())+60
            control.defer(identity_,token,until,'historical_daily_budget_exhausted')
        elif not lost.is_set():
            status = 'blocked' if int(job['attempts']) >= 3 else 'retryable_failed'
            gap_event={'job_id':identity_,'spec':spec,'status':status,'reason':str(exc)[:300],'coverage_status':'partial','observed_at':datetime.now(timezone.utc).isoformat()}
            saved=put_verified(control,control.config['prefix']+'/gap-events/'+identity_+'/'+uuid.uuid4().hex+'.json',canonical(gap_event),'application/json')
            control.finish(identity_, token, status, {'reason': str(exc)[:300], 'coverage_status': 'partial','gap_evidence_uri':saved['uri']})
        emit('job_incomplete', job_id=identity_, error=type(exc).__name__, reason=str(exc)[:300])
    finally:
        done.set()
        thread.join(timeout=2)


def main():
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *args: STOP.set())
    control = Control()
    emit('worker_ready', collection_enabled=control.allowed())
    while not STOP.is_set():
        state = control.get('control') or {}
        if not control.allowed() and not state.get('pilot_job_ids'):
            STOP.wait(15)
            continue
        try:
            job = control.claim_next(socket.gethostname() + ':' + str(os.getpid()))
            if job:
                process(control, job)
            else:
                STOP.wait(10)
        except Exception as exc:
            emit('worker_error', error=type(exc).__name__, reason=str(exc)[:300])
            STOP.wait(10)
    emit('worker_drained')


if __name__ == '__main__':
    main()
