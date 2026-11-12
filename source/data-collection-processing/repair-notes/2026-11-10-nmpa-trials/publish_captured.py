import json,tempfile
from pathlib import Path
from collection_storage import StorageSettings
from research_contract import load_json
from research_publication import bridge_nmpa_queue,prepare_for
from window_publication import publish_pending
import regulatory_athena
p=Path(__file__).parent;settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();print('New NMPA publication windows queued:',bridge_nmpa_queue(store,settings),flush=True);entries=json.load(open(p/'fresh-captures.json'));ids=[e['window_id']for e in entries];config=load_json(Path('config/regulatory-athena-pilot.json'));config.pop('source_manifests',None)
with tempfile.TemporaryDirectory(prefix='nmpa-publication-')as tmp:r=publish_pending(store,settings,'regulatory',config,prepare_for(regulatory_athena),Path(tmp),max_windows=4,window_ids=ids)
(p/'fresh-publication.json').write_text(json.dumps(r,indent=2));print(r,flush=True);assert r['status']=='complete'
