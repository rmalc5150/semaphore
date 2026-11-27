import json,boto3
from pathlib import Path
from decimal import Decimal
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an'
def get(k):return json.loads(s.get_object(Bucket=b,Key='research-data/'+k)['Body'].read())
w=json.loads((p/'worker-before.json').read_text())
for unit in ['optima-collection-daily.service','optima-authenticated-processing.service']:
 print('DETAIL',unit)
 for rr in w['jobs'].get(unit,{}).get('reports',[])[-1:]:
  v=rr['value'];print('TOP',list(v))
  epochs=v.get('universe_epochs',[v])
  for e in epochs:
   print('EPOCH',e.get('stream_id'),e.get('origin'),e.get('end_exclusive'))
   for source,row in e.get('sources',{}).items():
    if source in ('sec','hkex-filings','documents'):print('SOURCE',source,'next',row.get('next_date'),'windows',row.get('windows'))
# Raw evidence is in the failed run's failure.json, not the terminal manifest.
for f in p.glob('market-bad*'):
 m=json.loads(f.read_text());prefix='manifests/collection_runs/source=eodhd_market/dataset=market_records/'+m['run_id']+'/'
 listing=s.list_objects_v2(Bucket=b,Prefix='research-data/'+prefix)
 for obj in listing.get('Contents',[]):
  if obj['Key'].endswith('failure.json'):
   d=get(obj['Key'][14:]);(p/(f.stem+'-failure.json')).write_text(json.dumps(d,indent=2));print('FAILURE',f.stem,json.dumps(d)[:700])
