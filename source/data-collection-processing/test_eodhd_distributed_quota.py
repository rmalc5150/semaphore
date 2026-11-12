import unittest
from unittest.mock import patch
from eodhd_quota import S3Quota
from regulatory_collection import SourceIssue
from test_s3_runtime import Store

class DistributedQuotaTests(unittest.TestCase):
    def setUp(self):
        self.store=Store();self.now=1794474000.0
        self.config={'daily_call_ceiling':50,'requests_per_minute':5,'daily_group_caps':{'profiles':30,'market':20,'inventory':10},'shared_s3':{'region':'us-east-1','bucket':'test','key':'quota'}}
        self.a=S3Quota(self.config,lambda:self.now,self.sleep,self.store)
        self.b=S3Quota(self.config,lambda:self.now,self.sleep,self.store)
        self.a.sync({'apiRequestsDate':self.a.day(),'apiRequests':0,'dailyRateLimit':100000})
    def sleep(self,n):self.now+=n
    def test_workers_share_weighted_daily_usage(self):
        self.a.reserve('fundamentals/A');self.b.reserve('eod/A');self.a.reserve('exchange-symbol-list/A')
        self.assertEqual(self.b.status()['reserved_calls'],12)
        self.assertEqual(self.a.status()['groups'],{'profiles':10,'market':1,'inventory':1})
    def test_failed_conditional_write_rechecks_competing_reservation(self):
        original=self.store.put_object;inject=[True]
        def write(**kwargs):
            if inject[0]:
                inject[0]=False;self.b.reserve('fundamentals/A')
            return original(**kwargs)
        with patch.object(self.store,'put_object',side_effect=write):self.a.reserve('eod/A')
        self.assertEqual(self.a.status()['reserved_calls'],11)
    def test_group_cap_is_shared_and_cannot_be_overspent(self):
        for _ in range(3):self.a.reserve('fundamentals/A')
        with self.assertRaisesRegex(SourceIssue,'eodhd_shared_quota_reached'):self.b.reserve('fundamentals/B')
        self.assertEqual(self.a.status()['reserved_calls'],30)
    def test_request_rate_is_shared_even_for_zero_cost_account_calls(self):
        before=self.now
        for _ in range(3):self.a.reserve('user');self.b.reserve('user')
        self.assertGreaterEqual(self.now-before,60)
        self.assertEqual(self.a.status()['reserved_calls'],0)
    def test_sync_never_decreases_local_reservations(self):
        self.a.reserve('fundamentals/A');self.b.sync({'apiRequestsDate':self.a.day(),'apiRequests':2,'dailyRateLimit':100000})
        self.assertEqual(self.a.status()['reserved_calls'],10)
    def test_new_day_requires_a_fresh_provider_account_sync(self):
        self.now+=86400
        with self.assertRaisesRegex(SourceIssue,'eodhd_quota_refresh_required'):self.a.reserve('eod/A')

if __name__=='__main__':unittest.main()
