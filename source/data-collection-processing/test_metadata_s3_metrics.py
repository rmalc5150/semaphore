import hashlib
import unittest
from unittest.mock import Mock

from metadata_engine.s3_metrics import MeteredS3
from metadata_engine.worker import put


class S3MetricsTests(unittest.TestCase):
    def test_counts_direct_and_paginated_operations(self):
        client = Mock()
        paginator = Mock()
        paginator.paginate.return_value = iter(({'Contents': []}, {'Contents': []}))
        client.get_paginator.return_value = paginator
        s3 = MeteredS3(client)
        s3.get_object(Bucket='b', Key='a')
        list(s3.get_paginator('list_objects_v2').paginate(Bucket='b'))
        self.assertEqual(s3.counts(), {'get_object': 1, 'list_objects_v2': 2})

    def test_successful_checksum_write_has_no_readback(self):
        s3 = Mock()
        body = b'checked bytes'
        put(s3, 'bucket', 'key', body)
        self.assertEqual(s3.get_object.call_count, 0)
        self.assertEqual(s3.put_object.call_count, 1)
        self.assertIn('ChecksumSHA256', s3.put_object.call_args.kwargs)

