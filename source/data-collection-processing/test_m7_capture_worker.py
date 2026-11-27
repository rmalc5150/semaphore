import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from m7_capture_worker import wait_for_memory,pool_memory_path,memory_admission_threshold,lane_for
from uspto_rate_limit import pace
from collection_health_exporter import activity
import json,time
import constellation.m7_lifecycle as lifecycle

class CaptureAdmissionTests(unittest.TestCase):
    def test_memory_reservation_does_not_hold_the_capture_lock(self):
        import m7_capture_worker as worker
        with tempfile.TemporaryDirectory()as tmp,patch.object(worker,'BASE',Path(tmp)), \
             patch('sys.argv',['worker','--job','edinet-documents-daily']), \
             patch.object(worker,'pool_memory_path',return_value=Path(tmp)/'memory.current'), \
             patch.object(worker,'wait_for_memory',return_value=False),patch.object(worker.fcntl,'flock')as flock:
            self.assertEqual(worker.main(),75)
            flock.assert_not_called()

    def test_light_lane_has_four_slots_while_large_has_one(self):
        import m7_capture_worker as worker
        with tempfile.TemporaryDirectory() as tmp, patch.object(worker,'BASE',Path(tmp)):
            deadline=time.monotonic()+1
            first=worker.acquire_lane_slot('light',deadline)
            second=worker.acquire_lane_slot('light',deadline)
            third=worker.acquire_lane_slot('light',deadline)
            fourth=worker.acquire_lane_slot('light',deadline)
            self.assertIsNotNone(first)
            self.assertIsNotNone(second)
            self.assertIsNotNone(third)
            self.assertIsNotNone(fourth)
            first.close();second.close();third.close();fourth.close()
            large=worker.acquire_lane_slot('large',deadline)
            self.assertIsNotNone(large)
            large.close()

    def test_lane_assignment_and_shared_pool_headroom(self):
        self.assertEqual(lane_for('edinet-documents-daily'),'large')
        self.assertEqual(lane_for('patents-daily'),'light')
        self.assertEqual(memory_admission_threshold('edinet-documents-daily'),int(17*1024**3))
        self.assertEqual(memory_admission_threshold('patents-daily'),int(17*1024**3))

    def test_waiting_capture_launcher_is_a_queue_not_a_payload(self):
        def read(path):
            if path.name=='cgroup.procs':return '42\n'
            if path.name=='comm':return 'python\n'
            raise AssertionError('Waiting launcher must not count as payload')
        with patch.object(Path,'read_text',read),patch.object(Path,'read_bytes',return_value=b'python\0m7_capture_worker.py\0--job\0patents-daily'),patch('collection_health_exporter.time.clock_gettime',return_value=100):
            state,_=activity({'ActiveState':'activating','ControlGroup':'/example','ExecMainStartTimestampMonotonic':'1'},True)
        self.assertEqual(state,'queued')
    def test_memory_admission_and_timeout(self):
        with tempfile.TemporaryDirectory()as tmp:
            path=Path(tmp)/'memory.current';path.write_text('10')
            self.assertTrue(wait_for_memory(path,threshold=20,seconds=0))
            path.write_text('30')
            self.assertFalse(wait_for_memory(path,threshold=20,seconds=0))

    def test_pool_path_uses_the_real_nested_systemd_hierarchy(self):
        with patch.object(Path,'read_text',return_value='0::/constellation.slice/constellation-workers.slice/constellation-workers-capture.slice/example.service\n'):
            self.assertEqual(str(pool_memory_path()),'/sys/fs/cgroup/constellation.slice/constellation-workers.slice/constellation-workers-capture.slice/memory.current')
        with patch.object(Path,'read_text',return_value='0::/system.slice/example.service\n'):
            with self.assertRaisesRegex(RuntimeError,'inside constellation-workers'):pool_memory_path()

    def test_uspto_uses_shared_gate_when_enabled(self):
        with patch.dict('os.environ',{'CONSTELLATION_SHARED_HTTP_LIMITS':'1'}),patch('constellation.shared_limits.admit')as admit:
            pace(path='/unwritable/local-gate')
        admit.assert_called_once_with('https://api.uspto.gov/')

    def test_deployment_hold_expires_and_invalid_content_fails_closed(self):
        with tempfile.TemporaryDirectory()as tmp,patch.object(lifecycle,'STATE',Path(tmp)/'idle'):
            path=Path(tmp)/'m7-deployment-hold.json'
            self.assertFalse(lifecycle.deployment_hold_active())
            path.write_text(json.dumps({'expires_at':time.time()+30}))
            self.assertTrue(lifecycle.deployment_hold_active())
            path.write_text(json.dumps({'expires_at':time.time()-30}))
            self.assertFalse(lifecycle.deployment_hold_active())
            path.write_text('broken')
            self.assertTrue(lifecycle.deployment_hold_active())

    def test_metadata_controller_only_wakes_m7_for_durable_work(self):
        with patch('constellation.m7_batch.policy',return_value={}), \
             patch.object(lifecycle.subprocess,'call',return_value=0) as call, \
             patch.object(lifecycle,'metadata_pending',return_value=False), \
             patch.object(lifecycle,'dispatch') as dispatch:
            self.assertEqual(lifecycle.metadata(),0)
        dispatch.assert_not_called()
        self.assertIn('--no-publication',call.call_args.args[0])
        with patch('constellation.m7_batch.policy',return_value={}), \
             patch.object(lifecycle.subprocess,'call',return_value=0), \
             patch.object(lifecycle,'metadata_pending',return_value=True), \
             patch.object(lifecycle,'dispatch') as dispatch:
            self.assertEqual(lifecycle.metadata(),0)
        dispatch.assert_called_once_with('optima-m7-aux-metadata-publication.service')
