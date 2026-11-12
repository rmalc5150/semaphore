import unittest,json
from unittest.mock import Mock,patch
import nih_pagination as n
class Tests(unittest.TestCase):
 def test_split_reconciles_and_resumes_without_rediscovery(self):
  client=Mock();job={'parameters':{'url':'https://example.com','criteria':{}}};item=lambda i,*a:i
  rows=lambda *ids:[{'appl_id':i} for i in ids]
  with patch.object(n,'CAP',2),patch.object(n,'response',side_effect=[(rows(1),3),(rows(1),3),(rows(1),1),(rows(2),2),(rows(1),1)]):
   first,cursor=n.page(client,job,None,item)
  self.assertEqual(first,[1])
  with patch.object(n,'response',return_value=(rows(2,3),2)) as request:
   second,cursor=n.page(client,job,cursor,item)
  self.assertEqual(second,[2,3]);self.assertIsNone(cursor);self.assertEqual(request.call_count,1)
 def test_missing_dates_cannot_silently_reduce_scope(self):
  with patch.object(n,'CAP',2),patch.object(n,'response',side_effect=[([{'appl_id':1}],3),([{'appl_id':1}],2)]):
   with self.assertRaisesRegex(Exception,'nih_split_missing_undated_records'):n.page(Mock(),{'parameters':{'url':'u','criteria':{}}},None,Mock())
 def test_changed_partition_counts_cannot_complete(self):
  state={'version':1,'parts':[{'start':'2020-01-01','end':'2020-01-02','total':2}],'part':0,'offset':0,'total':2,'seen':[]}
  with patch.object(n,'response',return_value=([{'appl_id':1}],1)):
   with self.assertRaisesRegex(Exception,'nih_split_count_changed'):n.page(Mock(),{'parameters':{'url':'u','criteria':{}}},json.dumps(state),Mock())

 def test_split_ranges_share_exclusive_boundary(self):
  calls=[]
  def response(client,url,criteria,offset=0,limit=100):
   calls.append(criteria)
   totals=[3,3,1,2,1]
   return [{'appl_id':1}],totals[len(calls)-1]
  with patch.object(n,'CAP',2),patch.object(n,'response',side_effect=response):
   n.page(Mock(),{'parameters':{'url':'u','criteria':{}}},None,lambda *a:a)
  self.assertEqual(calls[2]['date_added']['to_date'],calls[3]['date_added']['from_date'])
