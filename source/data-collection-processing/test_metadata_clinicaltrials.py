import unittest,json,copy
from metadata_engine.clinicaltrials import validate,ProviderError
class ClinicalTrials(unittest.TestCase):
 def setUp(self):
  self.study={'protocolSection':{'identificationModule':{'nctId':'NCT01234567'},'statusModule':{'overallStatus':'RECRUITING'},'designModule':{'studyType':'INTERVENTIONAL'}},'hasResults':False};self.record={'source_record_id':'NCT01234567','source_url':'https://clinicaltrials.gov/study/NCT01234567','payload':{'data':copy.deepcopy(self.study)}};self.url='https://clinicaltrials.gov/api/v2/studies?format=json'
 def body(self):return json.dumps({'studies':[self.study]}).encode()
 def test_full_list_and_single_record(self):
  self.assertEqual(validate(self.body(),self.record,self.url)['nct_id'],'NCT01234567');validate(json.dumps(self.study).encode(),self.record,'https://clinicaltrials.gov/api/v2/studies/NCT01234567')
 def test_projection_and_wrong_host_rejected(self):
  for url in (self.url+'&fields=NCTId','https://other.example/api/v2/studies'):
   with self.assertRaises(ProviderError):validate(self.body(),self.record,url)
 def test_missing_protocol_or_changed_study_rejected(self):
  with self.assertRaises(ProviderError):validate(b'{"studies":[]}',self.record,self.url)
  self.record['payload']['data']['hasResults']=True
  with self.assertRaises(ProviderError):validate(self.body(),self.record,self.url)
 def test_duplicate_identity_and_request_receipt_rejected(self):
  with self.assertRaises(ProviderError):validate(json.dumps({'studies':[self.study,self.study]}).encode(),self.record,self.url)
  with self.assertRaises(ProviderError):validate(b'{"parameters":{}}',self.record,self.url)
