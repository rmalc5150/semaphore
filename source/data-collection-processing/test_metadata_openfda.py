import copy,json,unittest
from metadata_engine.openfda import validate,ProviderError
from research_contract import digest
class OpenFDA(unittest.TestCase):
 def setUp(self):
  self.sub={'submission_status':'AP','submission_type':'SUPPL','submission_number':'24','submission_status_date':'20260930'};self.app={'application_number':'ANDA040263','sponsor_name':'Example','products':[{'product_number':'001','brand_name':'Example'}],'submissions':[self.sub]};self.url='https://api.fda.gov/drug/drugsfda.json?limit=100';self.body={'meta':{'results':{'total':1}},'results':[self.app]};self.r={'source_record_id':'approval:ANDA040263:SUPPL:24','source_url':'https://api.fda.gov/drug/drugsfda.json','payload':{'data':{'action':'APPROVAL','application':copy.deepcopy(self.app),'submission':copy.deepcopy(self.sub)}}}
 def check(self,r=None,body=None,url=None):return validate(json.dumps(self.body if body is None else body).encode(),r or self.r,url or self.url)
 def test_approval_and_variant(self):
  self.assertEqual(self.check()['application_number'],'ANDA040263');r=copy.deepcopy(self.r);r['source_record_id']+=':variant:'+digest(r['payload']['data']);self.check(r)
  r['source_record_id']=r['source_record_id'][:-1]+'x'
  with self.assertRaises(ProviderError):self.check(r)
 def test_missing_modified_and_cross_application(self):
  for field in ('sponsor_name','products','application_number'):
   r=copy.deepcopy(self.r);r['payload']['data']['application'].pop(field)
   with self.assertRaises(ProviderError):self.check(r)
  r=copy.deepcopy(self.r);r['payload']['data']['submission']['submission_number']='99'
  with self.assertRaises(ProviderError):self.check(r)
 def test_identity_and_origin(self):
  r=copy.deepcopy(self.r);r['source_record_id']='approval:ANDA040263:SUPPL:25'
  with self.assertRaises(ProviderError):self.check(r)
  for u in [self.url.replace('api.fda.gov','evil.example'),self.url+'&count=sponsor_name',self.url+'&fields=application_number',self.url.replace('drugsfda.json','label.json')]:
   with self.assertRaises(ProviderError):self.check(url=u)
 def test_crl(self):
  row={'file_name':'example.pdf','letter_type':'COMPLETE RESPONSE','letter_date':'09/30/2026','company_name':'Example','text':'Public response'};r={'source_record_id':'crl:example.pdf','source_url':'https://api.fda.gov/transparency/crl.json','payload':{'data':row}};u=r['source_url'];self.check(r,{'results':[copy.deepcopy(row)]},u)
  variant=copy.deepcopy(r);variant['source_record_id']+=':variant:'+digest(row);self.check(variant,{'results':[copy.deepcopy(row)]},u)
  wrong=copy.deepcopy(row);wrong['company_name']='Other'
  with self.assertRaises(ProviderError):self.check(r,{'results':[wrong]},u)
 def test_receipt_and_non_approval(self):
  for body in ({'request':{'url':self.url}},{'results':[]}):
   with self.assertRaises(ProviderError):self.check(body=body)
  r=copy.deepcopy(self.r);r['payload']['data']['submission']['submission_status']='TA'
  with self.assertRaises(ProviderError):self.check(r)
if __name__=='__main__':unittest.main()
