import io,json,unittest
from unittest.mock import Mock,patch
import epmc_fulltext_capture as capture
class BoundedCapture(unittest.TestCase):
 def test_list_is_bounded_and_resumes_after_saved_key(self):
  store=Mock();store.client.list_objects_v2.return_value={'Contents':[{'Key':'research-data/q/a.json'}],'IsTruncated':True};settings=Mock(s3_prefix='research-data',s3_bucket='bucket')
  keys,more=capture.listed(store,settings,'q/','q/0.json');self.assertEqual(keys,['q/a.json']);self.assertTrue(more);self.assertEqual(store.client.list_objects_v2.call_args.kwargs['MaxKeys'],50);self.assertEqual(store.client.list_objects_v2.call_args.kwargs['StartAfter'],'research-data/q/0.json')
 def test_failed_article_gets_cooldown_and_next_article_still_runs(self):
  jobs=[{'source':'europe_pmc_fulltext','parameters':{'pmcid':'PMC1'}},{'source':'europe_pmc_fulltext','parameters':{'pmcid':'PMC2'}}];store=Mock();store.get.side_effect=[Mock(body=json.dumps(j))for j in jobs]
  with patch.object(capture,'listed',return_value=(['one','two'],False)),patch.object(capture,'load_state',return_value={}),patch.object(capture,'deadline'),patch.object(capture,'collect',side_effect=[RuntimeError('document unavailable'),{'status':'partial'}])as collect,patch.object(capture,'save_state')as save,patch.object(capture,'report',side_effect=lambda s,t,e:e):
   capture.capture(store,Mock(),{},{});
  self.assertEqual(collect.call_count,2);failed=[c.args[2]for c in save.call_args_list if c.args[2].get('status')=='failed'];self.assertEqual(len(failed),1);self.assertGreater(failed[0]['retry_after'],0)
 def test_mutable_checkpoint_uses_existing_etag(self):
  store=Mock();store.get.return_value=Mock(token='existing-etag')
  with patch.object(capture,'write_json')as put:capture.save_state(store,'state',{'cursor':'next'})
  self.assertEqual(put.call_args.args[3],'existing-etag')
 def test_incomplete_windows_are_never_queued_for_publication(self):
  store=Mock();capture.queue_window(store,{}, {'status':'partial','manifest':'incomplete'});store.get.assert_not_called()
