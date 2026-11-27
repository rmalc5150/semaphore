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

    def test_recent_worker_report_counts_as_an_invocation_after_unload(self):
        from collection_alerts import stamp
        now=1800000000
        evidence=Mock()
        evidence.confirmed.return_value=[]
        worker={'service':{'ExecMainStartTimestampMonotonic':'-50000000','Result':'success'},
                'activity':'idle','elapsed':0,'reports':[{'at':stamp(now-20),'value':{}}],
                'events':[],'latest_commit':None,'worker_unit':'optima-m7-committed-athena.service'}
        with patch('constellation.m7_health.view',return_value=worker), \
             patch('collection_health_exporter.properties',return_value={'UnitFileState':'enabled'}):
            result=inspect_job('optima-committed-athena.service',{'execution_worker_unit':worker['worker_unit']},evidence,0,now)
        self.assertEqual(result['last_start_age_seconds'],20)

if __name__=='__main__':unittest.main()

class ScheduledSleepTests(unittest.TestCase):
    def context(self):
        return patch('constellation.m7_batch.read', return_value={
            'phase':'sleeping','stopped_at':1000,'drain_proof':{'safe_to_stop':True},'requests':{'x':1001}})
    def test_sleep_requires_real_stopped_instance_proof_and_bounded_time(self):
        from constellation.m7_health import scheduled_sleep
        with self.context(), patch('constellation.m7_batch.policy', return_value={'off_hours':14,'max_off_hours':24}):
            self.assertEqual(scheduled_sleep(1100,'stopped')['queued_requests'],1)
            self.assertIsNone(scheduled_sleep(1100,'running'))
            self.assertIsNone(scheduled_sleep(1000+24*3600,'stopped'))
            self.assertIsNone(scheduled_sleep(999,'stopped'))
        with patch('constellation.m7_batch.read', return_value={'phase':'sleeping','stopped_at':1000}), patch('constellation.m7_batch.policy', return_value={'off_hours':14,'max_off_hours':24}):
            self.assertIsNone(scheduled_sleep(1100,'stopped'))
    def test_old_snapshot_is_historical_evidence_during_proven_sleep(self):
        evidence=Mock();evidence.prefix='research-data/';evidence.worker_instance_state='stopped'
        evidence.read.return_value=({'checked_at_epoch':1000,'jobs':{'job':{'service':{'Result':'exit-code'},'reports':[{'saved':'evidence'}],'events':[],'latest_commit':None}}},None,None)
        with self.context(), patch('constellation.m7_batch.policy', return_value={'off_hours':14,'max_off_hours':24}):
            item=view('job',evidence,3000)
        self.assertEqual(item['activity'],'scheduled_wait')
        self.assertEqual(item['service']['Result'],'exit-code')
        self.assertEqual(item['reports'],[{'saved':'evidence'}])
        self.assertEqual(item['scheduled_batch_wait']['snapshot_checked_at_epoch'],1000)
    def test_missing_snapshot_does_not_fabricate_success(self):
        evidence=Mock();evidence.prefix='research-data/';evidence.worker_instance_state='stopped';evidence.read.return_value=(None,None,None)
        with self.context(), patch('constellation.m7_batch.policy', return_value={'off_hours':14,'max_off_hours':24}):
            item=view('job',evidence,3000)
        self.assertEqual(item['service'],{})
        self.assertEqual(item['activity'],'scheduled_wait')

class ScheduledSleepAlertTests(unittest.TestCase):
    def test_scheduled_wait_suspends_stall_but_retains_source_error(self):
        from collection_alerts import evaluate, stamp
        now=1800000000;unit='job';config={'heartbeat_max_age_seconds':2700,'jobs':{unit:{'stale_progress_seconds':10,'max_start_gap_seconds':10,'execution_timeout_seconds':10}}}
        job={'activity':'scheduled_wait','timer_enabled':'enabled','timer_state':'active','scheduled_batch_wait':{'reason':'scheduled_batch_sleep'},'progress':{'pending':True,'last_verified_at':stamp(now-10000)},'issues':[{'code':'source_http_403','severity':'low','detail':'denied'}]}
        snapshot={'checked_at':stamp(now),'jobs':{unit:job}}
        prior={'observations':{unit:{'last_change':now-10000,'last_verified_at':stamp(now-10000)}}}
        active,_=evaluate(snapshot,prior,config,now)
        self.assertNotIn(unit+':progress_stalled',active)
        self.assertNotIn(unit+':missed_run',active)
        self.assertIn(unit+':source_http_403',active)

class HistoricalSuccessTests(unittest.TestCase):
    def test_sleep_preserves_wall_clock_of_verified_completed_invocation(self):
        evidence=Mock();evidence.prefix='research-data/';evidence.worker_instance_state='stopped'
        evidence.read.return_value=({'checked_at_epoch':1000,'boot_seconds':200,'jobs':{'job':{'service':{'ExecMainStartTimestampMonotonic':'100000000','ExecMainExitTimestampMonotonic':'180000000'},'reports':[]}}},None,None)
        with patch('constellation.m7_health.scheduled_sleep',return_value={'reason':'scheduled_batch_sleep'}),patch('constellation.m7_health.time.clock_gettime',return_value=2310):
            item=view('job',evidence,3010)
        # Ended at wall-clock 980, not at the time monitoring re-read the snapshot.
        translated_end=int(item['service']['ExecMainExitTimestampMonotonic'])/1e6
        self.assertEqual(3010-(2310-translated_end),980)

    def test_verified_invocation_can_recover_process_failure_during_sleep(self):
        evidence=Mock();evidence.confirmed.return_value=[('verified','2026-09-27T07:00:50Z')]
        service={'Result':'success','ExecMainStatus':'0','ExecMainStartTimestampMonotonic':'50000000','ExecMainExitTimestampMonotonic':'90000000'}
        reports=[{'at':'2026-09-27T07:00:50Z','value':{'status':'complete','manifest':'verified'}}]
        worker={'service':service,'activity':'scheduled_wait','elapsed':0,'reports':reports,'events':[],'latest_commit':None,'worker_unit':'optima-m7-committed-athena.service','scheduled_batch_wait':{'reason':'scheduled_batch_sleep'}}
        now=1790492490
        with patch('constellation.m7_health.view',return_value=worker),patch('collection_health_exporter.properties',return_value={'UnitFileState':'enabled','ActiveState':'active'}),patch('collection_health_exporter.time.clock_gettime',return_value=100):
            result=inspect_job('optima-committed-athena.service',{'execution_worker_unit':worker['worker_unit']},evidence,0,now)
        self.assertIn('successful_execution_at',result)
        self.assertEqual(result['activity'],'scheduled_wait')
        self.assertIsNone(result['result'])

class ScopedPublicationTests(unittest.TestCase):
    def test_wrong_manifest_receipt_cannot_clear_owning_scope(self):
        wid='a'*64;prefix='constellation-backfill/specialist-publication-queue/cms-payments/'
        evidence=Mock();evidence.confirmed.return_value=[];evidence.inventory.return_value={prefix+'one.json':{}}
        def read(key):
            if key.startswith(prefix):return {'window_id':wid,'manifests':['current']},None,None
            return {'window_id':wid,'status':'verified','manifests':['other']},None,None
        evidence.read.side_effect=read
        with patch('collection_health_exporter.properties',return_value={'UnitFileState':'enabled','ActiveState':'active'}),patch('collection_health_exporter.activity',return_value=('idle',0)),patch('collection_health_exporter.json_reports',return_value=([],[],None)):
            r=inspect_job('test.service',{'publication_scopes':[{'owner':'specialists','queue_prefix':prefix}]},evidence,0,time.time())
        self.assertEqual(r['publication_backlog'][prefix],1)
        self.assertTrue(r['progress']['pending'])
        self.assertNotIn('successful_execution_at',r)
