import unittest
from collection_alerts import outcome_issues
class LocalBudgets(unittest.TestCase):
 def test_partial_local_request_allowance_is_continuation(self):self.assertEqual(outcome_issues({'status':'partial','reason':'request_limit','records':195}),set())
 def test_failed_allowance_still_alerts(self):self.assertIn(('request_limit','low'),outcome_issues({'status':'failed','reason':'request_limit'}))
 def test_provider_rate_limit_and_integrity_still_alert(self):
  self.assertIn(('source_http_429','low'),outcome_issues({'status':'partial','reason':'source_http_429'}));self.assertIn(('raw_checksum_mismatch','high'),outcome_issues({'status':'partial','reason':'raw_checksum_mismatch'}))
