import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,Mock
import product_search_daily as p
from collection_storage import LocalStore,StorageSettings
from research_contract import ROOT,load_json,validate_record
from disclosure_collection import get_bytes


def receipt(endpoint,results):
 return {'http_status':200,'url':p.API+endpoint,'raw_s3_key':'research-data/test/'+endpoint.replace('/','_'),
  'sha256':'a'*64,'observed_at':'2026-10-18T10:00:00Z','data':{'status_code':20000,'tasks':[{'status_code':20000,'result':results}]}}

class ProductSearch(unittest.TestCase):
 def setUp(self):
  self.product={'product_id':'prd_00000000-0000-4000-8000-000000000001','canonical_name':'Robot X','sector_id':'robotics','review_status':'pending','collection_enabled':False,'row_version':1}
  self.query=p.product_queries({'products':[self.product]})[0]
  self.locale={'location_code':2840,'location_name':'United States','language_code':'en'}
  self.serp=receipt(p.SERP,[{'datetime':'2026-10-18 10:00:00 +00:00','items':[
   {'type':'organic','rank_group':2,'rank_absolute':4,'url':'https://maker.example/robot','title':'Robot X'},
   {'type':'video','items':[{'type':'video_element','url':'https://video.example/watch'}]}]}])
  self.trend=receipt(p.TRENDS,[{'items':[{'type':'dataforseo_trends_graph','keywords':['Robot X'],'data':[{'date_from':'2026-10-01','date_to':'2026-10-07','values':[20]}]},
    {'type':'subregion_interests','interests':[{'keyword':'Robot X','values':[{'geo_id':'US','geo_name':'United States','value':100},{'geo_id':'DE','geo_name':'Germany','value':0}]}]}]}])
 def test_all_nonarchived_products_even_if_collection_disabled(self):
  rejected={**self.product,'product_id':'rejected','review_status':'rejected'}
  archived={**self.product,'product_id':'archived','archived_at':'2026-01-01'}
  out=p.product_queries({'products':[self.product,rejected,archived]})
  self.assertEqual([r['product_id'] for r in out],[self.product['product_id']])
 def test_duplicate_names_remain_distinct_products_and_flag_ambiguity(self):
  out=p.product_queries({'products':[self.product,{**self.product,'product_id':'other'}]})
  self.assertEqual(len(out),2);self.assertTrue(all(x['query_ambiguity']=='duplicate_registry_name' for x in out))
 def test_geography_is_relative_and_domains_are_not_referrals(self):
  data=p.summarize(self.serp,self.trend,'Robot X')
  self.assertEqual({d['domain'] for d in data['visible_domains']},{'maker.example','video.example'})
  self.assertEqual(data['visible_domains'][0]['best_organic_rank'],2)
  self.assertEqual(data['geographic_interest']['regions'][1]['value'],0)
  self.assertIn('not visitor counts',data['geographic_interest']['unit'])
 def test_provider_errors_are_not_empty_success(self):
  bad=copy.deepcopy(self.serp);bad['data']['tasks'][0]['status_code']=40100
  with self.assertRaisesRegex(Exception,'no_paid_retry'):p.response_results(bad)
 def test_monthly_volumes_reuse_evidence_and_do_not_invent_zero(self):
  with tempfile.TemporaryDirectory() as d:
   store=LocalStore(d);paid=Mock(return_value=receipt(p.VOLUME,[{'keyword':'robot x','search_volume':None,'monthly_searches':[]}]))
   first=p.volumes(store,paid,[self.query],self.locale,'2026-10-18')
   second=p.volumes(store,paid,[self.query],self.locale,'2026-10-19')
   self.assertEqual(paid.call_count,1);self.assertEqual(first,second)
   self.assertEqual(first['Robot X']['status'],'insufficient_or_unavailable_data')
 def test_product_daily_commit_and_replay_no_additional_requests(self):
  universe=load_json(ROOT/'examples/sec-filings/universe.json');taxonomy=load_json(ROOT/'config/sectors.v1.json')
  with tempfile.TemporaryDirectory() as d:
   store=LocalStore(d);paid=Mock(side_effect=[self.serp,self.trend])
   volume={'status':'available','observed_at':'2026-10-01T00:00:00Z','provider_observation':{'search_volume':20},'evidence':p.evidence(self.serp)}
   snap={'key':'directory','sha256':'b'*64,'source_url':'rds://metadata_engine/entities?entity_type=product','retrieved_at':'2026-10-18T00:00:00Z'}
   out=p.collect_product(store,StorageSettings(),universe,taxonomy,paid,self.query,self.locale,'2026-10-18',volume,snap)
   replay=p.collect_product(store,StorageSettings(),universe,taxonomy,paid,self.query,self.locale,'2026-10-18',volume,snap)
   self.assertEqual(paid.call_count,2);self.assertTrue(replay['replayed'])
   m=json.loads(get_bytes(store,out['manifest']));b=m['pages'][0]['batches'][0]
   r=json.loads(get_bytes(store,b['key'],b['sha256']).splitlines()[0])
   self.assertEqual(validate_record(r,universe),[])
   self.assertEqual(r['payload']['data']['product']['product_id'],self.product['product_id'])
   self.assertIsNone(r['payload']['data']['actual_referral_sources']);self.assertFalse(r['payload']['data']['keyword_metrics']['refreshed_on_this_day'])
 def test_daily_budget_includes_monthly_calls(self):
  with tempfile.TemporaryDirectory() as d,patch.object(p,'ROOT',Path(d)):
   cfg={'daily_budget_usd':'1','request_reservation_usd':{'volume':'.20','snapshot':'.02'}}
   paid=p.PaidCapture('2026-10-18',cfg)
   folder=paid.monthly/'captures';folder.mkdir(parents=True)
   (folder/'receipt.json').write_text(json.dumps({'observed_at':'2026-10-18T00:00:00Z','sha256':'x','data':{'cost':1}}))
   with self.assertRaisesRegex(Exception,'budget_exhausted'):paid(p.SERP,{'keyword':'Robot X'})
 def test_ambiguous_paid_request_blocks_new_spending(self):
  with tempfile.TemporaryDirectory() as d,patch.object(p,'ROOT',Path(d)):
   paid=p.PaidCapture('2026-10-18',{'daily_budget_usd':'1','request_reservation_usd':{'volume':'.20','snapshot':'.02'}})
   folder=paid.folder/'captures';folder.mkdir(parents=True);(folder/'unknown.pending').write_text('pending')
   with self.assertRaisesRegex(Exception,'ambiguous_paid_request'):paid(p.SERP,{'keyword':'Robot X'})

 def test_empty_registry_replays_status_and_never_calls_provider(self):
  real_root=ROOT
  universe=load_json(real_root/'examples/sec-filings/universe.json');taxonomy=load_json(real_root/'config/sectors.v1.json')
  config={'storage_config':'storage','universe':'universe','taxonomy':'taxonomy','locales':[self.locale],
    'daily_budget_usd':'1','request_reservation_usd':{'volume':'.20','snapshot':'.02'}}
  with tempfile.TemporaryDirectory() as d:
   settings=StorageSettings(local_root=str(Path(d)/'store'))
   with patch.object(p,'ROOT',Path(d)),patch.object(p.StorageSettings,'load',return_value=settings),patch('product_search_directory.read_products',return_value={'products':[]}),patch.object(p,'load_json',side_effect=lambda path:universe if path.name=='universe' else taxonomy),patch.object(p.PaidCapture,'__call__') as paid:
    one=p.execute(config,'2026-10-18');two=p.execute(config,'2026-10-18')
   self.assertEqual(one['status'],'pending_dependency');self.assertEqual(two['actual_provider_cost_usd'],'0')
   self.assertIsNone(two['expected_observations']);paid.assert_not_called()

class DirectoryRepair(unittest.TestCase):
 def test_missing_registry_persists_pending_without_paid_calls(self):
  config={'storage_config':'storage','directory':{'mode':'metadata_engine'}}
  with tempfile.TemporaryDirectory()as tmp:
   settings=StorageSettings(local_root=str(Path(tmp)/'store'))
   with patch.object(p,'ROOT',Path(tmp)),patch.object(p.StorageSettings,'load',return_value=settings),patch('product_search_directory.read_products',return_value={'products':[]}),patch.object(p,'PaidCapture')as paid:
    r=p.execute(config,'2026-11-10',write_local_report=False)
   self.assertEqual(r['status'],'pending_dependency');self.assertIsNone(r['expected_observations']);self.assertFalse(r['capture_ready']);paid.assert_not_called()
   saved=json.loads(settings.store().get('operations/product-search/daily/2026-11-10/state.json').body)
   self.assertEqual(saved['requests_made'],0)
 def test_graph_products_include_candidates_without_inventing_sector(self):
  import product_search_directory as directory
  from contextlib import contextmanager
  class Cursor:
   def execute(self,*args):pass
   def fetchall(self):return [
    {'entity_hex':'0'*31+'1','name_original':'Product A','name_kind':'canonical','review_status':'verified'},
    {'entity_hex':'0'*31+'1','name_original':'Alias A','name_kind':'alias','review_status':'candidate'},
    {'entity_hex':'0'*31+'2','name_original':'Candidate B','name_kind':'source_label','review_status':'candidate'}]
  class DB:
   def __init__(self,*args):pass
   @contextmanager
   def tx(self):yield Cursor()
  with patch.object(directory,'Database',DB):r=directory.read_products()
  self.assertEqual(len(r['products']),2);self.assertEqual(len(p.product_queries(r)),2)
  self.assertTrue(all(x['sector_id']is None for x in r['products']));self.assertEqual(r['aliases'][0]['alias'],'Alias A')
 def test_runner_preserves_supervisor_for_populated_directory(self):
  import product_search_runner as runner
  with patch('product_search_directory.read_products',return_value={'products':[{'id':'one'}]}),patch.object(runner.os,'execvp',side_effect=RuntimeError('exec_called'))as execute:
   with self.assertRaisesRegex(RuntimeError,'exec_called'):runner.main(['--','/usr/bin/flock','lock','capture'])
   execute.assert_called_once_with('/usr/bin/flock',['/usr/bin/flock','lock','capture'])

if __name__=='__main__':unittest.main()
