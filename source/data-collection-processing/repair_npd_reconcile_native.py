"""Clear stale invalidations only after checking current manifests and parents."""
import fcntl,json,unittest
from datetime import date
from collection_storage import StorageSettings
from research_contract import ROOT,load_json as load_local
import boto3,hashlib
from copy import deepcopy
s3=boto3.client('s3',region_name='us-east-1')
bucket='data-collection-059416028963-us-east-1-an'
index=json.loads(s3.get_object(Bucket=bucket,Key='research-data/operations/s3-runtime/current.json')['Body'].read())
entry=index['paths']['config/company-universe.v0.2.json']
raw=s3.get_object(Bucket=bucket,Key=entry['key'])['Body'].read()
assert hashlib.sha256(raw).hexdigest()==entry['sha256']
universe=json.loads(raw)
def load_json(path):
 return deepcopy(universe) if path==ROOT/'config/company-universe.v0.2.json' else load_local(path)
import test_collection_operations
test_collection_operations.load_json=load_json
from collection_operations import Operations,load_stored,DEPENDENCIES
suite=unittest.defaultTestLoader.loadTestsFromName('test_collection_operations')
result=unittest.TextTestRunner().run(suite)
if not result.wasSuccessful():raise RuntimeError('Dependency regression failed')
with (ROOT/'.collection-operations.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 config=load_json(ROOT/'config/collection-operations.json')
 settings=StorageSettings.load(ROOT/config['storage_config']);store=settings.store()
 ops=Operations(store,settings,config,load_json(ROOT/'config/company-universe.v0.2.json'),load_json(ROOT/config['taxonomy']))
 start,end=date(2026,9,21),date(2026,9,22)
 for source in ['documents','press-releases','licensing-agreements','ma-announcements','strategic-transactions']:
  prior,_=load_stored(store,ops.outcome_key(source,start,end,'daily'));inputs=[]
  if not ops.completed(prior,source,start,end,'daily'):raise RuntimeError('Incomplete '+source)
  for parent in DEPENDENCIES[source]:
   p,_=load_stored(store,ops.outcome_key(parent,start,end,'daily'))
   if not ops.completed(p,parent,start,end,'daily'):raise RuntimeError('Incomplete parent '+parent)
   inputs.append(p['manifest'])
  if inputs!=prior.get('inputs',[]):raise RuntimeError('Changed parents '+source)
  before=sorted(ops.pending_dates(source))
  outcome=ops.window(source,start,end,'daily')
  assert outcome.get('already_complete')
  print(json.dumps({'source':source,'status':'verified_complete','manifest':outcome['manifest'],'pending_before':before,'pending_after':sorted(ops.pending_dates(source))}),flush=True)
