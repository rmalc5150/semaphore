#!/usr/bin/env python3
"""Read-only live checkpoint/manifest and publication receipt reconciliation."""
import hashlib,json,os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from collection_storage import StorageSettings
from research_contract import digest

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'reports/live-coverage';OUT.mkdir(exist_ok=True)
def main():
 s=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=s.store();base=s.s3_prefix.rstrip('/')+'/'
 started=datetime.now(timezone.utc).isoformat()
 def listing(prefix):
  for page in store.client.get_paginator('list_objects_v2').paginate(Bucket=s.s3_bucket,Prefix=base+prefix):
   for o in page.get('Contents',[]):yield o['Key'][len(base):],o['Size']
 keys=[k for k,_ in listing('checkpoints/task_') if k.endswith('/head.json')]
 raw=dict(listing('raw/'))
 print(json.dumps({'stage':'inventory','heads':len(keys),'raw_objects':len(raw)}),flush=True)
 def get(key):
  obj=store.get(key)
  if obj is None:raise ValueError('missing_object')
  return json.loads(obj.body),hashlib.sha256(obj.body).hexdigest()
 def task_check(key):
  try:
   head,sha=get(key);task=head['task'];tid='task_'+digest(task)
   problems=[]
   if head['task_id']!=tid or key!=f'checkpoints/{tid}/head.json':problems.append('task_identity_mismatch')
   versions=[]
   for mk in head.get('terminal_history',[]):
    m,msha=get(mk);errors=[]
    if m.get('task')!=task or m.get('task_id')!=tid:errors.append('manifest_task_mismatch')
    batches=[b for p in m.get('pages',[]) for b in p.get('batches',[])]
    if sum(b['records'] for b in batches)!=m.get('record_count'):errors.append('record_count_mismatch')
    missing=[b['key'] for b in batches if raw.get(b['key'])!=b['bytes']]
    # Raw listing predates GETs; recheck objects newly committed during scan.
    for bk in list(missing):
     b=next(b for b in batches if b['key']==bk)
     try:
      result=store.client.head_object(Bucket=s.s3_bucket,Key=base+bk)
      if result['ContentLength']==b['bytes']:missing.remove(bk)
     except Exception:pass
    if missing:errors.append('raw_object_missing_or_size_mismatch')
    complete=m.get('status')=='complete' and m.get('exhausted') is True
    if complete and m.get('expected_records') is not None and m['expected_records']!=m['record_count']:errors.append('expected_count_mismatch')
    versions.append({'manifest':mk,'manifest_sha256':msha,'status':m.get('status'),'finished_at':m.get('finished_at'),'reason_code':m.get('reason_code'),'records':m.get('record_count'),'complete_metadata_valid':complete and not errors and not problems,'errors':errors,'missing_raw':missing,'batch_count':len(batches),'sample_batch':batches[0] if batches else None})
   if head.get('terminal_manifest') and head['terminal_manifest'] not in head.get('terminal_history',[]):problems.append('terminal_not_committed')
   return {'checkpoint':key,'checkpoint_sha256':sha,'task':task,'head_status':head['status'],'head_records':head.get('record_count'),'versions':versions,'errors':problems,'observed_at':datetime.now(timezone.utc).isoformat()}
  except Exception as exc:return {'checkpoint':key,'errors':[type(exc).__name__],'head_status':'audit_error'}
 count=0
 with (OUT/'checkpoints.jsonl').open('w') as f,ThreadPoolExecutor(max_workers=4) as pool:
  for row in pool.map(task_check,keys):
   f.write(json.dumps(row,separators=(',',':'))+'\n');count+=1
   if count%250==0:print(json.dumps({'stage':'checkpoints','done':count,'total':len(keys)}),flush=True)
 operationkeys=[k for k,_ in listing('operations/') if k.endswith('.json')]
 receiptkeys=[k for k in operationkeys if '/publication-receipts/' in k]
 def receipt_check(key):
  try:
   r,sha=get(key);v,vsha=get(r['verification_key']);errors=[]
   if vsha!=r.get('verification_sha256'):errors.append('verification_hash_mismatch')
   if v.get('status')!='verified' or v.get('release_id')!=r.get('release_id'):errors.append('verification_identity_mismatch')
   return {'receipt_key':key,'sha256':sha,'receipt':r,'errors':errors}
  except Exception as exc:return {'receipt_key':key,'errors':[type(exc).__name__]}
 with (OUT/'publication-receipts.jsonl').open('w') as f,ThreadPoolExecutor(max_workers=4) as pool:
  for i,row in enumerate(pool.map(receipt_check,receiptkeys),1):
   f.write(json.dumps(row,separators=(',',':'))+'\n')
   if i%250==0:print(json.dumps({'stage':'receipts','done':i,'total':len(receiptkeys)}),flush=True)
 patent_rows=[receipt_check(k) for k in operationkeys if '/athena-publication/months/' in k]
 (OUT/'patent-publication-receipts.json').write_text(json.dumps(patent_rows,indent=2)+'\n')
 import boto3
 glue=boto3.client('glue',region_name=s.region);catalog={}
 for cfgpath in (ROOT/'config').glob('*athena*.json'):
  cfg=json.loads(cfgpath.read_text());db=cfg.get('database')
  if not db or db in catalog:continue
  try:
   tables=[]
   for page in glue.get_paginator('get_tables').paginate(DatabaseName=db):
    tables.extend({'table':t['Name'],'location':t.get('StorageDescriptor',{}).get('Location'),'partition_keys':[p['Name'] for p in t.get('PartitionKeys',[])]} for t in page['TableList'])
   catalog[db]={'status':'accessible','tables':tables}
  except Exception as exc:catalog[db]={'status':'error','error_type':type(exc).__name__}
 access={'checked_at':datetime.now(timezone.utc).isoformat(),'glue_catalog':catalog,'reddit_credentials_in_process_environment':{k:bool(os.environ.get(k)) for k in ['REDDIT_CLIENT_ID','REDDIT_CLIENT_SECRET']},'reddit_note':'Checks this process environment only; no credential values exposed. Missing variables do not exclude credentials elsewhere.','search_rankings':'No configured provider/history contract in current requirements.'}
 (OUT/'access-catalog.json').write_text(json.dumps(access,indent=2)+'\n')
 # One newest and one oldest nonempty completed batch per source/dataset.
 samples={}
 for line in (OUT/'checkpoints.jsonl').open():
  row=json.loads(line)
  if 'task' not in row:continue
  key=(row['task']['source'],row['task']['dataset'])
  for v in row['versions']:
   if v['complete_metadata_valid'] and v['sample_batch']:
    item={'task':row['task'],'version':v};old=samples.setdefault(key,{'oldest':item,'newest':item})
    for label,cmp in [('oldest',lambda a,b:a<b),('newest',lambda a,b:a>b)]:
     if cmp(v['finished_at'],old[label]['version']['finished_at']):old[label]=item
 with (OUT/'raw-samples.jsonl').open('w') as f:
  for key,pair in samples.items():
   for label,item in pair.items():
    b=item['version']['sample_batch'];obj=store.get(b['key']);body=obj.body;records=[json.loads(line) for line in body.splitlines()]
    result={'source':key[0],'dataset':key[1],'selection':label,'manifest':item['version']['manifest'],'key':b['key'],'hash_valid':hashlib.sha256(body).hexdigest()==b['sha256'],'records_valid':len(records)==b['records'],'sample_records':len(records),'available_at_nonnull':sum(r.get('available_at') is not None for r in records),'point_in_time_true':sum(r.get('point_in_time_eligible') is True for r in records),'event_at_examples':[r.get('event_at') for r in records[:2]],'observed_at':datetime.now(timezone.utc).isoformat()}
    f.write(json.dumps(result)+'\n')
 summary={'started_at':started,'finished_at':datetime.now(timezone.utc).isoformat(),'checkpoint_count':len(keys),'raw_objects_listed':len(raw),'publication_receipts':len(receiptkeys),'sample_source_datasets':len(samples),'limitations':['Non-atomic snapshot while collectors continue; checkpoint reads individually timestamped.','All committed terminal versions examined; raw object size/existence checked, byte hashes only sampled.','Provider access inferred only at recorded successful/failed run time; no paid provider calls made.','No historical availability inferred from event dates.']}
 (OUT/'snapshot.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
