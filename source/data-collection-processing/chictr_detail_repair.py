"""Bounded current-detail refresh for one explicitly identified existing ChiCTR trial."""
import json,re
from datetime import datetime,timedelta,timezone
from research_contract import ROOT,load_json,digest
from collection_storage import StorageSettings,write_json,now
from regulatory_collection import collect,EvidenceClient
from regulatory_sources import item,field_names,day
from metadata_engine.chictr_tables import parse_detail_page

REGISTRATION='ChiCTR2600132684'
URL='https://www.chictr.org.cn/showproj.html?proj=343036'
class DetailReplay:
 source='chictr';date_basis='registration_date';version='chictr-current-detail-repair-1';registry_ids=(REGISTRATION,)
 coverage='Current original full trial detail for one explicitly selected existing registration; not an exhaustive registry/history snapshot.'
 def page(self,client,start,end,mode,state,size):
  fields=parse_detail_page(client.rendered(URL,pending_validator=lambda doc:valid_detail(doc)))
  def value(words):return next((f['value']for f in fields if any(w in f['label'].lower()for w in words)),None)
  registration=value(('registration number','注册号'));date=day(value(('date of registration','注册时间')))
  if registration!=REGISTRATION or not date:raise ValueError('fresh_chictr_identity_or_registration_date_missing')
  data={'detailUrl':URL,'projectId':'343036','registrationNumber':registration,'registrationDate':date,'title':value(('public title','注册题目')),'studyType':value(('study type','研究类型')),'fields':fields}
  return [item(registration,'clinical_trial',data,URL,self.date_basis,date,field_names(fields),data['title'],coverage_note=self.coverage)],{},True

def valid_detail(document):
 fields=parse_detail_page(document)
 return any(f['value'].strip()==REGISTRATION for f in fields if 'registration number'in f['label'].lower()or'注册号'in f['label'])

def main():
 settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();universe=load_json(ROOT/'config/drugsfda-inventory-universe.json');taxonomy=load_json(ROOT/'config/sectors.v1.json');today=datetime.now(timezone.utc).date()
 result=collect(store,settings,universe,taxonomy,'chictr',today,today+timedelta(days=1),'daily',DetailReplay(),selection='all',max_pages=1)
 report={'source':'chictr','at':now(),'registration':REGISTRATION,**result}
 if result.get('manifest'):
  m=json.loads(store.get(result['manifest']).body);report['records']=m['record_count'];report['window_id']=digest(m['task'])
  if result['status']=='complete':
   key='constellation-backfill/specialist-publication-queue/chictr-detail-repair/'+report['window_id']+'.json'
   if store.get(key)is None:write_json(store,key,{'window_id':report['window_id'],'manifests':[result['manifest']],'queued_at':now()})
 write_json(store,'constellation-backfill/legacy-operation-receipts/chictr-detail-repair/'+today.isoformat()+'/'+digest(report)+'.json',report);print(json.dumps(report),flush=True)
 if result['status']!='complete':raise SystemExit(2)
if __name__=='__main__':main()
