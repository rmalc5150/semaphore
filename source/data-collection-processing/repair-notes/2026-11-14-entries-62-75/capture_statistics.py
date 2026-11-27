import json,time
from collection_storage import StorageSettings
from research_contract import ROOT,load_json
from specialist_inputs import collect
from metadata_engine.runtime_db import Database
from metadata_engine.evidence import evidence_for
from metadata_engine.reviewed_continuation import claim
from metadata_engine.worker import process
from metadata_engine.controller import publish
cfg=load_json(ROOT/'config/metadata-engine.json');db=Database(cfg);s=db.session.client('s3');b=cfg['bucket'];base='research-data/constellation-backfill/repairs/entries-62-75-20261114/'
settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();universe=load_json(ROOT/'config/company-universe.v0.5.json');taxonomy=load_json(ROOT/'config/sectors.v1.json')
sources={r['source']:r for r in load_json(ROOT/'config/specialist-inputs.json')['sources']}
specs=[('imf_portwatch_shipping_activity','historical','2019-01-01','2019-01-02',{}),('imf_portwatch_shipping_activity','daily','2026-11-06','2026-11-07',{}),('unido_iip_and_indstat','historical','2023-01-01','2024-01-01',{'dataset':'IIP','country_code':'840','variable_code':'53'}),('unido_iip_and_indstat','daily','2025-01-01','2026-01-01',{'dataset':'IIP','country_code':'840','variable_code':'53'}),('unido_iip_and_indstat','historical','2022-01-01','2023-01-01',{'dataset':'INDSTAT/4','country_code':'276','variable_code':'04'}),('unido_iip_and_indstat','daily','2023-01-01','2024-01-01',{'dataset':'INDSTAT/4','country_code':'276','variable_code':'04'})]
out={'captures':[],'metadata':{},'started_at':time.time()};batches=[]
def save():s.put_object(Bucket=b,Key=base+'statistics-capture.json',Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256')
for source,mode,start,end,params in specs:
 row=sources[source];job={**row,'mode':mode,'start':start,'end':end,'parameters':{'url':row['api'],'data_start':start,'data_end':end,**params}}
 result=collect(job,store,settings,universe,taxonomy,3);proof={'source':source,'mode':mode,'start':start,'end':end,'parameters':params,'result':result,'verified_rows':0};out['captures'].append(proof);save()
 if result['status']not in ('complete','partial'):continue
 m=json.loads(store.get(result['manifest']).body)
 for page in m['pages']:
  for batch in page['batches']:
   key=store._args(batch['key'])['Key'];raw=s.get_object(Bucket=b,Key=key)['Body'].read()
   rows=[json.loads(l)for l in raw.splitlines()if l.strip()]
   for record in rows:evidence_for(record,cfg['contracts'][source],s,b);proof['verified_rows']+=1
   batches.append((source,key))
 print(json.dumps(proof),flush=True);save()
for source in {a for a,_ in batches}:
 with db.tx()as c:
  c.execute("UPDATE engine_sources SET state='enabled',consecutive_raw_failures=0,last_reason=NULL,updated_at=UTC_TIMESTAMP(6) WHERE source_key=%s AND state='raw_stopped'",(source,))
for source,key in batches:
 head=s.head_object(Bucket=b,Key=key);db.enqueue(source,key,head['ETag'],'legacy_batch',500)
for source in {a for a,_ in batches}:
 done=0
 for _ in range(5):
  job=claim(db,source)
  if not job:break
  process(db,s,cfg,job);done+=1
 out['metadata'][source]={'processed':done,'published':publish(db,source_key=source)};save()
out['finished_at']=time.time();save();print(json.dumps(out['metadata']),flush=True)
