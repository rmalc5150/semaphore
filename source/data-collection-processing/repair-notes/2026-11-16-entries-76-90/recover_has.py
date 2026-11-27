from ops import *
code='''import json,boto3
from metadata_engine.runtime_db import Database
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');found=[]
with db.tx()as c:
 c.execute("SELECT input_key FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s AND state IN ('queued','raw_failed','retry','superseded') AND created_at>='2026-11-16'",('france_has_medicine_assessment_opinions',));jobs=c.fetchall()
for job in jobs:
 row=json.loads(s.get_object(Bucket=cfg['bucket'],Key=job['input_key'])['Body'].read().splitlines()[0])
 if row.get('artifact_kind')=='public_document':found.append({'receipt_key':job['input_key'],'record':row})
s.put_object(Bucket=cfg['bucket'],Key=BASE+'has-existing-originals.json',Body=json.dumps(found).encode(),ServerSideEncryption='AES256');print(json.dumps({'jobs_checked':len(jobs),'found':found}))
'''.replace('BASE',repr(BASE))
r=remote(T3,code);(P/'has-existing-originals.json').write_text(r['out']);print(r['out'])
