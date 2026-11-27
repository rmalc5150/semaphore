import os,sys,json
from pathlib import Path
from datetime import date
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker';os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1'
from collection_storage import StorageSettings,write_json
from regulatory_collection import EvidenceClient
from regulatory_sources import UK
settings=StorageSettings.load(root/'config/collection-storage.s3.json');store=settings.store();c=EvidenceClient(store,'uk_mhra')
rows,state,done=UK().page(c,date(2016,1,1),date(2026,11,18),'daily',{},100)
print('ILAP_ROWS',len(rows),'FIRST',json.dumps(rows[:1],default=str)[:1500]);print('EVIDENCE',json.dumps(c.evidence));write_json(store,'constellation-backfill/repairs/2026-11-18/mhra-current-list-probe.json',{'rows':rows,'evidence':c.evidence,'next':state})
