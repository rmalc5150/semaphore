"""Bounded S47 original-evidence capture, backfill receipts, and completion notification."""
import argparse
import fcntl
import hashlib
import json
import re
import sqlite3
from datetime import datetime,timedelta,timezone
from pathlib import Path
from urllib.request import HTTPRedirectHandler,build_opener
from zoneinfo import ZoneInfo

from collection_storage import StorageSettings,CollectionRun,AlreadyComplete,now,task_spec,write_json
from research_contract import ROOT,load_json,digest,seal_record
from regulatory_collection import EvidenceClient
from disclosure_collection import get_bytes
from nist_robotics import VERSION,ROOT_URL,canonical,parse_document

PREFIX='operations/nist-robotics/'


def replace(store,key,value):
    prior=store.get(key);return write_json(store,key,value,prior.token if prior else None)


def registry():
    db=sqlite3.connect(ROOT/'nist-robotics.sqlite3')
    db.executescript('''CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,mode TEXT,day TEXT,status TEXT,roots TEXT);
      CREATE TABLE IF NOT EXISTS docs(job TEXT,url TEXT,depth INTEGER,status TEXT DEFAULT 'pending',attempts INTEGER DEFAULT 0,
      retry_after TEXT DEFAULT '',error TEXT,payload TEXT,manifest TEXT,batch TEXT,PRIMARY KEY(job,url));
      CREATE TABLE IF NOT EXISTS excluded(job TEXT,url TEXT,reason TEXT,PRIMARY KEY(job,url));
      CREATE TABLE IF NOT EXISTS matches(job TEXT,day TEXT,status TEXT,PRIMARY KEY(job,day));
      CREATE TABLE IF NOT EXISTS control(key TEXT PRIMARY KEY,value TEXT);''')
    return db


class Redirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not canonical(newurl):raise ValueError('Non-NIST redirect excluded')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def enqueue(db,job,url,depth,config):
    if not canonical(url):return
    if db.execute('SELECT 1 FROM docs WHERE job=? AND url=?',(job,url)).fetchone():return
    reason='depth_limit' if depth>config['max_depth'] else 'document_limit' if db.execute('SELECT count(*) FROM docs WHERE job=?',(job,)).fetchone()[0]>=config['max_documents_per_job'] else None
    with db:
        if reason:db.execute('INSERT OR IGNORE INTO excluded VALUES (?,?,?)',(job,url,reason))
        else:
            db.execute('INSERT INTO docs(job,url,depth) VALUES (?,?,?)',(job,url,depth))
            db.execute("UPDATE jobs SET status='capturing' WHERE id=?",(job,))


def capture_daily_landing(db, store, settings, day):
    from grants_review_capture import capture_one
    from specialist_plan import jobs

    retry_key = 'landing-retry:' + day
    retry = db.execute('SELECT value FROM control WHERE key=?',(retry_key,)).fetchone()
    if retry and retry[0] > now():
        return None
    plan = load_json(ROOT/'config/specialist-inputs.json')
    plan['sources'] = [source for source in plan['sources'] if source['source']=='nist_robotics_methods']
    universe = load_json(ROOT/'config/company-universe.v0.5.json')
    taxonomy = load_json(ROOT/'config/sectors.v1.json')
    job = next((job for job in jobs(plan,universe,'daily',datetime.fromisoformat(day).date())
                if canonical(job['parameters']['url'])==ROOT_URL),None)
    if not job:
        return None
    result = capture_one(store,settings,universe,taxonomy,job,pages=1)
    if result.get('status')=='complete' and result.get('manifest'):
        return json.loads(store.get(result['manifest']).body)
    retry_at = datetime.fromtimestamp(result['retry_after'],timezone.utc).isoformat().replace('+00:00','Z')
    with db:
        db.execute('INSERT OR REPLACE INTO control VALUES (?,?)',(retry_key,retry_at))
    return None


def seed(db,store,config,mode,settings=None):
    day=datetime.now(ZoneInfo('Europe/Madrid')).date().isoformat()
    if mode=='daily':
        previous=db.execute("SELECT id FROM jobs WHERE mode='daily' AND status='capturing' ORDER BY day LIMIT 1").fetchone()
        if previous:return previous[0]
    if mode=='backfill':
        inventory=load_json(ROOT/config['inventory_file'])
        if digest(inventory)!=config['inventory_digest']:raise ValueError('Backfill input changed')
        job=config['job_id'];roots=[]
        for b in inventory['batches']:
            for line in get_bytes(store,b['key'],b['sha256']).splitlines():
                r=json.loads(line)
                roots.extend(r['payload'].get('source_evidence',[]))
    else:
        job='nist-daily-'+day
        if db.execute('SELECT 1 FROM control WHERE key=?',('seeded:'+job,)).fetchone():return job
        stored=store.get('operations/specialists/scheduler/daily.json')
        scheduler=json.loads(stored.body) if stored else {'jobs':{}}
        candidates=[r for r in scheduler['jobs'].values() if r['source']=='nist_robotics_methods' and r['status']=='complete' and datetime.fromisoformat(r['last_attempt'].replace('Z','+00:00')).astimezone(ZoneInfo('Europe/Madrid')).date().isoformat()==day]
        manifest=None
        if candidates:
            receipt=max(candidates,key=lambda r:r['last_attempt'])
            saved=store.get(receipt['manifest'])
            manifest=json.loads(saved.body) if saved else None
        if manifest is None and settings:
            manifest=capture_daily_landing(db,store,settings,day)
        if not manifest or manifest['status']!='complete' or not manifest['exhausted'] or datetime.fromisoformat(manifest['finished_at'].replace('Z','+00:00')).astimezone(ZoneInfo('Europe/Madrid')).date().isoformat()!=day:return None
        roots=[]
        for page in manifest['pages']:
            for b in page['batches']:
                for line in get_bytes(store,b['key'],b['sha256']).splitlines():roots.extend(json.loads(line)['payload'].get('source_evidence',[]))
    if db.execute('SELECT 1 FROM control WHERE key=?',('seeded:'+job,)).fetchone():return job
    with db:db.execute('INSERT OR IGNORE INTO jobs VALUES (?,?,?,?,?)',(job,mode,day,'capturing',json.dumps(roots)))
    enqueue(db,job,ROOT_URL,0,config)
    for ref in {r['sha256']:r for r in roots if r['source_url'].rstrip('/')==ROOT_URL}.values():
        document=parse_document(get_bytes(store,ref['key'],ref['sha256']),ROOT_URL)
        for link in document['links']:enqueue(db,job,link['url'],1,config)
    with db:db.execute('INSERT OR REPLACE INTO control VALUES (?,?)',('seeded:'+job,'complete'))
    return job


def commit(store,settings,source,identity,payload,job):
    universe=load_json(ROOT/'config/company-universe.v0.5.json');taxonomy=load_json(ROOT/'config/sectors.v1.json')
    day_match=re.search(r'20\d\d-\d\d-\d\d',job)
    day=day_match[0] if day_match else '2026-10-18'
    following=(datetime.fromisoformat(day)+timedelta(days=1)).date().isoformat()
    spec=task_spec(source,'specialist_inputs','daily',day+'T00:00:00Z',following+'T00:00:00Z',
        {'identity':identity,'job_id':job},VERSION,universe,taxonomy)
    try:run=CollectionRun.start(store,spec,universe,taxonomy,settings,resume=True)
    except AlreadyComplete as exc:
        m=json.loads(store.get(str(exc)).body);return str(exc),m['pages'][-1]['batches'][0]['key']
    if not run.exhausted:
        record=seal_record({'document_type':'collected_record','schema_version':'1.0','source':source,'dataset':'specialist_inputs',
          'source_record_id':identity,'source_record_id_basis':'documented_composite','source_url':payload['source_url'],
          'universe_version':universe['universe_version'],'company_ids':[],'product_ids':[],'person_ids':[],'listing_ids':[],
          'entity_match_status':'unresolved','event_at':None,'available_at':None,'source_updated_at':None,
          'ingested_at':now(),'availability_basis':'unknown','availability_evidence':[],'run_id':run.run_id,'payload':payload})
        run.commit_page([record],exhausted=True)
    manifest=run.finish('complete',expected_records=1)
    return manifest,run.state['pages'][-1]['batches'][0]['key']


def capture(db,store,settings,config,job):
    client=EvidenceClient(store,'nist_robotics_documents',opener=build_opener(Redirect()).open)
    for _ in range(config['documents_per_invocation']):
        row=db.execute("SELECT url,depth,attempts FROM docs WHERE job=? AND status IN ('pending','retry') AND retry_after<=? ORDER BY depth,url LIMIT 1",(job,now())).fetchone()
        if not row:break
        url,depth,attempts=row
        try:
            client.evidence=[];raw=client.get(url)
            if len(raw)>config['max_document_bytes']:raise ValueError('Document size cap')
            document=parse_document(raw,url)
            if len(document['text'])>2*1024*1024:
                document['text']=document['text'][:2*1024*1024];document['sections']=[];document['tables']=[];document['extraction_status']='text_index_truncated_original_archived'
            payload={'extraction_version':VERSION,'data':document,'source_url':url,'source_id':'S47','job_id':job,'source_evidence':client.evidence,
               'retrieved_at':now(),'point_in_time_eligible':False,'entity_link_status':'unreviewed'}
            manifest,batch=commit(store,settings,'nist_robotics_documents',digest([url,document['semantic_hash']]),payload,job)
            with db:db.execute("UPDATE docs SET status='done',payload=?,manifest=?,batch=?,error=NULL WHERE job=? AND url=?",(json.dumps(payload),manifest,batch,job,url))
            for link in document['links']:enqueue(db,job,link['url'],depth+1,config)
            print(json.dumps({'job':job,'captured':url,'kind':document['kind']}),flush=True)
        except Exception as exc:
            retry=(datetime.now(timezone.utc)+timedelta(minutes=15)).isoformat().replace('+00:00','Z')
            with db:db.execute('UPDATE docs SET status=?,attempts=attempts+1,retry_after=?,error=? WHERE job=? AND url=?',
              ('gap' if attempts+1>=config['max_attempts'] else 'retry',retry,type(exc).__name__+': '+str(exc)[:300],job,url))
    pending=db.execute("SELECT count(*) FROM docs WHERE job=? AND status NOT IN ('done','gap')",(job,)).fetchone()[0]
    if not pending:
        with db:db.execute("UPDATE jobs SET status='captured' WHERE id=?",(job,))
    report={'job_id':job,'updated_at':now(),'pending':pending,'counts':db.execute('SELECT status,count(*) FROM docs WHERE job=? GROUP BY status',(job,)).fetchall(),
      'excluded':db.execute('SELECT reason,count(*) FROM excluded WHERE job=? GROUP BY reason',(job,)).fetchall(),
      'scope':'NIST-only relevant HTML/PDF links, bounded depth and document count; historical snapshots do not reconstruct unavailable older linked documents.'}
    replace(store,PREFIX+'jobs/'+job+'/capture.json',report)
    (ROOT/'reports'/('nist-robotics-'+('backfill' if job==config['job_id'] else 'daily')+'-latest.json')).write_text(json.dumps(report,indent=2)+'\n')
    return report


def notify(db,store,settings,config,job):
    if job!=config['job_id'] or db.execute("SELECT status FROM jobs WHERE id=?",(job,)).fetchone()[0]!='captured':return
    if db.execute("SELECT 1 FROM control WHERE key='email_id'").fetchone():return
    if not db.execute("SELECT 1 FROM matches WHERE job=? AND status='complete'",(job,)).fetchone():return
    rows=db.execute("SELECT batch FROM docs WHERE job=? AND status='done'",(job,)).fetchall()
    with sqlite3.connect('file:'+str(ROOT/'committed-athena-index.sqlite3')+'?mode=ro',uri=True) as index:
        if not rows or any(not index.execute('SELECT 1 FROM verified_batches WHERE key=?',r).fetchone() for r in rows):return
    from committed_data_athena import query
    result=query(__import__('boto3').client('athena',region_name=settings.region),"SELECT count(*) FROM optima_collected_data.observations WHERE source='nist_robotics_documents' AND dataset='specialist_inputs' AND json_extract_scalar(payload_json,'$.extraction_version')='"+VERSION+"' AND json_extract_scalar(payload_json,'$.job_id')='"+job+"'")
    if int(result['rows'][0][0])!=len(rows):raise ValueError('NIST backfill Athena count mismatch')
    mapping_result=query(__import__('boto3').client('athena',region_name=settings.region),"SELECT count(DISTINCT json_extract_scalar(payload_json,'$.data.document_id')) FROM optima_collected_data.observations WHERE source='nist_robotics_product_matches' AND dataset='specialist_inputs' AND json_extract_scalar(payload_json,'$.job_id')='"+job+"'")
    if int(mapping_result['rows'][0][0])!=len(rows):return

    gaps=db.execute("SELECT url,error FROM docs WHERE job=? AND status='gap'",(job,)).fetchall()
    exclusions=db.execute('SELECT url,reason FROM excluded WHERE job=?',(job,)).fetchall()
    receipt={'job':job,'verified_at':now(),'document_count':len(rows),'gaps':gaps,'excluded_by_scope':exclusions,'athena':result,'mapping_athena':mapping_result,
       'extraction_outcomes':db.execute("SELECT json_extract(payload,'$.data.extraction_status'),count(*) FROM docs WHERE job=? AND status='done' GROUP BY 1",(job,)).fetchall(),
       'scope':'Pinned saved landing-page inventory, current retrievable linked evidence, max depth '+str(config['max_depth'])+' and max '+str(config['max_documents_per_job'])+' documents. Not a reconstructed historical NIST archive. Product matching/events are separate and may remain unresolved.'}
    replace(store,PREFIX+'jobs/'+job+'/completion.json',receipt)
    sns=__import__('boto3').client('sns',region_name=settings.region)
    subscriptions=[s for page in sns.get_paginator('list_subscriptions_by_topic').paginate(TopicArn=config['email_topic_arn']) for s in page['Subscriptions']]
    if not subscriptions or any(s['Protocol']!='email' or s['Endpoint']!=config['email_recipient'] or not s['SubscriptionArn'].startswith('arn:') for s in subscriptions):raise ValueError('NIST email recipient mismatch')
    message=sns.publish(TopicArn=config['email_topic_arn'],Subject='S47 evidence backfill complete'+(' - gaps recorded' if gaps else ' - verified'),Message=json.dumps(receipt,indent=2)+'\n\nSee S47_NIST_ROBOTICS.md and ENTITY_DISCOVERY_ROLLOUT_PLAN.md#sql-checks. Events are reviewable evidence candidates; no measured robot performance is inferred from a mention.')
    with db:db.execute("INSERT INTO control VALUES ('email_id',?)",(message['MessageId'],))


def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['daily','backfill'],required=True);a=p.parse_args()
    config=load_json(ROOT/'config/nist-robotics.json');settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store()
    with (ROOT/'.nist-robotics-capture.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        with registry() as db:
            job=seed(db,store,config,a.mode,settings)
            if job and a.mode=='daily' and db.execute('SELECT status FROM jobs WHERE id=?',(job,)).fetchone()==('captured',):
                print(json.dumps({'status':'current_day_captured','job':job}))
            elif job:
                capture(db,store,settings,config,job);notify(db,store,settings,config,job)
            else:print(json.dumps({'status':'waiting_for_completed_S47_capture_today'}))

if __name__=='__main__':main()
