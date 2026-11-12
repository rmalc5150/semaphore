import json,tempfile
from pathlib import Path
from collection_storage import StorageSettings
from specialist_publication import bridge_drugsfda_inventory
from source_observation_athena import prepare
from window_publication import publish_pending
p=Path(__file__).parent;entry=json.load(open(p/'fresh-capture.json'));settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();print('Bridged',bridge_drugsfda_inventory(store,settings),flush=True)
cfg=json.load(open('config/regulatory-athena-pilot.json'));cfg.pop('source_manifests',None)
from regulatory_athena import prepare
from collection_storage import write_json,now
qkey='operations/regulatory/publication-queue/'+entry['window_id']+'.json'
if store.get(qkey)is None:write_json(store,qkey,{'window_id':entry['window_id'],'manifests':[entry['manifest']],'queued_at':now()})
def build(s,settings,config,manifests,root):return prepare(s,settings,{**config,'source_manifests':manifests},root)
with tempfile.TemporaryDirectory(prefix='ema-medicines-publication-')as tmp:result=publish_pending(store,settings,'regulatory',cfg,build,Path(tmp),max_windows=1,window_ids=[entry['window_id']])
(p/'fresh-publication.json').write_text(json.dumps(result,indent=2));print(result,flush=True)
assert result['status']=='complete' and len(result['results'])==1 and result['results'][0]['status']in ('verified','already_verified')
