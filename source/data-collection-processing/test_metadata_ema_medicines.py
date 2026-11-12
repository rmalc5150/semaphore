import copy,json,unittest
from unittest.mock import Mock
from specialist_public_apis import fetch
from specialist_inputs import item
from metadata_engine.ema_medicines import validate,ProviderError,REPORT
class EMAMedicines(unittest.TestCase):
 def setUp(self):
  self.url='https://www.ema.europa.eu'+REPORT;self.row={'ema_product_number':'EMEA/H/C/000001','name_of_medicine':'Example','category':'Human','medicine_status':'Withdrawn','first_published_date':'','medicine_url':'https://www.ema.europa.eu/en/medicines/human/EPAR/example'};self.record={'source_record_id':self.row['ema_product_number'],'source_url':self.row['medicine_url'],'payload':{'data':copy.deepcopy(self.row)}}
 def check(self,record=None,response=None,url=None):return validate(json.dumps(response or {'data':[self.row]}).encode(),record or self.record,url or self.url)
 def test_full_row(self):self.assertEqual(self.check()['medicine_status'],'Withdrawn')
 def test_modified_projection_duplicate_and_identity(self):
  r=copy.deepcopy(self.record);r['payload']['data'].pop('medicine_status')
  with self.assertRaises(ProviderError):self.check(r)
  with self.assertRaises(ProviderError):self.check(response={'data':[self.row,self.row]})
  r=copy.deepcopy(self.record);r['source_record_id']='Other'
  with self.assertRaises(ProviderError):self.check(r)
 def test_untrusted_origin_and_receipt(self):
  for u in [self.url.replace('www.ema.europa.eu','evil.example'),self.url+'?fields=name',self.url.replace(REPORT,'/en/medicines')]:
   with self.assertRaises(ProviderError):self.check(url=u)
  with self.assertRaises(ProviderError):self.check(response={'request':self.url})
 def test_daily_retains_every_status_category_and_unknown_date(self):
  rows=[self.row,{**self.row,'ema_product_number':'EMEA/V/C/000002','category':'Veterinary','medicine_status':'Refused','first_published_date':'01/01/1990'}];client=Mock();client.get.return_value=json.dumps({'meta':{},'data':rows}).encode();out,cursor=fetch(client,{'adapter':'ema_json','mode':'daily','parameters':{'url':self.url,'start':'2026-11-09','end':'2026-11-11'}},None,item);self.assertEqual(len(out),2);self.assertIsNone(cursor);self.assertIsNone(out[0]['date'])
if __name__=='__main__':unittest.main()
