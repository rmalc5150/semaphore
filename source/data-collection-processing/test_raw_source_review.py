import base64,json,unittest,copy
from unittest.mock import patch
from datetime import date
from public_source_scope import decoded_response,in_scope,canonical_link
from metadata_engine.raw_catalog_review import validate_arxiv
from metadata_engine.evidence import RawFailure
from specialist_inputs import item
from nhsbsa_capture import fetch

class PublicReview(unittest.TestCase):
 def test_decodo_pdf_base64_decoded_with_wrapper_retained(self):
  pdf=b'%PDF-1.4\nexample\n%%EOF';encoded=base64.b64encode(pdf)
  body,media,wrapper=decoded_response(encoded,'https://www.cda-amc.ca/sites/default/files/DRR/2025/x.pdf','text/html')
  self.assertEqual(body,pdf);self.assertEqual(media,'application/pdf');self.assertEqual(wrapper,encoded)
 def test_incomplete_encoded_pdf_cannot_pass(self):
  with self.assertRaises(ValueError):decoded_response(base64.b64encode(b'%PDF-1.4 incomplete'),'https://example.com/x.pdf','text/html')
 def test_gateway_html_is_not_pdf(self):
  value=b'<html>Challenge</html>';self.assertEqual(decoded_response(value,'https://example.com/x.pdf','text/html')[0],value)
 def test_scope_excludes_unrelated_pages_and_images(self):
  self.assertFalse(in_scope('https://www.g-ba.de/service/veranstaltungen/test/','germany_g_ba_drug_benefit_assessments',True));self.assertFalse(in_scope('https://ifr.org/downloads/press/robot.jpg','international_federation_of_robotics_world_robotics'))
  self.assertFalse(in_scope('https://www.data.gouv.fr/datasets/population','france_assurance_maladie_open_medic',True))
 def test_native_ucdp_archive_allowed(self):self.assertTrue(in_scope('https://ucdp.uu.se/downloads/ged/ged261-csv.zip','ucdp_organized_violence'))
 def test_benefit_assessment_pdf_allowed(self):self.assertTrue(in_scope('https://www.g-ba.de/downloads/92-975-10168/2026-11-02_Nutzenbewertung-IQWiG_Durvalumab_D-1362.pdf','germany_g_ba_drug_benefit_assessments'))
 def test_has_relative_links_do_not_duplicate_jcms(self):self.assertEqual(canonical_link('jcms/x/fr/avis','https://www.has-sante.fr/jcms/y/fr/open-data',{'source':'france_has_medicine_assessment_opinions'}),'https://www.has-sante.fr/jcms/x/fr/avis')
 def arxiv(self):
  raw=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/2601.12345v2</id><title>Title</title><summary>Entire abstract</summary><published>2026-01-01</published><updated>2026-01-02</updated><author><name>A</name></author><category term="cs.AI"/></entry></feed>'
  data={'id':'http://arxiv.org/abs/2601.12345v2','title':'Title','summary':'Entire abstract','published':'2026-01-01','updated':'2026-01-02','authors':['A'],'categories':['cs.AI']};return raw,{'source_record_id':data['id'],'payload':{'data':data}}
 def test_arxiv_native_metadata_is_not_full_text(self):self.assertEqual(validate_arxiv(*self.arxiv())['record_type'],'publication_abstract_record')
 def test_native_manifest_arxiv_payload_is_matched(self):
  raw,row=self.arxiv();row['payload']=row['payload']['data'];self.assertEqual(validate_arxiv(raw,row)['record_type'],'publication_abstract_record')
 def test_arxiv_forged_abstract_rejected(self):
  raw,row=self.arxiv();row['payload']['data']['summary']='Changed'
  with self.assertRaises(RawFailure):validate_arxiv(raw,row)
 def test_nhsbsa_pagination_uses_actual_returned_rows(self):
  client=type('Client',(),{})();job={'parameters':{'period':'202401'}};catalog={'success':True,'result':{'resources':[{'name':'EPD_202401','format':'CSV'}]}}
  record={'YEAR_MONTH':202401,'ACTUAL_COST':0};page={'success':True,'result':{'records':[record],'fields':[{'id':'YEAR_MONTH'}],'resource_id':'EPD_202401','total':3}}
  with patch('additional_source_apis.get_json',side_effect=[({'success':True,'result':{'resources':[]}},None),(catalog,None),(page,None)]):rows,cursor=fetch(client,job,None,item)
  self.assertEqual(json.loads(cursor)['offset'],1);self.assertEqual(rows[0]['data']['native_record']['ACTUAL_COST'],0);self.assertNotIn('fields',job['parameters'])

class HASFileEncoding(unittest.TestCase):
 def test_cp1252_dollar_quoted_semicolon_export(self):
  import tempfile
  from pathlib import Path
  from metadata_engine.public_documents import validate_has_export
  with tempfile.TemporaryDirectory()as tmp:
   p=Path(tmp)/'asmr.csv';p.write_bytes('$Code$;$Dénomination$\r\n$CT-1$;$Médicament; formulation$\r\n'.encode('cp1252'));entry={'path':p};validate_has_export(entry)
   self.assertEqual(entry['validation']['rows'],1);self.assertEqual(entry['validation']['encoding'],'cp1252')
 def test_malformed_export_rejected(self):
  import tempfile
  from pathlib import Path
  from metadata_engine.public_documents import validate_has_export
  with tempfile.TemporaryDirectory()as tmp:
   p=Path(tmp)/'asmr.csv';p.write_text('one;two\n1;2;3\n')
   with self.assertRaises(RawFailure):validate_has_export({'path':p})

class CurrentNHS(unittest.TestCase):
 def test_current_snomed_catalogue_and_hyphenated_period(self):
  catalog={'success':True,'result':{'resources':[{'name':'EPD_SNOMED_202608','format':'CSV'}]}}
  old={'success':True,'result':{'resources':[{'name':'EPD_202506','format':'CSV'}]}}
  record={'YEAR_MONTH':'2026-08','SNOMED_CODE':'123','ACTUAL_COST':0}
  page={'success':True,'result':{'records':[record],'fields':[{'id':'SNOMED_CODE'}],'resource_id':'EPD_SNOMED_202608','total':1}}
  with patch('additional_source_apis.get_json',side_effect=[(catalog,None),(old,None),(page,None)]):rows,cursor=fetch(type('C',(),{})(),{'parameters':{}},None,item)
  self.assertIsNone(cursor);self.assertEqual(rows[0]['data']['native_record'],record);self.assertEqual(rows[0]['data']['dataset_id'],'english-prescribing-dataset-epd-with-snomed-code')

class HASDiscovery(unittest.TestCase):
 def test_native_link_export_discovers_only_medicine_opinions(self):
  from public_source_capture import discover
  source={'source':'france_has_medicine_assessment_opinions','hosts':['www.has-sante.fr'],'max_depth':3}
  url='https://static.data.gouv.fr/resources/evaluation-des-medicaments/20261028/url-has-20261028.csv'
  native=b'$Code$;$URL$\n$CT-1$;$https://www.has-sante.fr/jcms/p_1/fr/kisqali-avis-ct21717$\n$CT-2$;$https://evil.example/steal$\n'
  self.assertEqual(discover(native,url,source,1),[{'url':'https://www.has-sante.fr/jcms/p_1/fr/kisqali-avis-ct21717','depth':2}])
 def test_dataset_instructions_are_not_an_assessment(self):
  self.assertFalse(in_scope('https://static.data.gouv.fr/resources/evaluation-des-medicaments/20261028/medicament-explication.pdf','france_has_medicine_assessment_opinions'))

class WorldwideEquipmentDiscovery(unittest.TestCase):
 def test_worldwide_rows_exclude_japanese_only_and_fpd_equipment(self):
  from public_source_capture import discover
  source={'source':'semi_worldwide_equipment_billings','hosts':['www.seaj.or.jp'],'max_depth':3}
  html=b'<table><tr><td>Semiconductor Manufacturing Equipment(World Wide SEMS Report)</td><td><a href="world.pdf">PDF</a></td></tr><tr><td>Japan-only equipment</td><td><a href="japan.pdf">PDF</a></td></tr><tr><td>FPD</td><td><a href="fpd.pdf">PDF</a></td></tr></table>'
  self.assertEqual(discover(html,'https://www.seaj.or.jp/english/statistics/index.html',source,0),[{'url':'https://www.seaj.or.jp/english/statistics/world.pdf','depth':1}])

class NativeHASLinkFormat(unittest.TestCase):
 def test_headerless_native_export_discovers_ids_and_counts_first_record(self):
  import tempfile
  from pathlib import Path
  from public_source_capture import discover
  from metadata_engine.public_documents import validate_has_export
  body=b'CT-21575;https://www.has-sante.fr/jcms/p_4585939\nCT-21772;https://www.has-sante.fr/jcms/p_4585712\n'
  source={'source':'france_has_medicine_assessment_opinions','hosts':['www.has-sante.fr'],'max_depth':3}
  self.assertEqual(len(discover(body,'https://static.data.gouv.fr/resources/evaluation-des-medicaments/20261028/url-has-20261028.csv',source,1)),2)
  with tempfile.TemporaryDirectory()as tmp:
   p=Path(tmp)/'links.csv';p.write_bytes(body);entry={'path':p};validate_has_export(entry);self.assertEqual(entry['validation']['rows'],2);self.assertFalse(entry['validation']['header_present'])

if __name__=='__main__':unittest.main()
