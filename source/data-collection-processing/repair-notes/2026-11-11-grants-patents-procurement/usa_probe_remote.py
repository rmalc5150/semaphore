import os,sys
from pathlib import Path
from datetime import datetime,timezone
os.chdir('/opt/constellation/source');sys.path.insert(0,os.getcwd());os.environ['CONSTELLATION_ROLE']='worker';os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1'
from grants_review_capture import capture_one,plan_jobs
from collection_storage import StorageSettings
from research_contract import load_json
settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();universe=load_json(Path('config/company-universe.v0.3.json'));taxonomy=load_json(Path('config/sectors.v1.json'));plan=load_json(Path('config/specialist-inputs.json'));plan['sources']=[s for s in plan['sources']if s['source']=='usa_spending'];job=plan_jobs(plan,universe,datetime.now(timezone.utc).date())[0];capture_one(store,settings,universe,taxonomy,job,8)
