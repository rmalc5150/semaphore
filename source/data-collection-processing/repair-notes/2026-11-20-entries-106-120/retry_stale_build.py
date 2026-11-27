"""Retry failed inputs that were claimed by a pre-deployment metadata process."""
from concurrent.futures import ThreadPoolExecutor
import json

from deploy_on_wake import ROOT, s3_json
from metadata_engine.runtime_db import Database
from ops import B, P, session

OLD_BUILD = 'a116cf30d51a37cb518a1be283ca5516c66f7c1109d1e4c95e1c121c59af5c22'
REASON = 'missing_verified_raw_artifacts:provider_record'


def retry():
    activation = s3_json('activation.json')['targets']
    targets = {item['job_id'] for values in activation.values() for item in values}
    config = json.loads((ROOT/'config/metadata-engine.json').read_text())
    database = Database(config, session=session)
    s3 = session.client('s3')
    source_slots = ','.join(['%s'] * len(activation))
    with database.tx() as cursor:
        cursor.execute(f"""SELECT source_key,job_id,report_uri FROM engine_jobs
            WHERE source_key IN ({source_slots}) AND contract_version='2.0.3'
            AND state='raw_failed' AND reason=%s AND report_uri IS NOT NULL""", (*activation, REASON))
        candidates = cursor.fetchall()

    def check(row):
        prefix = 's3://'+B+'/'
        if not row['report_uri'].startswith(prefix):
            return False
        with s3.get_object(Bucket=B, Key=row['report_uri'][len(prefix):])['Body'] as stream:
            return json.load(stream).get('build_sha256') == OLD_BUILD

    with ThreadPoolExecutor(max_workers=6) as pool:
        verified = [row for row, matched in zip(candidates,pool.map(check,candidates)) if matched]
    retried = []
    for row in verified:
        with database.tx() as cursor:
            cursor.execute('SELECT state,contract_version,last_reason FROM engine_sources WHERE source_key=%s FOR UPDATE',(row['source_key'],))
            state = cursor.fetchone()
            if state['state'] not in ('enabled','raw_stopped') or state['contract_version'] != '2.0.3':
                continue
            if state['state'] == 'raw_stopped':
                cursor.execute("""SELECT COUNT(*) n FROM engine_jobs WHERE source_key=%s
                    AND contract_version='2.0.3' AND state='raw_failed'""",(row['source_key'],))
                known = sum(v['source_key']==row['source_key'] for v in verified)
                if known != cursor.fetchone()['n'] or state['last_reason'] != REASON:
                    continue
                cursor.execute("""UPDATE engine_sources SET state='enabled',consecutive_raw_failures=0,
                    last_reason=NULL,updated_at=UTC_TIMESTAMP(6) WHERE source_key=%s""",(row['source_key'],))
            priority = 500 if row['job_id'] in targets else 70
            cursor.execute("""UPDATE engine_jobs SET state='retry',available_after=UTC_TIMESTAMP(6),
                priority=GREATEST(priority,%s) WHERE job_id=%s AND state='raw_failed' AND report_uri=%s""",
                (priority,row['job_id'],row['report_uri']))
            if cursor.rowcount:
                retried.append(row)
    evidence = P/'stale-build-retries.json'
    prior = json.loads(evidence.read_text()) if evidence.exists() else []
    if retried:
        evidence.write_text(json.dumps(prior+retried,indent=2)+'\n')
    print(json.dumps({'checked':len(candidates),'requeued':len(retried),'target_jobs':sum(r['job_id'] in targets for r in retried)}))


if __name__=='__main__':
    retry()
