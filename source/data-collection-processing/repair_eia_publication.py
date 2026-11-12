"""Verify complete EIA generator scopes; preserve unpublished periods as deferred."""
import json
from research_contract import ROOT,load_json
from collection_storage import StorageSettings
from specialist_publication import publish

def main():
 settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store()
 state=json.loads(store.get('operations/specialists/scheduler/daily.json').body)
 rows={k:r for k,r in state['jobs'].items() if r.get('source')=='eia_battery_generators'}
 ids=[k for k,r in rows.items() if r.get('status')=='complete']
 report={'scopes':[{ 'job_id':k,'status':r.get('status'),'reason':r.get('reason'),'start':r.get('start')} for k,r in rows.items()]}
 report['publication']=publish(store,settings,load_json(ROOT/'config/specialist-inputs.json'),max(1,len(ids)),ids)
 print(json.dumps(report),flush=True)
 return int(report['publication']['status']=='failed')
if __name__=='__main__':raise SystemExit(main())
