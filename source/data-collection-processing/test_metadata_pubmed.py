import copy,hashlib,io,unittest,xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock
from metadata_engine.pubmed import validate,ProviderError,evidence
from metadata_engine.pubmed_enrichment import enrich
from metadata_engine.evidence import RawFailure
from metadata_engine.labelling import label_observation
class PubMedValidation(unittest.TestCase):
 def setUp(self):
  self.pmid='35129803';self.xml=Path('tests/fixtures/pubmed/'+self.pmid+'.xml').read_text();self.body=('<PubmedArticleSet>'+self.xml+'</PubmedArticleSet>').encode();self.url='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id='+self.pmid+'&retmode=xml';self.record={'source':'pubmed_abstracts','dataset':'specialist_inputs','source_record_id':self.pmid,'source_url':'https://pubmed.ncbi.nlm.nih.gov/'+self.pmid+'/','payload':{'data':{'pmid':self.pmid,'article_xml':self.xml}}}
 def test_whole_citation_and_abstract_are_verified_without_fulltext_claim(self):
  v=validate(self.body,self.record,self.url);self.assertEqual(v['abstract_status'],'provided');self.assertEqual(v['article_full_text'],'not_retrieved_or_established')
 def test_title_only_modified_xml_wrong_primary_pmid_or_enrichment_rejected(self):
  for case in ('truncated','pmid','enrichment'):
   r=copy.deepcopy(self.record)
   if case=='truncated':
    node=ET.fromstring(self.xml);node.find('MedlineCitation/Article').remove(node.find('MedlineCitation/Article/Abstract'));r['payload']['data']['article_xml']=ET.tostring(node,encoding='unicode')
   elif case=='pmid':r['source_record_id']='123';r['payload']['data']['pmid']='123'
   else:r['payload']['data']['enrichment']={**enrich(self.xml,self.pmid),'title':'Invented title'}
   with self.assertRaises(ProviderError):validate(self.body,r,self.url)
 def test_search_ids_wrong_host_or_non_xml_request_rejected(self):
  for url in (self.url.replace('efetch','esearch'),self.url.replace('eutils.ncbi.nlm.nih.gov','evil.example'),self.url.replace('retmode=xml','retmode=json')):
   with self.assertRaises(ProviderError):validate(self.body,self.record,url)
 def test_missing_provider_abstract_is_explicit_and_not_a_fulltext_error(self):
  pmid='34655480';xml=Path('tests/fixtures/pubmed/'+pmid+'.xml').read_text();record={**self.record,'source_record_id':pmid,'source_url':'https://pubmed.ncbi.nlm.nih.gov/'+pmid+'/','payload':{'data':{'pmid':pmid,'article_xml':xml}}};v=validate(('<PubmedArticleSet>'+xml+'</PubmedArticleSet>').encode(),record,self.url.replace(self.pmid,pmid));self.assertEqual(v['abstract_status'],'primary_abstract_not_provided')
 def test_book_record_primary_id_not_secondary_reference(self):
  xml='<PubmedBookArticle><BookDocument><PMID>123</PMID><ArticleTitle>Book chapter</ArticleTitle></BookDocument><PubmedBookData><ReferenceList><Reference><PMID>456</PMID></Reference></ReferenceList></PubmedBookData></PubmedBookArticle>';r={**self.record,'source_record_id':'123','source_url':'https://pubmed.ncbi.nlm.nih.gov/123/','payload':{'data':{'pmid':'123','article_xml':xml}}};validate(('<PubmedArticleSet>'+xml+'</PubmedArticleSet>').encode(),r,self.url.replace(self.pmid,'123'))
 def test_legacy_label_gets_derived_source_linked_context_and_scope(self):
  sha=hashlib.sha256(self.body).hexdigest();r=copy.deepcopy(self.record);r.update(ingested_at='2026-11-10T12:00:00Z');r['payload']['source_evidence']=[{'key':'source_documents/pubmed_abstracts/'+sha,'sha256':sha,'source_url':self.url}];s=Mock();s.get_object.return_value={'Body':io.BytesIO(self.body),'ContentLength':len(self.body)};art=evidence(r,s,'bucket');p={'source_key':'pubmed_abstracts','record_kind':'publication_abstract_record','contract_version':'2.0.3','adapter':'api_records','adapter_version':'2.0.3','license_policy_id':'test'};l=label_observation({**r,'raw_s3_uri':'s3://bucket/research-data/raw/batch','raw_sha256':'batchsha','raw_artifacts':art,'raw_completeness_status':'complete'},p);self.assertEqual(l['payload']['data']['enrichment']['pmid'],self.pmid);self.assertEqual(l['payload']['data']['article_xml'],self.xml);self.assertIn('pubmed_record_not_article_full_text',l['quality_flags']);self.assertNotIn('enrichment',r['payload']['data'])
 def test_fulltext_contracts_for_other_sources_remain_unchanged(self):
  from metadata_engine.source_policies import build
  from research_contract import ROOT
  p=build(ROOT);self.assertNotIn('full_text',p['pubmed_abstracts']['raw_requirements']['required_artifact_kinds']);self.assertIn('full_text',p['europe_pmc_fulltext']['raw_requirements']['required_artifact_kinds'])
