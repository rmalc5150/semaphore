"""Rotate bounded specialist daily passes on m7 using the existing scheduler state."""
import json
import subprocess
import sys
from collection_storage import StorageSettings,write_json,now
from research_contract import ROOT,load_json
from source_pauses import is_paused

def main():
    sources=sorted({s['source']for s in load_json(ROOT/'config/specialist-inputs.json')['sources']if s.get('enabled')and s.get('execution_lane','default')=='default'and not is_paused(s['source'])})
    if not sources:return 0
    store=StorageSettings.load(ROOT/'config/collection-storage.s3.json').store()
    key='operations/specialists/m7-daily-dispatch.json';old=store.get(key);state=json.loads(old.body)if old else{}
    source=next((s for s in sources if s>state.get('last_source','')),sources[0])
    write_json(store,key,{'last_source':source,'dispatched_at':now(),'eligible_sources':len(sources)},old.token if old else None)
    print(json.dumps({'stage':'specialist_daily_dispatch','source':source}),flush=True)
    return subprocess.call([sys.executable,'-B','specialist_inputs.py','--mode','daily','--source',source,'--max-jobs','1','--pages','1','--publish','0','--discovery-limit','100'],cwd=ROOT)

if __name__=='__main__':raise SystemExit(main())
