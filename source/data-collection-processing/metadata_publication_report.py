"""Refresh receipt-backed publication counts and optionally reconcile once in Athena."""
import argparse
import fcntl
import json
import os
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / 'state' / 'metadata-publication-counts.json'
OVERVIEW = ROOT.parent / 'data-source-overview.txt'
REPORT_SUFFIX = 'health/metadata-publication-counts.json'
RECEIPT_PAGE = 2000
RECEIPT_SQL = """
SELECT /*+ MAX_EXECUTION_TIME(3500) */ release_id, s3_uri, verified_at
  FROM publication_releases FORCE INDEX (PRIMARY)
 WHERE release_id > %s AND status='published' AND release_kind='labelled'
   AND verified_at IS NOT NULL AND s3_uri LIKE %s
 ORDER BY release_id LIMIT %s
"""
SOURCE_HEADING = re.compile(r'^(?:\d{3}|D\d{2}) .+ \[([a-z0-9_]+)\]$')
LEGACY_COUNT = re.compile(r'^\s*[\d,]+ labelled rows / [\d,]+ verified metadata releases\s*$')
OLD_BASIS = 'Labelled counts cover optima_metadata_engine.source_observations and use Athena queries or verified publication receipts.'
BASIS = 'Labelled metadata counts are source-wide and come from the saved verified publication ledger, not from per-source Athena scans.'
REPORT_HEADER = 'Saved metadata publication counts '
ATHENA_HEADER = 'Grouped metadata Athena verification '
ROW_LABEL = '    Labelled    '
ATHENA_ROW_LABEL = '    Athena grouped '
JOB_ID = re.compile(r'[0-9a-f]{64}')
IDENTIFIER = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*')


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def sums(entries):
    return {key: sum(item[key] for item in entries.values()) for key in ('rows', 'releases')} | {
        'source_count': sum(item['releases'] > 0 for item in entries.values())
    }


def accepted_jobs(cur, job_ids):
    """Keep exact PK lookups bounded as the production database load varies."""
    from pymysql.err import OperationalError
    marks = ','.join(['%s'] * len(job_ids))
    for attempt in range(2):
        try:
            cur.execute(f"""SELECT /*+ MAX_EXECUTION_TIME(3500) */ job_id, source_key, output_rows
                FROM engine_jobs FORCE INDEX (PRIMARY)
                WHERE job_id IN ({marks}) AND state='accepted' AND output_rows>0""", job_ids)
            return cur.fetchall()
        except OperationalError as exc:
            if exc.args[0] != 3024:
                raise
            if len(job_ids) > 64:
                mid = len(job_ids) // 2
                return [*accepted_jobs(cur, job_ids[:mid]), *accepted_jobs(cur, job_ids[mid:])]
            if attempt:
                raise
            time.sleep(.25)


def receipt_snapshot(db, collect=stamp):
    """Aggregate the database index of receipts, without opening or listing S3 files."""
    cfg = db.config
    receipt_prefix = f"s3://{cfg['bucket']}/{cfg['prefix'].rstrip('/')}/publication/"
    now = collect()
    with db.tx() as cur:
        cur.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        cur.execute('SELECT source_key FROM engine_sources ORDER BY source_key')
        entries = {row['source_key']: {'rows': 0, 'releases': 0, 'latest_verified_at': None}
                   for row in cur.fetchall()}
        # Keep lookups on both primary indexes. Both statements see the same
        # read snapshot, and withdrawals are reflected in each rebuild.
        after = b''
        examined = 0
        while True:
            cur.execute(RECEIPT_SQL, (after, receipt_prefix + '%', RECEIPT_PAGE))
            releases = cur.fetchall()
            if not releases:
                break
            by_job = {}
            for release in releases:
                job, _, path = release['s3_uri'].removeprefix(receipt_prefix).partition('/')
                if not JOB_ID.fullmatch(job) or not path.endswith('.json') or '/' in path \
                        or bytes.fromhex(job[:32]) != release['release_id']:
                    raise ValueError('invalid metadata publication receipt identity')
                by_job[job] = release['verified_at'].replace(tzinfo=timezone.utc).isoformat()
            for row in accepted_jobs(cur, tuple(by_job)):
                entry = entries[row['source_key']]
                entry['rows'] += int(row['output_rows'])
                entry['releases'] += 1
                entry['latest_verified_at'] = max(entry['latest_verified_at'] or '', by_job[row['job_id']])
            after = releases[-1]['release_id']
            examined += len(releases)
            if examined % (RECEIPT_PAGE * 25) == 0:
                print(json.dumps({'stage': 'metadata_receipt_rollup', 'releases_examined': examined}), flush=True)
            if len(releases) < RECEIPT_PAGE:
                break
    return {'as_of': now, 'basis': 'verified_publication_receipt_ledger', 'sources': entries,
            'totals': sums(entries)}


def athena_sql(config, job_ids=None):
    database = config['athena_database']
    if not IDENTIFIER.fullmatch(database):
        raise ValueError('invalid metadata database name')
    where = ''
    if job_ids is not None:
        job_ids = tuple(dict.fromkeys(job_ids))
        if not 1 <= len(job_ids) <= 50 or not all(JOB_ID.fullmatch(j) for j in job_ids):
            raise ValueError('specify 1 to 50 exact metadata job IDs')
        where = ' WHERE job_id IN (' + ','.join("'" + j + "'" for j in job_ids) + ')'
    return (f'SELECT source_key, COUNT(*) AS row_count, COUNT(DISTINCT job_id) AS releases '
            f'FROM "{database}"."source_observations"{where} GROUP BY source_key ORDER BY source_key')


def athena_counts(client, config, job_ids=None, *, wait=time.sleep, monotonic=time.monotonic, collect=stamp):
    """Start exactly one query. Never silently retry a completed or failed scan."""
    sql = athena_sql(config, job_ids)
    requested_at = collect()
    query_id = client.start_query_execution(
        QueryString=sql, WorkGroup=config['athena_workgroup'],
        ResultConfiguration={'OutputLocation': f"s3://{config['bucket']}/{config['prefix'].rstrip('/')}/athena-results/"},
        ResultReuseConfiguration={'ResultReuseByAgeConfiguration': {'Enabled': False}},
    )['QueryExecutionId']
    print(json.dumps({'stage': 'metadata_reporting_athena', 'query_execution_id': query_id,
                      'scope': 'exact_jobs' if job_ids is not None else 'all_sources'}), flush=True)
    return fetch_athena_counts(client, query_id, requested_at, 180 if job_ids is not None else 1800,
                               wait=wait, monotonic=monotonic, collect=collect)


def fetch_athena_counts(client, query_id, requested_at, seconds, *, wait=time.sleep, monotonic=time.monotonic, collect=stamp):
    """Wait for an already submitted query and read its grouped results."""
    deadline = monotonic() + seconds
    while True:
        execution = client.get_query_execution(QueryExecutionId=query_id)['QueryExecution']
        status = execution['Status']
        if status['State'] == 'SUCCEEDED':
            break
        if status['State'] in {'FAILED', 'CANCELLED'}:
            raise RuntimeError(f"metadata Athena query {query_id} {status['State']}: {status.get('StateChangeReason', '')}")
        if monotonic() >= deadline:
            client.stop_query_execution(QueryExecutionId=query_id)
            raise TimeoutError(f'metadata Athena query {query_id} exceeded the wait budget')
        wait(5)
    paginator = client.get_paginator('get_query_results')
    entries = {}
    header = True
    for page in paginator.paginate(QueryExecutionId=query_id):
        for row in page['ResultSet']['Rows']:
            if header:
                header = False
                if [col.get('VarCharValue') for col in row['Data']] != ['source_key', 'row_count', 'releases']:
                    raise ValueError('unexpected Athena result columns')
                continue
            source, count, releases = [col.get('VarCharValue') for col in row['Data']]
            if not source or source in entries or not 0 < int(releases) <= int(count):
                raise ValueError('invalid or duplicate grouped Athena result')
            entries[source] = {'rows': int(count), 'releases': int(releases)}
    if header:
        raise ValueError('Athena returned no result header')
    return {'as_of': requested_at, 'completed_at': collect(), 'basis': 'grouped_athena_readback',
            'query_execution_id': query_id, 'bytes_scanned': execution['Statistics']['DataScannedInBytes'],
            'sources': entries, 'totals': sums(entries)}


def render_overview(text, report, uri):
    """Update only the labelled publication fields. Keep the raw-evidence inventory intact."""
    heading_count = 0
    source = None
    routine = report['receipts']
    grouped = report.get('athena')
    lines = []
    inserted_header = False
    for line in text.splitlines():
        if line.startswith((ROW_LABEL, ATHENA_ROW_LABEL, REPORT_HEADER, ATHENA_HEADER)):
            continue
        if line == OLD_BASIS or line == BASIS:
            lines.append(BASIS)
            lines.append(f"{REPORT_HEADER}{routine['as_of']} — {uri}")
            if grouped:
                lines.append(f"{ATHENA_HEADER}{grouped['as_of']} — {grouped['query_execution_id']}")
            inserted_header = True
            continue
        heading = SOURCE_HEADING.fullmatch(line)
        if heading:
            heading_count += 1
            source = heading[1]
        if source is not None and line.startswith('    Athena'):
            label = line.split('Athena', 1)[1].strip()
            items = [item for item in label.split(' · ') if not LEGACY_COUNT.fullmatch(item)]
            if items:
                lines.append('    Athena      ' + ' · '.join(items))
            continue
        if source is not None and line.startswith('    Metadata'):
            count = routine['sources'].get(source)
            if count is not None:
                lines.append(f"{ROW_LABEL}{count['rows']:,} rows / {count['releases']:,} verified metadata releases (source-wide)")
            if grouped and (checked := grouped['sources'].get(source)) is not None:
                lines.append(f"{ATHENA_ROW_LABEL}{checked['rows']:,} rows / {checked['releases']:,} job partitions (source-wide, as of grouped check)")
            source = None
        lines.append(line)
    if not heading_count or not inserted_header:
        raise ValueError('the source overview format did not match')
    return '\n'.join(lines) + '\n'


def write_atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = (path.stat().st_mode & 0o777) if path.exists() else 0o644
    temp = None
    try:
        with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False) as handle:
            temp = Path(handle.name)
            handle.write(text)
        os.chmod(temp, mode)
        temp.replace(path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def read_cache(path):
    if not path.exists():
        return {}
    report = json.loads(path.read_text())
    if report.get('schema_version') != 1 or not isinstance(report.get('receipts'), dict):
        raise ValueError('invalid saved publication report')
    return report


def refresh(session, metadata, monitoring, *, compare_athena=False, publish_saved=False, cache=CACHE, overview=OVERVIEW):
    from metadata_engine.runtime_db import Database
    target = monitoring['prefix'].rstrip('/') + '/' + REPORT_SUFFIX
    bucket = monitoring['bucket']
    uri = f's3://{bucket}/{target}'
    cache.parent.mkdir(parents=True, exist_ok=True)
    grouped_path = cache.with_suffix('.athena.json')
    if compare_athena:
        # A manual reconciliation may be slow. Don't let it hold up the daily
        # receipt refresh, and don't allow parallel all-source reconciliations.
        with cache.with_suffix('.athena.lock').open('a') as query_lock:
            fcntl.flock(query_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            grouped = athena_counts(session.client('athena'), metadata)
            write_atomic(grouped_path, json.dumps(grouped, sort_keys=True) + '\n')
    with cache.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        existing = read_cache(cache)
        # A manual Athena reconciliation doesn't need to rescan the routine
        # ledger. Keep that independently timestamped daily snapshot.
        routine = existing.get('receipts') if compare_athena or publish_saved else None
        if routine is None:
            if publish_saved:
                raise ValueError('no saved receipt snapshot to publish')
            routine = receipt_snapshot(Database(metadata, session=session))
        grouped = json.loads(grouped_path.read_text()) if grouped_path.exists() else existing.get('athena')
        report = {'schema_version': 1, 'report_uri': uri, 'receipts': routine}
        if grouped:
            report['athena'] = grouped
        text = overview.read_text()
        updated = render_overview(text, report, uri)
        encoded = json.dumps(report, indent=2, sort_keys=True) + '\n'
        session.client('s3').put_object(Bucket=bucket, Key=target, Body=encoded.encode(),
                                        ContentType='application/json', ServerSideEncryption='AES256')
        write_atomic(cache, encoded)
        if updated != text:
            write_atomic(overview, updated)
        return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--athena', action='store_true', help='Explicitly run and save one all-source Athena reconciliation.')
    mode.add_argument('--publish-saved', action='store_true', help='Publish snapshots already saved locally without scanning Athena or the database.')
    mode.add_argument('--verify-job', action='append', type=str, help='Read back these exact published job IDs only (repeat up to 50 times).')
    args = p.parse_args()
    import boto3
    config = json.loads((ROOT / 'config' / 'metadata-engine.json').read_text())
    session = boto3.Session(region_name=config['region'])
    if args.verify_job:
        report = athena_counts(session.client('athena'), config, args.verify_job)
        print(json.dumps(report))
        return
    monitoring = json.loads((ROOT / 'config' / 'collection-monitoring.json').read_text())
    report = refresh(session, config, monitoring, compare_athena=args.athena, publish_saved=args.publish_saved)
    print(json.dumps({'report_uri': report['report_uri'], 'receipt_totals': report['receipts']['totals'],
                      'grouped_query_id': report.get('athena', {}).get('query_execution_id')}))


if __name__ == '__main__':
    main()
