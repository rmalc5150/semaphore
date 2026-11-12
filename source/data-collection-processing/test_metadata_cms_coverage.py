import copy,json,unittest
from pathlib import Path
from metadata_engine.cms_coverage import validate,ProviderError,enrichment
class CMS(unittest.TestCase):
 def setUp(self):
  self.policy=json.loads(Path('repair-notes/2026-11-10-cms/cms_coverage/sample-record.json').read_text())
  self.doc=json.loads(Path('repair-notes/2026-11-10-cms/cms_coverage_documents/sample-record.json').read_text())
 def original(self,r):
  d=r['payload']['data'];return json.dumps(d if r['source']=='cms_coverage_documents' else {'data':[d],'meta':{'status':{'id':200}}}).encode()
 def url(self,r):return r['payload']['source_evidence'][0]['source_url']
 def test_both_originals(self):
  for r in (self.policy,self.doc):self.assertEqual(validate(self.original(r),r,self.url(r))['provider'],'CMS national coverage')
 def test_entire_record_required(self):
  for r in (self.policy,self.doc):
   body=self.original(r);r=copy.deepcopy(r)
   if r['source']=='cms_coverage':r['payload']['data'].pop('last_updated')
   else:r['payload']['data']['data'][0].pop('revision_history')
   with self.assertRaises(ProviderError):validate(body,r,self.url(r))
 def test_identity_mismatch(self):
  for r in (self.policy,self.doc):
   r['source_record_id']='NCD:999:1'
   with self.assertRaises(ProviderError):validate(self.original(r),r,self.url(r))
 def test_document_request_version(self):
  with self.assertRaises(ProviderError):validate(self.original(self.doc),self.doc,self.url(self.doc).replace('ncdver=2','ncdver=3'))
 def test_unapproved_origin(self):
  with self.assertRaises(ProviderError):validate(self.original(self.doc),self.doc,self.url(self.doc).replace('api.coverage.cms.gov','example.com'))
 def test_inventory_url_mismatch(self):
  self.policy['source_url']=self.policy['source_url'].replace('ncdid=306','ncdid=307')
  with self.assertRaises(ProviderError):validate(self.original(self.policy),self.policy,self.url(self.policy))
 def test_valid_short_policy_is_not_a_gap(self):
  row=self.doc['payload']['data']['data'][0];row['indications_limitations']='Not covered.';row['item_service_description']=''
  self.assertEqual(validate(self.original(self.doc),self.doc,self.url(self.doc))['provider'],'CMS national coverage')
 def test_missing_body(self):
  row=self.doc['payload']['data']['data'][0];row['indications_limitations']='';row['item_service_description']=''
  with self.assertRaises(ProviderError):validate(self.original(self.doc),self.doc,self.url(self.doc))
 def test_error_status(self):
  self.doc['payload']['data']['meta']['status']['id']=403
  with self.assertRaises(ProviderError):validate(self.original(self.doc),self.doc,self.url(self.doc))
 def test_unfinished_document_page(self):
  self.doc['payload']['data']['meta']['next_token']='more'
  with self.assertRaises(ProviderError):validate(self.original(self.doc),self.doc,self.url(self.doc))
 def test_readable_context_preserves_original(self):
  original=copy.deepcopy(self.doc['payload']['data']);context=enrichment(original)
  self.assertGreater(len(context['coverage_criteria_text']),100)
  self.assertNotIn('&lt;p',context['coverage_criteria_text'])
  self.assertFalse(context['historical_vintage_verified'])
  self.assertEqual(original,self.doc['payload']['data'])
if __name__=='__main__':unittest.main()
