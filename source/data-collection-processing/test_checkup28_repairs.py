import unittest
from datetime import date
from unittest.mock import Mock
from regulatory_sources import FDA
from specialist_authenticated import table_rows
class Tests(unittest.TestCase):
 def test_exact_empty_recall_response(self):
  self.assertEqual(table_rows({'STATUSCODE':412,'MESSAGE':'No results found'}),[])
  with self.assertRaises(Exception):table_rows({'STATUSCODE':412,'MESSAGE':'No results found','RESULTCOUNT':3})
  with self.assertRaises(Exception):table_rows({'STATUSCODE':400})
 def test_undated_submission_and_distinct_variants_retained(self):
  s={'submission_type':'SUPPL','submission_number':'51','submission_status':'AP'}
  row={'application_number':'NDA021014','submissions':[s,s,{**s,'submission_status_date':'20160612'}]}
  c=Mock();c.json.return_value={'results':[row],'meta':{'results':{'total':1},'last_updated':'x'}}
  rows,_,_=FDA().page(c,date(2016,6,1),date(2016,7,1),'historical',{},100)
  self.assertEqual(len(rows),2);self.assertEqual(len({r['id']for r in rows}),2)
  undated=next(r for r in rows if r['date'] is None)
  self.assertEqual(undated['action_date_status'],'unavailable')
  self.assertEqual(undated['window_membership'],'application_matched_query_only')

 def test_publication_timestamp_projection(self):
  from regulatory_athena import calendar_date
  self.assertEqual(calendar_date('2026-10-16T08:16:22.741942Z'),date(2026,10,16))
  self.assertEqual(calendar_date('2026-10-16'),date(2026,10,16))
  with self.assertRaises(ValueError):calendar_date('invalid')
