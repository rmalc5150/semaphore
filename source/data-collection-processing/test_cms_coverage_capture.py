import io,json,unittest
from unittest.mock import Mock,patch
import cms_coverage_capture as capture
class BoundedCapture(unittest.TestCase):
 def test_list_is_bounded_and_resumes_after_saved_key(self):
  store=Mock();store.client.list_objects_v2.return_value={'Contents':[{'Key':'research-data/q/a.json'}],'IsTruncated':True};settings=Mock(s3_prefix='research-data',s3_bucket='bucket')
  keys,more=capture.listed(store,settings,'q/','q/0.json');self.assertEqual(keys,['q/a.json']);self.assertTrue(more);self.assertEqual(store.client.list_objects_v2.call_args.kwargs['MaxKeys'],50);self.assertEqual(store.client.list_objects_v2.call_args.kwargs['StartAfter'],'research-data/q/0.json')
 def test_failed_article_gets_cooldown_and_next_article_still_runs(self):
  jobs=[{'source':'cms_coverage_documents','parameters':{'query':{'ncdid':1,'ncdver':1}}},{'source':'cms_coverage_documents','parameters':{'query':{'ncdid':2,'ncdver':1}}}];store=Mock();store.get.side_effect=[Mock(body=json.dumps(j))for j in jobs]
  with patch.object(capture,'listed',return_value=(['one','two'],False)),patch.object(capture,'load_state',return_value={}),patch.object(capture,'deadline'),patch.object(capture,'collect',side_effect=[RuntimeError('document unavailable'),{'status':'partial'}])as collect,patch.object(capture,'save_state')as save,patch.object(capture,'report',side_effect=lambda s,t,e:e):
   capture.capture(store,Mock(),{},{});
  self.assertEqual(collect.call_count,2);failed=[c.args[2]for c in save.call_args_list if c.args[2].get('status')=='failed'];self.assertEqual(len(failed),1);self.assertGreater(failed[0]['retry_after'],0)
 def test_mutable_checkpoint_uses_existing_etag(self):
  store=Mock();store.get.return_value=Mock(token='existing-etag')
  with patch.object(capture,'write_json')as put:capture.save_state(store,'state',{'cursor':'next'})
  self.assertEqual(put.call_args.args[3],'existing-etag')
 def test_incomplete_windows_are_never_queued_for_publication(self):
  store=Mock();capture.queue_window(store,{}, {'status':'partial','manifest':'incomplete'});store.get.assert_not_called()

class MetadataQueue(unittest.TestCase):
 def test_complete_batch_enters_current_contract_queue(self):
  store=Mock();store.get.return_value=Mock(token='etag')
  with patch('metadata_engine.runtime_db.Database')as database,patch.object(capture,'load_json',return_value={'bucket':'b'}) :
   capture.queue_metadata(store,{'task':{'source':'cms_coverage_documents'},'pages':[{'batches':[{'key':'raw/source=cms_coverage_documents/x.jsonl'}]}]})
  database.return_value.enqueue.assert_called_once_with('cms_coverage_documents','research-data/raw/source=cms_coverage_documents/x.jsonl','etag','legacy_batch',100)

class RuntimeBoundary(unittest.TestCase):
 def test_worker_enqueue_uses_separate_metadata_installation(self):
  store=Mock();store.get.return_value=Mock(token='etag')
  with patch.object(capture.Path,'exists',return_value=True),patch('subprocess.run')as run:
   capture.queue_metadata(store,{'task':{'source':'cms_coverage_documents'},'pages':[{'batches':[{'key':'raw/source=cms_coverage_documents/x.jsonl'}]}]})
  self.assertEqual(str(run.call_args.kwargs['cwd']),'/opt/constellation/metadata-engine-runtime')
  self.assertEqual(run.call_args.kwargs['timeout'],30)
  self.assertTrue(run.call_args.kwargs['check'])
  self.assertEqual(json.loads(run.call_args.kwargs['input'])[0]['source'],'cms_coverage_documents')
 def test_daily_document_uses_todays_window(self):
  from datetime import datetime,timezone
  store=Mock();store.get.return_value=Mock(body=json.dumps({'source':'cms_coverage_documents','mode':'daily','start':'2000-01-01','end':'2000-01-02','parameters':{'query':{'ncdid':1,'ncdver':1}}}))
  with patch.object(capture,'listed',return_value=(['one'],False)),patch.object(capture,'load_state',return_value={}),patch.object(capture,'deadline'),patch.object(capture,'collect',return_value={'status':'partial'})as collect,patch.object(capture,'save_state'),patch.object(capture,'report',side_effect=lambda s,t,e:e):
   capture.capture(store,Mock(),{}, {})
  self.assertEqual(collect.call_args.args[0]['start'],datetime.now(timezone.utc).date().isoformat())
