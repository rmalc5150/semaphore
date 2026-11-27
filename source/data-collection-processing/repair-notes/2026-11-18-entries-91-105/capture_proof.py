import os,json,time
from pathlib import Path
import boto3
from metadata_engine.evidence import evidence_for,object_bytes
from metadata_engine.streaming import session as streaming
from metadata_engine.worker import load_input
from collection_storage import StorageSettings
from research_contract import ROOT,load_json
from specialist_inputs import collect
import public_source_capture as pc
from regional_source_review import Page,discover
B='data-collection-059416028963-us-east-1-an';BASE='research-data/constellation-backfill/repairs/entries-91-105-20261118/';s=boto3.client('s3',region_name='us-east-1')
policies=json.loads(s.get_object(Bucket=B,Key=BASE+'checkpoint/policies.json')['Body'].read());updates=json.loads(s.get_object(Bucket=B,Key=BASE+'checkpoint/public-source-updates.json')['Body'].read());native=json.loads(s.get_object(Bucket=B,Key=BASE+'checkpoint/native-source-updates.json')['Body'].read());staged=json.loads(s.get_object(Bucket=B,Key=BASE+'staged-originals.json')['Body'].read());out={'public':{},'native':{},'started_at':time.time()}
def save():s.put_object(Bucket=B,Key=BASE+'capture-proof.json',Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256')
def check_receipt(r,key):
 rows,_,_=load_input(s,B,{'input_key':key,'input_format':'public_receipt'})
 with streaming():
  checks=[evidence_for(row,policies[r['source']],s,B)for row in rows]
 return {'status':'verified','record':r,'receipt_key':key,'validated_rows':len(rows),'artifact_sample':checks[0]if checks else[]}
for source,items in staged.items():
 results=[]
 for item in items:
  try:results.append(check_receipt(item['record'],item['receipt_key']))
  except Exception as e:results.append({'status':'failed','url':item['record']['source_url'],'reason':type(e).__name__+':'+str(e)[:500]})
 out['public'][source]={'status':'verified'if results and all(r['status']=='verified'for r in results)else'failed','results':results};save();print(source,[(r['status'],r.get('validated_rows'),r.get('reason'))for r in results],flush=True)
# Actual original files referenced by current official release/detail pages.
selected={}
source='china_nhsa_reimbursement_and_procurement';selected[source]=[r['url']for r in staged[source][0]['linked_documents']if 'downfile.jsp'in r['url']][:2]
source='indonesia_esdm_and_geological_agency_mineral_statistics'
try:
 row,links=pc.capture(s,updates[source],{'url':updates[source]['seeds'][0],'depth':0},'historical',publish_receipt=False);selected[source]=[r['url']for r in links if r['url'].lower().endswith('.pdf')][:1]
 if not selected[source]:raise RuntimeError('current_resource_report_pdf_not_discovered')
except Exception as e:out['public'][source]={'status':'failed','reason':type(e).__name__+':'+str(e)};save()
source='brazil_anm_cfem_mining_royalties';selected[source]=updates[source]['historical_seeds']
for source,urls in selected.items():
 results=out['public'].get(source,{}).get('results',[])
 for url in urls:
  try:
   r,_=pc.capture(s,updates[source],{'url':url,'depth':1},'historical',publish_receipt=False);assert r['artifact_kind']=='public_document';key=BASE+'staged-receipts/'+source+'/'+r['sha256']+'.jsonl';pc.put(s,key,pc.encode(r),'application/x-ndjson');results.append(check_receipt(r,key))
  except Exception as e:results.append({'status':'failed','url':url,'reason':type(e).__name__+':'+str(e)[:500]})
  out['public'][source]={'status':'verified'if results and all(r['status']=='verified'for r in results)else'failed','results':results};save();print(source,url,results[-1]['status'],results[-1].get('reason'),flush=True)
settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();universe=load_json(ROOT/'config/company-universe.v0.5.json');taxonomy=load_json(ROOT/'config/sectors.v1.json')
for source in native:
 out['native'][source]={}
 # Separate collector invocations retain daily and historical task provenance.
 for mode,start,end in [('historical','2026-11-02','2026-11-03'),('daily','2026-11-17','2026-11-18')]:
  entry={'batches':[],'failed_batches':[]};out['native'][source][mode]=entry
  try:
   spec=native[source];job={**spec,'mode':mode,'start':start,'end':end,'parameters':{'url':spec['api']}};result=collect(job,store,settings,universe,taxonomy,4);entry['collection']=result
   if result['status']in ('complete','partial'):
    manifest=json.loads(store.get(result['manifest']).body)
    for page in manifest['pages']:
     for batch in page['batches']:
      key='research-data/'+batch['key'];rows,_,_=load_input(s,B,{'input_key':key,'input_format':'legacy_batch'})
      try:
       with streaming():
        for row in rows:evidence_for(row,policies[source],s,B)
       entry['batches'].append({'key':key,'validated_rows':len(rows)})
      except Exception as e:entry['failed_batches'].append({'key':key,'reason':type(e).__name__+':'+str(e)[:500]})
   entry['verified_rows']=sum(r['validated_rows']for r in entry['batches']);entry['status']='verified'if entry['verified_rows']else'failed'
  except Exception as e:entry.update(status='failed',reason=type(e).__name__+':'+str(e)[:500])
  save();print(source,mode,entry,flush=True)
out['finished_at']=time.time();save();print('All bounded raw proof passes finished.',flush=True)
