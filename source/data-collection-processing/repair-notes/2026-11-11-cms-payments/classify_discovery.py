import json
from pathlib import Path
from metadata_engine.runtime_db import Database
from metadata_engine.controller import enqueue_objects
p=Path(__file__).parent;db=Database(json.load(open('config/metadata-engine.json')))
with db.tx() as c:
 c.execute("SELECT * FROM engine_jobs WHERE source_key='cms_payments_catalog' AND input_format='public_receipt' AND state IN ('queued','retry','raw_failed')");jobs=c.fetchall()
for j in jobs:enqueue_objects(db,[{'Key':j['input_key'],'ETag':j['input_etag']}],'public_receipt',j['priority'])
with db.tx() as c:
 c.execute("SELECT job_id,state,reason FROM engine_jobs WHERE source_key='cms_payments_catalog' AND input_format='public_receipt'");rows=c.fetchall()
(p/'discovery-receipt-classification.json').write_text(json.dumps(rows,indent=2,default=str));print('Classified',sum(r['state']=='superseded'for r in rows),'discovery-only receipts; preserved all raw files.')
