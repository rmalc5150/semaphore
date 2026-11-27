from ops import *
code=r'''import json,boto3
from concurrent.futures import ThreadPoolExecutor
from metadata_engine.runtime_db import Database
from regional_source_review import in_scope
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');bucket=cfg['bucket'];sources=SOURCES;out=[]
for source in sources:
 with db.tx()as c:
  c.execute("SELECT * FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s AND state='accepted' AND contract_version<>'2.0.3' LIMIT 1000",(source,));jobs=c.fetchall()
 def inspect(job):
  if job['input_format']!='public_receipt':return {'job':job,'classification':'manual_review_other_format'}
  response=s.get_object(Bucket=bucket,Key=job['input_key']);raw=response['Body'].read(2*1024**2+1);assert len(raw)<=2*1024**2;rows=[json.loads(l)for l in raw.splitlines()if l.strip()]
  invalid=bool(rows)and all(r.get('source')==source and (r.get('artifact_kind')!='public_document'or not in_scope(r.get('source_url',''),source)or r.get('media_type','').startswith('image/'))for r in rows)
  return {'job':job,'classification':'confirmed_out_of_scope_original'if invalid else'needs_new_validation','receipts':rows}
 with ThreadPoolExecutor(max_workers=8)as pool:out.extend(pool.map(inspect,jobs))
from collections import Counter
key=BASE+'legacy-accepted-audit.json';s.put_object(Bucket=bucket,Key=key,Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256');print(json.dumps({'key':key,'counts':dict(Counter(r['classification']for r in out)),'by_source':dict(Counter(r['job']['source_key']for r in out if r['classification']=='confirmed_out_of_scope_original'))}))
'''.replace('SOURCES',repr(SOURCES)).replace('BASE',repr(BASE))
r=remote(T3,code);print(r['out']);(P/'legacy-accepted-audit-summary.json').write_text(r['out']);(P/'legacy-accepted-audit.json').write_bytes(session.client('s3').get_object(Bucket=B,Key=BASE+'legacy-accepted-audit.json')['Body'].read())
