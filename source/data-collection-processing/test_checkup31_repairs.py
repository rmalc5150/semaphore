import json,unittest
from unittest.mock import Mock,patch
from additional_source_apis import fetch,datacite_page
from regulatory_collection import SourceIssue
class Repairs(unittest.TestCase):
 def test_fred_segments_are_contiguous_and_count_all_pages(self):
  job={'adapter':'additional_fred','start':'2016-01-01','end':'2017-01-01','parameters':{'series_id':'T10Y2Y','realtime_end':'2022-01-01'}}
  cursor=None;calls=[];c=Mock()
  def get(client,url,p,*args):
   calls.append(p)
   return {'observations':[{'date':'2016-01-01','realtime_start':p['realtime_start'],'realtime_end':p['realtime_end'],'value':'1'}],'count':1},None
  cursor=json.dumps({'series_metadata':{},'segment_start':'2016-01-01','offset':0})
  with patch('additional_source_apis.get_json',side_effect=get):
   for i in range(3):
    rows,cursor=fetch(c,job,cursor,lambda identity,data,url,day,**kw:{'id':identity,'data':data})
    self.assertEqual(len(rows),1)
  self.assertIsNone(cursor);self.assertEqual(c.expected_records,3)
  self.assertEqual([(p['realtime_start'],p['realtime_end'])for p in calls],[('2016-01-01','2018-12-31'),('2019-01-01','2021-12-31'),('2022-01-01','2022-01-01')])
 def test_datacite_shrinks_page_without_dropping_cursor(self):
  seen=[]
  def get(c,u,p):
   seen.append(dict(p))
   if p['page[size]']>1:raise SourceIssue('additional_response_too_large_split_scope')
   return {'data':[]},None
  with patch('additional_source_apis.get_json',side_effect=get):datacite_page(Mock(),'https://api.datacite.org/dois',{'page[cursor]':'abc','query':'original'})
  self.assertEqual([x['page[size]']for x in seen],[100,10,1]);self.assertTrue(all(x['page[cursor]']=='abc' and x['query']=='original'for x in seen))
 def test_datacite_does_not_retry_authentication_errors(self):
  with patch('additional_source_apis.get_json',side_effect=SourceIssue('source_http_403'))as get:
   with self.assertRaises(SourceIssue):datacite_page(Mock(),'https://api.datacite.org/dois',{})
   self.assertEqual(get.call_count,1)
 def test_single_record_over_limit_remains_failure(self):
  with patch('additional_source_apis.get_json',side_effect=SourceIssue('additional_response_too_large_split_scope'))as get:
   with self.assertRaises(SourceIssue):datacite_page(Mock(),'https://api.datacite.org/dois',{})
   self.assertEqual(get.call_count,3)
