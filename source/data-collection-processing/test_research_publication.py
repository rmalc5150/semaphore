import tempfile
from pathlib import Path
import unittest
from collection_storage import StorageSettings, write_json
from research_contract import digest
from research_publication import discover


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.settings = StorageSettings(local_root=str(Path(tmp.name)))
        self.store = self.settings.store()
        self.task = {'source': 'sec_edgar', 'dataset': 'filings', 'window': {'start': '2021-01-01'}}
        self.wid = digest(self.task)
        self.head_key = 'checkpoints/task_' + self.wid + '/head.json'
        self.manifest_key = 'manifests/first/final.json'
        self.head = {'task': self.task, 'status': 'complete', 'terminal_manifest': self.manifest_key,
                     'terminal_history': [self.manifest_key]}
        write_json(self.store, self.head_key, self.head)
        write_json(self.store, self.manifest_key, {'task': self.task, 'task_id': 'task_' + self.wid,
                   'status': 'complete', 'exhausted': True})

    def test_committed_run_queued_once(self):
        self.assertEqual(discover(self.store, self.settings)['sec'], 1)
        self.assertEqual(discover(self.store, self.settings)['sec'], 0)

    def test_partial_refresh_preserves_existing_queue(self):
        discover(self.store, self.settings)
        key = 'operations/sec/publication-queue/' + self.wid + '.json'
        before = self.store.get(key).body
        obj = self.store.get(self.head_key)
        write_json(self.store, self.head_key, {**self.head, 'status': 'partial'}, obj.token)
        self.assertEqual(discover(self.store, self.settings)['sec'], 0)
        self.assertEqual(self.store.get(key).body, before)

    def test_uncommitted_run_rejected(self):
        obj = self.store.get(self.head_key)
        write_json(self.store, self.head_key, {**self.head, 'terminal_history': []}, obj.token)
        self.assertEqual(discover(self.store, self.settings)['sec'], 0)
        self.assertTrue(list((Path(self.settings.local_root) / 'operations/research-publication/failures').glob('*.json')))

    def test_bad_checkpoint_does_not_prevent_good_source(self):
        write_json(self.store, 'checkpoints/task_bad/head.json',
                   {**self.head, 'terminal_history': []})
        self.assertEqual(discover(self.store, self.settings)['sec'], 1)
        self.assertIsNotNone(self.store.get('operations/sec/publication-queue/' + self.wid + '.json'))


if __name__ == '__main__':
    unittest.main()

class GroupIsolationTests(unittest.TestCase):
    def test_legacy_controller_call_cannot_run_heavy_publication_inline(self):
        from unittest.mock import patch
        import research_publication as publication
        with patch.dict('os.environ',{'OPTIMA_S3_RUNTIME':'1'}),patch.object(publication,'ROOT',Path('/home/ec2-user/data-collection-processing')),patch.object(publication.StorageSettings,'load')as load,patch('sys.argv',['research_publication.py','--owners','people']):
            self.assertEqual(publication.main(),2)
            load.assert_not_called()

    def test_recovery_drains_existing_queue_without_discovery_scan(self):
        from unittest.mock import patch, Mock
        import research_publication as publication
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);settings=StorageSettings(local_root=str(root/'store'))
            with patch.object(publication,'ROOT',root),patch.object(publication,'GROUPS',{'sec':('sec.json',Mock())}),patch.object(publication.StorageSettings,'load',return_value=settings),patch.object(publication,'discover')as discover,patch.object(publication,'bridge_nmpa_queue')as bridge,patch.object(publication,'load_json',return_value={}),patch.object(publication,'publish_pending',return_value={'status':'complete'})as publish,patch('sys.argv',['research_publication.py','--skip-discovery']):
                self.assertEqual(publication.main(),0)
                discover.assert_not_called();bridge.assert_not_called();publish.assert_called_once()

    def test_group_exception_does_not_stop_next_group(self):
        from unittest.mock import patch, Mock
        import research_publication as publication
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = StorageSettings(local_root=str(root/'store'))
            module = Mock()
            with patch.object(publication, 'ROOT', root), \
                 patch.object(publication, 'GROUPS', {'bad':('bad.json',module),'good':('good.json',module)}), \
                 patch.object(publication.StorageSettings, 'load', return_value=settings), \
                 patch.object(publication, 'discover', return_value={}), \
                 patch.object(publication, 'load_json', return_value={}), \
                 patch.object(publication, 'publish_pending', side_effect=[RuntimeError('broken source'), {'status':'complete'}]) as publish, \
                 patch('sys.argv', ['research_publication.py']):
                self.assertEqual(publication.main(), 1)
                self.assertEqual([c.args[2] for c in publish.call_args_list], ['bad','good'])
