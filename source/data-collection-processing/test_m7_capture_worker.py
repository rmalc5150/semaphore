import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from m7_capture_worker import wait_for_memory,pool_memory_path
from uspto_rate_limit import pace
from collection_health_exporter import activity
import json,time
import constellation.m7_lifecycle as lifecycle

class CaptureAdmissionTests(unittest.TestCase):
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
            self.assertEqual(str(pool_memory_path()),'/sys/fs/cgroup/constellation.slice/constellation-workers.slice/memory.current')
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
