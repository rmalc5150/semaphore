import unittest,io,json
from unittest.mock import Mock
from datetime import datetime,timezone
from collection_health_exporter import Evidence
class Limits(unittest.TestCase):
 def response(self,body,size=None):return {'Body':io.BytesIO(body),'ContentLength':len(body)if size is None else size,'LastModified':datetime.now(timezone.utc)}
 def test_large_runtime_index_allowed_and_closed(self):
  body=b'{"paths":{}}'+b' '*(9*1024*1024);r=self.response(body);s=Mock();s.get_object.return_value=r
  self.assertEqual(Evidence(s,'b','research-data').read('operations/s3-runtime/current.json')[0],{'paths':{}});self.assertTrue(r['Body'].closed)
 def test_ordinary_large_metadata_rejected_and_closed(self):
  r=self.response(b'{}',9*1024*1024);s=Mock();s.get_object.return_value=r
  with self.assertRaises(ValueError):Evidence(s,'b','research-data').read('other.json')
  self.assertTrue(r['Body'].closed)
 def test_runtime_cap_still_enforced(self):
  r=self.response(b'{}',33*1024*1024);s=Mock();s.get_object.return_value=r
  with self.assertRaises(ValueError):Evidence(s,'b','research-data').read('operations/s3-runtime/current.json')
