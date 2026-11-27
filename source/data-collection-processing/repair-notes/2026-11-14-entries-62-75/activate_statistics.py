import hashlib,json
from pathlib import Path
from ops import remote,T3,M7,session,B,BASE,P
files={}
for name in ['public_statistics_apis.py','metadata_engine/public_statistics.py','metadata_engine/labelling.py','metadata_engine/controller.py']:
 raw=Path(name).read_bytes();sha=hashlib.sha256(raw).hexdigest();key='research-data/constellation-backfill/deployments/entries-62-75-20261114/'+sha+'/'+name
 session.client('s3').put_object(Bucket=B,Key=key,Body=raw,ServerSideEncryption='AES256');files[name]={'key':key,'sha256':sha}
code='''import json,os,hashlib,boto3,subprocess
from pathlib import Path
s=boto3.client('s3',region_name='us-east-1');files=FILES
for root in ROOTS:
 root=Path(root)
 for name,ref in files.items():
  raw=s.get_object(Bucket=BUCKET,Key=ref['key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==ref['sha256'];compile(raw,name,'exec');p=root/name;tmp=p.with_suffix('.6275.tmp');tmp.write_bytes(raw);os.chown(tmp,1000,1000);tmp.replace(p)
 if root.name.endswith('.service'):
  p=root/'config/constellation-specialist-historical.json';cfg=json.loads(p.read_text());cfg['backfill_end_exclusive']='2026-11-14';p.write_text(json.dumps(cfg,indent=2)+'\\n');os.chown(p,1000,1000)
print(json.dumps({'installed':files}))
'''.replace('FILES',repr(files)).replace('BUCKET',repr(B))
roots=['/opt/constellation/metadata-engine-runtime','/opt/constellation/auxiliary-publication/source']+['/opt/constellation/legacy/constellation-specialist-'+source+'.service'for source in ['unido_iip_and_indstat','imf_portwatch_shipping_activity']]
r=remote(M7,code.replace('ROOTS',repr(roots)));(P/'statistics-activation-m7.json').write_text(r['out']);print('m7 native parser updated and historical targets aligned',flush=True)
r=remote(T3,code.replace('ROOTS',repr([str(Path.cwd())]))+'''from metadata_engine.runtime_db import Database
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);proof=json.loads(s.get_object(Bucket=BUCKET,Key=BASE+'statistics-capture.json')['Body'].read());superseded=[]
for source in ['unido_iip_and_indstat','imf_portwatch_shipping_activity']:
 assert any(e['source']==source and e['verified_rows']>0 for e in proof['captures'])
 with db.tx()as c:
  c.execute("SELECT * FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s AND state IN ('queued','retry','raw_failed') AND input_format='public_receipt' LIMIT 100",(source,));jobs=c.fetchall()
 for job in jobs:
  rows=[json.loads(l)for l in s.get_object(Bucket=BUCKET,Key=job['input_key'])['Body'].read().splitlines()if l.strip()]
  if not rows or not all(r.get('source')==source and (r.get('artifact_kind')=='discovery_page'or(source=='unido_iip_and_indstat'and r.get('source_url','').startswith('https://stat.unido.org/portal/dataset/getDataset/')))for r in rows):continue
  with db.tx()as c:
   c.execute("UPDATE engine_jobs SET state='superseded',reason='catalogue_or_discovery_only; native_statistics_capture_verified',finished_at=UTC_TIMESTAMP(6) WHERE job_id=%s AND state IN ('queued','retry','raw_failed')",(job['job_id'],));superseded.append(job['job_id'])
  with db.tx()as c:c.execute("UPDATE source_date_failures SET status='resolved' WHERE source_key=%s AND latest_job_id=%s AND reason_code='public_capture_is_discovery_page_only' AND status='open'",(source,job['job_id']))
 with db.tx()as c:c.execute("UPDATE engine_sources SET state='enabled',consecutive_raw_failures=0,last_reason=NULL WHERE source_key=%s AND state='raw_stopped'",(source,))
# Both new routes are queued by the existing historical dispatcher. The daily
# rotation already reads these enabled sources from specialist-inputs.json.
subprocess.run(['systemctl','start','--no-block','optima-historical-dispatch-all.service','optima-specialist-daily.service'],check=False)
key=BASE+'statistics-discovery-cleanup.json';s.put_object(Bucket=BUCKET,Key=key,Body=json.dumps({'superseded':superseded}).encode(),ServerSideEncryption='AES256');print(json.dumps({'superseded_discovery_jobs':len(superseded),'key':key}))
'''.replace('BUCKET',repr(B)).replace('BASE',repr(BASE)));(P/'statistics-activation-t3.json').write_text(r['out']);print(r['out'][-1300:])
