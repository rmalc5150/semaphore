import unittest
from contextlib import contextmanager
from unittest.mock import Mock,patch
from pymysql.err import OperationalError
from constellation import shared_limits as limits

class RetryTests(unittest.TestCase):
    def attempt(self,errors):
        cursor=Mock();cursor.fetchone.return_value={'next_request_at':0,'now_epoch':1}
        calls=[]
        @contextmanager
        def db():
            calls.append(True)
            if errors:raise errors.pop(0)
            yield cursor
        c=Mock();c.db=db
        return c,cursor,calls
    def test_transient_lock_retry_requires_a_successful_admission(self):
        c,cur,calls=self.attempt([OperationalError(1205,'lock timeout')])
        with patch.object(limits,'_CONTROL',c),patch.dict('os.environ',{'CONSTELLATION_SHARED_HTTP_LIMITS':'1'}),patch.object(limits.time,'sleep') as sleep:
            limits.admit('https://api.fda.gov/drug/drugsfda.json')
        self.assertEqual(len(calls),2)
        self.assertTrue(any('UPDATE backfill_http_limits SET' in c.args[0] for c in cur.execute.call_args_list))
        sleep.assert_called_once_with(.5)
    def test_persistent_failure_stays_closed_after_three_attempts(self):
        c,cur,calls=self.attempt([OperationalError(2003,'unreachable')]*3)
        with patch.object(limits,'_CONTROL',c),patch.dict('os.environ',{'CONSTELLATION_SHARED_HTTP_LIMITS':'1'}),patch.object(limits.time,'sleep'),self.assertRaises(OperationalError):
            limits.admit('https://api.fda.gov/drug/drugsfda.json')
        self.assertEqual(len(calls),3);cur.execute.assert_not_called()
    def test_auth_failure_is_not_retried(self):
        c,cur,calls=self.attempt([OperationalError(1045,'denied')])
        with patch.object(limits,'_CONTROL',c),patch.dict('os.environ',{'CONSTELLATION_SHARED_HTTP_LIMITS':'1'}),patch.object(limits.time,'sleep') as sleep,self.assertRaises(OperationalError):
            limits.admit('https://api.fda.gov/drug/drugsfda.json')
        self.assertEqual(len(calls),1);sleep.assert_not_called()

if __name__=='__main__':unittest.main()
