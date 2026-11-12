import json
from pathlib import Path
from collection_storage import StorageSettings,write_json,now
from constellation.control import Control
from constellation.legacy_dispatch import dispatch
from constellation.legacy_routes import route
p=Path(__file__).parent;settings=StorageSettings.load(Path('config/collection-storage.s3.json'));store=settings.store();key='constellation-backfill/specialist-schedulers/constellation-specialist-bls_wages.service/historical.json'
stored=store.get(key);state=json.loads(stored.body);(p/'bls-scheduler-before.json').write_bytes(stored.body)
changed=[]
for identity,row in state.get('jobs',{}).items():
 if row.get('status')=='failed' and row.get('error_type')=='AccessDenied' and 's3:G' in row.get('reason',''):
  row['retry_after']=now();row['retry_authorization']={'at':now(),'basis':'owner-approved BLS metadata permission repair; verified worker Put/Get','prior_failure_preserved':True};changed.append(identity)
if changed:write_json(store,key,state,stored.token)
result={'at':now(),'eligible_permission_failures':changed,'provider_retry_limits_changed':False,'dispatch':dispatch(Control(),route('constellation-specialist-bls_wages.service'))}
(p/'bls-retry-decision.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
