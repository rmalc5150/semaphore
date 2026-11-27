"""Publish only the already-validated screening outputs in this repair snapshot."""
import json,time
from metadata_engine.runtime_db import Database
from metadata_engine.controller import publish
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');base='research-data/constellation-backfill/repairs/trade-screening-20261113/'
before=json.loads(s.get_object(Bucket=cfg['bucket'],Key=base+'before.json')['Body'].read())
ids=[j['job_id']for j in before['publication']if j['publication_status']!='published'];results=[]
for offset in range(0,len(ids),5):
 chunk=ids[offset:offset+5];n=publish(db,source_key='trade_screening',job_ids=chunk);results.append({'job_ids':chunk,'published_batches':n});print(json.dumps(results[-1]),flush=True)
with db.tx()as c:
 c.execute("SELECT j.job_id,j.output_rows,r.status publication_status FROM engine_jobs j LEFT JOIN publication_releases r ON r.release_id=UNHEX(SUBSTRING(j.job_id,1,32)) WHERE j.source_key='trade_screening' AND j.job_id IN ("+','.join('%s'for _ in ids)+')',tuple(ids));rows=c.fetchall()
assert len(rows)==len(ids)and all(r['publication_status']=='published'for r in rows),rows
out={'repaired_batches':len(rows),'repaired_observations':sum(r['output_rows']for r in rows),'calls':results,'verified_publication_rows':rows}
s.put_object(Bucket=cfg['bucket'],Key=base+'publication-repair.json',Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256');print(json.dumps(out,default=str),flush=True)
