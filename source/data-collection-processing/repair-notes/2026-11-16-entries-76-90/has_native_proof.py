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
existing=json.loads(s.get_object(Bucket=b,Key=base+'has-existing-originals.json')['Body'].read());results=[]
for ref in existing:
 try:
  artifacts=receipt_evidence(ref['record']);results.append({**ref,'status':'verified','artifacts':artifacts})
 except Exception as e:results.append({**ref,'status':'failed','reason':type(e).__name__+':'+str(e)})
if results:out['public']['france_has_medicine_assessment_opinions']={'status':'verified'if any(v['status']=='verified'for v in results)else'failed','results':results};save()
print(json.dumps({'has':[(v['status'],v.get('reason'))for v in results],'nhs':out['native']['daily']},default=str),flush=True)
