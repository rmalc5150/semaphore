import json
from datetime import date
from collection_storage import StorageSettings
from research_contract import ROOT
from regulatory_collection import collect
from regulatory_sources import ClinicalTrials
s=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=s.store();m=json.loads((ROOT/'repair-notes/2026-10-23-checkup/ct-final.json').read_text());t=m['task'];u=json.loads(store.get('manifests/configurations/universe/'+t['universe_hash']+'.json').body);tax=json.loads(store.get('manifests/configurations/taxonomy/'+t['taxonomy_hash']+'.json').body)
r=collect(store,s,u,tax,'clinicaltrials',date(2021,2,1),date(2021,3,1),'historical',ClinicalTrials(),max_pages=2)
print(json.dumps(r),flush=True)
if r['status']=='failed':raise SystemExit(2)
