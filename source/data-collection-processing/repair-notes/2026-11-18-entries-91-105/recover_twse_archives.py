"""Revalidate genuine pre-repair native snapshots instead of discarding them."""
import json,boto3,hashlib
from metadata_engine.regional_public import twse_rows
from metadata_engine.evidence import object_bytes
from regional_source_review import in_scope
from metadata_engine.runtime_db import Database,fingerprint
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');b=cfg['bucket'];base='research-data/constellation-backfill/repairs/entries-91-105-20261118/';source='taiwan_twse_mops_issuer_and_revenue_archives';jobs=json.loads(s.get_object(Bucket=b,Key=base+'jobs-before-'+source+'.json')['Body'].read());proof=json.loads(s.get_object(Bucket=b,Key=base+'capture-proof.json')['Body'].read());already={(r['record']['source_url'],r['record']['sha256'])for r in proof['public'][source]['results']};found={};skipped=[]
for job in jobs:
 if job['input_format']!='public_receipt':continue
 try:
  rows=[json.loads(l)for l in object_bytes(s,b,job['input_key'],2*1024**2).splitlines()if l.strip()]
  for r in rows:
   if r.get('source')!=source or not in_scope(r.get('source_url',''),source):continue
   identity=(r['source_url'],r['sha256'])
   if identity in already:continue
   native=twse_rows(r,s,b)
   if identity not in found or r['retrieved_at']<found[identity]['record']['retrieved_at']:found[identity]={'record':r,'validated_rows':len(native),'old_receipt':job['input_key']}
 except Exception as e:skipped.append({'job_id':job['job_id'],'reason':type(e).__name__+':'+str(e)[:200]})
queued=[]
for identity,e in found.items():
 r={**e['record'],'artifact_kind':'public_document','recovered_from_receipt':e['old_receipt']};key=base+'recovered-twse-receipts/'+r['sha256']+'.jsonl';raw=(json.dumps(r,sort_keys=True,ensure_ascii=False)+'\n').encode();s.put_object(Bucket=b,Key=key,Body=raw,ServerSideEncryption='AES256');etag=s.head_object(Bucket=b,Key=key)['ETag'];db.enqueue(source,key,etag,'public_receipt',200);queued.append({'job_id':fingerprint([source,key,etag,'public_receipt','2.0.3']),'receipt_key':key,'validated_rows':e['validated_rows'],'retrieved_at':r['retrieved_at'],'source_url':r['source_url'],'sha256':r['sha256']})
out={'recovered_unique_original_snapshots':len(queued),'queued':queued,'excluded':skipped,'scope':'Authentic earlier captured native TWSE snapshots with original retrieval dates preserved. Historical MOPS coverage before these retained snapshots remains unverified.'};s.put_object(Bucket=b,Key=base+'recovered-twse-archives.json',Body=json.dumps(out).encode(),ServerSideEncryption='AES256');print(json.dumps({'recovered_unique_original_snapshots':len(queued),'native_rows':sum(r['validated_rows']for r in queued),'excluded':len(skipped)}),flush=True)
