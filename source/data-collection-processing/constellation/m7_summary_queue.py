"""Durable, fixed-purpose S3 queue for m7 gap audits and database summaries."""
import argparse,fcntl,json,time,uuid,threading
from datetime import datetime,timezone
from pathlib import Path
from botocore.exceptions import ClientError
from constellation.control import Control

KEY='research-data/constellation-backfill/summary-queue/jobs.json'
UNIT='optima-m7-summary-worker.service'
def stamp():return datetime.now(timezone.utc).isoformat()
def read(c):
    try:
        r=c.s3.get_object(Bucket=c.config['bucket'],Key=KEY)
        try:return json.loads(r['Body'].read()),r['ETag']
        finally:r['Body'].close()
    except ClientError as e:
        if e.response['Error']['Code'] not in ('NoSuchKey','404'):raise
        return {'jobs':[]},None
def mutate(c,fn):
    for _ in range(8):
        doc,etag=read(c);result=fn(doc)
        try:
            c.s3.put_object(Bucket=c.config['bucket'],Key=KEY,Body=json.dumps(doc).encode(),ServerSideEncryption='AES256',**({'IfMatch':etag}if etag else {'IfNoneMatch':'*'}))
            return result
        except ClientError as e:
            if e.response['Error']['Code'] not in ('PreconditionFailed','412','ConditionalRequestConflict'):raise
            time.sleep(.2)
    raise RuntimeError('summary queue contention')
def pending(c):
    return any(j['state'] in ('pending','running')for j in read(c)[0]['jobs'])
def enqueue(c,kind):
    def add(doc):
        existing=next((j for j in doc['jobs']if j['kind']==kind and j['state']in ('pending','running')),None)
        if existing is None:
            existing={'id':uuid.uuid4().hex,'kind':kind,'state':'pending','queued_at':stamp(),'attempts':0}
            doc['jobs'].append(existing)
        # Retain unfinished jobs and recent receipts; reports remain immutable.
        done=[j for j in doc['jobs']if j['state']in ('complete','failed')][-20:]
        doc['jobs']=[j for j in doc['jobs']if j['state']in ('pending','running')]+done
        return existing['id']
    return mutate(c,add)
def change(c,identity,**values):
    def update(doc):
        job=next(j for j in doc['jobs']if j['id']==identity);job.update(values)
    mutate(c,update)
def summarize(c,job):
    from constellation.database_diagnostic import run
    return run(c,job,change,stamp)
def work(c,kind=None):
    doc,_=read(c)
    candidates=[j for j in doc['jobs']if (kind is None or j['kind']==kind)and(j['state']=='pending'or(j['state']=='running'and j.get('lease_until',0)<time.time()))]
    if not candidates:return
    candidates.sort(key=lambda j:j.get('last_run_at',0))
    job=candidates[0]
    with Path('/opt/constellation/summary-worker/'+job['kind']+'.lock').open('a')as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        current=next(j for j in read(c)[0]['jobs']if j['id']==job['id'])
        if current['state']!='pending'and not(current['state']=='running'and current.get('lease_until',0)<time.time()):return
        return work_claimed(c,current)
def work_claimed(c,job):
    change(c,job['id'],state='running',lease_until=time.time()+300,attempts=job['attempts']+1,last_run_at=time.time(),last_error=job.get('error'),error=None)
    done=threading.Event()
    def heartbeat():
        while not done.wait(60):
            try:change(c,job['id'],lease_until=time.time()+300)
            except Exception as e:print('Summary heartbeat retry: '+type(e).__name__,flush=True)
    thread=threading.Thread(target=heartbeat,daemon=True);thread.start()
    try:
        if job['kind']=='gaps':
            from constellation.gaps import build
            report=build(c)
        elif job['kind']=='database':report=summarize(c,job)
        else:raise ValueError('Unknown summary kind')
        if report is None:return
        key=c.config['prefix']+'/summary-reports/'+job['id']+'.json'
        c.s3.put_object(Bucket=c.config['bucket'],Key=key,Body=json.dumps(report).encode(),ServerSideEncryption='AES256',IfNoneMatch='*')
        change(c,job['id'],state='complete',report_key=key,finished_at=stamp(),checkpoint=None)
        print(json.dumps({'job_id':job['id'],'kind':job['kind'],'report_key':key,'state':'complete'}),flush=True)
    except Exception as e:
        failures=job.get('failures',0)+1
        change(c,job['id'],state='failed'if failures>=3 else 'pending',failures=failures,error=type(e).__name__+': '+str(e)[:500])
        raise
    finally:done.set();thread.join(timeout=1)
def poll(c):
    for job in read(c)[0]['jobs']:
        if job['state']=='complete'and not job.get('promoted'):
            r=c.s3.get_object(Bucket=c.config['bucket'],Key=job['report_key'])
            try:body=r['Body'].read()
            finally:r['Body'].close()
            report=json.loads(body)
            if job['kind']=='gaps':
                report['evidence_uri']='s3://'+c.config['bucket']+'/'+job['report_key']
                dest='research-data/monitoring/health/constellation-gaps.json'
            else:dest='research-data/monitoring/health/database-summary.json'
            c.s3.put_object(Bucket=c.config['bucket'],Key=dest,Body=json.dumps(report).encode(),ServerSideEncryption='AES256')
            change(c,job['id'],promoted=True)
    if pending(c):
        from constellation.m7_lifecycle import STATE,dispatch
        with (STATE.parent/'m7-lifecycle.lock').open('a')as lock:
            fcntl.flock(lock,fcntl.LOCK_EX);dispatch(UNIT)
def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('gaps','database','poll','work'));p.add_argument('--kind',choices=('gaps','database'));a=p.parse_args();c=Control()
    if a.mode=='work':
        with Path('/opt/constellation/summary-worker/worker'+('-'+a.kind if a.kind else'')+'.lock').open('a')as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);work(c,a.kind)
    else:
        if a.mode in ('gaps','database'):enqueue(c,a.mode)
        poll(c)
if __name__=='__main__':main()
