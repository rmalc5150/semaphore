"""One isolated historical invocation at a time; no daily schedules on c7i."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import threading
import time
import uuid

from constellation.control import Control, canonical
from constellation.legacy_routes import route, validate_spec
from constellation.worker import emit, put_verified
from constellation.coverage_scope import specialist_scope

STOP=threading.Event()


def checkpoint_events(body,unit):
    events=[]
    for line in body.splitlines():
        try:event=json.loads(line)
        except (ValueError,UnicodeDecodeError):continue
        if isinstance(event,dict) and event.get('stage')=='s3_checkpoint_verified' and event.get('unit')==unit:
            events.append(event)
    return events


def execute(control,job):
    spec=json.loads(job['spec_json']);validate_spec(spec)
    row=route(spec['parameters']['unit'])
    identity=job['job_id'];token=job['lease_token']
    root=Path('/opt/constellation/legacy')/row['unit']
    base=Path('/dev/shm/constellation-legacy')/row['unit']
    base.mkdir(parents=True,exist_ok=True)
    prefix=control.config['prefix']+'/legacy-runtime/'+row['unit']
    env=dict(os.environ,OPTIMA_S3_RUNTIME_ROOT=str(root),OPTIMA_S3_RUNTIME_BASE=str(base),
        OPTIMA_S3_RUNTIME_PREFIX=prefix,OPTIMA_S3_RUNTIME_SEED_KEY=control.config['legacy_seed_key'],
        OPTIMA_S3_RUNTIME='0',PYTHONPATH=str(root),CONSTELLATION_ROLE='worker',
        CONSTELLATION_SHARED_HTTP_LIMITS='1',PYTHONDONTWRITEBYTECODE='1')
    if row.get('specialist_source'):
        env['CONSTELLATION_SPECIALIST_SCHEDULER_PREFIX']='constellation-backfill/specialist-schedulers/'+row['unit']
        env['CONSTELLATION_SPECIALIST_DISCOVERY_PREFIX']='constellation-backfill/specialist-discovered-jobs/'
        env['CONSTELLATION_SPECIALIST_PUBLICATION_PREFIX']='constellation-backfill/specialist-publication-queue/'
        env['CONSTELLATION_SPECIALIST_PLAN']=str(root/'config/constellation-specialist-historical.json')
    env['CONSTELLATION_VERIFY_MISSING_S3_KEYS']='1'
    env['CONSTELLATION_OPERATION_RECEIPT_PREFIX']='constellation-backfill/legacy-operation-receipts/'+row['unit']
    argv=[str(root/'.venv/bin/python'),'-B',str(root/'s3_runtime.py'),'--unit',row['unit'],'--',
        str(root/'.venv/bin/python'),'-B',str(root/row['argv'][0]),*row['argv'][1:]]
    log=Path('/opt/constellation/tmp')/(identity+'.log')
    stopped=False;lost=threading.Event();done=threading.Event()
    def renew():
        while not done.wait(30):
            try:control.renew(identity,token)
            except Exception:
                lost.set();return
    heartbeat=threading.Thread(target=renew,daemon=True);heartbeat.start()
    process=None
    try:
        with log.open('wb') as output:
            process=subprocess.Popen(argv,cwd=root,env=env,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
            deadline=time.monotonic()+row['timeout_seconds']
            interrupted=None
            next_pause_check=0
            while process.poll() is None:
                if time.monotonic()>=next_pause_check:
                    paused=not control.allowed(identity)
                    next_pause_check=time.monotonic()+5
                if STOP.is_set() or lost.is_set() or time.monotonic()>deadline or paused:
                    if interrupted is None:
                        os.killpg(process.pid,signal.SIGINT);interrupted=time.monotonic();stopped=True
                    elif time.monotonic()-interrupted>150:
                        os.killpg(process.pid,signal.SIGKILL)
                time.sleep(.5)
        # A retained pending marker means RAM contains uncommitted state. Keep
        # this service's workspace intact and retry recovery before more work.
        body=log.read_bytes()
        checkpoints=checkpoint_events(body,row['unit'])
        checkpointed=False
        def state_object(key):
            response=control.s3.get_object(Bucket=control.config['bucket'],Key=key)
            try:return json.loads(response['Body'].read())
            finally:response['Body'].close()
        if checkpoints and not (base/'pending.json').exists():
            expected=checkpoints[-1]['run_id']
            current=state_object(prefix+'/current.json')
            immutable=state_object(prefix+'/manifests/'+expected+'.json')
            checkpointed=(current==immutable and current.get('run_id')==expected and current.get('unit')==row['unit'])
        coverage_windows=[]
        route_drained=False
        for line in body.decode('utf-8',errors='replace').splitlines():
            try:event=json.loads(line)
            except ValueError:continue
            if not isinstance(event,dict) or not event.get('report_key'):continue
            key='research-data/'+event['report_key']
            if not key.startswith(control.config['prefix']+'/legacy-operation-receipts/'):continue
            report=state_object(key)
            if report.get('collector')=='public_document_capture':
                route_drained=report.get('route_drained',False)
            if report.get('mode')=='historical' and 'remaining_jobs' in report:
                route_drained=report['remaining_jobs']==0
                for window in report.get('outcomes',[]):
                    coverage_windows.append({'scope':specialist_scope(window),'scope_version':2,
                        'start':window['start'],'end':window['end_exclusive'],'status':window['status'],
                        'reason':window.get('reason'),'evidence_uri':'s3://'+control.config['bucket']+'/'+key,'updated_at':time.time()})
            entries=report.get('sources',{})
            if entries and all(e.get('next_date','')>=spec['end'] for e in entries.values()):route_drained=True
            for source,entry in entries.items():
                for window in entry.get('windows',[]):
                    coverage_windows.append({'scope':'|'.join((source,report['stream_id'],'configured_legacy_scope')),
                        'start':window['start'],'end':window['end'],'status':window['status'],
                        'reason':window.get('reason'),'evidence_uri':'s3://'+control.config['bucket']+'/'+key,
                        'updated_at':time.time()})
        saved=put_verified(control,control.config['prefix']+'/legacy-reports/'+identity+'/'+uuid.uuid4().hex+'.log',body,'text/plain')
        success=process.returncode in (0,2) and checkpointed and not lost.is_set() and not stopped
        result={'route_drained':route_drained,'coverage_windows':coverage_windows,'execution_kind':'legacy_invocation','coverage_status':'not_audited',
            'checkpoint_verified':checkpointed,'report_uri':saved['uri'],'exit_code':process.returncode,
            'legacy_unit':row['unit'],'runtime_prefix':prefix,
            'coverage_note':'A checkpointed bounded invocation is not complete historical source coverage.'}
        if not lost.is_set():
            control.finish(identity,token,'succeeded' if success else 'blocked' if job['attempts']>=3 else 'retryable_failed',result)
        emit('legacy_invocation_finished',job_id=identity,**result)
    finally:
        done.set();heartbeat.join(timeout=2)
        if process and process.poll() is None:os.killpg(process.pid,signal.SIGKILL)


def main():
    for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,lambda *a:STOP.set())
    control=Control();emit('legacy_worker_ready',collection_enabled=control.allowed())
    while not STOP.is_set():
        job=None
        try:
            job=control.claim_next(socket.gethostname()+':legacy:'+str(os.getpid()),kind=os.environ.get('CONSTELLATION_EXECUTOR_KIND','legacy'))
            if job:execute(control,job)
            else:STOP.wait(15)
        except Exception as exc:
            if job:
                try:
                    control.finish(job['job_id'],job['lease_token'],'blocked' if job['attempts']>=3 else 'retryable_failed',
                        {'execution_kind':'legacy_invocation','checkpoint_verified':False,'coverage_status':'not_audited',
                         'reason':'executor_verification_error','error':type(exc).__name__})
                except Exception:pass  # Expired leases cannot commit; reconciliation retains the failure.
            emit('legacy_worker_error',error=type(exc).__name__,reason=str(exc)[:250]);STOP.wait(15)


if __name__=='__main__':main()
