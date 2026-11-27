import unittest
from research_contract import digest
from grants_review_capture import completed_summary
class CompletedCaptureSummaryTests(unittest.TestCase):
 def test_only_exact_complete_planned_scopes_are_reported(self):
  job={'source':'uspto_assignment_histories','start':'2016-01-01'}
  row={'job':job,'status':'complete','manifest':'manifests/collection_runs/test/final.json'}
  state={'windows':{digest(job):row}}
  self.assertEqual(completed_summary([job],state)['completed_scopes'],1)
  self.assertIsNone(completed_summary([job,dict(job,start='2017-01-01')],state))
  for change in [{'status':'partial'},{'manifest':None},{'job':dict(job,start='other')}]:
   self.assertIsNone(completed_summary([job],{'windows':{digest(job):dict(row,**change)}}))
  self.assertIsNone(completed_summary([],state))
