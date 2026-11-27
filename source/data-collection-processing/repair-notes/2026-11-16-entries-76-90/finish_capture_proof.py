import json,os,hashlib
from pathlib import Path
import boto3
from research_contract import ROOT,load_json
from metadata_engine.evidence import evidence_for,object_bytes
from metadata_engine.streaming import session as streaming
from metadata_engine.runtime_db import Database
from metadata_engine.worker import load_input
import public_source_capture as pc
s=boto3.client('s3',region_name='us-east-1');b='data-collection-059416028963-us-east-1-an';base='research-data/constellation-backfill/repairs/entries-76-90-20261116/';out=json.loads(s.get_object(Bucket=b,Key=base+'capture-proof.json')['Body'].read());before=json.loads(s.get_object(Bucket=b,Key=base+'before.json')['Body'].read());cfg=load_json(ROOT/'config/metadata-engine.json');sources={r['source']:r for r in load_json(ROOT/'config/constellation-public-sources.json')['sources']};db=Database(cfg)
def save():s.put_object(Bucket=b,Key=base+'capture-proof.json',Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256')
def verify(row):
 record={'source':row['source'],'dataset':'public_documents','source_record_id':row['sha256'],'payload':{'source_evidence':[{'s3_uri':row['artifact_uri'],'sha256':row['sha256'],'source_url':row['source_url'],'retrieved_at':row['retrieved_at']}]}}
 with streaming():return evidence_for(record,cfg['contracts'][row['source']],s,b)
selected={'international_federation_of_robotics_world_robotics':['https://ifr.org/img/worldrobotics/Executive_Summary_WR_2025_Industrial_Robots.pdf'],'iea_pvps_solar_deployment_reports':['https://iea-pvps.org/wp-content/uploads/2026/04/Snapshot-of-Global-PV-Markets-2026.pdf'],'france_has_medicine_assessment_opinions':['https://static.data.gouv.fr/resources/evaluation-des-medicaments/20261028-081437/asmr-20261028.csv','https://static.data.gouv.fr/resources/evaluation-des-medicaments/20261028-081404/smr-20261028.csv']}
for source,urls in selected.items():
 results=[]
 for url in urls:
  try:
   row,_=pc.capture(s,sources[source],{'url':url,'depth':1},'historical');artifacts=verify(row);key=pc.PREFIX+'/athena/review-20261116-'+row['sha256']+'.jsonl';pc.put(s,key,pc.encode(row),'application/x-ndjson');results.append({'status':'verified','receipt_key':key,'record':row,'artifacts':artifacts})
  except Exception as e:results.append({'status':'failed','url':url,'reason':type(e).__name__+':'+str(e)})
  out['public'][source]={'status':'verified'if any(x['status']=='verified'for x in results)else'failed','results':results};save();print(source,[(v['status'],v.get('reason'))for v in results],flush=True)
source='sia_wsts_public_semiconductor_sales';sample=before[source]['samples'][0];row=sample['record']
try:
 artifacts=verify(row);out['public'][source]={'status':'verified','receipt_key':sample['input_key'],'record':row,'artifacts':artifacts,'availability_note':'Provider removed this older URL (404); complete saved original remains verified. Daily collection follows current billings-index links.'}
except Exception as e:out['public'][source]={'status':'failed','reason':type(e).__name__+':'+str(e)}
save();print(source,out['public'][source]['status'],out['public'][source].get('reason'),flush=True)
source='arxiv';checks=[]
for job in before[source]['failed_jobs']:
 try:
  rows,raw,m=load_input(s,b,job,db)
  for row in rows:evidence_for(row,cfg['contracts'][source],s,b)
  checks.append({'job_id':job['job_id'],'input_key':job['input_key'],'status':'verified','rows_sampled':len(rows)})
 except Exception as e:checks.append({'job_id':job['job_id'],'status':'failed','reason':type(e).__name__+':'+str(e)})
out[source]=checks;save();print(source,checks,flush=True)
