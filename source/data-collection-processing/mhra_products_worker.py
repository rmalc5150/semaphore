"""Bounded whole-catalogue MHRA product-document capture; failures are per file."""
import fcntl,hashlib,io,json,signal,time
from datetime import datetime,timedelta,timezone,date
from pathlib import Path
from pypdf import PdfReader
from collection_storage import StorageSettings,CollectionRun,AlreadyComplete,task_spec,write_json,now
from research_contract import ROOT,load_json,digest
from regulatory_collection import EvidenceClient,CompanyMatcher,normalize
from regulatory_sources import item
from mhra_product_enrichment import INDEX,public_search_key

PREFIX='constellation-backfill/specialist-schedulers/mhra-products'
def document_timeout(signum,frame):raise TimeoutError('mhra_document_time_budget')
def main():
 with open('/opt/constellation/tmp/mhra-products.lock','a')as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();universe=load_json(ROOT/'config/drugsfda-inventory-universe.json');taxonomy=load_json(ROOT/'config/sectors.v1.json');matcher=CompanyMatcher(universe)
  key=PREFIX+'/state.json';prior=store.get(key);state=json.loads(prior.body)if prior else {'offset':0,'captured':0,'failed':0,'cycle_started':now()[:10]};start=date.fromisoformat(state['cycle_started']);client=EvidenceClient(store,'uk_mhra');offset=state['offset']
  if offset>=100000:raise RuntimeError('mhra_catalogue_partitioning_required_at_100000; remaining work retained')
  response=client.json(INDEX,params={'api-version':'2017-11-11','search':'*','$top':10,'$skip':offset,'$count':'true'},api_key=public_search_key(client),api_key_parameter='api-key');entries=response.get('value');total=response.get('@odata.count');assert isinstance(entries,list)and isinstance(total,int)and(entries or offset>=total),'mhra_catalogue_missing_page';page_ref=client.evidence[-1];out=[]
  started=time.monotonic();signal.signal(signal.SIGALRM,document_timeout)
  for entry in entries:
   if time.monotonic()-started>170:break
   url=entry.get('metadata_storage_path','');identity='product_document:'+hashlib.sha256(url.encode()).hexdigest();run=None
   try:
    signal.alarm(45)
    assert url.startswith('https://mhraproducts4853.blob.core.windows.net/docs/'),'unexpected_official_document_host'
    spec=task_spec('uk_mhra','research_records','daily',start.isoformat()+'T00:00:00Z',(start+timedelta(days=1)).isoformat()+'T00:00:00Z',{'document_url':url,'document_id':entry.get('metadata_storage_name'),'scope':'all public catalogue documents, no product/company filter'},'mhra-products-v1',universe,taxonomy)
    try:run=CollectionRun.start(store,spec,universe,taxonomy,settings,resume=True)
    except AlreadyComplete as complete:manifest=str(complete)
    else:
     client.evidence.clear();raw=client.get(url);assert raw.lstrip().startswith(b'%PDF-')and b'%%EOF'in raw[-4096:],'invalid_or_truncated_pdf';text='\n'.join(p.extract_text()or ''for p in PdfReader(io.BytesIO(raw)).pages)
     data={'category':'medicine_document','catalogue_record':entry,'document_sha256':hashlib.sha256(raw).hexdigest(),'text':text,'text_status':'extracted'if text.strip()else 'no_extractable_text','coverage_note':'Current public medicine document; not licence status or historical-vintage proof'}
     row=item(identity,'regulatory_snapshot',data,url,'retrieved_current_document',None,title=entry.get('product_name'),coverage_note=data['coverage_note']);row['source_evidence']=[page_ref,client.evidence[-1]]
     run.commit_page([normalize(row,run,matcher,row['source_evidence'],now())],exhausted=True);manifest=run.finish('complete',expected_records=1)
    window=digest(spec);queue='constellation-backfill/specialist-publication-queue/mhra-products/'+window+'.json'
    if store.get(queue)is None:write_json(store,queue,{'window_id':window,'manifests':[manifest],'queued_at':now()})
    result={'status':'complete','document_url':url,'manifest':manifest,'window_id':window};state['captured']+=1
   except Exception as error:
    if run:
     try:run.finish('partial','mhra_document_capture_gap')
     except Exception:pass
    result={'status':'gap','document_url':url,'reason':type(error).__name__+': '+str(error)[:200]};state['failed']+=1;write_json(store,'constellation-backfill/legacy-operation-receipts/mhra-products/gaps/'+digest([now(),url])+'.json',result)
   signal.alarm(0);out.append(result);state['offset']+=1
  state.update(provider_document_count=total,last_outcomes=out,updated_at=now(),scope='All public indexed SPC/PIL/PAR documents; document count is not a unique-drug or licence count',status='continuing'if state['offset']<total else 'enumeration_finished_with_possible_gaps')
  if state['offset']>=total:
   write_json(store,'constellation-backfill/legacy-operation-receipts/mhra-products/cycles/'+digest(state)+'.json',state);state.update(offset=0,cycle_started=now()[:10])
  write_json(store,key,state,prior.token if prior else None);print(json.dumps(state),flush=True)
if __name__=='__main__':main()
