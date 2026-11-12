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
            c.execute("UPDATE engine_jobs SET state='queued',available_after=UTC_TIMESTAMP(6) WHERE job_id=%s AND state='uncommitted' AND finished_at<DATE_SUB(UTC_TIMESTAMP(6),INTERVAL 15 MINUTE)",(identity,))
            return inserted

    def claim(self):
        with self.tx() as c:
            # Lock the source first: only one active job per source can affect
            # its consecutive-failure counter. Expired jobs recover with fencing.
            c.execute("SELECT s.source_key FROM engine_sources s WHERE s.state='enabled' AND EXISTS(SELECT 1 FROM engine_jobs j WHERE j.source_key=s.source_key AND ((j.state IN ('queued','retry') AND j.available_after<=UTC_TIMESTAMP(6)) OR (j.state='running' AND j.lease_until<UTC_TIMESTAMP(6)))) AND NOT EXISTS(SELECT 1 FROM engine_jobs r WHERE r.source_key=s.source_key AND r.state='running' AND r.lease_until>=UTC_TIMESTAMP(6)) ORDER BY s.updated_at LIMIT 1 FOR UPDATE SKIP LOCKED")
            source=c.fetchone()
            if not source:return None
            c.execute("SELECT job_id FROM engine_jobs FORCE INDEX (source_ready_order) WHERE source_key=%s AND ((state IN ('queued','retry') AND available_after<=UTC_TIMESTAMP(6)) OR (state='running' AND lease_until<UTC_TIMESTAMP(6))) ORDER BY priority DESC,created_at,job_id LIMIT 1",(source['source_key'],))
            candidate=c.fetchone()
            if not candidate:return None
            c.execute('SELECT * FROM engine_jobs WHERE job_id=%s FOR UPDATE',(candidate['job_id'],));job=c.fetchone();token=str(uuid.uuid4())
            c.execute("UPDATE engine_jobs SET state='running',lease_token=%s,lease_until=DATE_ADD(UTC_TIMESTAMP(6),INTERVAL 600 SECOND),attempts=attempts+1 WHERE job_id=%s",(token,job['job_id']))
            c.execute('UPDATE engine_sources SET updated_at=UTC_TIMESTAMP(6) WHERE source_key=%s',(source['source_key'],))
            job['lease_token']=token
            return job

    def finish(self, job, state, reason=None, report=None, output=None, rows=0):
        with self.tx() as c:
            c.execute('SELECT * FROM engine_sources WHERE source_key=%s FOR UPDATE',(job['source_key'],)); source=c.fetchone()
            c.execute('SELECT * FROM engine_jobs WHERE job_id=%s FOR UPDATE',(job['job_id'],)); current=c.fetchone()
            if current['state']!='running' or current['lease_token']!=job['lease_token']:
                raise RuntimeError('metadata_lease_lost')
            c.execute('UPDATE engine_jobs SET state=%s,reason=%s,report_uri=%s,output_uri=%s,output_rows=%s,finished_at=UTC_TIMESTAMP(6),lease_until=NULL,available_after=DATE_ADD(UTC_TIMESTAMP(6),INTERVAL 15 MINUTE) WHERE job_id=%s',
                      (state,reason,report,output,rows,job['job_id']))
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
            if state in ('accepted','raw_failed'):
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
