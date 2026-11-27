import json,io,contextlib
from pathlib import Path
from constellation.finish_aux_migration import remote,T3,session

P=Path(__file__).parent
CODE='''import json
from metadata_engine.runtime_db import Database
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');out={}
for source in ('sam_gov_opportunities', 'uspto_odp', 'bis_sdmx_api', 'fred_alfred_series_and_vintages', 'unido_iip_and_indstat', 'ilostat_labor_statistics', 'imf_portwatch_shipping_activity', 'ember_electricity_demand_and_generation', 'wto_timeseries_api', 'wto_quantitative_restrictions_api', 'wto_eping_sps_tbt_notifications', 'epo_ops_patent_legal_events', 'copernicus_era5_era5_land'):
 entry={}
 with db.tx()as c:
  c.execute('SELECT * FROM engine_sources WHERE source_key=%s',(source,));entry['source']=c.fetchone()
  c.execute('SELECT state,count(*) AS jobs FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s GROUP BY state',(source,));entry['counts']=c.fetchall()
  c.execute("SELECT * FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s AND state IN ('raw_failed','retry','uncommitted') LIMIT 15",(source,));entry['failed_jobs']=c.fetchall()
  c.execute("SELECT * FROM engine_jobs FORCE INDEX(source_publication_order) WHERE source_key=%s AND state='accepted' ORDER BY finished_at DESC,job_id DESC LIMIT 4",(source,));entry['native_jobs']=c.fetchall()
  c.execute("SELECT job_id FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s AND state='queued' ORDER BY job_id LIMIT 4",(source,));pending=c.fetchall()
  for identity in pending:
   c.execute("SELECT * FROM engine_jobs WHERE job_id=%s",(identity['job_id'],));entry['native_jobs'].append(c.fetchone())
 entry['samples']=[]
 for j in entry['native_jobs'][:2]:
  try:
   r=s.get_object(Bucket=cfg['bucket'],Key=j['input_key']);body=r['Body'].read(4*1024*1024);r['Body'].close()
   entry['samples'].append({'input_key':j['input_key'],'record':json.loads(body.splitlines()[0])})
  except Exception as e:entry['samples'].append({'input_key':j['input_key'],'error':str(e)})
 out[source]=entry
key='research-data/constellation-backfill/repairs/entries-62-75-20261114/before.json'
s.put_object(Bucket=cfg['bucket'],Key=key,Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256')
print(json.dumps({'key':key}))
'''
capture=io.StringIO()
with contextlib.redirect_stdout(capture):remote(T3,CODE)
result=json.loads(capture.getvalue());print(result['status'],result['err'])
key=json.loads(result['out'])['key'];body=session.client('s3').get_object(Bucket='data-collection-059416028963-us-east-1-an',Key=key)['Body'].read()
(P/'before.json').write_bytes(body)
for source,d in json.loads(body).items():
 print(source,d['source'],d['counts'])
 print('FAILURES',[(j['state'],j['input_format'],j['reason'])for j in d['failed_jobs']])
 for r in d['samples'][:1]:print('SAMPLE',json.dumps(r)[:1300])
