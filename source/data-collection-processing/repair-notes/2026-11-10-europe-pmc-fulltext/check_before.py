import json,boto3
from pathlib import Path
from metadata_engine.runtime_db import Database
p=Path(__file__).parent;config=json.load(open('config/metadata-engine.json'));db=Database(config);out={}
with db.tx()as c:
 for name,sql in {'source':"SELECT * FROM engine_sources WHERE source_key='europe_pmc_fulltext'",'jobs':"SELECT * FROM engine_jobs WHERE source_key='europe_pmc_fulltext' ORDER BY (state='raw_failed') DESC,priority DESC LIMIT 100"}.items():c.execute(sql);out[name]=c.fetchall()
(p/'before.json').write_text(json.dumps(out,indent=2,default=str));print('SOURCE',out['source']);print('JOBS',[(j['input_format'],j['state'],j['reason'])for j in out['jobs']][:10])
s=db.session.client('s3');seen=set()
for j in out['jobs']:
 if j['input_format'].startswith('legacy_batch') and j['input_key']not in seen:
  seen.add(j['input_key']);raw=s.get_object(Bucket=config['bucket'],Key=j['input_key'])['Body'].read();r=json.loads(raw.splitlines()[0]);(p/'sample-record.json').write_text(json.dumps(r,indent=2));print('RECORD',json.dumps(r)[:3500]);break
