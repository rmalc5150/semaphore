"""One native, resumable EPO patent lookup used to verify a deployment."""
import json,os
from datetime import datetime,timezone
from pathlib import Path
from specialist_inputs import collect
from collection_storage import StorageSettings
from research_contract import ROOT,load_json
from specialist_plan import jobs

def main():
 mode=os.environ['EPO_BOOTSTRAP_MODE'];plan=load_json(Path(os.environ['CONSTELLATION_SPECIALIST_PLAN']));source=next(r for r in plan['sources'] if r['source']=='epo_ops_patent_legal_events');candidate=next(r for r in source['scopes'] if 'ASML' in r['applicant'].upper());source={**source,'scopes':[candidate]};universe=load_json(ROOT/'config/company-universe.v0.5.json');taxonomy=load_json(ROOT/'config/sectors.v1.json');settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json')
 candidates=list(jobs({**plan,'sources':[source]},universe,mode,datetime.now(timezone.utc).date()))
 if mode=='daily':
  from epo_ops import control
  c=control();prefix=c.config['prefix']+'/epo/registry/';objects=c.s3.list_objects_v2(Bucket=c.config['bucket'],Prefix=prefix,MaxKeys=100).get('Contents',[]);known=next(r['Key'] for r in objects if not r['Key'].endswith('/EP.1000000.A1.json'));shard=known.removeprefix(prefix).split('/')[0]
  if os.environ.get('EPO_PROOF_REFERENCE'):
   import hashlib
   shard=hashlib.sha256(os.environ['EPO_PROOF_REFERENCE'].encode()).hexdigest()[0]
  job=next(j for j in candidates if j['parameters'].get('purpose')=='refresh' and j['parameters']['shard']==shard)
 else:job=next(j for j in candidates if j['parameters'].get('purpose')=='discovery' and j['parameters'].get('discovery_start')=='2016-01-01')
 result=collect(job,settings.store(),settings,universe,taxonomy,6);print(json.dumps({'epo_bootstrap_mode':mode,'job':job,'result':result}),flush=True)
 if result['status']=='failed':raise SystemExit(1)
if __name__=='__main__':main()
