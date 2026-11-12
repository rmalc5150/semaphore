import json
from pathlib import Path
from metadata_engine.runtime_db import Database
p=Path(__file__).parent;db=Database(json.load(open('config/metadata-engine.json')));sources=tuple(json.loads((p/'sources.json').read_text()));out={}
with db.tx()as c:
 for name,sql in {'sources':'SELECT source_key,state,contract_version,consecutive_raw_failures,last_reason FROM engine_sources WHERE source_key IN %s','failures':"SELECT source_key,state,reason,count(*) jobs FROM engine_jobs WHERE source_key IN %s AND contract_version='2.0.3' AND state IN ('raw_failed','retry') GROUP BY source_key,state,reason"}.items():c.execute(sql,(sources,));out[name]=c.fetchall()
(p/'live-status.json').write_text(json.dumps(out,indent=2,default=str));print(json.dumps(out,default=str))
