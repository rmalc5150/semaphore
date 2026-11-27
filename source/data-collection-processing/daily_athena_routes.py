"""Reuse manifest-bound publisher proof and sample a few live Athena routes."""
from datetime import date
import hashlib
import json
import re
from botocore.exceptions import ClientError
from committed_data_athena import BASE, DB, OWNER, PREFIX, committed_partition, read_committed_partitions

HEX = re.compile(r'[0-9a-f]{64}')
IDENT = re.compile(r'[A-Za-z0-9_-]+')
QUERY_ID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}')
LIVE_CHECKS = 8


def verified_publisher(s3, bucket, pointer):
    """Require the hashed immutable copy, not only the mutable latest pointer."""
    digest = pointer.get('verification_sha256', '')
    key = pointer.get('verification_key')
    if not HEX.fullmatch(digest) or key != f'athena-committed/verifications/{digest}.json':
        raise ValueError('invalid publisher verification pointer')
    response = s3.get_object(Bucket=bucket, Key=PREFIX+key)
    try:
        raw = response['Body'].read(16 * 1024**2 + 1)
    finally:
        response['Body'].close()
    if len(raw) > 16 * 1024**2 or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('publisher verification checksum mismatch')
    saved = json.loads(raw)
    display = {k: v for k, v in pointer.items() if k not in {'verification_key','verification_sha256','checked_at'}}
    if saved != display or saved.get('status') != 'verified':
        raise ValueError('publisher pointer does not match the verified report')
    return saved


def plan_routes(publisher, previous, day, *, limit=LIVE_CHECKS):
    last = previous.get('published_route_proofs', {})
    proof = {(r['source'],r['dataset']): r for r in publisher.get('partition_verifications', [])}
    if len(proof) != len(publisher.get('partition_verifications', [])):
        raise ValueError('duplicate publisher partition proof')
    rows = {}
    failures = []
    changed = set()
    for part in publisher['sources']:
        source,dataset = part['source'],part['dataset']
        if not IDENT.fullmatch(source) or not IDENT.fullmatch(dataset):
            raise ValueError('invalid publisher route identity')
        route = source+'--'+dataset
        if route in rows:
            raise ValueError('duplicate publisher route')
        digest = part['manifest_sha256']
        receipt = proof.get((source,dataset), {})
        qid = receipt.get('query_id', '')
        if (not HEX.fullmatch(digest) or receipt.get('manifest_sha256') != digest
                or not QUERY_ID.fullmatch(qid)):
            rows[route] = {'status':'invalid', 'manifest_sha256':digest, 'source':source, 'dataset':dataset}
            failures.append({'name':route,'state':'FAILED','reason':'missing matching manifest-bound publisher receipt'})
            continue
        entry = {'manifest_sha256':digest, 'query_id':qid, 'source':source, 'dataset':dataset,
                 'records':int(part['records'])}
        old = last.get(route, {})
        reused = (old.get('status') == 'verified' and old.get('manifest_sha256') == digest
                  and old.get('query_id') == qid and old.get('records') == entry['records'])
        entry.update(status='verified', basis='receipt_reused' if reused else 'manifest_changed_verified')
        if not reused:changed.add(route)
        rows[route] = entry
    # Retest failed live checks until they recover, taking no more than the
    # daily budget. A rotating canary tests the public view independently.
    pending = {r['name']:r for r in previous.get('route_live_failures', []) if r['name'] in rows}
    candidates = sorted(k for k,v in rows.items() if v['status']=='verified' and v['records']>0)
    picked = [k for k in sorted(pending) if k in candidates][:limit]
    remaining = limit-len(picked)
    if candidates and remaining:
        start = date.fromisoformat(day).toordinal()*limit % len(candidates)
        rotation = candidates[start:]+candidates[:start]
        picked.extend([k for k in rotation if k not in picked][:remaining])
    return rows, changed, picked, pending, failures


def inspect_changes(glue, athena, bucket, publisher, rows, changed):
    """Check catalog identity and current newly released batch proof, not raw data files."""
    failures = []
    ordered = sorted(changed)
    if ordered:
        try:
            catalog = read_committed_partitions(glue)
        except ClientError:
            catalog = None
        for route in ordered:
            row=rows[route]; source,dataset=row['source'],row['dataset']
            expected = f"s3://{bucket}/{BASE}manifests/{source}/{dataset}/{row['manifest_sha256']}/"
            try:
                current = committed_partition(glue,catalog,source,dataset)
                if not current or current['StorageDescriptor']['Location'] != expected or current.get('Parameters',{}).get('optima_owner') != OWNER:
                    raise ValueError('catalog route does not match verified manifest location')
            except (ClientError,ValueError,KeyError) as error:
                row['status']='invalid'
                failures.append({'name':route,'state':'FAILED','reason':str(error)[:240]})
    batch_queries = {}
    for batch in (publisher.get('verification') or {}).get('queries', []):
        route=batch['source']+'--'+batch['dataset']
        if route not in changed:
            continue
        qid=batch.get('query_id', '')
        if (not QUERY_ID.fullmatch(qid) or batch.get('status') != 'verified'
                or not HEX.fullmatch(batch.get('batch_group',''))
                or batch.get('rows') != [[str(batch['records']),'0']]):
            rows[route]['status']='invalid'
            failures.append({'name':route,'state':'FAILED','reason':'invalid new batch verification receipt'})
            continue
        batch_queries[qid]=route
    statuses=[]
    ids=sorted(batch_queries)
    for offset in range(0,len(ids),50):
        part=ids[offset:offset+50]
        found={}
        try:
            response=athena.batch_get_query_execution(QueryExecutionIds=part)
            found={r['QueryExecutionId']:r['Status']['State'] for r in response.get('QueryExecutions', [])}
        except ClientError as error:
            found={qid:error.response['Error']['Code'] for qid in part}
        for qid in part:
            state=found.get(qid,'INSPECTION_FAILED')
            route=batch_queries[qid]
            statuses.append({'query_id':qid,'state':state,'route':route})
            if state!='SUCCEEDED':
                rows[route]['status']='invalid'
                failures.append({'name':route,'state':state,'query_id':qid,
                                 'reason':'new batch verification is not successful'})
    return statuses, failures


def sample_query(entry):
    source,dataset=entry['source'],entry['dataset']
    if not IDENT.fullmatch(source) or not IDENT.fullmatch(dataset):
        raise ValueError('invalid live sample route')
    return (f'{source}--{dataset}', 'optima-collected-data',
            f"SELECT observation_id FROM {DB}.observations WHERE source='{source}' AND dataset='{dataset}' LIMIT 1")
