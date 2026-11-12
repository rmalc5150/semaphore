import copy,hashlib,io,unittest
from pathlib import Path
from unittest.mock import Mock
from metadata_engine.nmpa import evidence
from metadata_engine.nmpa_tables import structured_detail,parse_detail_page
from metadata_engine.evidence import RawFailure
from metadata_engine.labelling import label_observation
class NMPARawValidation(unittest.TestCase):
 def setUp(self):
  self.registration='CTR20231998';self.url='https://www.chinadrugtrials.org.cn/clinicaltrials.searchlistdetail.dhtml?reg_no='+self.registration;self.body=Path('tests/fixtures/nmpa/CTR20231998.html').read_bytes();self.facts=structured_detail(self.body.decode(),self.registration);self.fields=parse_detail_page(self.body.decode());self.date=next(m['date']for m in self.facts['milestones']if m['kind']=='FIRST_PUBLIC_DISCLOSURE');self.record={'source':'nmpa_trials','dataset':'research_records','source_record_id':self.registration,'source_url':self.url,'payload':{'record_type':'clinical_trial','data':{'registrationNumber':self.registration,'fields':copy.deepcopy(self.fields),'structured':copy.deepcopy(self.facts),'firstPublicDisclosureDate':self.date}}}
 def check(self,record=None,body=None,url=None):
  r=copy.deepcopy(record or self.record);raw=body or self.body;r['payload']['source_evidence']=[{'key':'source_documents/nmpa_trials/detail','sha256':hashlib.sha256(raw).hexdigest(),'source_url':url or self.url}];s=Mock();s.get_object.return_value={'Body':io.BytesIO(raw),'ContentLength':len(raw)};return evidence(r,s,'bucket')
 def test_full_native_fields_and_structured_facts(self):self.assertEqual(self.check()[0]['validation']['field_count'],len(self.fields))
 def test_modified_fields_facts_identity_and_date_are_rejected(self):
  for change in ('fields','structured','identity','date'):
   r=copy.deepcopy(self.record)
   if change=='fields':r['payload']['data']['fields'].pop()
   elif change=='structured':r['payload']['data']['structured']['phase']='Invented phase'
   elif change=='identity':r['source_record_id']='CTR20230000'
   else:r['payload']['data']['firstPublicDisclosureDate']='2026-11-10'
   with self.assertRaises(RawFailure):self.check(r)
 def test_wrong_host_blocked_page_and_listing_as_full_detail_are_rejected(self):
  with self.assertRaises(RawFailure):self.check(url=self.url.replace('www.chinadrugtrials.org.cn','evil.example'))
  with self.assertRaises(RawFailure):self.check(body=b'<html><table><tr><th>Access denied</th><td>Try later</td></tr></table></html>')
  with self.assertRaises(RawFailure):self.check(url=self.url.replace('searchlistdetail','searchlist'))
 def test_inventory_only_is_exact_original_row_and_has_explicit_scope(self):
  listing='<html><table><tr><td>1</td><td>CTR20231998</td><td>进行中</td><td>药物</td><td>适应症</td><td>标题</td></tr></table>当前第1页，共1页，共1条记录</html>'.encode();url='https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml?keywords=&currentpage=1';r={'source':'nmpa_trials','dataset':'registry_inventory','source_record_id':self.registration,'source_url':self.url,'payload':{'registration_number':self.registration,'detail_url':self.url,'listing_page':1,'advertised_total_pages':1,'advertised_total_records':1,'title':'标题','search_result_columns':['1',self.registration,'进行中','药物','适应症','标题']}}
  a=self.check(r,listing,url);self.assertEqual(a[0]['validation']['completeness_scope'],'original_inventory_row_only_not_full_trial')
  labelled=label_observation({**r,'ingested_at':'2026-11-10T18:00:00Z','raw_s3_uri':'s3://bucket/research-data/raw/batch','raw_sha256':'abc','raw_completeness_status':'complete','raw_artifacts':a},{'source_key':'nmpa_trials','record_kind':'source_record','contract_version':'test','adapter':'api_records','adapter_version':'test','license_policy_id':'test'});self.assertEqual(labelled['record_kind'],'registry_inventory');self.assertIn('registry_inventory_not_trial_detail',labelled['quality_flags'])
  r['payload']['search_result_columns'][3]='Wrong drug'
  with self.assertRaises(RawFailure):self.check(r,listing,url)
 def test_missing_provider_date_is_preserved_as_unknown(self):
  raw=self.body.replace(self.date.encode(),'暂未填写此信息'.encode());facts=structured_detail(raw.decode(),self.registration)
  if any(m['kind']=='FIRST_PUBLIC_DISCLOSURE'for m in facts['milestones']):self.fail('fixture date was not replaced')
  r=copy.deepcopy(self.record);r['payload']['data'].update(fields=parse_detail_page(raw.decode()),structured=facts,firstPublicDisclosureDate=None);self.check(r,raw)
 def test_source_milestone_dates_require_matching_original_fact(self):
  fact=self.facts['milestones'][0];data={'registrationNumber':self.registration,'id':self.registration+':milestone:'+fact['kind']+':'+fact['date'],'action':fact['kind'],'date':fact['date'],'date_basis':'explicit_source_date','source_fact':fact};r=copy.deepcopy(self.record);r['source_record_id']=data['id'];r['payload'].update(record_type='regulatory_event',data=data);self.check(r)
  r['payload']['data']['source_fact']={**fact,'date':'2026-11-10'}
  with self.assertRaises(RawFailure):self.check(r)
 def test_first_observed_is_identified_as_collector_observation(self):
  r=copy.deepcopy(self.record);rid=self.registration+':first_observed';r['source_record_id']=rid;r['payload'].update(record_type='regulatory_event',data={'registrationNumber':self.registration,'id':rid,'action':'FIRST_OBSERVED','date':'2026-11-10T18:00:00Z','date_basis':'first_observed_not_trial_start'});self.assertEqual(self.check(r)[0]['validation']['completeness_scope'],'collector_observation_not_actual_trial_change_date')
