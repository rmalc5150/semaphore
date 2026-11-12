import copy,json,unittest
from pathlib import Path
from metadata_engine.fda_authenticated import SOURCES,validate,ProviderError,context
BASE=Path('repair-notes/2026-11-11-fda-authenticated')
class FDA(unittest.TestCase):
 def setUp(self):
  self.examples={source:(json.loads((BASE/source/'sample-record.json').read_text()),(BASE/source/'sample-response.json').read_bytes())for source in SOURCES}
 def test_originals_all_sources(self):
  for source,(r,b)in self.examples.items():
   with self.subTest(source=source):self.assertEqual(validate(b,r,r['payload']['source_evidence'][0]['source_url'])['provider'],'FDA authenticated data')
 def test_whole_row_equality(self):
  for source,(r,b)in self.examples.items():
   r=copy.deepcopy(r);r['payload']['data'].pop(next(iter(r['payload']['data'])))
   with self.subTest(source=source),self.assertRaises(ProviderError):validate(b,r,r['payload']['source_evidence'][0]['source_url'])
 def test_identity_mismatch(self):
  for source,(r,b)in self.examples.items():
   r['source_record_id']='wrong'
   with self.subTest(source=source),self.assertRaises(ProviderError):validate(b,r,r['payload']['source_evidence'][0]['source_url'])
 def test_wrong_endpoint(self):
  for source,(r,b)in self.examples.items():
   with self.subTest(source=source),self.assertRaises(ProviderError):validate(b,r,'https://example.com/')
 def test_scope_date_checked(self):
  for source,(r,b)in self.examples.items():
   if source=='fda_product_codes':continue
   r['payload']['scope']['start']='2099-01-01'
   with self.subTest(source=source),self.assertRaises(ProviderError):validate(b,r,r['payload']['source_evidence'][0]['source_url'])
 def test_protocol_400_is_success_but_401_is_failure(self):
  for source,(r,b)in self.examples.items():
   data=json.loads(b);data['statuscode'if source.startswith('fda_dd_')else 'STATUSCODE'if source=='fda_ires_recalls'else'APIRETURNCODE']=401
   with self.subTest(source=source),self.assertRaises(ProviderError):validate(json.dumps(data).encode(),r,r['payload']['source_evidence'][0]['source_url'])
 def test_truncated_reference_rejected(self):
  r,b=self.examples['fda_product_codes'];data=json.loads(b);data['RESULT']['DATA']=data['RESULT']['DATA'][:1]
  with self.assertRaises(ProviderError):validate(json.dumps(data).encode(),r,r['payload']['source_evidence'][0]['source_url'])
 def test_industry_leading_zero_and_scope_preserved(self):
  r,b=self.examples['fda_product_codes'];c=context(r);self.assertFalse(c['full_five_component_taxonomy']);self.assertEqual(c['industry_code'],r['payload']['data']['INDID'])
 def test_legacy_recall_projection_is_explicit(self):self.assertTrue(context(self.examples['fda_ires_recalls'][0])['legacy_selected_columns'])
 def test_pcb_table_width_rejected(self):
  r,b=self.examples['fda_product_codes'];data=json.loads(b);data['RESULT']['DATA'][0].append('wrong')
  with self.assertRaises(ProviderError):validate(json.dumps(data).encode(),r,r['payload']['source_evidence'][0]['source_url'])
