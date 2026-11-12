import unittest
from contextlib import contextmanager
from unittest.mock import Mock, patch
from constellation.control import Control

class QueueIsolationTests(unittest.TestCase):
    def control(self):
        c=Control.__new__(Control);c.config={};cursor=Mock();cursor.fetchone.return_value=None
        @contextmanager
        def db():yield cursor
        c.db=db;c.get=lambda key:{'enabled':True,'stop_after_epoch':9999999999}
        return c,cursor
    def test_claim_prioritizes_low_attempt_work_and_excludes_parked_jobs(self):
        c,cursor=self.control()
        with patch.dict('os.environ',{'CONSTELLATION_ROLE':'controller'}):
            self.assertIsNone(c.claim_next('test'))
        sql=cursor.execute.call_args.args[0]
        self.assertIn('ORDER BY attempts,updated_at,job_id',sql)
        self.assertIn('attempts < 3',sql)
        self.assertNotIn("'blocked'",sql)
        self.assertIn('FOR UPDATE SKIP LOCKED',sql)
    def test_failed_job_releases_lease_with_bounded_backoff(self):
        c,cursor=self.control();cursor.rowcount=1
        c.finish('job','token','retryable_failed',{'reason':'provider_503'})
        sql,args=cursor.execute.call_args.args
        self.assertIn('lease_until=0',sql)
        self.assertIn('LEAST(21600,300*POW',sql)
        self.assertEqual(args[0],'retryable_failed')
