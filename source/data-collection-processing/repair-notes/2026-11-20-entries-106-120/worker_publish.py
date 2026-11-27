"""Process and publish exact verified replacement jobs on the worker."""
from datetime import datetime, timezone
import json
import time
import uuid

from metadata_engine.controller import publish
from metadata_engine.runtime_db import Database
from metadata_engine.streaming import session as streaming
from metadata_engine.worker import process
from worker_proof import B, BASE, get, save

cfg=json.load(open('config/metadata-engine.json'))
db=Database(cfg)
s3=db.session.client('s3')
targets=get('activation.json')['targets']
out={}

def claim(source, identity):
    with db.tx() as cursor:
        cursor.execute('SELECT state FROM engine_sources WHERE source_key=%s FOR UPDATE',(source,))
        if cursor.fetchone()['state']!='enabled':
            return None
        cursor.execute('SELECT * FROM engine_jobs WHERE source_key=%s AND job_id=%s FOR UPDATE',(source,identity))
        job=cursor.fetchone()
        if job['state'] not in ('queued','retry'):
            return None
        cursor.execute("SELECT 1 FROM engine_jobs WHERE source_key=%s AND state='running' AND lease_until>=UTC_TIMESTAMP(6) LIMIT 1",(source,))
        if cursor.fetchone():
            return None
        token=str(uuid.uuid4())
        cursor.execute("UPDATE engine_jobs SET state='running',lease_token=%s,lease_until=DATE_ADD(UTC_TIMESTAMP(6),INTERVAL 10 MINUTE),attempts=attempts+1 WHERE job_id=%s",(token,identity))
        job['lease_token']=token
        return job

for source, items in targets.items():
    result={'jobs':[],'errors':[]}
    out[source]=result
    for item in items:
        identity=item['job_id']
        try:
            job=claim(source,identity)
            if job:
                with streaming():
                    process(db,s3,cfg,job)
            with db.tx() as cursor:
                cursor.execute('SELECT job_id,state,output_rows,reason FROM engine_jobs WHERE job_id=%s',(identity,))
                result['jobs'].append(cursor.fetchone())
        except Exception as e:
            result['errors'].append(type(e).__name__+': '+str(e)[:220])
    accepted=[r['job_id'] for r in result['jobs'] if r['state']=='accepted' and r['output_rows']>0]
    try:
        for offset in range(0,len(accepted),5):
            publish(db,source_key=source,job_ids=accepted[offset:offset+5])
    except Exception as e:
        result['errors'].append(type(e).__name__+': '+str(e)[:220])
    save('worker-publication.json',{'sources':out,'finished':False})
save('worker-publication.json',{'sources':out,'finished':True})
