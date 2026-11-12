"""Bounded S3-only NIH replay while scheduled specialist collectors are quiesced."""
import json,subprocess
from pathlib import Path
from collection_storage import StorageSettings,write_json,now
from specialist_inputs import collect
from research_contract import ROOT
for unit in ('optima-specialist-daily.service','optima-specialist-historical.service'):
 state=subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','--value'],text=True).strip()
 if state in ('active','activating','deactivating'):raise RuntimeError('Scheduled specialist collector is active')
s=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=s.store()
key='operations/specialists/scheduler/historical.json';obj=store.get(key);state=json.loads(obj.body)
id='9d9a82b1c201f072c2848d0ae5024acb8fced65376ce07bf231c6a2d68a8de7b';prior=state['jobs'][id]
m=json.loads(store.get(prior['manifest']).body);t=m['task']
u=json.loads(store.get('manifests/configurations/universe/'+t['universe_hash']+'.json').body)
tax=json.loads(store.get('manifests/configurations/taxonomy/'+t['taxonomy_hash']+'.json').body)
r=collect(prior['job'],store,s,u,tax,1)
state['jobs'][id]={**prior,**r,'last_attempt':now()};state['updated_at']=now();write_json(store,key,state,obj.token)
report={'prior_manifest':prior['manifest'],'capture':r,'at':now()}
(ROOT/'repair-notes/2026-10-23-checkup/nih-boundary-replay.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
