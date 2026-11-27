import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from constellation import m7_batch as batch
from constellation import m7_historical_policy as work


class HistoricalPolicyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        p = patch.object(batch, 'STATE', Path(temp.name) / 'state.json')
        p.start()
        self.addCleanup(p.stop)
        self.settings = {'session_hours': 12, 'off_hours': 12, 'historical_wake_hours': 10,
                         'shutdown_check_minutes': 60, 'historical_work': {}}
        self.ec2 = Mock()
        self.lifecycle = Mock(INSTANCE='main')

    def tick(self, phase, actual, now=86400, **fields):
        self.ec2.describe_instances.return_value = {'Reservations': [{'Instances': [
            {'State': {'Name': actual}, 'LaunchTime': datetime.fromtimestamp(1, timezone.utc)}]}]}
        batch.save({'phase': phase, 'requests': {'optima-m7-aux-metadata-publication.service': 1}, **fields})
        return batch.tick_historical(batch.read(), self.settings, now, self.ec2, self.lifecycle)

    def test_does_not_start_at_9h59_even_after_days_off(self):
        with patch.object(work, 'eligible_work', return_value={'estimated_seconds': 35999,
                          'capture_enabled': True, 'authorization_seconds': 99999}):
            self.assertEqual(self.tick('sleeping', 'stopped', now=700000, stopped_at=0)['phase'], 'sleeping')
        self.ec2.start_instances.assert_not_called()
        self.lifecycle.dispatch.assert_not_called()

    def test_starts_at_ten_hours_and_only_after_minimum_off(self):
        with patch.object(work, 'eligible_work', return_value={'estimated_seconds': 36000,
                          'capture_enabled': True, 'authorization_seconds': 99999}) as m:
            self.assertEqual(self.tick('sleeping', 'stopped', now=43199, stopped_at=0)['phase'], 'sleeping')
            m.assert_not_called()
            self.assertEqual(self.tick('sleeping', 'stopped', now=43200, stopped_at=0)['phase'], 'starting')
        self.ec2.start_instances.assert_called_once_with(InstanceIds=['main'])

    def test_offline_authorization_or_short_remaining_window_blocks_wake(self):
        self.assertFalse(work.meets_wake_threshold({'capture_enabled': False, 'authorization_seconds': 36000,
                                                  'estimated_seconds': 72000}, 36000))
        self.assertFalse(work.meets_wake_threshold({'capture_enabled': True, 'authorization_seconds': 35999,
                                                  'estimated_seconds': 72000}, 36000))

    def test_twelve_hour_limit_drains_without_waiting_for_estimate(self):
        with patch.object(work, 'eligible_work') as m, patch.object(batch, 'remote_control') as remote:
            remote.side_effect = [{'safe_to_stop': False}, {'safe_to_stop': True}]
            self.assertEqual(self.tick('running', 'running', started_at=1, now=43201)['phase'], 'draining')
            self.ec2.stop_instances.assert_not_called()
            self.assertEqual(self.tick('draining', 'running', started_at=1, now=43231)['phase'], 'draining')
            self.ec2.stop_instances.assert_called_once_with(InstanceIds=['main'])
            self.assertEqual(self.tick('draining', 'stopped', started_at=1, now=43260)['phase'], 'sleeping')
            m.assert_not_called()

    def test_external_stop_cannot_bypass_threshold(self):
        with patch.object(work, 'eligible_work') as m:
            self.assertEqual(self.tick('running', 'stopped', started_at=1)['phase'], 'sleeping')
            self.ec2.start_instances.assert_not_called()
            m.assert_not_called()

    def test_keeps_non_historical_requests_held_without_losing_them(self):
        batch.save({'phase': 'running', 'requests': {}})
        self.assertFalse(batch.dispatch_allowed('optima-m7-summary-worker.service', historical_only=True))
        self.assertIn('optima-m7-summary-worker.service', batch.read()['requests'])
        h = next(iter(work.HISTORICAL_DISPATCH_UNITS))
        self.assertTrue(batch.dispatch_allowed(h, historical_only=True))
        self.assertEqual(batch.runnable_requests(batch.read(), historical_only=True), (h,))

    def test_remaining_snapshot_uses_current_position_and_checks_identity(self):
        spec = {'sha256':'snapshot', 'parts': [[1024**3, 1000000]] * 30}
        limits = {'openalex_fast_gib_per_hour': 1, 'openalex_fast_records_per_hour': 2000000}
        result = work.snapshot_estimate({'next_part': 10, 'snapshot_sha256': 'snapshot'}, spec, limits)
        self.assertEqual((result['parts'], result['estimated_seconds']), (20, 36000))
        with self.assertRaises(ValueError):
            work.snapshot_estimate({'next_part': 10, 'snapshot_sha256': 'wrong'}, spec, limits)


if __name__ == '__main__':
    unittest.main()
