"""Verify that archival failures and changing files cannot cause data loss."""
import base64
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from botocore.exceptions import ClientError


class Body(io.BytesIO):
    def iter_chunks(self, chunk_size):
        while True:
            chunk = self.read(chunk_size)
            if not chunk:
                return
            yield chunk


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.parts = []
        self.corrupt_archive = False
        self.on_archive_read = None
        self.fail_upload = False
        self.aborted = False

    def head_object(self, Key, **kwargs):
        if Key not in self.objects:
            raise ClientError({'Error': {'Code': '404'}}, 'HeadObject')
        return {}

    def put_object(self, Key, Body, ChecksumSHA256, **kwargs):
        assert base64.b64encode(hashlib.sha256(Body).digest()).decode() == ChecksumSHA256
        self.objects[Key] = Body

    def get_object(self, Key, **kwargs):
        value = self.objects[Key]
        if Key.endswith(('.tar', '.tar.gz')):
            if self.on_archive_read:
                self.on_archive_read()
            if self.corrupt_archive:
                value = value[:-1] + bytes([value[-1] ^ 1])
        return {'Body': Body(value)}

    def create_multipart_upload(self, **kwargs):
        return {'UploadId': 'test-upload'}

    def upload_part(self, Body, PartNumber, ChecksumSHA256, **kwargs):
        if self.fail_upload:
            raise RuntimeError('Upload failed')
        assert base64.b64encode(hashlib.sha256(Body).digest()).decode() == ChecksumSHA256
        self.parts.append(Body)
        return {'ETag': str(PartNumber), 'ChecksumSHA256': ChecksumSHA256}

    def complete_multipart_upload(self, Key, **kwargs):
        self.objects[Key] = b''.join(self.parts)

    def abort_multipart_upload(self, **kwargs):
        self.aborted = True


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/tmp')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / 'work'
        self.work.mkdir()
        self.group = self.root / 'outputs'
        self.group.mkdir()
        self.data = self.group / 'data.json'
        self.data.write_text('{"record": 1}\n')
        self.code = self.group / 'source.py'
        self.code.write_text('print("keep")\n')
        self.s3 = FakeS3()
        spec = importlib.util.spec_from_file_location('migration', Path(__file__).with_name('migrate_server_data_to_s3.py'))
        self.module = importlib.util.module_from_spec(spec)
        with patch('boto3.client', return_value=self.s3):
            spec.loader.exec_module(self.module)
        self.module.ROOT = self.root
        self.module.WORK = self.work

    def test_verified_archive_deletes_data_and_preserves_code(self):
        self.module.migrate('outputs', True, True)
        self.assertFalse(self.data.exists())
        self.assertTrue(self.code.exists())
        import tarfile
        archive = next(v for k, v in self.s3.objects.items() if k.endswith('.tar.gz'))
        with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as tf:
            self.assertEqual(tf.extractfile('outputs/data.json').read(), b'{"record": 1}\n')

    def test_corrupt_readback_preserves_local_data(self):
        self.s3.corrupt_archive = True
        with self.assertRaisesRegex(RuntimeError, 'SHA256'):
            self.module.migrate('outputs', True)
        self.assertTrue(self.data.exists())

    def test_changed_file_is_not_deleted(self):
        self.s3.on_archive_read = lambda: self.data.write_text('new content')
        self.module.migrate('outputs', True)
        self.assertEqual(self.data.read_text(), 'new content')

    def test_failed_upload_preserves_data_and_aborts_multipart(self):
        self.s3.fail_upload = True
        with self.assertRaisesRegex(RuntimeError, 'Upload failed'):
            self.module.migrate('outputs', True)
        self.assertTrue(self.data.exists())
        self.assertTrue(self.s3.aborted)

    def test_existing_archive_cannot_be_overwritten(self):
        self.s3.objects[self.module.PREFIX + '/outputs.tar'] = b'original backup'
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.module.migrate('outputs', True)
        self.assertTrue(self.data.exists())

    def test_code_configuration_and_path_traversal_are_rejected(self):
        for name in ['config', 'schemas', 'tests', 'examples', 'systemd']:
            (self.root / name).mkdir()
            with self.assertRaises(ValueError):
                self.module.migrate(name, True)
        with self.assertRaises(ValueError):
            self.module.migrate('../outputs', True)


if __name__ == '__main__':
    unittest.main()
