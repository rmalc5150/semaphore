import copy,json,unittest
from pathlib import Path
from metadata_engine.cms_catalog import validate,ProviderError
class Catalog(unittest.TestCase):
 def setUp(self):
  self.record=json.loads(Path('repair-notes/2026-11-11-cms-payments/sample-record.json').read_text());self.row=self.record['payload']['data'];self.url=self.record['payload']['source_evidence'][0]['source_url']
 def body(self):return json.dumps([self.row]).encode()
 def test_original_descriptor(self):self.assertEqual(validate(self.body(),self.record,self.url)['provider'],'CMS Open Payments catalog')
 def test_missing_provider_field_rejected(self):
  body=self.body();self.record=copy.deepcopy(self.record);del self.record['payload']['data']['contactPoint']
  with self.assertRaises(ProviderError):validate(body,self.record,self.url)
 def test_wrong_identifier(self):
  self.record['source_record_id']='00000000-0000-0000-0000-000000000000'
  with self.assertRaises(ProviderError):validate(self.body(),self.record,self.url)
 def test_wrong_origin(self):
  with self.assertRaises(ProviderError):validate(self.body(),self.record,self.url.replace('openpaymentsdata.cms.gov','example.com'))
 def test_wrong_dataset_url(self):
  self.record['source_url']+='wrong'
  with self.assertRaises(ProviderError):validate(self.body(),self.record,self.url)
 def test_catalog_requires_download(self):
  self.row['distribution']=[]
  with self.assertRaises(ProviderError):validate(self.body(),self.record,self.url)
 def test_conflicting_duplicate_identity_rejected(self):
  other={**self.row,'title':'conflict'}
  with self.assertRaises(ProviderError):validate(json.dumps([self.row,other]).encode(),self.record,self.url)
 def test_repeated_identical_descriptor_allowed(self):self.assertEqual(validate(json.dumps([self.row,self.row]).encode(),self.record,self.url)['dataset_id'],self.row['identifier'])
 def test_query_projection_rejected(self):
  with self.assertRaises(ProviderError):validate(self.body(),self.record,self.url+'?fields=title')
