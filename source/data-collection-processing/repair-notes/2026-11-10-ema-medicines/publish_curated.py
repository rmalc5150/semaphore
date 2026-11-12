import json,tempfile
from pathlib import Path
from collection_storage import StorageSettings
from specialist_publication import bridge_drugsfda_inventory
from source_observation_athena import prepare
from window_publication import publish_pending
p=Path(__file__).parent;entry=json.load(open(p/'fresh-capture.json'));settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();print('Bridged',bridge_drugsfda_inventory(store,settings),flush=True)
cfg={'owner':'specialists','database':'optima_specialist_inputs','workgroup':'optima-specialist-inputs','region':settings.region,'curated_prefix':'curated/specialists/releases','query_results_prefix':'athena-results/specialists','dataset':'specialist_inputs','coverage_note':'Current EMA report snapshot, all published medicine rows; not all national medicines or historical vintages','allowed_sources':['ema_medicines']}
def build(s,settings,config,manifests,root):return prepare(s,settings,{**config,'source_manifests':manifests},root)
with tempfile.TemporaryDirectory(prefix='ema-medicines-publication-')as tmp:result=publish_pending(store,settings,'specialists',cfg,build,Path(tmp),max_windows=1,window_ids=[entry['window_id']])
(p/'fresh-publication.json').write_text(json.dumps(result,indent=2));print(result,flush=True)
assert result['status']=='complete' and len(result['results'])==1 and result['results'][0]['status']in ('verified','already_verified')
