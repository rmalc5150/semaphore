import unittest,json
from unittest.mock import Mock,patch
from credential_source_apis import fetch
from additional_source_apis import fetch as additional_fetch
from specialist_inputs import item
from regulatory_collection import SourceIssue
from research_contract import digest
class ProviderCorrections(unittest.TestCase):
 def census(self,start='2019-01-01',code='260400'):
  return {'adapter':'additional_census','start':start,'end':start[:7]+'-28','parameters':{'url':'https://api.census.gov/data/timeseries/intltrade/imports/hs','direction':'imports','commodity':code}}
 def test_census_empty_requires_positive_same_period_control(self):
  client=Mock();client.evidence=[{'sha256':'empty'},{'sha256':'control'}]
  with patch('credential_source_apis.get_json',side_effect=[(None,None),([['CTY_CODE','I_COMMODITY'],['1','-']],None)]):
   self.assertEqual(fetch(client,self.census(),None,item),([],None))
  self.assertEqual(client.expected_records,0);self.assertIn('not a zero',client.empty_scope_evidence['interpretation'])
 def test_census_unpublished_period_remains_incomplete(self):
  from datetime import datetime,timezone
  start=datetime.now(timezone.utc).date().replace(day=1).isoformat()
  with patch('credential_source_apis.get_json',return_value=(None,None))as get:
   with self.assertRaisesRegex(SourceIssue,'not_yet_published'):fetch(Mock(),self.census(start,'TOTAL'),None,item)
  self.assertEqual(get.call_count,1)
 def test_census_old_missing_period_and_unknown_code_not_accepted(self):
  with patch('credential_source_apis.get_json',return_value=(None,None)):
   with self.assertRaisesRegex(SourceIssue,'requires_review'):fetch(Mock(),self.census(code='999999'),None,item)
   with self.assertRaisesRegex(SourceIssue,'requires_review'):fetch(Mock(),self.census(),None,item)
 def bio(self):return {'adapter':'additional_biorxiv','start':'2020-01-01','end':'2020-02-01','parameters':{'repository':'biorxiv'}}
 def client(self):
  c=Mock();c.evidence=[{'key':'original'}];c.get.return_value=b'%PDF-1.4\nOriginal\n%%EOF';return c
 def test_identical_biorxiv_duplicates_reconcile_provider_positions(self):
  row={'doi':'10.1101/abc','version':'1','date':'2020-01-01'};other={**row,'doi':'10.1101/def'};c=self.client()
  with patch('additional_source_apis.get_json',return_value=({'messages':[{'status':'ok','total':3}],'collection':[row,row,other]},None)):
   rows,cursor=additional_fetch(c,self.bio(),None,item)
  self.assertEqual(len(rows),2);self.assertIsNone(cursor);self.assertEqual(c.expected_records,2);self.assertEqual(c.get.call_count,2)
 def test_conflicting_biorxiv_duplicates_remain_errors(self):
  row={'doi':'10.1101/abc','version':'1','date':'2020-01-01'};changed={**row,'title':'different'}
  with patch('additional_source_apis.get_json',return_value=({'messages':[{'status':'ok','total':2}],'collection':[row,changed]},None)):
   with self.assertRaisesRegex(SourceIssue,'conflicting_duplicate'):additional_fetch(self.client(),self.bio(),None,item)
 def test_biorxiv_duplicate_on_later_page_is_not_downloaded_again(self):
  row={'doi':'10.1101/abc','version':'1','date':'2020-01-01'};cursor=json.dumps({'offset':1,'total':2,'duplicate_rows':0,'seen_signatures':{'10.1101/abc:v1':digest(row)}});c=self.client()
  with patch('additional_source_apis.get_json',return_value=({'messages':[{'status':'ok','total':2}],'collection':[row]},None)):
   rows,next_cursor=additional_fetch(c,self.bio(),cursor,item)
  self.assertEqual(rows,[]);self.assertIsNone(next_cursor);self.assertEqual(c.expected_records,1);c.get.assert_not_called()
