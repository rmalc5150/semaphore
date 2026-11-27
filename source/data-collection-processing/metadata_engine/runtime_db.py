"""Short TLS transactions and fenced per-source work for metadata processing."""
from contextlib import contextmanager,nullcontext
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import uuid
import threading
import re

import boto3
import pymysql

ROOT = Path(__file__).resolve().parents[1]
STREAMING_RETRY = 'streaming_lane_required'


def host_excluded_sources():
    """Read a temporary source handoff on this worker only."""
    try:
        content = Path('/opt/constellation/metadata-worker-exclusions').read_text()
    except FileNotFoundError:
        return ()
    return tuple(sorted(set(content.split())))


def streaming_retry_sql(column):
    """Match the current routing reason and retries recorded by older workers."""
    return (f"(LOCATE('streaming_lane_required',COALESCE({column},''))>0 "
            f"OR LOCATE('larger_artifact_requires_streaming_adapter',COALESCE({column},''))>0)")


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def source_failure_state(count, failed):
    count = count + 1 if failed else 0
    return count, 'raw_stopped' if count >= 4 else 'enabled'


def source_failure_mode(config, source_key):
    """Only explicitly reviewed sources may use a non-blocking raw-failure queue."""
    return config.get('verified_source_failure_handling', {}).get(source_key)


def source_parallelism(config):
    """Allow extra ordinary leases only on sources with date-scoped repair."""
    return {
        source: limit
        for source, limit in config.get('metadata_source_parallelism', {}).items()
        if source != 'edinet_filings' and type(limit) is int and limit in (2, 3)
        and source_failure_mode(config, source) == 'queue_by_source_date'
    }


def failure_date(job):
    """Use the collection date encoded in a committed key; never invent history."""
    match = re.search(r'/ingestion_date=(\d{4}-\d{2}-\d{2})/', job.get('input_key', ''))
    if match:
        return match.group(1)
    # Public/native inputs do not always encode a source window.  Their queue
    # entry is explicitly the processing date, not a claim about provider time.
    return datetime.now(timezone.utc).date().isoformat()


class Database:
    def __init__(self, config, session=None):
        self.config = config
        self.session = session or boto3.Session(region_name=config['region'])
        self.credentials = None
        self.local=threading.local()

    @contextmanager
    def tx(self):
        if self.credentials is None:
            self.credentials = json.loads(self.session.client('secretsmanager').get_secret_value(SecretId=self.config['db_secret'])['SecretString'])
        s = self.credentials
        db=getattr(self.local,'connection',None)
        if db is None or not db.open:
            db = pymysql.connect(host=s['host'], port=int(s['port']), user=s['username'], password=s['password'],
                database='metadata_engine', ssl_ca=str(ROOT/'config/rds-us-east-1-ca-bundle.pem'), ssl_verify_cert=True,
                ssl_verify_identity=True, charset='utf8mb4', connect_timeout=10, read_timeout=30, write_timeout=30,
                autocommit=False, cursorclass=pymysql.cursors.DictCursor, init_command="SET time_zone='+00:00'")
            with db.cursor() as setup:
                setup.execute('SET SESSION max_execution_time=10000, innodb_lock_wait_timeout=10')
            self.local.connection=db
        try:
            with db.cursor() as c:
                yield c
            db.commit()
        except BaseException:
            # Preserve the original timeout; a broken rollback must not hide it.
            try:db.rollback()
            except Exception:
                db.close();self.local.connection=None
            raise
        # One connection per thread for this bounded invocation avoids a TLS
        # handshake per object. Every method still commits/rolls back promptly.

    def cursor(self, key):
        with self.tx() as c:
            c.execute('SELECT cursor_json FROM engine_cursors WHERE cursor_key=%s', (key,))
            row = c.fetchone()
        return json.loads(row['cursor_json']) if row else {}

    def save_cursor(self, key, state):
        with self.tx() as c:
            c.execute('INSERT INTO engine_cursors VALUES(%s,%s,UTC_TIMESTAMP(6)) ON DUPLICATE KEY UPDATE cursor_json=VALUES(cursor_json),updated_at=UTC_TIMESTAMP(6)', (key,encoded(state)))

    def enqueue(self, source, key, etag, form, priority=0,cursor=None):
        with (nullcontext(cursor) if cursor is not None else self.tx()) as c:
            c.execute('SELECT contract_version,state FROM engine_sources WHERE source_key=%s', (source,))
            row = c.fetchone()
            if not row or row['state'] in ('owner_paused','access_layer'):
                return False
            identity = fingerprint([source,key,etag,form,row['contract_version']])
            c.execute("INSERT IGNORE INTO engine_jobs(job_id,source_key,input_key,input_etag,input_format,contract_version,priority,available_after,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))",
                      (identity,source,key,etag,form,row['contract_version'],priority))
            inserted=c.rowcount == 1
            # A raw object may be discovered before its collector commits the
            # final manifest. Recheck it after the next discovery pass.
            c.execute("UPDATE engine_jobs SET state='queued',available_after=UTC_TIMESTAMP(6) WHERE job_id=%s AND state='uncommitted' AND available_after<=UTC_TIMESTAMP(6) AND finished_at<DATE_SUB(UTC_TIMESTAMP(6),INTERVAL 15 MINUTE)",(identity,))
            return inserted

    def claim(self, source_key=None):
        excluded = host_excluded_sources()
        if source_key in excluded:
            return None
        with self.tx() as c:
            ordinary = 'NOT ' + streaming_retry_sql('j.reason')
            ordinary_row = 'NOT ' + streaming_retry_sql('reason')
            parallelism = source_parallelism(self.config)
            # Preserve the existing EDINET policy. New parallel sources also
            # fence distinct input keys and keep streaming work exclusive.
            edinet_extra_leases = (
                2 if source_failure_mode(self.config, 'edinet_filings') == 'queue_by_source_date' else 0
            )
            active_probe = """SELECT 1 FROM engine_jobs r FORCE INDEX (source_state_priority)
                WHERE r.source_key=s.source_key AND r.state='running'
                  AND r.lease_until>=UTC_TIMESTAMP(6) LIMIT 1"""
            params = [edinet_extra_leases]
            branches = []
            for slots in (2, 3):
                sources = sorted(source for source, limit in parallelism.items() if limit == slots)
                if sources:
                    masks = ','.join(['%s'] * len(sources))
                    branches.append(f"WHEN s.source_key IN ({masks}) THEN ({active_probe} OFFSET {slots - 1})")
                    params.extend(sources)
            ordinary_capacity = f"({active_probe})"
            if branches:
                ordinary_capacity = 'CASE ' + ' '.join(branches) + f' ELSE {ordinary_capacity} END'
            source_filter = 'AND s.source_key=%s' if source_key is not None else ''
            if source_key is not None:
                params.append(source_key)
            if excluded:
                source_filter += ' AND s.source_key NOT IN (' + ','.join(['%s'] * len(excluded)) + ')'
                params.extend(excluded)
            # Discover without locks: sorting a locking scan can lock every
            # scanned source before LIMIT, starving independent workers.
            # Probe separate (source, state) ranges. Scalar LIMIT 1 probes
            # prevent the optimizer from flattening these into a wide join.
            c.execute(f"""
                SELECT s.source_key FROM engine_sources s
                WHERE s.state='enabled'
                  AND (
                    (SELECT 1 FROM engine_jobs j FORCE INDEX (source_state_priority)
                     WHERE j.source_key=s.source_key AND j.state='queued'
                       AND j.available_after<=UTC_TIMESTAMP(6) LIMIT 1)=1
                    OR (SELECT 1 FROM engine_jobs j FORCE INDEX (source_state_priority)
                        WHERE j.source_key=s.source_key AND j.state='retry'
                          AND j.available_after<=UTC_TIMESTAMP(6) AND {ordinary} LIMIT 1)=1
                    OR (SELECT 1 FROM engine_jobs j FORCE INDEX (source_state_priority)
                        WHERE j.source_key=s.source_key AND j.state='running'
                          AND j.lease_until<UTC_TIMESTAMP(6) AND {ordinary} LIMIT 1)=1
                  )
                  AND IF(s.source_key='edinet_filings',
                         ({active_probe} OFFSET %s), {ordinary_capacity}) IS NULL
                  {source_filter}
                ORDER BY s.updated_at LIMIT 32
            """, tuple(params))
            sources=c.fetchall()
            for source in sources:
                key=source['source_key']
                c.execute("SELECT state FROM engine_sources WHERE source_key=%s FOR UPDATE SKIP LOCKED",(key,))
                locked=c.fetchone()
                if not locked or locked['state']!='enabled':continue
                # Locking reads see current committed state even when candidate
                # discovery established an older repeatable-read snapshot.
                # The source row remains locked while rechecking the admission
                # limit and claiming a different, individually fenced job.
                active_inputs = ()
                if key in parallelism:
                    c.execute(f"""SELECT input_key,{streaming_retry_sql('reason')} AS streaming
                        FROM engine_jobs FORCE INDEX (source_jobs)
                        WHERE source_key=%s AND state='running' AND lease_until>=UTC_TIMESTAMP(6)
                        LIMIT %s FOR UPDATE""", (key, parallelism[key]))
                    running = c.fetchall()
                    if len(running) >= parallelism[key] or any(job['streaming'] for job in running):
                        continue
                    active_inputs = tuple(dict.fromkeys(job['input_key'] for job in running))
                else:
                    extra_leases = edinet_extra_leases if key == 'edinet_filings' else 0
                    c.execute("SELECT job_id FROM engine_jobs FORCE INDEX (source_jobs) WHERE source_key=%s AND state='running' AND lease_until>=UTC_TIMESTAMP(6) LIMIT 1 OFFSET %s FOR UPDATE",(key, extra_leases))
                    if c.fetchone():continue
                input_filter = ''
                if active_inputs:
                    input_filter = 'AND input_key NOT IN (' + ','.join(['%s'] * len(active_inputs)) + ')'
                # Each state probe uses the priority index. Input exclusions
                # apply to retry and expired leases as well as fresh work.
                c.execute(f"""
                    SELECT job_id FROM (
                      (SELECT job_id,priority,created_at FROM engine_jobs FORCE INDEX (source_state_priority)
                       WHERE source_key=%s AND state='queued' AND available_after<=UTC_TIMESTAMP(6) {input_filter}
                       ORDER BY priority DESC,created_at,job_id LIMIT 1)
                      UNION ALL
                      (SELECT job_id,priority,created_at FROM engine_jobs FORCE INDEX (source_state_priority)
                       WHERE source_key=%s AND state='retry' AND available_after<=UTC_TIMESTAMP(6) AND {ordinary_row} {input_filter}
                       ORDER BY priority DESC,created_at,job_id LIMIT 1)
                      UNION ALL
                      (SELECT job_id,priority,created_at FROM engine_jobs FORCE INDEX (source_state_priority)
                       WHERE source_key=%s AND state='running' AND lease_until<UTC_TIMESTAMP(6) AND {ordinary_row} {input_filter}
                       ORDER BY priority DESC,created_at,job_id LIMIT 1)
                    ) candidates
                    ORDER BY priority DESC,created_at,job_id LIMIT 1
                """,(key,*active_inputs)*3)
                candidate=c.fetchone()
                if not candidate:continue
                c.execute(f"""
                    SELECT * FROM engine_jobs WHERE job_id=%s AND source_key=%s AND (
                      (state='queued' AND available_after<=UTC_TIMESTAMP(6))
                      OR (state='retry' AND available_after<=UTC_TIMESTAMP(6) AND {ordinary_row})
                      OR (state='running' AND lease_until<UTC_TIMESTAMP(6) AND {ordinary_row})
                    ) FOR UPDATE SKIP LOCKED
                """,(candidate['job_id'],key))
                job=c.fetchone()
                if not job:continue
                token=str(uuid.uuid4())
                c.execute("UPDATE engine_jobs SET state='running',lease_token=%s,lease_until=DATE_ADD(UTC_TIMESTAMP(6),INTERVAL 600 SECOND),attempts=attempts+1 WHERE job_id=%s",(token,job['job_id']))
                c.execute('UPDATE engine_sources SET updated_at=UTC_TIMESTAMP(6) WHERE source_key=%s',(key,))
                job['lease_token']=token
                return job
            return None

    def finish(self, job, state, reason=None, report=None, output=None, rows=0):
        with self.tx() as c:
            c.execute('SELECT * FROM engine_sources WHERE source_key=%s FOR UPDATE',(job['source_key'],)); source=c.fetchone()
            c.execute('SELECT * FROM engine_jobs WHERE job_id=%s FOR UPDATE',(job['job_id'],)); current=c.fetchone()
            if current['state']!='running' or current['lease_token']!=job['lease_token']:
                raise RuntimeError('metadata_lease_lost')
            retry_minutes = 0 if state == 'retry' and reason == STREAMING_RETRY else 15
            if (job['source_key']=='edinet_filings' and state=='uncommitted'
                    and reason=='collection_manifest_not_yet_present' and current['attempts']>=3):
                retry_minutes = 360
            c.execute('UPDATE engine_jobs SET state=%s,reason=%s,report_uri=%s,output_uri=%s,output_rows=%s,finished_at=UTC_TIMESTAMP(6),lease_until=NULL,available_after=DATE_ADD(UTC_TIMESTAMP(6),INTERVAL %s MINUTE) WHERE job_id=%s',
                      (state,reason,report,output,rows,retry_minutes,job['job_id']))
            mode=source_failure_mode(self.config, job['source_key'])
            if state=='raw_failed' and mode=='queue_by_source_date':
                c.execute('''INSERT INTO source_date_failures
                    (source_key,dataset,failure_date,reason_code,latest_job_id,report_uri,first_seen_at,last_seen_at,failure_count,status)
                    VALUES(%s,%s,%s,%s,%s,%s,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),1,'open')
                    ON DUPLICATE KEY UPDATE reason_code=VALUES(reason_code),latest_job_id=VALUES(latest_job_id),report_uri=VALUES(report_uri),last_seen_at=UTC_TIMESTAMP(6),failure_count=failure_count+1,status='open' ''',
                    (job['source_key'],job.get('dataset') or 'unknown',failure_date(job),reason,job['job_id'],report))
            if state=='retry':
                digest=fingerprint([job['source_key'],job['job_id'],'metadata_worker',reason])
                c.execute('''INSERT INTO pipeline_failures
                    (failure_id,source_key,job_id,stage,error_reason,report_uri,first_seen_at,last_seen_at,occurrence_count,status)
                    VALUES(%s,%s,%s,'metadata_worker',%s,%s,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),1,'open')
                    ON DUPLICATE KEY UPDATE report_uri=VALUES(report_uri),last_seen_at=UTC_TIMESTAMP(6),occurrence_count=occurrence_count+1,status='open' ''',
                    (digest,job['source_key'],job['job_id'],reason,report))
            if state in ('accepted','raw_failed') and source['state'] == 'enabled':
                # Reviewed sources keep collecting: failed windows are queued
                # separately, while the source circuit breaker remains for
                # unreviewed sources whose contract/capture is suspect.
                failed=state=='raw_failed' and mode!='queue_by_source_date'
                count,new_state=source_failure_state(source['consecutive_raw_failures'],failed)
                # A successful empty window neither resets nor increments raw checks.
                if state=='accepted' and rows==0:return
                c.execute('UPDATE engine_sources SET state=%s,consecutive_raw_failures=%s,last_reason=%s,updated_at=UTC_TIMESTAMP(6) WHERE source_key=%s',(new_state,count,reason,job['source_key']))
                if new_state=='raw_stopped':
                    generation=source['stop_generation']+1
                    c.execute('UPDATE engine_sources SET stop_generation=%s WHERE source_key=%s',(generation,job['source_key']))
                    payload={'source':job['source_key'],'consecutive_raw_failures':count,'job_id':job['job_id'],'reason':reason,'report_uri':report}
                    c.execute('INSERT IGNORE INTO engine_notifications(notification_id,source_key,generation,payload,created_at) VALUES(%s,%s,%s,%s,UTC_TIMESTAMP(6))',
                              (fingerprint([job['source_key'],generation]),job['source_key'],generation,encoded(payload)))

    def stats(self,include_jobs=True):
        with self.tx() as c:
            jobs=None
            if include_jobs:
                c.execute('SELECT state,COUNT(*) n FROM engine_jobs FORCE INDEX (work_queue) GROUP BY state');jobs=c.fetchall()
            c.execute('SELECT source_key,state,consecutive_raw_failures,last_reason FROM engine_sources WHERE state<>%s',('enabled',));sources=c.fetchall()
            c.execute('SELECT COUNT(*) n FROM engine_notifications WHERE sent_at IS NULL');pending=c.fetchone()['n']
        return {'jobs':jobs,'job_counts_included':include_jobs,'restricted_sources':sources,'unsent_notifications':pending}


@contextmanager
def collection_tx(session,config,role='worker'):
    """Read collection commit evidence using its existing separate identity."""
    secret=json.loads(session.client('secretsmanager').get_secret_value(SecretId=config['collection_'+role+'_secret'])['SecretString'])
    conn=pymysql.connect(host=config['collection_host'],port=3306,user=secret['username'],password=secret['password'],database='constellation_operations',
        connect_timeout=10,read_timeout=30,ssl_ca=str(ROOT/'config/rds-us-east-1-ca-bundle.pem'),ssl_verify_cert=True,ssl_verify_identity=True,
        cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as c:yield c
    finally:conn.close()
