import json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from collection_storage import LocalStore,StorageSettings,write_json
from research_contract import ROOT,load_json
from regulatory_collection import SourceIssue
import nmpa_resumed_capture as worker
class ResumeChecks(unittest.TestCase):
 def test_inventory_cache_is_incremental_and_checks_new_raw_checksums(self):
  import hashlib
  from unittest.mock import Mock
  from collection_storage import write_checked
  with tempfile.TemporaryDirectory()as tmp:
   store=LocalStore(tmp);raw=(json.dumps({'source':'nmpa_trials','dataset':'registry_inventory','source_record_id':'CTR20230001'})+'\n').encode();write_checked(store,'batch',raw);manifest={'task':{'source':'nmpa_trials'},'pages':[{'batches':[{'key':'batch','sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'records':1}]}]};path=str(Path(tmp)/'cache.sqlite3')
   self.assertEqual(worker.cached_inventory_ids(store,manifest,path),{'CTR20230001'})
   with patch.object(store,'get',side_effect=AssertionError('verified old batch fetched twice')):self.assertEqual(worker.cached_inventory_ids(store,manifest,path),{'CTR20230001'})
   empty={**manifest,'pages':[]};self.assertEqual(worker.cached_inventory_ids(store,empty,path),set())
   bad={'key':'bad','sha256':'wrong','bytes':len(raw),'records':1};write_checked(store,'bad',raw);manifest['pages'][0]['batches'].append(bad)
   with self.assertRaisesRegex(ValueError,'checksum'):worker.cached_inventory_ids(store,manifest,path)
 def test_budget_never_exceeds_configured_reservation(self):
  with tempfile.TemporaryDirectory()as tmp:
   store=LocalStore(tmp);self.assertTrue(worker.reserve(store,8));self.assertTrue(worker.reserve(store,8));self.assertFalse(worker.reserve(store,8))
 def test_publication_bridge_retains_exact_manifests_and_is_idempotent(self):
  from research_publication import bridge_nmpa_queue
  with tempfile.TemporaryDirectory()as tmp:
   settings=StorageSettings(local_root=tmp);store=settings.store();write_json(store,'constellation-backfill/specialist-publication-queue/nmpa-resumed/one.json',{'source':'nmpa_trials','dataset':'research_records','window_id':'one','manifests':['committed']})
   self.assertEqual(bridge_nmpa_queue(store,settings),1);self.assertEqual(bridge_nmpa_queue(store,settings),0);self.assertEqual(json.loads(store.get('operations/regulatory/publication-queue/one.json').body)['manifests'],['committed'])
 def test_reconciliation_retains_prior_original_html_for_change_proof(self):
  db=sqlite3.connect(':memory:');db.execute('CREATE TABLE trials(registration TEXT,manifest TEXT)');db.execute('INSERT INTO trials VALUES (?,?)',('CTR20230001','old-manifest'))
  old={'payload':{'record_type':'clinical_trial','source_evidence':[{'key':'prior-original','sha256':'verified'}],'data':{'structured':{'status':'old'}}},'ingested_at':'2026-01-01T00:00:00Z'};parent={'payload':{'source_evidence':[]}};trial=('CTR20230001',json.dumps(parent),'2025-01-01','{}','2025-01-01',0)
  with patch.object(worker,'output_rows',return_value=([old],[])):
   result=worker.prior_detail_trial(None,db,trial,{})
  self.assertEqual(json.loads(result[1])['payload']['source_evidence'][0]['key'],'prior-original');self.assertEqual(json.loads(result[3]),{'status':'old'});self.assertEqual(result[4],old['ingested_at']);db.close()
 def test_historical_page_failure_does_not_block_daily_discovery(self):
  from datetime import datetime,timezone,date
  with tempfile.TemporaryDirectory()as tmp:
   store=LocalStore(tmp);settings=StorageSettings(local_root=tmp);u=load_json(ROOT/'examples/research-contract/universe.json');t=load_json(ROOT/'config/sectors.v1.json');head={'status':'partial','task':{'scope':{'snapshot_date':'2026-09-22'}}};config={'max_provider_requests_per_day':100}
   with patch.object(worker,'inventory_context',return_value=(head,u,t)),patch.object(worker,'bounded_inventory',side_effect=[{'status':'partial','records':20},{'status':'deferred','reason':'provider_unavailable'}])as capture:
    r=worker.inventory_step(store,settings,config);self.assertEqual(capture.call_args_list[0].args[-1],datetime.now(timezone.utc).date());self.assertEqual(capture.call_args_list[1].args[-1],date(2026,9,22));self.assertEqual(r['results']['daily']['records'],20)
   with patch.object(worker,'inventory_context',return_value=(head,u,t)),patch.object(worker,'bounded_inventory',return_value={'status':'partial','records':20})as capture:
    r=worker.inventory_step(store,settings,config);self.assertEqual(capture.call_count,1);self.assertNotIn('baseline',r['results'])
 def test_bad_trial_does_not_block_remaining_trials_or_lose_progress(self):
  with tempfile.TemporaryDirectory()as tmp:
   store=LocalStore(tmp);settings=StorageSettings(local_root=tmp);universe=load_json(ROOT/'examples/research-contract/universe.json');taxonomy=load_json(ROOT/'config/sectors.v1.json');db=sqlite3.connect(':memory:');db.execute('CREATE TABLE trials(registration TEXT,parent TEXT,first_seen TEXT,baseline TEXT,baseline_at TEXT,attempts INT,status TEXT)')
   for i in range(4):db.execute('INSERT INTO trials VALUES(?,?,?,?,?,?,?)',(f'CTR2023000{i}','{}','2026-01-01','{}','2026-01-01',0,'pending'))
   head={'pages':[]};config={'seed_inventory_pages':0,'inventory_checkpoint':'head','max_provider_requests_per_day':16,'revisit_days':14};write_json(store,'head',head)
   def capture(s,settings,u,t,c,d,client,trial,cycle):
    if trial[0]=='CTR20230000':raise SourceIssue('scrape_target_http_403',True)
    manifest='test/'+trial[0]+'.json';write_json(s,manifest,{'task':{'source':'nmpa_trials','registration':trial[0]}});return [{}],[],manifest
   with patch.object(worker,'seed_database',return_value=db),patch.object(worker,'inventory_context',return_value=(head,universe,taxonomy)),patch.object(worker,'load_json',side_effect=lambda p:universe if 'universe'in str(p)else taxonomy),patch.object(worker,'capture',side_effect=capture):
    result=worker.details_step(store,settings,config)
   self.assertEqual([r['status']for r in result['results']],['retry','captured','captured','captured']);state=json.loads(store.get(worker.PREFIX+'/progress.json').body);self.assertEqual(state['processed'],3);self.assertEqual(state['last_registration'],'CTR20230003');self.assertEqual(state['retry_ids'][0]['registration'],'CTR20230000')
