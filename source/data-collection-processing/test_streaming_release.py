import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from collection_storage import StorageSettings
from streaming_release import file_digest, upload, remote_digest


class BoundedBody(io.BytesIO):
    def read(self, size=-1):
        if size < 0 or size > 1024 * 1024:
            raise AssertionError('Unbounded object read')
        return super().read(size)


class StreamingTests(unittest.TestCase):
    def test_large_local_upload_retry_and_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'input'
            source.write_bytes(b'a' * (3 * 1024 * 1024 + 1))
            store = StorageSettings(local_root=str(root / 'store')).store()
            expected = file_digest(source)
            upload(store, 'curated/data', source, expected)
            upload(store, 'curated/data', source, expected)
            self.assertEqual(remote_digest(store, 'curated/data'), expected)
            source.write_bytes(b'changed')
            with self.assertRaises(FileExistsError):
                upload(store, 'curated/data', source, file_digest(source))

    def test_remote_readback_is_bounded_and_closed(self):
        class Store:
            client = Mock()
            def _args(self, key):
                return {'Bucket': 'test', 'Key': key}
        store = Store(); body = BoundedBody(b'x' * (3 * 1024 * 1024))
        store.client.get_object.return_value = {'Body': body}
        self.assertEqual(remote_digest(store, 'key')[1], 3 * 1024 * 1024)
        self.assertTrue(body.closed)


if __name__ == '__main__':
    unittest.main()
