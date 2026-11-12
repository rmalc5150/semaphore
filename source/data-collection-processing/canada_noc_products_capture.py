"""Bounded, resumable all-NOC product capture from one daily original bulk response."""
import fcntl,hashlib,json
from datetime import datetime,timedelta,timezone
from collection_storage import StorageSettings,CollectionRun,AlreadyComplete,task_spec,write_json,now
from research_contract import ROOT,load_json,digest
from specialist_inputs import SpecialistClient,normalized,item
from metadata_engine.canada_noc import product_id

def page_rows(rows,offset,size=4000):
    offset=int(offset);selected=rows[offset:offset+size];following=offset+len(selected)
    return selected,str(following) if following<len(rows) else None

def save_progress(store,key,report):
    previous=store.get(key)
    write_json(store,key,report,previous.token if previous else None)

def main():
 with open('/opt/constellation/tmp/canada-noc-products.lock','a')as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();day=datetime.now(timezone.utc).date();base='constellation-backfill/legacy-operation-receipts/canada-noc-products/'+day.isoformat()+'/'
  prior=store.get(base+'progress.json')
  if prior and json.loads(prior.body)['status']=='complete':print(prior.body.decode(),flush=True);return
  universe=load_json(ROOT/'config/drugsfda-inventory-universe.json');taxonomy=load_json(ROOT/'config/sectors.v1.json');url='https://health-products.canada.ca/api/notice-of-compliance/drugproduct/'
  stage=store.get(base+'stage.json')
  if stage:ref=json.loads(stage.body);raw=store.get(ref['key']).body
  else:
   client=SpecialistClient(store,'canada_noc');raw=client.get(url,params={'lang':'en','type':'json'});ref=client.evidence[-1];write_json(store,base+'stage.json',ref)
  assert hashlib.sha256(raw).hexdigest()==ref['sha256'];rows=json.loads(raw);assert isinstance(rows,list) and rows
  # Keep every distinct provider row, including distinct DINs/brands on one notice.
  by_id={product_id(row):row for row in rows};provider_rows=len(rows);rows=list(by_id.values());del by_id;del raw
  parameters={'url':url,'query':{'lang':'en','type':'json'},'snapshot_sha256':ref['sha256']}
  spec=task_spec('canada_noc','specialist_inputs','daily',day.isoformat()+'T00:00:00Z',(day+timedelta(days=1)).isoformat()+'T00:00:00Z',{'adapter':'canada_noc_products','parameters':parameters,'source_id':'S24','coverage_note':'Entire current official NOC product table; DIN/brand/NOC linkage, not all marketed Canadian drugs or historical vintages'},'canada-noc-products-1',universe,taxonomy)
  try:run=CollectionRun.start(store,spec,universe,taxonomy,settings,resume=True)
  except AlreadyComplete as e:
   manifest=str(e);saved=json.loads(store.get(manifest).body);captured=saved['record_count'];cursor=None;status='complete'
  else:
   selected,cursor=page_rows(rows,int(run.cursor or 0))
   run.commit_page((normalized(item(product_id(row),row,url,basis='derived'),run,[ref])for row in selected),next_cursor=cursor,exhausted=cursor is None)
   status='complete'if cursor is None else'partial';manifest=run.finish(status,None if cursor is None else'page_budget',expected_records=len(rows)if cursor is None else None);captured=run.state['record_count']
  identity=digest({'spec':spec,'snapshot_sha256':ref['sha256']})
  if cursor is None:
   assert captured==len(rows)
   key='constellation-backfill/specialist-publication-queue/canada-noc/'+identity+'.json'
   if store.get(key)is None:write_json(store,key,{'window_id':identity,'manifests':[manifest],'queued_at':now()})
  report={'source':'canada_noc','record_type':'drug_product','day':day.isoformat(),'status':status,'manifest':manifest,'window_id':identity,'provider_rows':provider_rows,'distinct_provider_rows':len(rows),'captured_rows':captured,'next_offset':cursor,'at':now()};save_progress(store,base+'progress.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':main()
