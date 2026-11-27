import copy,json,unittest
from metadata_engine.economic_records import validate,ProviderError
from research_contract import digest

class EconomicRecords(unittest.TestCase):
 def qr(self):
  data={'id':12,'in_force_from':'2026-01-01','restrictions':[{'code':'X'}]}
  record={'source':'wto_quantitative_restrictions_api','source_record_id':'qrs:12','event_at':{'value':'2026-01-01'},'payload':{'data':data,'scope':{'resource':'qrs','year':2026}}}
  original={'data':[copy.deepcopy(data)],'meta':{'total':1,'current_page':1}}
  return record,original,'https://api.wto.org/qrs/qrs?page=1&year_of_entry_into_force=2026'
 def eping(self):
  data={'id':'1','distributionDate':'2026-01-04T00:00:00Z','title':'A notification','notifiedDocumentLink':'https://example.org/original.pdf'}
  record={'source':'wto_eping_sps_tbt_notifications','source_record_id':'1','event_at':{'value':'2026-01-04'},'payload':{'data':data,'scope':{'data_start':'2026-01-01','data_end':'2026-02-01'}}}
  original={'items':[copy.deepcopy(data)],'totalCount':1,'currentPage':1}
  return record,original,'https://api.wto.org/eping/notifications/search?distributionDateFrom=2026-01-01&distributionDateTo=2026-01-31&page=1'
 def ember(self):
  native={'entity':'A','entity_code':'A','date':'2026-01-01','series':'Solar','generation_twh':0,'is_aggregate_entity':False,'is_aggregate_series':False}
  data={**native,'dataset':'electricity-generation','attribution':'Ember'}
  identity=digest({'dataset':'electricity-generation',**{k:native.get(k)for k in ('entity','entity_code','date','series','is_aggregate_entity','is_aggregate_series')}})
  record={'source':'ember_electricity_demand_and_generation','source_record_id':identity,'payload':{'data':data,'scope':{'dataset':'electricity-generation','data_start':'2026-01-01','data_end':'2026-02-01'}}}
  return record,{'data':[native],'stats':{'number_of_records':1}},'https://api.ember-energy.org/v1/electricity-generation/monthly?start_date=2026-01&end_date=2026-01'
 def check(self,fixture):
  row,original,url=fixture;return validate(json.dumps(original).encode(),row,url)
 def test_qr_full_native_restriction(self):self.assertEqual(self.check(self.qr())['record_type'],'trade_restriction_record')
 def test_qr_changed_fields_rejected(self):
  row,body,url=self.qr();row['payload']['data']['restrictions']=[]
  with self.assertRaisesRegex(ProviderError,'original_row_mismatch'):self.check((row,body,url))
 def test_qr_wrong_year_rejected(self):
  row,body,url=self.qr()
  with self.assertRaisesRegex(ProviderError,'date_or_scope'):self.check((row,body,url.replace('2026','2025')))
 def test_eping_whole_metadata(self):self.assertEqual(self.check(self.eping())['record_type'],'trade_notification_metadata')
 def test_legacy_eping_scope_uses_exact_archived_query_window(self):
  row,body,url=self.eping();row['payload']['scope']={'url':'https://api.wto.org/eping/notifications/search'}
  self.assertEqual(self.check((row,body,url))['record_type'],'trade_notification_metadata')
 def test_eping_missing_description_or_fields_rejected(self):
  row,body,url=self.eping();row['payload']['data'].pop('notifiedDocumentLink')
  with self.assertRaises(ProviderError):self.check((row,body,url))
 def test_eping_wrong_window_rejected(self):
  row,body,url=self.eping();row['payload']['scope']['data_end']='2026-01-15'
  with self.assertRaisesRegex(ProviderError,'window_mismatch'):self.check((row,body,url))
 def test_ember_zero_is_preserved(self):self.assertEqual(self.check(self.ember())['record_type'],'electricity_observation')
 def test_ember_response_count_mismatch(self):
  row,body,url=self.ember();body['stats']['number_of_records']=2
  with self.assertRaisesRegex(ProviderError,'incomplete_response'):self.check((row,body,url))
 def test_ember_forged_value_rejected(self):
  row,body,url=self.ember();row['payload']['data']['generation_twh']=10
  with self.assertRaisesRegex(ProviderError,'original_row_mismatch'):self.check((row,body,url))
 def test_untrusted_host_rejected(self):
  row,body,url=self.qr()
  with self.assertRaises(ProviderError):self.check((row,body,url.replace('api.wto.org','example.org')))
 def test_epo_exact_original_and_dates(self):
  import xml.etree.ElementTree as ET
  from epo_ops import legal_rows
  raw=b'<ops:world-patent-data xmlns:ops="http://ops.epo.org" xmlns="http://www.epo.org/exchange"><ops:patent-family><ops:family-member family-id="1"><publication-reference><document-id document-id-type="docdb"><country>EP</country><doc-number>1</doc-number><kind>A1</kind></document-id></publication-reference><ops:legal code="X"><ops:L007EP>2020-01-01</ops:L007EP><ops:L525EP>19990101</ops:L525EP></ops:legal></ops:family-member></ops:patent-family></ops:world-patent-data>'
  scope={'snapshot_end':'2026-11-14','applicant':'A','company_id':'candidate'}
  def item(identity,data,url,day,basis):return {'id':identity,'data':data,'day':day}
  native=legal_rows(ET.fromstring(raw),'EP.1.A1',scope,item)[0]
  row={'source':'epo_ops_patent_legal_events','source_record_id':native['id'],'event_at':{'value':native['day']},'payload':{'data':native['data'],'scope':scope}}
  url='https://ops.epo.org/3.2/rest-services/legal/publication/docdb/EP.1.A1'
  self.assertEqual(validate(raw,row,url)['record_type'],'patent_legal_event')
  row['event_at']['value']='1999-01-01'
  with self.assertRaisesRegex(ProviderError,'gazette_date'):validate(raw,row,url)

if __name__=='__main__':unittest.main()
