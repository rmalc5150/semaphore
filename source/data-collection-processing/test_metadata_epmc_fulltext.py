import copy,hashlib,io,unittest
from unittest.mock import Mock
from metadata_engine.epmc_fulltext import validate,parse_original,enrichment,evidence,ProviderError
from metadata_engine.evidence import RawFailure
XML='''<?xml version="1.0"?><article xmlns:xlink="http://www.w3.org/1999/xlink" article-type="research-article"><front><article-meta><article-id pub-id-type="pmcid">PMC123</article-id><title-group><article-title>Example trial</article-title></title-group><permissions><license>Source licence text</license></permissions></article-meta></front><body><sec><title>Results</title><p>Observed trial outcomes.<ext-link xlink:href="https://example.org"><?provider-route original?></ext-link></p></sec></body></article>'''
URL='https://www.ebi.ac.uk/europepmc/webservices/rest/PMC123/fullTextXML'
def record(xml=XML,url=URL):return {'source':'europe_pmc_fulltext','source_record_id':'PMC123','source_url':url,'payload':{'data':{'pmcid':'PMC123','article_xml':xml}}}
class FullText(unittest.TestCase):
 def test_original_full_article_and_processing_instructions(self):
  r=validate(XML.encode(),record(),URL);self.assertEqual(r['pmcid'],'PMC123');self.assertEqual(r['body_sections'],1);self.assertGreater(r['body_characters'],10)
 def test_wrong_id_abstract_only_and_modified_xml_rejected(self):
  for xml in [XML.replace('PMC123','PMC456'),XML.replace('<body>','<abstract>').replace('</body>','</abstract>'),XML.replace('Observed trial outcomes.','Invented findings.')]:
   with self.assertRaises(ProviderError):validate(XML.encode(),record(xml),URL)
 def test_derived_context_cannot_override_the_provider_article(self):
  r=record();r['payload']['data']['enrichment']={**enrichment(XML,'PMC123'),'title':'Invented'}
  with self.assertRaisesRegex(ProviderError,'derived_context_mismatch'):validate(XML.encode(),r,URL)
 def test_discovery_or_untrusted_origin_rejected(self):
  for url in [URL.replace('www.ebi.ac.uk','evil.example'),URL.replace('/fullTextXML','/search'),URL.replace('https:','http:')]:
   with self.assertRaises(ProviderError):validate(XML.encode(),record(url=url),url)
 def test_ncbi_fallback_retains_original_wrapper_identity(self):
  url='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=123&retmode=xml';xml=XML[XML.index('<article '):];body=('<pmc-articleset>'+xml+'</pmc-articleset>').encode();self.assertEqual(validate(body,record(xml,url),url)['pmcid'],'PMC123')
  with self.assertRaises(ProviderError):validate(body,record(xml,url),url.replace('id=123','id=456'))
 def test_full_body_and_licence_are_available_as_derived_context(self):
  r=enrichment(XML,'PMC123');self.assertIn('Observed trial outcomes.',r['body_text']);self.assertEqual(r['license_statements'][0]['text'],'Source licence text')
 def test_checksum_and_original_fulltext_reference_required(self):
  r=record();sha=hashlib.sha256(XML.encode()).hexdigest();r['payload']['source_evidence']=[{'key':'source_documents/europe_pmc_fulltext/'+sha,'sha256':sha,'source_url':URL}];s=Mock();s.get_object.return_value={'Body':io.BytesIO(XML.encode()),'ContentLength':len(XML)};a=evidence(r,s,'bucket');self.assertEqual(a[0]['artifact_kind'],'full_text');r['payload']['source_evidence'][0]['sha256']='bad';s.get_object.return_value={'Body':io.BytesIO(XML.encode()),'ContentLength':len(XML)}
  with self.assertRaises(RawFailure):evidence(r,s,'bucket')
 def test_policy_keeps_substantive_fulltext_requirement(self):
  from metadata_engine.source_policies import build
  from pathlib import Path
  p=build(Path('.'))['europe_pmc_fulltext'];self.assertIn('full_text',p['raw_requirements']['required_artifact_kinds']);self.assertIn('www.ebi.ac.uk',p['allowed_hosts'])

class DiscoveryReceiptClassification(unittest.TestCase):
 def test_only_confirmed_discovery_pages_are_excluded(self):
  import json
  from unittest.mock import patch
  from metadata_engine.controller import enqueue_objects
  for kind,excluded in [('discovery_page',True),('primary_document',False)]:
   db=Mock();db.config={'bucket':'bucket','contracts':{'europe_pmc_fulltext':{'contract_version':'2.0.3'}}};db.enqueue.return_value=True;c=Mock();body=json.dumps({'source':'europe_pmc_fulltext','artifact_kind':kind}).encode()
   with patch('metadata_engine.controller.object_bytes',return_value=body):count=enqueue_objects(db,[{'Key':'receipt','ETag':'etag'}],'public_receipt',0,c)
   self.assertEqual(count,0 if excluded else 1);self.assertEqual(c.execute.called,excluded)
