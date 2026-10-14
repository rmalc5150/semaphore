from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
import tempfile
import unittest
from eodhd_quota import SharedQuota,cost_group
from regulatory_collection import SourceIssue

class QuotaTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.path=Path(t.name)/'quota.db';self.stamp=datetime(2026,9,24,tzinfo=timezone.utc).timestamp()
        self.config={'daily_call_ceiling':98000,'requests_per_minute':900,'daily_group_caps':{'profiles':88000,'market':9000,'inventory':1000}}
        self.q=SharedQuota(self.path,self.config,clock=lambda:self.stamp,sleeper=self.sleep)
        self.q.sync({'apiRequestsDate':'2026-09-24','apiRequests':79000,'dailyRateLimit':100000})
    def sleep(self,seconds):self.stamp+=seconds
    def test_costs_and_retry_reservations_share_one_daily_counter(self):
        self.q.reserve('fundamentals/X.US');self.q.reserve('eod/X.US');self.q.reserve('eod/X.US')
        state=self.q.status();self.assertEqual(state['reserved_calls'],79012)
        self.assertEqual(state['groups']['profiles'],79010);self.assertEqual(state['groups']['market'],2)
    def test_parallel_clients_cannot_spend_same_remaining_unit(self):
        self.config['daily_group_caps']['market']=1
        def reserve(_):
            try:self.q.reserve('div/X.US');return True
            except SourceIssue:return False
        with ThreadPoolExecutor(max_workers=4) as pool:result=list(pool.map(reserve,range(8)))
        self.assertEqual(sum(result),1)
    def test_stale_account_never_reclaims_reserved_calls(self):
        self.q.reserve('fundamentals/X.US')
        self.q.sync({'apiRequestsDate':'2026-09-24','apiRequests':79000,'dailyRateLimit':100000})
        self.assertEqual(self.q.status()['reserved_calls'],79010)
    def test_midnight_lazy_provider_reset(self):
        self.stamp+=86400
        with self.assertRaises(SourceIssue):self.q.reserve('eod/X.US')
        self.q.sync({'apiRequestsDate':'2026-09-24','apiRequests':99999,'dailyRateLimit':100000})
        self.q.reserve('eod/X.US');self.assertEqual(self.q.status()['reserved_calls'],1)
    def test_account_requests_are_free_but_rate_limited(self):
        self.config['requests_per_minute']=2
        self.q.reserve('user');self.q.reserve('user');old=self.stamp
        self.q.reserve('user');self.assertGreaterEqual(self.stamp-old,60)
        self.assertEqual(self.q.status()['reserved_calls'],79000)
    def test_unknown_endpoint_is_not_silently_undercharged(self):
        with self.assertRaises(SourceIssue):self.q.reserve('eod-bulk-last-day/US')

if __name__=='__main__':unittest.main()
