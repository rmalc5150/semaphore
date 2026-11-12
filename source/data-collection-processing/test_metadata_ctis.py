import unittest,json,copy
from metadata_engine.ctis import validate,ProviderError
class CTIS(unittest.TestCase):
 def setUp(self):
  self.id='2026-526189-25-00';self.decision={'id':9,'decision':'authorized'};self.app={'id':7,'submissionDate':'2026-01-01','decisions':[self.decision]};self.detail={'ctNumber':self.id,'authorizedApplication':{'applicationInfo':[self.app]}};self.url='https://euclinicaltrials.eu/ctis-public-api/retrieve/'+self.id
  self.record={'source_record_id':self.id,'source_url':'https://euclinicaltrials.eu/ctis-public/view/'+self.id,'payload':{'record_type':'clinical_trial','data':{'detail':copy.deepcopy(self.detail),'summary':{'ctNumber':self.id}}}}
 def check(self,r=None,d=None,u=None):return validate(json.dumps(self.detail if d is None else d).encode(),r or self.record,u or self.url)
 def test_full_detail(self):self.assertEqual(self.check()['ct_number'],self.id)
 def test_event_records(self):
  r=copy.deepcopy(self.record);r['payload']['record_type']='regulatory_event';r['source_record_id']=self.id+':application:7:submitted';r['payload']['data']={'application':self.app,'action':'SUBMITTED','trial_summary':{'ctNumber':self.id}};self.check(r)
  r['source_record_id']=self.id+':decision:9';r['payload']['data']={'application_id':7,'decision':self.decision,'trial_summary':{'ctNumber':self.id}};self.check(r)
  r['payload']['data']['application_id']=8
  with self.assertRaises(ProviderError):self.check(r)
 def test_wrong_host_search_projection(self):
  for u in [self.url.replace('euclinicaltrials.eu','evil.example'),self.url.replace('/retrieve/'+self.id,'/search'),self.url+'?fields=ctNumber']:
   with self.assertRaises(ProviderError):self.check(u=u)
 def test_mismatched_or_missing_original(self):
  for d in [{'ctNumber':'2026-123456-00-00'}, {'ctNumber':self.id}, {'ctNumber':self.id,'authorizedApplication':{'applicationInfo':[]}}]:
   with self.assertRaises(ProviderError):self.check(d=d)
  r=copy.deepcopy(self.record);r['payload']['data']['detail']['ctNumber']='wrong'
  with self.assertRaises(ProviderError):self.check(r)
 def test_summary_and_url_identity(self):
  for field in ['url','summary']:
   r=copy.deepcopy(self.record)
   if field=='url':r['source_url']+='wrong'
   else:r['payload']['data']['summary']['ctNumber']='wrong'
   with self.assertRaises(ProviderError):self.check(r)
if __name__=='__main__':unittest.main()
