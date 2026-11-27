import unittest
from constellation.gaps import current_specialist_outcome
class ExactCheckpointReconciliation(unittest.TestCase):
 def setUp(self):self.old={'job_id':'a','job':{'source':'one','parameters':{'commodity':'260400'}},'last_attempt':'2026-11-14','status':'failed'}
 def test_newer_same_task_replaces_failed_execution(self):
  new={**self.old,'last_attempt':'2026-11-16','status':'complete'}
  self.assertIs(current_specialist_outcome(self.old,new),new)
 def test_other_task_or_dimensions_cannot_clear_gap(self):
  for update in ({'job_id':'b'},{'job':{'source':'one','parameters':{'commodity':'TOTAL'}}}):
   self.assertIs(current_specialist_outcome(self.old,{**self.old,'last_attempt':'2026-11-16','status':'complete',**update}),self.old)
 def test_old_or_missing_checkpoint_preserves_failure(self):
  for new in (None,{**self.old,'last_attempt':'2026-11-13','status':'complete'}):self.assertIs(current_specialist_outcome(self.old,new),self.old)

class CensusPublicationLag(unittest.TestCase):
 def test_expected_release_is_deferred_without_clearing_an_old_gap(self):
  from constellation.gaps import expected_census_release
  from datetime import date
  w={'scope':'us_census_international_trade_api|C118|specialist_historical|exact','start':'2026-10-01','status':'partial','reason':'census_period_not_yet_published'}
  self.assertTrue(expected_census_release(w,date(2026,11,16)))
  self.assertFalse(expected_census_release(w,date(2026,12,1)))
  self.assertFalse(expected_census_release({**w,'reason':'source_http_403'},date(2026,11,16)))
  self.assertFalse(expected_census_release({**w,'scope':'other|C118'},date(2026,11,16)))
