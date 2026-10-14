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
        with self.assertRaisesRegex(ValueError, 'Uncommitted'):
            discover(self.store, self.settings)


if __name__ == '__main__':
    unittest.main()
