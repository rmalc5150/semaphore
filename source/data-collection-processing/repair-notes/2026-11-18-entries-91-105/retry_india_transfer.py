import json,time
from metadata_engine.runtime_db import Database
from metadata_engine.evidence import evidence_for
from metadata_engine.streaming import session as streaming
import public_source_capture as pc
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');b=cfg['bucket'];base='research-data/constellation-backfill/repairs/entries-91-105-20261118/';source='india_ibm_mineral_production';spec=next(r for r in json.load(open('config/constellation-public-sources.json'))['sources']if r['source']==source);url='https://ibm.gov.in/writereaddata/files/173329851267500950dda2eMSMP_September_2024_.pdf';out={}
for attempt in range(2):
 try:
  row,_=pc.capture(s,spec,{'url':url,'depth':1},'historical',publish_receipt=False)
  record={'source':source,'source_record_id':row['sha256'],'dataset':'public_documents','payload':{'source_evidence':[{'s3_uri':row['artifact_uri'],'sha256':row['sha256'],'source_url':url,'retrieved_at':row['retrieved_at']}]}}
  with streaming():artifacts=evidence_for(record,cfg['contracts'][source],s,b)
  key=pc.PREFIX+'/states/historical/'+source+'/'+spec['raw_content_revision']+'.json';state,etag=pc.read_json(s,key);s.put_object(Bucket=b,Key=base+'india-transfer-state-before.json',Body=pc.encode(state),ServerSideEncryption='AES256');state['failures'].pop(url,None);state['frontier']=[r for r in state['frontier']if r['url']!=url];state['done'][url]={'at':row['retrieved_at'],'sha256':row['sha256'],'kind':row['artifact_kind']};pc.put(s,key,pc.encode(state),IfMatch=etag);receipt=pc.PREFIX+'/athena/india-transfer-recovery-'+row['sha256']+'.jsonl';pc.put(s,receipt,pc.encode(row),'application/x-ndjson');out={'status':'verified_recovered','record':row,'artifacts':artifacts,'receipt_key':receipt};break
 except Exception as e:
  out={'status':'retry_pending','reason':type(e).__name__+':'+str(e)[:250],'url':url};time.sleep(2)
s.put_object(Bucket=b,Key=base+'india-transfer-recovery.json',Body=json.dumps(out).encode(),ServerSideEncryption='AES256');print(json.dumps({k:v for k,v in out.items()if k not in ('record','artifacts')}),flush=True)
