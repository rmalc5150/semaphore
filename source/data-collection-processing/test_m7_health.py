import time
import unittest
from unittest.mock import Mock,patch
from constellation.m7_health import view
from collection_health_exporter import inspect_job

class WorkerHealthTests(unittest.TestCase):
    def test_worker_failure_is_not_hidden_by_successful_controller_dispatch(self):
        evidence=Mock();evidence.confirmed.return_value=[]
        worker={'service':{'ActiveState':'failed','Result':'exit-code','ExecMainStatus':'1'},
                'activity':'idle','elapsed':0,'reports':[],'events':[],
                'latest_commit':None,'worker_unit':'optima-m7-committed-athena.service'}
        with patch('constellation.m7_health.view',return_value=worker),patch('collection_health_exporter.properties',return_value={'UnitFileState':'enabled'}):
            result=inspect_job('optima-committed-athena.service',{'execution_worker_unit':worker['worker_unit']},evidence,0,time.time())
        self.assertEqual(result['result'],'exit-code')
        self.assertEqual(result['exit_status'],1)
        self.assertEqual(result['execution_host']['unit'],worker['worker_unit'])

    def test_worker_uptime_is_translated_into_controller_clock_domain(self):
        evidence=Mock();evidence.prefix='research-data/'
        evidence.read.return_value=({'checked_at_epoch':1000,'boot_seconds':200,'jobs':{'job':{'service':{'ExecMainStartTimestampMonotonic':'100000000'},'activity':'running','elapsed':100}}},None,None)
        with patch('constellation.m7_health.time.clock_gettime',return_value=310):
            result=view('job',evidence,1010)
        self.assertEqual(result['service']['ExecMainStartTimestampMonotonic'],'200000000')
        self.assertEqual(result['elapsed'],110)

    def test_stale_worker_snapshot_cannot_claim_health(self):
        evidence=Mock();evidence.prefix='research-data/'
        evidence.read.return_value=({'checked_at_epoch':1},None,None)
        with self.assertRaisesRegex(RuntimeError,'older than 15 minutes'):view('job',evidence,1000)

if __name__=='__main__':unittest.main()
