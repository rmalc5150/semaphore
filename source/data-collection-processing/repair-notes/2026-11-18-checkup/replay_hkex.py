import os,sys,json,subprocess
from pathlib import Path
from datetime import date
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker';os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1'
from collection_storage import StorageSettings,write_json
from research_contract import load_json
from collection_operations import Operations
settings=StorageSettings.load(root/'config/collection-storage.s3.json');store=settings.store();cfg=load_json(root/'config/constellation-core-public.json');cfg['max_pages']=3
op=Operations(store,settings,cfg,load_json(root/cfg['universe']),load_json(root/cfg['taxonomy']))
r=op.window('hkex-filings',date(2026,10,7),date(2026,10,8),'daily');write_json(store,'constellation-backfill/repairs/2026-11-18/hkex-replay.json',r);print(json.dumps(r),flush=True)
