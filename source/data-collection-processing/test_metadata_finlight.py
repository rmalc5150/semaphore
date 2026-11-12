import json,unittest
from metadata_engine.finlight import validate,ProviderError
class Finlight(unittest.TestCase):
 def setUp(self):
  self.row={'link':'https://publisher.example/a','title':'A report','publishDate':'2026-11-09T01:00:00Z','source':'publisher.example','language':'en','summary':'A summary'};self.record={'source_url':self.row['link'],'source_record_id':self.row['link'],'payload':{'data':dict(self.row)}};self.url='https://api.finlight.me/v2/articles'
 def body(self,rows=None):return json.dumps({'status':'ok','page':1,'articles':[self.row]if rows is None else rows}).encode()
 def test_original_provider_row_matches(self):
  self.assertEqual(validate(self.body(),self.record,self.url)['article_identity'],self.row['link'])
 def test_request_receipt_is_not_response(self):
  with self.assertRaises(ProviderError):validate(b'{"endpoint":"x","parameters":{}}',self.record,self.url)
 def test_changed_identity_or_content_rejected(self):
  with self.assertRaises(ProviderError):validate(self.body([]),self.record,self.url)
  self.record['payload']['data']['title']='changed'
  with self.assertRaises(ProviderError):validate(self.body(),self.record,self.url)
 def test_other_host_or_duplicate_rejected(self):
  with self.assertRaises(ProviderError):validate(self.body(),self.record,'https://other.example/api')
  with self.assertRaises(ProviderError):validate(self.body([self.row,self.row]),self.record,self.url)
