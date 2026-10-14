import unittest
from monitoring_extra_jobs import extend
from collection_alerts import outcome_issues
class MonitoringTests(unittest.TestCase):
    def test_new_jobs_and_digest_are_preserved(self):
        c=extend({'jobs':{},'email_digest_seconds':86400})
        self.assertEqual(c['email_digest_seconds'],86400)
        self.assertEqual(c['jobs']['optima-search-capture.service']['timer'],'optima-search-daily.timer')
        self.assertTrue(c['jobs']['optima-authenticated-daily.service']['checkpoint_progress'])
        self.assertEqual(c['jobs']['optima-specialist-publication.service']['publication_owners'],['specialists'])
    def test_partial_reddit_error_and_publication_reason_are_visible(self):
        self.assertIn(('reddit_http_429','low'),outcome_issues({'status':'partial','capture_error':'reddit_http_429'}))
        self.assertIn(('uncommitted_publication_input','low'),outcome_issues({'status':'failed','reason_code':'uncommitted_publication_input'}))
