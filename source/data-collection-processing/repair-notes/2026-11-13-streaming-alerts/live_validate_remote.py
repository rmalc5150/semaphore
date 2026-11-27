import os,sys,json,subprocess
from pathlib import Path
os.chdir('/opt/constellation/metadata-engine-runtime');sys.path.insert(0,os.getcwd())
from metadata_engine.runtime_db import Database
c=json.load(open('config/metadata-engine.json'));db=Database(c)
with db.tx()as x:x.execute("SELECT source_key,state,consecutive_raw_failures,last_reason FROM engine_sources WHERE source_key IN ('trade_screening','european_commission_cordis','bis_sdmx_api','hkex_prices','faostat_food_balances','indonesia_esdm_and_geological_agency_mineral_statistics','university_technology_transfer_catalogs_and_reports','personnel_archive','hkex_news')");print(json.dumps({'states':x.fetchall()},default=str))
print(subprocess.run(['systemctl','show','constellation-workers.slice','-p','MemoryCurrent','-p','MemoryMax'],capture_output=True,text=True).stdout)
