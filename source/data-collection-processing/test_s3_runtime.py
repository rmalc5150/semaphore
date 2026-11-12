"""Exercise lazy state recovery, persistence ordering and disk-write prevention."""
from contextlib import closing
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from botocore.exceptions import ClientError
import s3_runtime
import s3_runtime_fs as fs


class Body(io.BytesIO):
    def iter_chunks(self, chunk_size):
        while True:
            value = self.read(chunk_size)
            if not value:
                break
            yield value


class Store:
    def __init__(self):
        self.objects = {}
        self.etags = {}
        self.corrupt = False

    def get_object(self, Bucket, Key):
        if Key not in self.objects:
            raise ClientError({'Error': {'Code': 'NoSuchKey'}}, 'GetObject')
        value = self.objects[Key]
        if self.corrupt and '/snapshots/' in Key and not Key.endswith('manifest.json'):
            value += b'corrupt'
        return {'Body': Body(value), 'ETag': self.etags.get(Key, 'seed-etag')}

    def put_object(self, Bucket, Key, Body, IfMatch=None, IfNoneMatch=None, **kwargs):
        if (IfMatch and IfMatch != self.etags.get(Key)) or (IfNoneMatch == '*' and Key in self.objects):
            raise ClientError({'Error': {'Code': 'PreconditionFailed'}}, 'PutObject')
        self.objects[Key] = Body
        self.etags[Key] = hashlib.md5(Body).hexdigest()
        return {'ETag': self.etags[Key]}

    def upload_file(self, Filename, Bucket, Key, **kwargs):
        self.objects[Key] = Path(Filename).read_bytes()


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/tmp')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'code'
        self.base = Path(self.temp.name) / 'ram'
        self.work = self.base / 'work'
        self.root.mkdir()
        self.work.mkdir(parents=True)
        for name in ('locks', 'deletions'):
            (self.base / name).mkdir()
        self.s3 = Store()
        self.state = {'schema_version': 1, 'paths': {}}
        self.patches = []
        for module in (fs, s3_runtime):
            for name, value in [('ROOT', self.root), ('BASE', self.base), ('WORK', self.work)]:
                patcher = patch.object(module, name, value)
                patcher.start()
                self.addCleanup(patcher.stop)
        patcher = patch.object(fs, '_INDEX', self.state['paths'])
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch.object(fs, '_CLIENT', self.s3)
        patcher.start()
        self.addCleanup(patcher.stop)

    def remote(self, rel, data):
        key = 'seed/' + rel
        self.s3.objects[key] = data
        self.state['paths'][rel] = {'key': key, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

    def test_checkpoint_uploads_before_enumerating_the_entire_tree(self):
        first=self.work/'first.json';first.write_text('{}')
        second=self.work/'second.json';second.write_text('{}')
        def paths():
            yield first
            self.assertTrue(any('/snapshots/run-stream/first.json'in key for key in self.s3.objects),
                            'Checkpoint must stream files instead of collecting all paths in RAM')
            yield second
        with patch.object(s3_runtime,'normalize_databases'),patch.object(Path,'rglob',return_value=paths()):
            state,_=s3_runtime.checkpoint(self.s3,self.state,None,'test','run-stream')
        self.assertEqual(set(state['paths']),{'first.json','second.json'})

    def test_lazy_json_hydration_is_verified_and_keeps_disk_empty(self):
        self.remote('reports/latest.json', b'{"offset":7}')
        self.assertFalse((self.work / 'reports/latest.json').exists())
        mapped = fs.hydrate(self.root / 'reports/latest.json')
        self.assertEqual(mapped.read_bytes(), b'{"offset":7}')
        self.assertFalse((self.root / 'reports/latest.json').exists())

    def test_corrupt_hydration_leaves_no_target(self):
        self.remote('reports/state.json', b'good')
        self.s3.objects['seed/reports/state.json'] = b'bad'
        with self.assertRaisesRegex(ValueError, 'checksum'):
            fs.hydrate(self.root / 'reports/state.json')
        self.assertFalse((self.work / 'reports/state.json').exists())

    def test_python_writes_are_redirected_and_source_writes_denied(self):
        original = io.open
        path = self.root / 'reports/latest.json'
        with fs.mapped_open(original, path, 'w') as handle:
            handle.write('{"progress":1}')
        self.assertFalse(path.exists())
        self.assertTrue((self.work / 'reports/latest.json').exists())
        with self.assertRaises(PermissionError):
            fs.mapped_open(original, self.root / 'capture.py', 'w')

    def test_remote_glob_discovers_only_requested_plans(self):
        self.remote('reports/eodhd-auto-plan-2026-10-09.json', b'{}')
        self.remote('reports/other.json', b'{}')
        self.assertEqual([p.name for p in fs.glob(self.root / 'reports', 'eodhd-auto-plan-*.json')],
                         ['eodhd-auto-plan-2026-10-09.json'])

    def test_sqlite_readonly_uri_recovers_existing_state(self):
        source = self.base / 'original.sqlite3'
        with closing(sqlite3.connect(source)) as db:
            db.execute('CREATE TABLE progress (n INTEGER)')
            db.execute('INSERT INTO progress VALUES (42)')
            db.commit()
        self.remote('progress.sqlite3', source.read_bytes())
        uri = 'file:' + str(self.root / 'progress.sqlite3') + '?mode=ro'
        with closing(fs.connect(uri, uri=True)) as db:
            self.assertEqual(db.execute('SELECT n FROM progress').fetchone(), (42,))
        self.assertFalse((self.root / 'progress.sqlite3').exists())

    def test_checkpoint_preserves_unhydrated_state_and_applies_deletions(self):
        self.remote('untouched.sqlite3', b'old-state-not-downloaded')
        self.remote('reports/retry.json', b'{"retry":true}')
        fs.unlink(self.root / 'reports/retry.json')
        (self.work / 'reports').mkdir(exist_ok=True)
        (self.work / 'reports/latest.json').write_text('{"progress":2}')
        state, etag = s3_runtime.checkpoint(self.s3, self.state, None, 'test', 'run1')
        self.assertIn('untouched.sqlite3', state['paths'])
        self.assertNotIn('reports/retry.json', state['paths'])
        self.assertIn('reports/latest.json', state['paths'])
        self.assertIn(s3_runtime.CURRENT, self.s3.objects)

    def test_failed_readback_does_not_advance_durable_pointer(self):
        (self.work / 'reports').mkdir()
        (self.work / 'reports/latest.json').write_text('{}')
        self.s3.corrupt = True
        with self.assertRaisesRegex(ValueError, 'checksum'):
            s3_runtime.checkpoint(self.s3, self.state, None, 'test', 'run1')
        self.assertNotIn(s3_runtime.CURRENT, self.s3.objects)
        self.assertTrue((self.work / 'reports/latest.json').exists())

    def test_compare_and_swap_rejects_concurrent_checkpoint(self):
        self.s3.put_object(Bucket='', Key=s3_runtime.CURRENT, Body=b'{"paths":{}}')
        with self.assertRaises(ClientError):
            s3_runtime.checkpoint(self.s3, self.state, 'stale-etag', 'test', 'run1')
        self.assertEqual(self.s3.objects[s3_runtime.CURRENT], b'{"paths":{}}')

    def test_installed_hooks_support_pathlib_and_native_parquet_in_ram(self):
        import builtins
        import os
        import pyarrow as pa
        import pyarrow.parquet as pq
        (self.root / 'reports').mkdir()
        directory = self.work / 'research-window-build'
        directory.mkdir()
        (self.root / 'research-window-build').symlink_to(directory, target_is_directory=True)
        self.remote('reports/previous.json', b'{"previous":1}')
        self.remote('reports/retry.json', b'{"retry":true}')
        try:
            fs.install()
            self.assertEqual((self.root / 'reports/previous.json').read_text(), '{"previous":1}')
            (self.root / 'reports/latest.json').write_text('{"latest":2}')
            self.assertFalse(os.path.exists(self.root / 'reports/latest.json'))
            self.assertEqual((self.work / 'reports/latest.json').read_text(), '{"latest":2}')
            (self.root / 'reports/retry.json').unlink()
            self.assertFalse((self.root / 'reports/retry.json').exists())
            self.assertNotIn('retry.json', [p.name for p in (self.root / 'reports').glob('*.json')])
            with closing(sqlite3.connect(self.root / 'fresh.sqlite3')) as db:
                db.execute('CREATE TABLE rows(n INTEGER)')
                db.execute('INSERT INTO rows VALUES(7)')
                db.commit()
            self.assertFalse(os.path.exists(self.root / 'fresh.sqlite3'))
            target = self.root / 'research-window-build/part.parquet'
            pq.write_table(pa.table({'n': [1, 2]}), target)
            self.assertTrue(os.path.exists(directory / 'part.parquet'))
            with self.assertRaises(PermissionError):
                (self.root / 'capture.py').write_text('overwrite')
        finally:
            builtins.open = fs._OPEN
            io.open = fs._IO_OPEN
            Path.stat = fs._STAT
            Path.glob = fs._GLOB
            Path.rglob = fs._RGLOB
            Path.unlink = fs._UNLINK
            sqlite3.connect = fs._CONNECT

    def test_uspto_gate_preserves_symlink_and_persisted_reservation(self):
        import os
        import builtins
        from uspto_rate_limit import pace
        rel = '.uspto-request-gate.json'
        original = self.root / rel
        original.symlink_to(self.work / rel)
        self.remote(rel, b'{"next_request_at":102}')
        sleeps = []
        try:
            fs.install()
            with patch.dict(os.environ, {'OPTIMA_S3_RUNTIME': '1'}):
                pace(original, interval=2, clock=lambda: 100, sleeper=sleeps.append)
            self.assertTrue(os.path.islink(original))
            self.assertEqual(json.loads((self.work / rel).read_text()), {'next_request_at':104})
            self.assertEqual(sleeps, [2])
            self.assertFalse((self.work / '.uspto-request-gate.pending.json').exists())
        finally:
            builtins.open = fs._OPEN
            io.open = fs._IO_OPEN
            Path.stat = fs._STAT
            Path.glob = fs._GLOB
            Path.rglob = fs._RGLOB
            Path.unlink = fs._UNLINK
            sqlite3.connect = fs._CONNECT

    def test_path_traversal_is_rejected_in_remote_index(self):
        self.s3.objects[s3_runtime.CURRENT] = b'{"paths":{"../escape":{}}}'
        with self.assertRaisesRegex(ValueError, 'Unsafe path'):
            s3_runtime.read_index(self.s3)


if __name__ == '__main__':
    unittest.main()
