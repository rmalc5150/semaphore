"""One explicit DOI's current complete metadata through native storage/publication."""
import json
from datetime import datetime,timedelta,timezone
from urllib.parse import quote
from collection_storage import StorageSettings,CollectionRun,AlreadyComplete,task_spec,write_json,now
from research_contract import ROOT,load_json,digest,seal_record
from regulatory_collection import EvidenceClient,instant
from conference_collection import publication,NOTE,SOURCE
from metadata_engine.crossref import validate
DOI='10.51161/v-convesp/78963'
def main():
 settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();u=load_json(ROOT/'config/crossref-resumed-universe.json');t=load_json(ROOT/'config/sectors.v1.json');day=datetime.now(timezone.utc).date();scope={'type':'proceedings-article','date_filter':'one_explicit_current_doi','selected_dois':[DOI],'coverage_note':'One explicit DOI current provider metadata, not a complete daily or historical window.'};spec=task_spec(SOURCE,'conference_records','daily',instant(day),instant(day+timedelta(days=1)),scope,'crossref-current-work-probe-1',u,t)
 try:run=CollectionRun.start(store,spec,u,t,settings)
 except AlreadyComplete as done:result={'status':'complete','manifest':str(done),'already_complete':True}
 else:
  client=EvidenceClient(store,SOURCE);url='https://api.crossref.org/works/'+quote(DOI,safe='');raw=client.get(url);response=json.loads(raw);data=response['message'];record={'document_type':'collected_record','schema_version':'1.0','source':SOURCE,'dataset':'conference_records','source_record_id':DOI,'source_record_id_basis':'provider','source_url':'https://doi.org/'+quote(DOI,safe='/'),'universe_version':u['universe_version'],'company_ids':[],'listing_ids':[],'product_ids':[],'person_ids':[],'entity_match_status':'unresolved','event_at':publication(data),'source_updated_at':None,'available_at':None,'availability_basis':'unknown','availability_evidence':[],'ingested_at':now(),'run_id':run.run_id,'payload':{'record_type':'conference_publication','title':(data.get('title')or[None])[0],'date_basis':'provider_published_date','data':data,'coverage_note':scope['coverage_note']+' '+NOTE,'source_evidence':list(client.evidence)}};validate(raw,record,url);run.commit_page([seal_record(record)],next_cursor=None,exhausted=True);result={'status':'complete','records':1,'manifest':run.finish('complete',expected_records=1)}
 identity=digest(spec);key='constellation-backfill/conferences-resumed/publication-queue/'+identity+'.json'
 if store.get(key)is None:write_json(store,key,{'window_id':identity,'manifests':[result['manifest']],'queued_at':now()})
 report={'source':SOURCE,'mode':'current_work_probe','window_id':identity,'at':now(),**result};write_json(store,'constellation-backfill/conferences-resumed/receipts/'+str(day)+'/'+digest(report)+'.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':main()
