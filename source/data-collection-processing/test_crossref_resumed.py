import io,json,tempfile,unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock,patch
from collection_storage import LocalStore,StorageSettings,write_json
from conference_collection import advance,VERSION
from conference_athena import bridge_resumed
from research_contract import digest
import crossref_resumed_capture as worker
class Resumed(unittest.TestCase):
 def test_daily_failure_does_not_prevent_historical_attempt(self):
  store=Mock();settings=Mock();settings.store.return_value=store
  with patch.object(worker,'open',return_value=io.StringIO()),patch.object(worker.fcntl,'flock'),patch.object(worker.StorageSettings,'load',return_value=settings),patch.object(worker,'load_json',return_value={}),patch.object(worker,'historical_start',return_value=date(2016,1,1)),patch.object(worker,'deadline'),patch.object(worker,'advance',side_effect=[RuntimeError('bounded provider error'),{'status':'complete'}])as call,patch.object(worker,'write_json')as save,patch('sys.stdout',new=io.StringIO()):worker.main()
  self.assertEqual(call.call_count,2);self.assertEqual(save.call_count,2);self.assertEqual(save.call_args_list[0].args[2]['status'],'failed');self.assertEqual(save.call_args_list[1].args[2]['mode'],'historical')
 def test_native_progress_is_preserved_in_private_namespace(self):
  with tempfile.TemporaryDirectory()as tmp:
   store=LocalStore(tmp);settings=StorageSettings(local_root=tmp);u={'universe_version':'example'};t={};origin=date(2026,9,23);day=date(2026,11,9);identity=digest({'version':VERSION,'daily_filter':'update','universe':digest(u),'taxonomy':digest(t),'mode':'daily','origin':str(origin)});prefix='constellation-backfill/conferences-resumed';key=prefix+'/progress/'+identity+'.json';write_json(store,key,{'next_date':str(day)});write_json(store,'manifest.json',{'task':{'scope':{}},'status':'complete'})
   with patch.dict('os.environ',{'CONSTELLATION_CONFERENCE_OPERATION_PREFIX':prefix}),patch('conference_collection.collect',return_value={'status':'complete','manifest':'manifest.json'})as collect:r=advance(store,settings,u,t,'daily',origin,date(2026,11,10),max_pages=24)
   self.assertEqual(collect.call_args.args[4],day);self.assertEqual(collect.call_args.kwargs['max_pages'],24);self.assertEqual(json.loads(store.get(key).body)['next_date'],'2026-11-10')
 def test_stale_or_invalid_provider_cursors_restart(self):
  from conference_collection import recent_cursor
  head={'terminal_manifest':'old.json','cursor':'old-cursor'}
  for reason,at in [('conference_page_budget','2021-01-01T00:00:00Z'),('source_http_400','2099-01-01T00:00:00Z')]:
   with patch('conference_collection.load_stored',return_value=({'reason_code':reason,'finished_at':at},None)):self.assertFalse(recent_cursor(Mock(),head))
 def test_publication_bridge_is_idempotent(self):
  with tempfile.TemporaryDirectory()as tmp:
   settings=StorageSettings(local_root=tmp);store=settings.store();entry={'window_id':'example','manifests':['manifest.json']};write_json(store,'constellation-backfill/conferences-resumed/publication-queue/example.json',entry);self.assertEqual(bridge_resumed(store,settings),1);self.assertEqual(bridge_resumed(store,settings),0)
