"""Complete the scoped repair after the lifecycle controller wakes m7."""
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

from botocore.exceptions import ClientError
from ops import B, BASE, M7, P, session

ROOT=P.resolve().parents[1]
TIMER='optima-source-review-106-120.timer'
STATE=P/'deployment-state.json'
s3=session.client('s3')
ssm=session.client('ssm')


def s3_json(name, absent=None):
    try:
        with s3.get_object(Bucket=B,Key=BASE+name)['Body'] as content:
            return json.load(content)
    except ClientError as error:
        if error.response['Error']['Code'] in ('NoSuchKey','404'):
            return absent
        raise


def save_s3(name, value):
    s3.put_object(Bucket=B,Key=BASE+name,Body=json.dumps(value,default=str,ensure_ascii=False).encode(),ServerSideEncryption='AES256')


def save_state(state):
    state['updated_at']=datetime.now(timezone.utc).isoformat()
    temporary=STATE.with_suffix('.tmp')
    temporary.write_text(json.dumps(state,indent=2,default=str)+'\n')
    temporary.replace(STATE)


def save_config(path, value):
    backup=P/'configuration-before'/path.name
    backup.parent.mkdir(exist_ok=True)
    if path.exists() and not backup.exists():
        backup.write_bytes(path.read_bytes())
    temporary=path.with_name(path.name+'.source-review')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    os.chown(temporary,1000,1000)
    temporary.replace(path)


def available():
    r=session.client('ec2').describe_instances(InstanceIds=[M7])['Reservations'][0]['Instances'][0]
    if r['State']['Name']!='running':
        return False
    rows=ssm.describe_instance_information(Filters=[{'Key':'InstanceIds','Values':[M7]}])['InstanceInformationList']
    return bool(rows and rows[0]['PingStatus']=='Online')


def send(action):
    plan=s3_json('deployment-plan.json')
    statement=(
        'import boto3,hashlib,sys;'
        f"body=boto3.client('s3',region_name='us-east-1').get_object(Bucket={B!r},Key={BASE+'worker_deploy.py'!r})['Body'].read();"
        f"assert hashlib.sha256(body).hexdigest()=={plan['worker_deploy_sha256']!r};"
        f"sys.argv=['worker_deploy.py',{action!r}];"
        "exec(compile(body,'worker_deploy.py','exec'),{'__name__':'__main__'})"
    )
    command='/opt/constellation/legacy-venv/bin/python -c '+shlex.quote(statement)
    return ssm.send_command(InstanceIds=[M7],DocumentName='AWS-RunShellScript',
                            Parameters={'commands':[command],'executionTimeout':['240']},
                            TimeoutSeconds=270)['Command']['CommandId']


def result(identity):
    try:
        return ssm.get_command_invocation(CommandId=identity,InstanceId=M7)
    except ssm.exceptions.InvocationDoesNotExist:
        return {'Status':'Pending'}


def activate(sources, proof):
    from constellation.control import Control
    from constellation.historical_guard import dispatch_guard
    from constellation.legacy_dispatch import dispatch
    from constellation.legacy_routes import manifest, specification
    from metadata_engine.controller import register_contract
    from metadata_engine.runtime_db import Database, fingerprint

    policies=s3_json('policies.json')
    updates=s3_json('capture-updates.json')
    active_sources=set(sources)
    config_path=ROOT/'config/metadata-engine.json'
    config=json.loads(config_path.read_text())
    config['contracts'].update({s:policies[s] for s in sources})
    config.setdefault('verified_source_failure_handling',{}).update({s:'queue_by_source_date' for s in sources})
    config['build_sha256']=hashlib.sha256(b''.join(p.read_bytes() for p in sorted((ROOT/'metadata_engine').glob('*.py')))).hexdigest()
    database=Database(config,session=session)
    targets={}
    census='us_census_international_trade_api'
    for source in sources:
        checks=proof[source]
        form='legacy_batch' if source==census else 'public_receipt'
        # One verified batch for each mode is enough for the publication check.
        references=[(mode, checks[mode][0]['key']) for mode in ('daily','historical')]
        etags={key:s3.head_object(Bucket=B,Key=key)['ETag'] for _,key in references}
        with database.tx() as cursor:
            cursor.execute('SELECT * FROM engine_sources WHERE source_key=%s FOR UPDATE',(source,))
            control=cursor.fetchone()
            if not control or control['state'] in ('owner_paused','access_layer'):
                continue
            cursor.execute("SELECT job_id FROM engine_jobs WHERE source_key=%s AND state='running' AND lease_until>=UTC_TIMESTAMP(6) LIMIT 1",(source,))
            if cursor.fetchone():
                raise RuntimeError('source_lease_active:'+source)
            cursor.execute("SELECT * FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s AND contract_version<>'2.0.3' AND state IN ('queued','retry','raw_failed','uncommitted') FOR UPDATE",(source,))
            old=cursor.fetchall()
            backup_key='before-contract/'+source+'.json'
            if s3_json(backup_key) is None:
                save_s3(backup_key,{'source':control,'jobs':old})
            register_contract(database,policies[source],cursor)
            if source==census:
                # Keep the committed batches that predate the repaired validator.
                for job in old:
                    if job['input_format']=='legacy_batch':
                        database.enqueue(source,job['input_key'],job['input_etag'],'legacy_batch',70,cursor)
            cursor.execute("UPDATE engine_jobs SET state='superseded',reason=%s,finished_at=UTC_TIMESTAMP(6) WHERE source_key=%s AND contract_version<>'2.0.3' AND state IN ('queued','retry','raw_failed','uncommitted')",
                           ('replaced_by_verified_census_contract' if source==census else 'original_provider_route_replaces_legacy_discovery',source))
            cursor.execute("UPDATE engine_sources SET state='enabled',consecutive_raw_failures=0,last_reason=NULL,updated_at=UTC_TIMESTAMP(6) WHERE source_key=%s AND state='raw_stopped'",(source,))
            targets[source]=[]
            for mode,key in references:
                database.enqueue(source,key,etags[key],form,500,cursor)
                identity=fingerprint([source,key,etags[key],form,'2.0.3'])
                cursor.execute("UPDATE engine_jobs SET priority=500 WHERE job_id=%s AND state IN ('queued','retry')",(identity,))
                targets[source].append({'job_id':identity,'mode':mode,'input_key':key})
    save_config(config_path,config)
    path=ROOT/'config/constellation-public-sources.json'
    document=json.loads(path.read_text())
    document['sources']=[{**row,**updates[row['source']]} if row['source'] in targets and row['source'] in updates else row
                         for row in document['sources']]
    save_config(path,document)
    install_daily({name:source for name,source in s3_json('daily-worker-map.json').items() if source in targets})
    collection=Control(session=session)
    historical=[]
    with dispatch_guard(collection) as acquired:
        if acquired and collection.allowed():
            for row in manifest()['routes']:
                sources_to_job=[s for s in targets if s in row['unit']]
                if not sources_to_job or not row['execution_enabled']:
                    continue
                outcome=dispatch_revised_route(collection,row)
                historical.append(outcome)
    info={'targets':targets,'historical':historical,'enabled_sources':list(targets),'excluded_after_proof':sorted(active_sources-set(targets))}
    save_s3('activation.json',info)
    (P/'activation.json').write_text(json.dumps(info,indent=2)+'\n')


def dispatch_revised_route(collection,row):
    from constellation.legacy_routes import specification
    key='legacy:'+row['unit']
    with collection.db() as cursor:
        cursor.execute("SELECT job_id FROM backfill_jobs WHERE source_key=%s AND status IN ('pending','running','retryable_failed') AND attempts<3 LIMIT 1",(key,))
        existing=cursor.fetchone()
    identity=existing['job_id'] if existing else collection.register(specification(row,'entries-106-120-20261120'))
    with collection.db() as cursor:
        cursor.execute("UPDATE backfill_jobs SET updated_at=0,next_attempt_at=0 WHERE job_id=%s AND status IN ('pending','retryable_failed')",(identity,))
    return {'unit':row['unit'],'job_id':identity,'prior_job_retained':bool(existing)}


def install_daily(jobs):
    if not jobs:
        return
    config=ROOT/'config/m7-public-file-jobs.json'
    previous=json.loads(config.read_text()) if config.exists() else {}
    save_config(config,{**previous,**jobs})
    system=Path('/etc/systemd/system')
    template=(system/'optima-public-ndb-daily.service').read_text()
    timer_template=(system/'optima-public-ndb-daily.timer').read_text()
    units=[]
    for name in jobs:
        unit='optima-'+name
        (system/(unit+'.service')).write_text(template.replace('public-ndb-daily',name))
        (system/(unit+'.timer')).write_text(timer_template.replace('public-ndb-daily',name))
        units.append(unit)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemd-analyze','verify',*[u+'.service' for u in units],*[u+'.timer' for u in units]],check=True)
    subprocess.run(['systemctl','enable','--now',*[u+'.timer' for u in units]],check=True)
    subprocess.run(['systemctl','start','--no-block',*[u+'.service' for u in units],'constellation-public-daily.service'],check=True)


def terminal(state, status, **values):
    state.update(phase=status,**values)
    save_state(state)
    save_s3('deployment-result.json',state)
    subprocess.run(['systemctl','stop',TIMER],check=False)


def tick(state):
    phase=state['phase']
    if phase in ('complete','partial','failed','expired'):
        subprocess.run(['systemctl','stop',TIMER],check=False)
        return
    if time.time()-state['created_at']>26*3600:
        terminal(state,'expired',reason='worker_validation_did_not_finish_within_26_hours')
        return
    if not available():
        if not STATE.exists():
            save_state(state)
        return
    if phase=='waiting_for_scheduled_boot':
        state.update(phase='launching_raw_proof',command=send('prepare'))
    elif phase in ('launching_raw_proof','installing_worker','launching_publication'):
        reply=result(state['command'])
        if reply['Status'] not in ('Success','Failed','TimedOut','Cancelled'):
            return
        if reply['Status']!='Success':
            if phase=='launching_raw_proof' and 'worker_batch_is_paused' in reply['StandardErrorContent']:
                state.update(phase='waiting_for_scheduled_boot',command=None)
                save_state(state)
                return
            terminal(state,'failed',command_status=reply['Status'],error=reply.get('StandardErrorContent','')[-2600:])
            return
        if phase=='installing_worker':
            state['worker_install']=reply['StandardOutputContent']
            proof=s3_json('worker-raw-proof.json')['sources']
            activate(state['sources'],proof)
            state.update(phase='launching_publication',command=send('publish'))
        else:
            state.update(phase='waiting_for_raw_proof' if phase=='launching_raw_proof' else 'waiting_for_publication',unit_started=time.time())
    elif phase=='waiting_for_raw_proof':
        proof=s3_json('worker-raw-proof.json',{})
        if not proof.get('finished'):
            if time.time()-state['unit_started']>28*60:
                terminal(state,'partial',reason='worker_raw_proof_did_not_finish',proof=proof)
            return
        from source_pauses import is_paused
        sources=sorted(s for s,values in proof['sources'].items() if values['validated_both_modes'] and not is_paused(s))
        if not sources:
            terminal(state,'partial',reason='no_source_passed_both_raw_proofs',proof=proof)
            return
        save_s3('activation-scope.json',{'sources':sources})
        state.update(phase='installing_worker',sources=sources,command=send('install'))
    elif phase=='waiting_for_publication':
        publication=s3_json('worker-publication.json',{})
        if not publication.get('finished'):
            if time.time()-state['unit_started']>28*60:
                terminal(state,'partial',reason='worker_publication_did_not_finish')
            return
        state.update(phase='verifying_capture_and_athena',verification_started=time.time())
    elif phase=='verifying_capture_and_athena':
        from verify_live import verify
        status, evidence=verify()
        save_s3('live-verification.json',evidence)
        if status=='complete' or time.time()-state['verification_started']>45*60:
            from update_review import write
            write(evidence)
            terminal(state,status)
            return
    save_state(state)


def main():
    with (P/'deploy.lock').open('a') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            return
        state=json.loads(STATE.read_text()) if STATE.exists() else {'phase':'waiting_for_scheduled_boot','created_at':time.time()}
        try:
            tick(state)
        except Exception as error:
            state['last_error']=type(error).__name__+': '+str(error)[:1200]
            state['consecutive_retry_errors']=state.get('consecutive_retry_errors',0)+1
            save_state(state)
            if state['consecutive_retry_errors']>=4:
                terminal(state,'partial',reason=state['last_error'])
            raise
        else:
            if state.pop('consecutive_retry_errors',None) is not None:
                state.pop('last_error',None)
                save_state(state)


if __name__=='__main__':
    main()
