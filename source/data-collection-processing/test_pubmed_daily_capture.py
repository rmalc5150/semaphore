import io,unittest
from unittest.mock import Mock,patch
import pubmed_daily_capture as capture

class DailyCapture(unittest.TestCase):
 def test_failed_topic_is_logged_and_does_not_stop_next_topic(self):
  store=Mock();store.get.return_value=None;settings=Mock();settings.store.return_value=store
  topics=[{'source':'pubmed_abstracts','parameters':{'term':x}} for x in ('failed','next')]
  with patch.object(capture,'open',return_value=io.StringIO()),patch.object(capture.fcntl,'flock'),patch.object(capture.StorageSettings,'load',return_value=settings),patch.object(capture,'load_json',return_value={'sources':[{'source':'pubmed_abstracts'}]}),patch.object(capture,'jobs',return_value=topics),patch.object(capture,'collect',side_effect=[RuntimeError('bounded failure'),{'status':'partial'}]) as collect,patch.object(capture,'write_json') as save,patch('sys.stdout',new=io.StringIO()):
   with self.assertRaises(SystemExit) as stopped:capture.main()
  self.assertEqual(stopped.exception.code,2);self.assertEqual(collect.call_count,2);self.assertEqual(save.call_count,2)
  self.assertEqual(save.call_args_list[0].args[2]['status'],'failed');self.assertEqual(save.call_args_list[1].args[2]['status'],'partial')
