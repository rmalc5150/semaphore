from datetime import date
import tempfile
import unittest
from unittest.mock import patch
from collection_storage import StorageSettings
from collection_operations import load_stored
from research_contract import ROOT,load_json
from news_operations import NewsOperations
from window_publication import list_keys

class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.settings=StorageSettings(local_root=self.temp.name)
        self.store=self.settings.store()
        self.runner=NewsOperations(self.store,self.settings,load_json(ROOT/'config/news-operations.json'))

    def test_partial_never_queued_and_resume_advances_only_completed_provider(self):
        def collect(*args):
            return {'status':'partial','reason':'page_limit'} if args[5]=='finlight' else {'status':'complete','manifest':'complete'}
        with patch('news_operations.collect',side_effect=collect):
            result=self.runner.run(lambda *a:None,date(2026,9,24))
        state,_=load_stored(self.store,self.runner.prefix+'/finlight/daily.json')
        self.assertEqual(state['next_date'],'2026-09-23')
        state,_=load_stored(self.store,self.runner.prefix+'/marketaux/daily.json')
        self.assertEqual(state['next_date'],'2026-09-24')
        self.assertEqual(result['status'],'partial')
        keys=list_keys(self.store,self.settings,'operations/news/publication-queue/')
        self.assertTrue(keys)
        self.assertTrue(all(load_stored(self.store,k)[0]['provider']=='marketaux' for k in keys))

    def test_reconciliation_revision_is_stable_across_partial_retry(self):
        seen=[]
        def collect(*args):
            if args[4].get('reconciliation_revision'):
                seen.append(args[4]['reconciliation_revision']); return {'status':'partial','reason':'page_limit'}
            return {'status':'complete','manifest':'complete'}
        with patch('news_operations.collect',side_effect=collect):
            self.runner.run(lambda *a:None,date(2026,9,24))
            self.runner.run(lambda *a:None,date(2026,9,25))
        self.assertTrue(seen)
        self.assertEqual(set(seen),{'2026-09-24'})

    def test_source_drift_refresh_is_once_per_day_and_keeps_prior_manifest(self):
        calls = []
        def collect(*args):
            calls.append(args[13])
            return {'status': 'failed', 'reason': 'news_source_changed_refresh_required', 'manifest': 'old-evidence'}
        with patch('news_operations.collect', side_effect=collect):
            self.runner.window('marketaux', date(2026,9,25), 'daily', None, self.runner.daily)
            self.runner.window('marketaux', date(2026,9,25), 'daily', None, self.runner.daily)
        self.assertEqual(calls, [False, True, False])
        keys = list_keys(self.store, self.settings, self.runner.prefix + '/restarts/')
        self.assertEqual(load_stored(self.store, keys[0])[0]['prior_manifest'], 'old-evidence')

    def test_queue_write_failure_cannot_advance_collection_cursor(self):
        original=__import__('news_operations').write_json
        def write(store,key,*args):
            if '/publication-queue/' in key: raise RuntimeError('queue down')
            return original(store,key,*args)
        with patch('news_operations.collect',return_value={'status':'complete','manifest':'m'}), patch('news_operations.write_json',side_effect=write):
            with self.assertRaises(RuntimeError): self.runner.run(lambda *a:None,date(2026,9,24))
        self.assertIsNone(load_stored(self.store,self.runner.prefix+'/finlight/daily.json')[0])

if __name__=='__main__': unittest.main()
