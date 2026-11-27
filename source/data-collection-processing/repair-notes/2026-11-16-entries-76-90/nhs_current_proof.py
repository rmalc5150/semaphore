import os,json,hashlib,base64,io
from pathlib import Path
import boto3
from metadata_engine.evidence import evidence_for,object_bytes
from metadata_engine.streaming import session as streaming
from collection_storage import StorageSettings
from research_contract import ROOT,load_json
from specialist_inputs import collect
import public_source_capture as pc
b='data-collection-059416028963-us-east-1-an';base='research-data/constellation-backfill/repairs/entries-76-90-20261116/';s=boto3.client('s3',region_name='us-east-1');cfg=load_json(ROOT/'config/metadata-engine.json');before=json.loads(s.get_object(Bucket=b,Key=base+'before.json')['Body'].read());policies=json.loads(s.get_object(Bucket=b,Key=base+'policies.json')['Body'].read());sources={r['source']:r for r in load_json(ROOT/'config/constellation-public-sources.json')['sources']};out=json.loads(s.get_object(Bucket=b,Key=base+'capture-proof.json')['Body'].read())
def save():s.put_object(Bucket=b,Key=base+'capture-proof.json',Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256')
def receipt_evidence(row):
 record={'source':row['source'],'source_record_id':row['sha256'],'dataset':'public_documents','payload':{'source_evidence':[{'s3_uri':row['artifact_uri'],'sha256':row['sha256'],'source_url':row['source_url'],'retrieved_at':row['retrieved_at']}]}}
 with streaming():return evidence_for(record,policies[row['source']],s,b)
# Use the existing collection commit protocol for native prescribing rows.
settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();universe=load_json(ROOT/'config/company-universe.v0.5.json');taxonomy=load_json(ROOT/'config/sectors.v1.json');source='england_nhsbsa_prescribing_data';spec=next(r for r in load_json(ROOT/'config/specialist-inputs.json')['sources']if r['source']==source)
for mode,start,end,params in [('daily','2026-11-15','2026-11-16',{'release_selection':'latest_available'})]:
 job={**spec,'mode':mode,'start':start,'end':end,'parameters':{'url':spec['api'],**params}};result=collect(job,store,settings,universe,taxonomy,1);entry={'collection':result,'verified_rows':0,'batches':[]};out['native'][mode]=entry;save()
 if result['status']in ('complete','partial'):
  m=json.loads(store.get(result['manifest']).body)
  for page in m['pages']:
   for batch in page['batches']:
    key='research-data/'+batch['key'];rows=[json.loads(l)for l in object_bytes(s,b,key).splitlines()if l.strip()]
    for row in rows:evidence_for(row,policies[source],s,b);entry['verified_rows']+=1
    entry['batches'].append(key)
 save();print(source,mode,result,'verified',entry['verified_rows'],flush=True)

