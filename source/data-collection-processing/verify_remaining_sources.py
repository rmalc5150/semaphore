"""Independent live receipt, count and payload checks for six repaired sources."""
import json,time,hashlib
from pathlib import Path
import boto3
from collection_storage import StorageSettings
P=Path('repair-notes/2026-10-21-remaining-sources');store=StorageSettings.load('config/collection-storage.s3.json').store();a=boto3.client('athena',region_name='us-east-1')
old=json.loads(Path('repair-notes/2026-10-21-individual-replays/athena-receipts.json').read_text());targets={x['step']:x['job_id'] for x in old if x['step']!='eia-retail'};targets['eia-generators']='5b088153420b49d5c8a490ab6e9b690bff487f68a05ca0cabd728e7664e6c913'
def query(sql):
 q=a.start_query_execution(QueryString=sql,WorkGroup='optima-specialist-inputs',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}},ResultConfiguration={'OutputLocation':'s3://data-collection-059416028963-us-east-1-an/research-data/athena-results/specialists/'})['QueryExecutionId']
 for _ in range(180):
  r=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];s=r['Status']['State']
  if s=='SUCCEEDED':return {'query_id':q,'result':a.get_query_results(QueryExecutionId=q)['ResultSet'],'bytes_scanned':r['Statistics'].get('DataScannedInBytes')}
  if s in ('FAILED','CANCELLED'):raise RuntimeError(str(r['Status']))
  time.sleep(1)
 raise RuntimeError('Query still running '+q)
out=[]
for name,identity in targets.items():
 obj=store.get('operations/specialists/publication-receipts/'+identity+'.json');assert obj,name;receipt=json.loads(obj.body);assert receipt['status']=='verified'
 ev=store.get(receipt['verification_key']);assert hashlib.sha256(ev.body).hexdigest()==receipt['verification_sha256']
 where=" FROM optima_specialist_inputs.source_observations_windows WHERE window_id='"+identity+"'"
 count=query('SELECT count(*)'+where);sample=query('SELECT *'+where+' LIMIT 1')
 n=int(count['result']['Rows'][1]['Data'][0]['VarCharValue']);expected=int(next(v[1] for v in receipt['query']['rows'] if v[0]=='source_observations'));assert n==expected,(name,n,expected)
 (P/(name+'-athena-sample.json')).write_text(json.dumps(sample,indent=2))
 out.append({'source':name,'window_id':identity,'records':n,'count_query_id':count['query_id'],'sample_query_id':sample['query_id'],'receipt_hash_verified':True});(P/'fresh-athena-checks.json').write_text(json.dumps(out,indent=2));print(json.dumps(out[-1]),flush=True)
