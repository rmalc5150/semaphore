import json
from pathlib import Path
import subprocess
import shlex
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parent


class MemoryBudgetTests(unittest.TestCase):
    def test_all_jobs_capped_and_heavy_jobs_share_one_lock(self):
        config = json.loads((ROOT / 'config/ram-budget.json').read_text())
        units = {p.name for p in (ROOT / 'systemd').glob('optima-*.service')}
        self.assertEqual(units, set(config['jobs']))
        max_heavy = 0; light_sum = 0
        for name, policy in config['jobs'].items():
            text = (ROOT / 'systemd' / (name + '.d') / '50-memory-budget.conf').read_text()
            self.assertIn('Slice=optima-data.slice', text)
            self.assertIn('MemoryMax=' + str(policy['memory_max_bytes']), text)
            if policy['serialized']:
                self.assertIn('/usr/bin/flock --exclusive', text)
                self.assertIn('/.heavy-job.lock ', text)
                self.assertIn('/usr/bin/timeout --signal=INT', text)
                command = next(line.removeprefix('ExecStart=') for line in text.splitlines()
                               if line.startswith('ExecStart=/usr/bin/flock'))
                parts = shlex.split(command)
                duration = parts[parts.index('/usr/bin/timeout') + 3]
                self.assertEqual(subprocess.run(['/usr/bin/timeout', duration, '/usr/bin/true']).returncode, 0)
                max_heavy = max(max_heavy, policy['memory_max_bytes'])
            else:
                light_sum += policy['memory_max_bytes']
        # Reserve 64 MB for queued flock/timeout wrappers and bookkeeping.
        self.assertLess(max_heavy + light_sum + 64000000, config['jobs_aggregate_max_bytes'])

    def test_flock_waiters_do_not_overlap_payloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); lock = str(root / 'lock'); marker = root / 'entered'
            first = subprocess.Popen(['/usr/bin/flock', '--exclusive', lock, '/bin/sh', '-c',
                                      'touch "$1"; sleep 0.3', 'sh', str(marker)])
            try:
                deadline = time.monotonic() + 3
                while not marker.exists() and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertTrue(marker.exists())
                result = subprocess.run(['/usr/bin/flock', '--exclusive', '--nonblock',
                                         '--conflict-exit-code', '75', lock, '/usr/bin/true'])
                self.assertEqual(result.returncode, 75)
                self.assertEqual(first.wait(timeout=3), 0)
                self.assertEqual(subprocess.run(['/usr/bin/flock', '--exclusive', '--nonblock', lock, '/usr/bin/true']).returncode, 0)
            finally:
                if first.poll() is None:
                    first.terminate(); first.wait()


if __name__ == '__main__':
    unittest.main()
