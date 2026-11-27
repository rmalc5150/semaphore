import os,json,hashlib,base64,io
from pathlib import Path
import boto3
from metadata_engine.evidence import evidence_for,object_bytes
from metadata_engine.streaming import session as streaming
from collection_storage import StorageSettings
from research_contract import ROOT,load_json
from specialist_inputs import collect
import public_source_capture as pc
b='data-collection-059416028963-us-east-1-an';base='research-data/constellation-backfill/repairs/entries-76-90-20261116/';s=boto3.client('s3',region_name='us-east-1');cfg=load_json(ROOT/'config/metadata-engine.json');before=json.loads(s.get_object(Bucket=b,Key=base+'before.json')['Body'].read());policies=json.loads(s.get_object(Bucket=b,Key=base+'policies.json')['Body'].read());sources={r['source']:r for r in load_json(ROOT/'config/constellation-public-sources.json')['sources']};out={'public':{},'native':{},'catalogue_exclusions':[]}
def save():s.put_object(Bucket=b,Key=base+'capture-proof.json',Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256')
def receipt_evidence(row):
 record={'source':row['source'],'source_record_id':row['sha256'],'dataset':'public_documents','payload':{'source_evidence':[{'s3_uri':row['artifact_uri'],'sha256':row['sha256'],'source_url':row['source_url'],'retrieved_at':row['retrieved_at']}]}}
 with streaming():return evidence_for(record,policies[row['source']],s,b)
selected={
'ucdp_organized_violence':['https://ucdp.uu.se/downloads/ged/ged261-csv.zip','https://ucdp.uu.se/downloads/candidateged/GEDEvent_v26_01_26_09.csv'],
'sia_wsts_public_semiconductor_sales':['https://www.wsts.org/esraCMS/extension/media/f/WST/7802/WSTS-Monthly_data_-_3MMA_-_Aug_2026.pdf'],
'semi_worldwide_equipment_billings':['https://www.seaj.or.jp/english/statistics/4777967556197.pdf'],
'germany_g_ba_drug_benefit_assessments':['https://www.g-ba.de/downloads/92-975-10168/2026-11-02_Nutzenbewertung-IQWiG_Durvalumab_D-1362.pdf'],
'france_assurance_maladie_open_medic':['https://open-data-assurance-maladie.ameli.fr/medicaments/download_file.php?file=Open_MEDIC_Base_Complete%2FOPEN_MEDIC_2025.zip']}
# Select authentic archived public PDFs for the already populated report lanes.
from public_source_scope import in_scope
for source in ['international_federation_of_robotics_world_robotics','iea_pvps_solar_deployment_reports','canada_cda_amc_cadth_reimbursement_reviews']:
 candidates=before[source]['native_jobs']+before[source]['failed_jobs'];chosen=[]
 for job in candidates:
  if job['input_format']!='public_receipt':continue
  row=json.loads(object_bytes(s,b,job['input_key']).splitlines()[0]);url=row.get('source_url','')
  if in_scope(url,source)and url.lower().endswith('.pdf'):chosen.append((job,row))
  if chosen:break
 if chosen:
  job,row=chosen[0]
  try:
   raw=object_bytes(s,b,row['artifact_uri'].split(b+'/',1)[1],expected=row['sha256'])
   if raw.lstrip().startswith(b'JVBER'):
    decoded=base64.b64decode(b''.join(raw.split()),validate=True);assert decoded.startswith(b'%PDF-')and b'%%EOF'in decoded[-4096:]
    key=pc.PREFIX+'/objects/'+source+'/'+hashlib.sha256(decoded).hexdigest();pc.put(s,key,decoded,'application/pdf');row={**row,'artifact_kind':'public_document','artifact_uri':'s3://'+b+'/'+key,'sha256':hashlib.sha256(decoded).hexdigest(),'bytes':len(decoded),'media_type':'application/pdf','gateway_representation':{'s3_uri':row['artifact_uri'],'sha256':row['sha256'],'encoding':'base64'}}
    receiptkey=pc.PREFIX+'/athena/review-20261116-'+row['sha256']+'.jsonl';pc.put(s,receiptkey,pc.encode(row),'application/x-ndjson')
   else:receiptkey=job['input_key']
   artifacts=receipt_evidence(row);out['public'][source]={'status':'verified','receipt_key':receiptkey,'record':row,'artifacts':artifacts};save();print(source,'verified archived original',flush=True)
  except Exception as e:out['public'][source]={'status':'failed','reason':type(e).__name__+':'+str(e)};save()
# Current authoritative HAS exports are discovered from the provider-owned index.
index=sources['france_has_medicine_assessment_opinions'];row,links=pc.capture(s,index,{'url':index['seeds'][0],'depth':0},'historical')
selected[index['source']]=[r['url']for r in links if any(k in r['url'].lower()for k in ('/asmr-','/smr-','url-has-'))][:2]
for source,urls in selected.items():
 results=[]
 for url in urls:
  try:
   row,_=pc.capture(s,sources[source],{'url':url,'depth':1},'historical');assert row['artifact_kind']=='public_document';artifacts=receipt_evidence(row);receiptkey=pc.PREFIX+'/athena/review-20261116-'+row['sha256']+'.jsonl';pc.put(s,receiptkey,pc.encode(row),'application/x-ndjson');results.append({'status':'verified','receipt_key':receiptkey,'record':row,'artifacts':artifacts})
  except Exception as e:results.append({'status':'failed','url':url,'reason':type(e).__name__+':'+str(e)})
  out['public'][source]={'status':'verified'if any(v['status']=='verified'for v in results)else'failed','results':results};save();print(source,[(r['status'],r.get('reason'))for r in results],flush=True)
# Use the existing collection commit protocol for native prescribing rows.
settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();universe=load_json(ROOT/'config/company-universe.v0.5.json');taxonomy=load_json(ROOT/'config/sectors.v1.json');source='england_nhsbsa_prescribing_data';spec=next(r for r in load_json(ROOT/'config/specialist-inputs.json')['sources']if r['source']==source)
for mode,start,end,params in [('historical','2016-01-01','2016-02-01',{'period':'201601'}),('daily','2026-11-15','2026-11-16',{'release_selection':'latest_available'})]:
 job={**spec,'mode':mode,'start':start,'end':end,'parameters':{'url':spec['api'],**params}};result=collect(job,store,settings,universe,taxonomy,1);entry={'collection':result,'verified_rows':0,'batches':[]};out['native'][mode]=entry;save()
 if result['status']in ('complete','partial'):
  m=json.loads(store.get(result['manifest']).body)
  for page in m['pages']:
   for batch in page['batches']:
    key='research-data/'+batch['key'];rows=[json.loads(l)for l in object_bytes(s,b,key).splitlines()if l.strip()]
    for row in rows:evidence_for(row,policies[source],s,b);entry['verified_rows']+=1
    entry['batches'].append(key)
 save();print(source,mode,result,'verified',entry['verified_rows'],flush=True)
# Verify actual committed native rows, using their producer's input loader.
from metadata_engine.worker import load_input
from metadata_engine.runtime_db import Database
db=Database(cfg)
for source in ['arxiv','nasa_power_weather_and_solar_resource','usgs_earthquakes']:
 checks=[];jobs=(before[source]['failed_jobs']if source=='arxiv'else before[source]['native_jobs'])[:2]
 for job in jobs:
  try:
   rows,raw,manifest=load_input(s,b,job,db)
   for row in rows[:2]:evidence_for(row,policies.get(source,cfg['contracts'][source]),s,b)
   checks.append({'job_id':job['job_id'],'input_key':job['input_key'],'status':'verified','rows_sampled':min(2,len(rows))})
  except Exception as e:checks.append({'job_id':job['job_id'],'status':'failed','reason':type(e).__name__+':'+str(e)})
 out[source]=checks;save();print(source,checks,flush=True)
print('Capture and original validation proof saved',flush=True)
