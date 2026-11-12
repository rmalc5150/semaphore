import copy,hashlib,io,json,unittest
from unittest.mock import Mock
from metadata_engine.crossref import validate,evidence,ProviderError
from metadata_engine.evidence import RawFailure
class CrossrefValidation(unittest.TestCase):
 def setUp(self):
  self.url='https://api.crossref.org/works?filter=type%3Aproceedings-article&rows=500&cursor=*';self.data={'DOI':'10.1234/example','type':'proceedings-article','title':['A trial report'],'author':[{'family':'Example','affiliation':[]}],'published':{'date-parts':[[2021]]},'event':{'name':'Example congress'},'license':[],'unanticipated-provider-field':{'retain':'all'}};self.body=json.dumps({'status':'ok','message':{'total-results':1,'items':[self.data]}}).encode();self.record={'source':'crossref_proceedings','source_record_id':'10.1234/example','source_url':'https://doi.org/10.1234/example','payload':{'data':copy.deepcopy(self.data)}}
 def test_full_metadata_without_abstract_is_valid_with_explicit_scope(self):
  r=validate(self.body,self.record,self.url);self.assertEqual(r['abstract_status'],'not_deposited_in_returned_metadata');self.assertIn('not_collected',r['full_text_status'])
 def test_missing_or_changed_provider_fields_and_wrong_type_or_doi_rejected(self):
  for field,value in [('author',[]),('type','journal-article'),('DOI','10.1234/other'),('title',['Invented'])]:
   r=copy.deepcopy(self.record);r['payload']['data'][field]=value
   with self.assertRaises(ProviderError):validate(self.body,r,self.url)
  r=copy.deepcopy(self.record);del r['payload']['data']['unanticipated-provider-field']
  with self.assertRaises(ProviderError):validate(self.body,r,self.url)
 def test_projection_wrong_origin_and_receipt_only_rejected(self):
  for url in [self.url+'&select=DOI,title',self.url.replace('api.crossref.org','evil.example'),self.url.replace('https:','http:')]:
   with self.assertRaises(ProviderError):validate(self.body,self.record,url)
  with self.assertRaises(ProviderError):validate(b'{"status":"ok","message":{}}',self.record,self.url)
 def test_single_work_and_case_insensitive_primary_doi(self):
  r=copy.deepcopy(self.record);r['source_record_id']='10.1234/EXAMPLE';validate(json.dumps({'status':'ok','message':self.data}).encode(),r,'https://api.crossref.org/works/10.1234%2Fexample')
 def test_original_bytes_are_checked_and_cached_once_per_shared_response(self):
  sha=hashlib.sha256(self.body).hexdigest();r=copy.deepcopy(self.record);r['payload']['source_evidence']=[{'key':'source_documents/crossref_proceedings/'+sha,'sha256':sha,'source_url':self.url}];s=Mock();s.get_object.return_value={'Body':io.BytesIO(self.body),'ContentLength':len(self.body)}
  self.assertEqual(evidence(r,s,'bucket')[0]['artifact_kind'],'provider_record');evidence(r,s,'bucket');self.assertEqual(s.get_object.call_count,1)
  r['payload']['source_evidence'][0]['sha256']='bad';s.get_object.return_value={'Body':io.BytesIO(self.body),'ContentLength':len(self.body)}
  with self.assertRaises(RawFailure):evidence(r,s,'bucket')
 def test_saved_api_page_is_expanded_into_real_doi_records(self):
  from metadata_engine.crossref import from_public_receipt
  sha=hashlib.sha256(self.body).hexdigest();s=Mock();s.get_object.return_value={'Body':io.BytesIO(self.body),'ContentLength':len(self.body)};r={'artifact_uri':'s3://bucket/research-data/public/object','sha256':sha,'source_url':self.url,'retrieved_at':'2026-11-10T20:00:00Z'};rows=from_public_receipt(r,s,'bucket');self.assertEqual(rows[0]['source_record_id'],'10.1234/example');self.assertEqual(rows[0]['payload']['data'],self.data);self.assertIn('source_evidence',rows[0]['payload'])
 def test_worker_expands_archived_api_receipts_before_labelling(self):
  from metadata_engine.worker import load_input
  sha=hashlib.sha256(self.body).hexdigest();receipt={'source':'crossref_proceedings','artifact_kind':'public_document','artifact_uri':'s3://bucket/research-data/public/object','sha256':sha,'source_url':self.url,'retrieved_at':'2026-11-10T20:00:00Z'};raw=json.dumps(receipt).encode();s=Mock()
  def get(**kw):
   data=raw if kw['Key']=='receipt.jsonl'else self.body
   return {'Body':io.BytesIO(data),'ContentLength':len(data)}
  s.get_object.side_effect=get;rows,_,_=load_input(s,'bucket',{'input_key':'receipt.jsonl','input_format':'public_receipt'});self.assertEqual(rows[0]['source_record_id'],'10.1234/example');self.assertEqual(rows[0]['payload']['data'],self.data)
 def test_fullpaper_requirement_remains_for_actual_fulltext_source(self):
  from metadata_engine.source_policies import build
  from pathlib import Path
  policies=build(Path('.'));self.assertEqual(policies['crossref_proceedings']['raw_requirements']['required_artifact_kinds'],['provider_record']);self.assertIn('full_text',policies['europe_pmc_fulltext']['raw_requirements']['required_artifact_kinds'])
