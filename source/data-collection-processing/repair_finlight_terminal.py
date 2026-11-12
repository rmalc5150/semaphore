"""One explicit refresh of the evidenced changing Finlight daily scope."""
import json
from datetime import date,timedelta
import boto3
from collection_storage import StorageSettings,write_json,now
from research_contract import ROOT,load_json
from collection_operations import load_stored
from news_operations import NewsOperations
from news_collection import NewsClient,collect
from finlight_backfill import setup
settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();ops=NewsOperations(store,settings,load_json(ROOT/'config/news-operations.json'))
state_key=ops.prefix+'/finlight/daily.json';state,token=load_stored(store,state_key);day=date.fromisoformat(state['next_date'])
failed=next((r for r in reversed(state['last_result'].get('results',[])) if r.get('reason')=='news_source_changed_refresh_required'),None)
if not failed:print(json.dumps({'status':'no_drift_scope_to_refresh'}));raise SystemExit(0)
m=json.loads(store.get(failed['manifest']).body);scope=m['task']['scope']
secret=json.loads(boto3.client('secretsmanager',region_name=ops.daily['region']).get_secret_value(SecretId=ops.daily['secret_id'])['SecretString'])
pc=ops.daily['providers']['finlight'];control,_,_=setup();cap=control['max_requests_per_day'] if control['enabled'] else pc['max_requests_per_day']
client=NewsClient(store,'finlight',secret[pc['secret_field']],cap,ops.config['requests_per_lane']['daily'])
result=collect(store,settings,ops.universe,ops.taxonomy,ops.daily,'finlight',scope['target'],scope['language'],day,day+timedelta(days=1),'daily',client,ops.config['max_pages'],True,False)
print(json.dumps({'stage':'explicit_finlight_repair','prior_manifest':failed['manifest'],'result':result}),flush=True)
if result['status']=='complete':
 result=ops.window('finlight',day,'daily',client,ops.daily)
 if result['status']=='complete':state['next_date']=str(day+timedelta(days=1))
 state.update(last_result=result,attempted_date=str(day),updated_at=now());write_json(store,state_key,state,token)
 print(json.dumps({'stage':'finlight_day_recheck','result':result}),flush=True)
raise SystemExit(0 if result['status']=='complete' else 2)
