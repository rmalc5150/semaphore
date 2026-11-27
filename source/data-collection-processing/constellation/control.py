"""RDS MySQL durable work queue, fenced leases and shared provider budgets.

The controller registers partitions and controls pause/resume. Workers receive
only reviewed specifications and cannot change control flags or register jobs.
"""
import argparse
from contextlib import contextmanager
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

import boto3
import pymysql

ROOT = Path(__file__).resolve().parents[1]
TERMINAL = {'succeeded', 'blocked', 'permanently_unavailable'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def job_id(spec):
    return hashlib.sha256(canonical(spec)).hexdigest()


def settings():
    return json.loads((ROOT / 'config/constellation-infrastructure.json').read_text())


class LeaseLost(RuntimeError):
    pass


class Control:
    def __init__(self, config=None, session=None):
        self.config = config or settings()
        self.session = session or boto3.Session(region_name=self.config['region'])
        self.s3 = self.session.client('s3')
        role = os.environ.get('CONSTELLATION_ROLE', 'controller')
        if role not in {'controller', 'worker'}:
            raise ValueError('Unknown database role')
        self.secret_id = self.config[role + '_secret_arn']
        self._credentials = None
        self._credentials_at = 0

    @contextmanager
    def db(self):
        # Bounded connection lifetime avoids idle connection buildup on t4g.micro.
        if self._credentials is None or time.time() - self._credentials_at > 300:
            response = self.session.client('secretsmanager').get_secret_value(SecretId=self.secret_id)
            self._credentials = json.loads(response['SecretString'])
            self._credentials_at = time.time()
        secret = self._credentials
        connection = pymysql.connect(host=self.config['db_host'], port=3306,
            user=secret['username'], password=secret['password'], database=self.config['database'],
            connect_timeout=10, read_timeout=30, write_timeout=30,
            charset='utf8mb4', autocommit=False, cursorclass=pymysql.cursors.DictCursor,
            ssl_ca=str(ROOT / 'config/rds-us-east-1-ca-bundle.pem'), ssl_verify_cert=True, ssl_verify_identity=True)
        try:
            with connection.cursor() as cursor:
                yield cursor
            connection.commit()
        except BaseException:
            # A lost connection can also fail rollback; retain the original cause.
            try:connection.rollback()
            except pymysql.MySQLError:pass
            raise
        finally:
            connection.close()

    def get(self, key):
        with self.db() as cursor:
            if key == 'control':
                cursor.execute('SELECT * FROM backfill_control WHERE singleton=1')
                row = cursor.fetchone()
                if row:
                    row['enabled'] = bool(row['enabled'])
                    row['pilot_job_ids'] = json.loads(row['pilot_job_ids'])
                return row
            if key.startswith('job#'):
                cursor.execute('SELECT * FROM backfill_jobs WHERE job_id=%s', (key[4:],))
                return cursor.fetchone()
            raise ValueError('Unsupported state key')

    def allowed(self, identity=None):
        state = self.get('control') or {}
        return (state.get('enabled') is True or identity in state.get('pilot_job_ids', [])) and (
            float(state.get('stop_after_epoch', 0)) > time.time())

    def set_enabled(self, enabled, pilot_ids=None):
        with self.db() as cursor:
            cursor.execute('UPDATE backfill_control SET enabled=%s,pilot_job_ids=%s WHERE singleton=1',
                (enabled, json.dumps(pilot_ids or [])))

    def daily_allowed(self):
        """Daily capture has its own switch; a historical pause must not stop t3."""
        if os.environ.get('CONSTELLATION_ROLE','controller')!='controller':return False
        if 'daily_collection_enabled' in self.config:return bool(self.config['daily_collection_enabled'])
        return bool((self.get('control') or {}).get('enabled'))

    def register(self, spec):
        if set(spec) != {'source_key', 'dataset', 'geography', 'start', 'end', 'edition', 'extractor_version', 'parameters'}:
            raise ValueError('Invalid partition specification')
        if spec['source_key'].startswith('legacy:'):
            from constellation.legacy_routes import validate_spec
        else:
            from constellation.sources import validate_spec
        validate_spec(spec)
        identity = job_id(spec)
        with self.db() as cursor:
            cursor.execute('INSERT IGNORE INTO backfill_jobs(job_id,source_key,spec_json,status,created_at,updated_at) VALUES(%s,%s,%s,%s,UNIX_TIMESTAMP(),UNIX_TIMESTAMP())',
                (identity, spec['source_key'], canonical(spec).decode(), 'pending'))
            cursor.execute('SELECT spec_json FROM backfill_jobs WHERE job_id=%s', (identity,))
            if json.loads(cursor.fetchone()['spec_json']) != spec:
                raise ValueError('Partition identity collision')
        return identity

    def claim_next(self, worker, kind='raw'):
        # Keep idle/network-bound concurrency without admitting more work when
        # the shared pool is already approaching its memory allowance.
        threshold=self.config.get('worker_pool',{}).get('admission_memory_high_gib') if os.environ.get('CONSTELLATION_ROLE')=='worker' else None
        memory=Path('/sys/fs/cgroup/constellation-workers.slice/memory.current')
        if threshold and memory.exists() and int(memory.read_text())>=float(threshold)*1024**3:
            return None
        # SKIP LOCKED allows workers to claim independent rows without waiting.
        # A single UPDATE fences prior owners by replacing the random lease token.
        state = self.get('control') or {}
        if float(state.get('stop_after_epoch', 0)) <= time.time():
            return None
        pilot_ids = state.get('pilot_job_ids', [])
        if not state.get('enabled') and not pilot_ids:
            return None
        extra = ''
        values = ['legacy:%']
        if kind not in {'raw','legacy','public'}:
            raise ValueError('Unknown worker execution kind')
        extra += " AND source_key " + ("LIKE %s" if kind in {'legacy','public'} else "NOT LIKE %s")
        if kind=='public':
            extra += ' AND source_key LIKE %s'
            values.append('legacy:constellation-public-%')
        if os.environ.get('CONSTELLATION_ROLE')=='worker' and Path('/opt/constellation/historical-only').is_file():
            extra += " AND source_key <> '__lease_check__'"
            if kind in {'legacy','public'}:
                from constellation.legacy_routes import manifest
                nonhistorical = ['legacy:' + r['unit'] for r in manifest()['routes']
                                 if r['route_kind'] in ('independent_public_daily','migration_probe')]
                if nonhistorical:
                    extra += ' AND source_key NOT IN (' + ','.join(['%s'] * len(nonhistorical)) + ')'
                    values.extend(nonhistorical)
        # Keep one provider from occupying the entire pool while rate-limited.
        extra += " AND source_key NOT IN (SELECT source_key FROM backfill_jobs WHERE status='running' AND lease_until>=UNIX_TIMESTAMP() GROUP BY source_key HAVING COUNT(*) >= CASE WHEN source_key='arxiv' THEN 1 ELSE " + ('1' if kind in {'legacy','public'} else '2') + ' END) '
        if not state.get('enabled'):
            extra += ' AND job_id IN (' + ','.join(['%s'] * len(pilot_ids)) + ')'
            values.extend(pilot_ids)
        with self.db() as cursor:
            cursor.execute("SELECT * FROM backfill_jobs WHERE status IN ('pending','retryable_failed','running') AND lease_until < UNIX_TIMESTAMP() AND next_attempt_at <= UNIX_TIMESTAMP() AND attempts < 3" + extra +
                ' ORDER BY attempts,updated_at,job_id LIMIT 1 FOR UPDATE SKIP LOCKED', values)
            row = cursor.fetchone()
            if not row:
                return None
            token = uuid.uuid4().hex
            cursor.execute("UPDATE backfill_jobs SET status='running', lease_token=%s,lease_until=UNIX_TIMESTAMP()+180,worker_id=%s,updated_at=UNIX_TIMESTAMP(),attempts=attempts+1 WHERE job_id=%s",
                (token, worker, row['job_id']))
            row.update(status='running', lease_token=token, attempts=row['attempts'] + 1)
            return row

    def renew(self, identity, token):
        with self.db() as cursor:
            cursor.execute("UPDATE backfill_jobs SET lease_until=UNIX_TIMESTAMP()+180 WHERE job_id=%s AND lease_token=%s AND status='running' AND lease_until >= UNIX_TIMESTAMP()", (identity, token))
            if cursor.rowcount != 1:
                # A heartbeat in the same second may write the identical value.
                cursor.execute("SELECT job_id FROM backfill_jobs WHERE job_id=%s AND lease_token=%s AND status='running' AND lease_until >= UNIX_TIMESTAMP()", (identity, token))
                if not cursor.fetchone():
                    raise LeaseLost(identity)

    def finish(self, identity, token, status, result):
        if status not in TERMINAL | {'retryable_failed'}:
            raise ValueError(status)
        legacy_checkpoint = (result.get('execution_kind') == 'legacy_invocation' and
            result.get('checkpoint_verified') is True and result.get('report_uri') and
            result.get('coverage_status') == 'not_audited')
        if status == 'succeeded' and not legacy_checkpoint and not (result.get('manifest_uri') and result.get('coverage_status') == 'verified_complete'):
            raise ValueError('Success requires a verified manifest and exhausted pagination')
        if status == 'permanently_unavailable' and not all(result.get(field) for field in (
                'source_key', 'period_start', 'period_end', 'reason', 'evidence_uri', 'reviewed_at')):
            raise ValueError('Permanent gap requires scoped evidence and a review timestamp')
        with self.db() as cursor:
            cursor.execute("UPDATE backfill_jobs SET status=%s,result_json=%s,updated_at=UNIX_TIMESTAMP(),lease_until=0,next_attempt_at=UNIX_TIMESTAMP()+LEAST(21600,300*POW(4,GREATEST(0,attempts-1))) WHERE job_id=%s AND lease_token=%s AND status='running' AND lease_until >= UNIX_TIMESTAMP()",
                (status, canonical(result).decode(), identity, token))
            if cursor.rowcount != 1:
                raise LeaseLost(identity)

    def request_slot(self, source, identity, token):
        """Serialize a provider request and reserve its daily budget atomically.

        Legacy adapters remain ineligible until daily clients share this quota
        mechanism; no cross-host use of their local quota databases is allowed.
        """
        from constellation.sources import PROVIDERS
        policy = PROVIDERS[source]
        while True:
            if not self.allowed(identity):
                raise RuntimeError('backfill_paused')
            self.renew(identity, token)
            day = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            reserved = False
            with self.db() as cursor:
                cursor.execute('INSERT INTO backfill_quotas(source_key,quota_day) VALUES(%s,%s) ON DUPLICATE KEY UPDATE source_key=VALUES(source_key)', (source, day))
                cursor.execute('SELECT *,UNIX_TIMESTAMP() AS now_epoch FROM backfill_quotas WHERE source_key=%s AND quota_day=%s FOR UPDATE', (source, day))
                row = cursor.fetchone()
                if row['used_requests'] >= policy['daily_budget']:
                    raise RuntimeError('historical_daily_budget_exhausted')
                if row['next_request_at'] <= row['now_epoch']:
                    cursor.execute('UPDATE backfill_quotas SET next_request_at=UNIX_TIMESTAMP()+%s,used_requests=used_requests+1 WHERE source_key=%s AND quota_day=%s',
                        (policy['interval_seconds'], source, day))
                    reserved = True
            if reserved:
                return
            time.sleep(1)

    @contextmanager
    def provider_connection(self, source, identity, token):
        """arXiv permits one connection across all our machines."""
        if source!='arxiv':
            yield
            return
        with self.db() as cursor:
            acquired=False
            try:
                while not acquired:
                    if not self.allowed(identity):raise RuntimeError('backfill_paused')
                    self.renew(identity,token)
                    cursor.execute("SELECT GET_LOCK('constellation:arxiv:http',1) AS acquired")
                    acquired=cursor.fetchone()['acquired']==1
                yield
            finally:
                if acquired:cursor.execute("SELECT RELEASE_LOCK('constellation:arxiv:http')")

    def defer(self, identity, token, until, reason, evidence=None):
        """Defer a job without consuming its failure retry allowance."""
        result = {**(evidence or {}), 'reason': reason, 'coverage_status': 'deferred_not_a_gap'}
        with self.db() as cursor:
            cursor.execute("UPDATE backfill_jobs SET status='pending', attempts=GREATEST(0,attempts-1), lease_until=0, next_attempt_at=%s, updated_at=UNIX_TIMESTAMP(), result_json=%s WHERE job_id=%s AND lease_token=%s AND status='running' AND lease_until>=UNIX_TIMESTAMP()",
                (until, canonical(result).decode(),identity,token))
            if cursor.rowcount!=1:raise LeaseLost(identity)

    def reconcile(self):
        with self.db() as cursor:
            cursor.execute("UPDATE backfill_jobs SET status='blocked',result_json=%s,updated_at=UNIX_TIMESTAMP() WHERE attempts >= 3 AND lease_until < UNIX_TIMESTAMP() AND status IN ('running','retryable_failed')",
                (canonical({'reason': 'attempt_budget_exhausted', 'coverage_status': 'partial'}).decode(),))
            return cursor.rowcount


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['status', 'pause', 'resume', 'reconcile', 'register'])
    parser.add_argument('--spec', type=Path)
    args = parser.parse_args()
    control = Control()
    if args.action == 'status':
        with control.db() as cursor:
            cursor.execute("SELECT status,COUNT(*) AS jobs FROM backfill_jobs WHERE source_key <> '__lease_check__' GROUP BY status")
            counts = cursor.fetchall()
            cursor.execute("SELECT COUNT(*) AS retained_lease_checks FROM backfill_jobs WHERE source_key='__lease_check__'")
            diagnostics = cursor.fetchone()
        print(json.dumps({'control': control.get('control'), 'jobs': counts, 'diagnostics': diagnostics}, default=str))
    elif args.action in {'pause', 'resume'}:
        control.set_enabled(args.action == 'resume')
    elif args.action == 'register':
        if not args.spec:
            parser.error('--spec required')
        print(control.register(json.loads(args.spec.read_text())))
    else:
        print(json.dumps({'expired_final_attempts_blocked': control.reconcile()}))


if __name__ == '__main__':
    main()
