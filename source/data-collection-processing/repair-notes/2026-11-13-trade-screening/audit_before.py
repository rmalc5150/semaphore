import json,io,contextlib
from pathlib import Path
from constellation.finish_aux_migration import remote,T3,session
P=Path(__file__).parent
code='''import json
from metadata_engine.runtime_db import Database,fingerprint
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);out={}
with db.tx()as c:
 for name,sql,params in [
  ('source',"SELECT * FROM engine_sources WHERE source_key='trade_screening'",()),
  ('counts',"SELECT state,count(*) jobs,sum(output_rows) output_rows FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key='trade_screening' GROUP BY state",()),
  ('publication',"SELECT j.job_id,j.state,j.input_key,j.input_format,j.output_rows,j.output_uri,j.finished_at,r.status publication_status,r.s3_uri publication_receipt FROM engine_jobs j LEFT JOIN publication_releases r ON r.release_id=UNHEX(SUBSTRING(j.job_id,1,32)) WHERE j.source_key='trade_screening' AND j.state='accepted' ORDER BY j.finished_at DESC LIMIT 200",()),
  ('failures',"SELECT job_id,input_key,input_format,state,reason,available_after FROM engine_jobs WHERE source_key='trade_screening' AND state IN ('raw_failed','retry','uncommitted') LIMIT 80",()),
  ('scan',"SELECT cursor_json FROM engine_cursors WHERE cursor_key=%s",('publication_scan_'+fingerprint('trade_screening'),))]:
  c.execute(sql,params);out[name]=c.fetchall()
key='research-data/constellation-backfill/repairs/trade-screening-20261113/before.json';db.session.client('s3').put_object(Bucket=cfg['bucket'],Key=key,Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256');print(json.dumps({'key':key}))
'''
cap=io.StringIO()
with contextlib.redirect_stdout(cap):remote(T3,code)
r=json.loads(cap.getvalue());assert r['status']=='Success',r
key=json.loads(r['out'])['key'];body=session.client('s3').get_object(Bucket='data-collection-059416028963-us-east-1-an',Key=key)['Body'].read();(P/'before.json').write_bytes(body);d=json.loads(body)
print('SOURCE',d['source']);print('COUNTS',d['counts']);print('PUBLICATIONS',len(d['publication']),'unpublished',sum(j['publication_status']!='published'for j in d['publication']));print('FAILURES',d['failures']);print('SCAN',d['scan'])
