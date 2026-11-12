import os,sys,json
os.chdir('/opt/constellation/source');sys.path.insert(0,os.getcwd());os.environ['CONSTELLATION_ROLE']='worker';os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1'
from pathlib import Path
from grants_review_capture import capture_one
from collection_storage import StorageSettings
from research_contract import load_json
settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();universe=load_json(Path('config/company-universe.v0.3.json'));taxonomy=load_json(Path('config/sectors.v1.json'));s=next(r for r in load_json(Path('config/specialist-inputs.json'))['sources']if r['source']=='ted_notices');job={'source':'ted_notices','source_id':s['source_id'],'adapter':'ted','mode':'daily','start':'2026-11-04','end':'2026-11-05','parameters':{'url':s['api'],'query':'publication-number = 768246-2026','fields':s['fields']},'coverage_note':'One exact notice verification; original XML, returned search fields and extracted stage/parties retained. Not full archive completion.'};capture_one(store,settings,universe,taxonomy,job,1)
