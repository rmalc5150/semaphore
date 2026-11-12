import copy,json,unittest
from unittest.mock import Mock
from metadata_engine.canada_noc import validate,ProviderError
from specialist_public_apis import fetch
from specialist_inputs import item
class CanadaNOC(unittest.TestCase):
 def setUp(self):
  self.url='https://health-products.canada.ca/api/notice-of-compliance/noticeofcompliancemain/'
  self.row={'noc_number':123,'noc_crp_product_name':'Example','noc_date':'1990-01-01','noc_active_status':'0','noc_last_update_date':'1111-11-11'}
  self.record={'source_record_id':'123','source_url':self.url,'payload':{'data':copy.deepcopy(self.row)}}
 def check(self,record=None,rows=None,url=None):return validate(json.dumps(rows if rows is not None else [self.row]).encode(),record or self.record,url or self.url+'?lang=en&type=json')
 def test_original_product_links(self):
  from metadata_engine.canada_noc import product_id
  row={'noc_number':123,'noc_br_product_id':4,'noc_br_brand_id':5,'noc_br_brandname':'Example','noc_br_din':'00123456'}
  r={'source_record_id':product_id(row),'source_url':self.url.replace('noticeofcompliancemain','drugproduct'),'payload':{'data':row}}
  self.check(record=r,rows=[row],url=r['source_url']+'?lang=en&type=json')
  r['payload']['data']={**row,'noc_br_din':'87654321'}
  with self.assertRaises(ProviderError):self.check(record=r,rows=[row],url=r['source_url']+'?lang=en&type=json')
 def test_product_pagination_resumes_without_overlap(self):
  from canada_noc_products_capture import page_rows
  rows=list(range(8001));a,c=page_rows(rows,0);b,d=page_rows(rows,c);e,f=page_rows(rows,d);self.assertEqual(a+b+e,rows);self.assertIsNone(f)
 def test_progress_updates_use_compare_and_swap(self):
  import tempfile
  from canada_noc_products_capture import save_progress
  from collection_storage import LocalStore
  with tempfile.TemporaryDirectory()as tmp:
   store=LocalStore(tmp);save_progress(store,'progress.json',{'captured_rows':4000});save_progress(store,'progress.json',{'captured_rows':8000});self.assertEqual(json.loads(store.get('progress.json').body)['captured_rows'],8000)
 def test_product_checkpoint_resume_real_storage(self):
  import tempfile
  from canada_noc_products_capture import page_rows
  from collection_storage import LocalStore,StorageSettings,CollectionRun,task_spec
  from specialist_inputs import normalized,item
  from research_contract import load_json,ROOT
  from metadata_engine.canada_noc import product_id
  universe=load_json(ROOT/'examples/research-contract/universe.json');taxonomy=load_json(ROOT/'config/sectors.v1.json')
  spec=task_spec('canada_noc','specialist_inputs','daily','2026-11-10T00:00:00Z','2026-11-11T00:00:00Z',{'parameters':{},'source_id':'S24','coverage_note':'fixture'},'test',universe,taxonomy)
  rows=[{'noc_number':1,'noc_br_product_id':2},{'noc_number':2,'noc_br_product_id':3}]
  with tempfile.TemporaryDirectory()as tmp:
   store=LocalStore(tmp);settings=StorageSettings(local_root=tmp);run=CollectionRun.start(store,spec,universe,taxonomy,settings)
   selected,cursor=page_rows(rows,0,1);run.commit_page((normalized(item(product_id(r),r,self.url,basis='derived'),run,[])for r in selected),next_cursor=cursor,exhausted=False);run.finish('partial','page_budget')
   resumed=CollectionRun.start(store,spec,universe,taxonomy,settings,resume=True);self.assertEqual(resumed.cursor,'1')
   selected,cursor=page_rows(rows,resumed.cursor,1);resumed.commit_page((normalized(item(product_id(r),r,self.url,basis='derived'),resumed,[])for r in selected),next_cursor=cursor,exhausted=True);key=resumed.finish('complete',expected_records=2);self.assertEqual(json.loads(store.get(key).body)['record_count'],2)
 def test_original_complete_row(self):self.assertEqual(self.check()['noc_number'],'123')
 def test_provider_empty_comparator_name_is_not_dropped(self):
  self.row['noc_crp_product_name']='';self.record['payload']['data']['noc_crp_product_name']='';self.check()
 def test_modified_row_duplicate_and_identity(self):
  r=copy.deepcopy(self.record);r['payload']['data'].pop('noc_active_status')
  with self.assertRaises(ProviderError):self.check(record=r)
  self.check(rows=[self.row,self.row])
  r=copy.deepcopy(self.record);r['source_record_id']='124'
  with self.assertRaises(ProviderError):self.check(record=r)
 def test_receipt_projection_wrong_host(self):
  for u in [self.url.replace('health-products.canada.ca','evil.example')+'?lang=en&type=json',self.url+'?lang=en&type=json&fields=noc_number',self.url]:
   with self.assertRaises(ProviderError):self.check(url=u)
  with self.assertRaises(ProviderError):self.check(rows={'receipt':self.url})
 def test_full_inventory_scope_not_company_filtered(self):
  from specialist_plan import jobs
  from datetime import date
  plan={'historical_start':'2016-01-01','backfill_end_exclusive':'2026-11-10','sources':[{'source_id':'S24','source':'canada_noc','adapter':'canada_noc','api':self.url,'enabled':True,'historical':True,'full_inventory':True}]}
  out=list(jobs(plan,{'companies':[]},'daily',date(2026,11,10)));self.assertEqual(len(out),1);self.assertTrue(out[0]['parameters']['full_inventory']);self.assertEqual(out[0]['parameters']['start'],'1900-01-01')
 def test_full_inventory_retains_old_inactive_and_all_types(self):
  client=Mock();client.get.return_value=json.dumps([self.row,{**self.row,'noc_number':124,'noc_date':'2026-11-09','noc_product_type':'Biologic'}]).encode()
  job={'adapter':'canada_noc','parameters':{'url':self.url,'query':{'lang':'en','type':'json'},'start':'2026-11-01','end':'2026-11-11','full_inventory':True}}
  rows,cursor=fetch(client,job,None,item);self.assertEqual(len(rows),2);self.assertIsNone(cursor)
  job['parameters']['full_inventory']=False;rows,_=fetch(client,job,None,item);self.assertEqual(len(rows),1)
