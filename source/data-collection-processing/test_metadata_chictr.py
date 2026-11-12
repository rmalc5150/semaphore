import copy,hashlib,io,unittest
from unittest.mock import Mock,patch
from metadata_engine.chictr import validate,ProviderError
from metadata_engine.chictr_tables import parse_detail_page
from metadata_engine.evidence import evidence_for
class ChiCTRValidation(unittest.TestCase):
 def setUp(self):
  self.url='https://www.chictr.org.cn/showproj.html?proj=343036';self.body='<html><body><table><tr><td>注册号： Registration number</td><td>ChiCTR2600132684</td></tr><tr><td>注册时间： Date of Registration</td><td>2026-09-17</td></tr><tr><td>Public title</td><td>Example trial</td></tr><tr><td>Intervention</td><td>Example treatment<br>Detailed schedule</td></tr></table></body></html>'.encode();self.data={'registrationNumber':'ChiCTR2600132684','projectId':'343036','registrationDate':'2026-09-17','detailUrl':self.url,'fields':parse_detail_page(self.body.decode())};self.record={'source':'chictr','source_record_id':'ChiCTR2600132684','source_url':self.url,'payload':{'data':copy.deepcopy(self.data)}}
 def test_registry_timestamp_matches_day_without_changing_raw_fields(self):
  body=self.body.replace(b'2026-09-17',b'2026-09-17 00:00:00');r=copy.deepcopy(self.record);r['payload']['data']['fields']=parse_detail_page(body.decode());validate(body,r,self.url)
 def test_complete_original_field_list(self):self.assertEqual(validate(self.body,self.record,self.url)['field_count'],4)
 def test_wrong_origin_search_page_and_project_are_rejected(self):
  for u in [self.url.replace('www.chictr.org.cn','evil.example'),self.url.replace('showproj','searchproj'),self.url.replace('343036','123')]:
   with self.assertRaises(ProviderError):validate(self.body,self.record,u)
 def test_mismatched_registry_number_and_modified_or_partial_fields(self):
  for change in ('identity','modified','partial','date'):
   r=copy.deepcopy(self.record)
   if change=='identity':r['source_record_id']='ChiCTR2600132685';r['payload']['data']['registrationNumber']=r['source_record_id']
   elif change=='modified':r['payload']['data']['fields'][-1]['value']='Different treatment'
   elif change=='partial':r['payload']['data']['fields'].pop()
   else:r['payload']['data']['registrationDate']='2026-09-18'
   with self.assertRaises(ProviderError):validate(self.body,r,self.url)
 def test_incomplete_rendered_table_retries_before_capture(self):
  import tempfile
  from regulatory_collection import EvidenceClient
  from collection_storage import LocalStore
  from metadata_engine.chictr_tables import has_trial_detail
  with tempfile.TemporaryDirectory()as tmp:
   client=EvidenceClient(LocalStore(tmp),'chictr',sleeper=Mock())
   with patch('decodo_scraping_api.cached_token',return_value='fixture'),patch('decodo_scraping_api.scrape_content',side_effect=['<table><tr><td>Loading</td></tr></table>',self.body.decode()])as fetch:
    result=client.rendered(self.url,pending_validator=has_trial_detail);self.assertEqual(result,self.body.decode());self.assertEqual(fetch.call_count,2);self.assertEqual(len(client.evidence),2)
 def test_access_block_cannot_replace_trial(self):
  with self.assertRaises(ProviderError):validate(b'<html><title>Access denied</title><table><tr><td>Login</td><td>Required</td></tr></table></html>',self.record,self.url)
 def test_only_matching_original_page_is_downloaded(self):
  sha=hashlib.sha256(self.body).hexdigest();self.record['payload']['source_evidence']=[{'key':'source_documents/chictr/search','sha256':sha,'source_url':self.url.replace('showproj','searchproj')},{'key':'source_documents/chictr/other','sha256':sha,'source_url':self.url.replace('343036','123')},{'key':'source_documents/chictr/detail','sha256':sha,'source_url':self.url}]
  s=Mock();s.get_object.return_value={'Body':io.BytesIO(self.body),'ContentLength':len(self.body)};policy={'adapter':'api_records','allowed_hosts':['www.chictr.org.cn'],'raw_requirements':{'required_artifact_kinds':['provider_record']}};out=evidence_for(self.record,policy,s,'bucket');self.assertEqual(out[0]['artifact_kind'],'provider_record');self.assertEqual(s.get_object.call_count,1);self.assertTrue(s.get_object.call_args.kwargs['Key'].endswith('/detail'))

class DiscoveryClassification(unittest.TestCase):
 def test_only_discovery_receipts_are_classified_as_non_trial_inputs(self):
  import json
  from metadata_engine.controller import enqueue_objects
  for kind,excluded in [('discovery_page',True),('primary_document',False)]:
   db=Mock();db.config={'bucket':'bucket','contracts':{'chictr':{'contract_version':'2.0.3'}}};db.enqueue.return_value=True;c=Mock();body=json.dumps({'source':'chictr','artifact_kind':kind}).encode()
   with patch('metadata_engine.controller.object_bytes',return_value=body):count=enqueue_objects(db,[{'Key':'receipt','ETag':'etag'}],'public_receipt',0,c)
   self.assertEqual(count,0 if excluded else 1);self.assertEqual(c.execute.called,excluded)
