import json
from pathlib import Path
from metadata_engine.runtime_db import Database
p=Path(__file__).parent;c=json.load(open('config/metadata-engine.json'));db=Database(c);out={}
with db.tx()as x:
 x.execute("SELECT /*+ MAX_EXECUTION_TIME(8000) */ source_key,job_id,input_key,input_format,reason,state FROM engine_jobs WHERE state='retry' AND reason LIKE '%%larger_artifact_requires_streaming_adapter%%' LIMIT 40");out['oversized_jobs']=x.fetchall()
(p/'before.json').write_text(json.dumps(out,indent=2,default=str));print(json.dumps(out,default=str))
s=db.session.client('s3');o=s.list_objects_v2(Bucket=c['bucket'],Prefix='research-data/monitoring/',Delimiter='/');print('Monitoring prefixes',[r['Prefix']for r in o.get('CommonPrefixes',[])], 'keys',[r['Key']for r in o.get('Contents',[])])
