import json,hashlib
from pathlib import Path
import boto3
from collection_storage import StorageSettings
from research_contract import ROOT,load_json
from market_operations import MarketOperations
P=ROOT/'repair-notes/2026-10-21-market-coverage'
s3=boto3.client('s3',region_name='us-east-1');bucket='data-collection-059416028963-us-east-1-an'
index=json.loads(s3.get_object(Bucket=bucket,Key='research-data/operations/s3-runtime/current.json')['Body'].read())
cfg=load_json(ROOT/'config/market-operations.json')
e=index['paths'][cfg['universe']];raw=s3.get_object(Bucket=bucket,Key=e['key'])['Body'].read()
assert hashlib.sha256(raw).hexdigest()==e['sha256']
u=json.loads(raw);(P/'universe.json').write_text(json.dumps(u))
settings=StorageSettings.load(ROOT/cfg['storage_config']);store=settings.store()
ops=MarketOperations(store,settings,cfg,u,load_json(ROOT/cfg['taxonomy']))
out={'prefix':ops.prefix,'listings':ops.symbols}
for name in ['daily','historical','coverage-exclusions']:
 o=store.get(ops.prefix+'/'+name+'.json');out[name]=json.loads(o.body) if o else None
(P/'before.json').write_text(json.dumps(out,indent=2))
from collections import Counter
for lane in ['daily','historical']:
 items=out[lane]['symbols']
 bad={s:v for s,v in items.items() if v.get('gaps') or v.get('last_result',{}).get('status') not in ['complete','excluded']}
 print(lane,len(items),'unresolved',len(bad),'reasons',Counter(v.get('last_result',{}).get('reason')for v in bad.values()))
 print('symbols:', ' '.join(bad))
