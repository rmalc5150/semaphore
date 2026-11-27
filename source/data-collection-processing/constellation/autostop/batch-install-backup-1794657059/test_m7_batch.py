"""Batch policy, durable deferred requests and drain-before-stop tests."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from constellation import m7_batch as batch


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.patch = patch.object(batch, 'STATE', Path(self.tmp.name) / 'state.json')
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.settings = {'off_hours': 19, 'max_off_hours': 24, 'session_hours': 5,
                         'batch_jobs': 26000, 'overflow_jobs': 130000}

    def test_first_install_preserves_backlog_processing(self):
        self.assertTrue(batch.dispatch_allowed('unit'))
        self.assertEqual(batch.read()['phase'], 'catchup')
        self.assertFalse(batch.should_drain(batch.read(), {'metadata': 1, 'historical': 0}, 0, self.settings))

    def test_sleep_requests_are_durable_coalesced_and_do_not_wake(self):
        batch.save({'phase': 'sleeping', 'requests': {}, 'stopped_at': 0})
        self.assertFalse(batch.dispatch_allowed('unit'))
        first = batch.read()['requests']['unit']
        self.assertFalse(batch.dispatch_allowed('unit'))
        self.assertEqual(batch.read()['requests'], {'unit': first})

    def test_daily_batch_and_overflow_thresholds(self):
        state = {'phase': 'sleeping', 'requests': {'unit': 0}, 'stopped_at': 0}
        self.assertIsNone(batch.wake_reason(state, {'metadata': 26000}, 18*3600, self.settings))
        self.assertEqual(batch.wake_reason(state, {'metadata': 26000}, 19*3600, self.settings), 'batch_ready')
        self.assertEqual(batch.wake_reason(state, {'metadata': 130000}, 3600, self.settings), 'overflow_backlog')
        self.assertEqual(batch.wake_reason(state, {'metadata': 0}, 24*3600, self.settings), 'daily_work_due')

    def test_empty_sleep_does_not_wake_for_calendar_alone(self):
        self.assertIsNone(batch.wake_reason({'phase': 'sleeping', 'stopped_at': 0}, {'metadata': 0, 'historical': 0}, 48*3600, self.settings))

    def test_five_hour_budget_drains_even_with_new_arrivals(self):
        state = {'phase': 'running', 'started_at': 0}
        counts = {'metadata': 1000, 'historical': 2}
        self.assertFalse(batch.should_drain(state, counts, 4*3600, self.settings))
        self.assertTrue(batch.should_drain(state, counts, 5*3600, self.settings))

    def test_shutdown_requires_remote_drain_proof(self):
        batch.save({'phase': 'catchup', 'requests': {}})
        ec2 = Mock()
        ec2.describe_instances.return_value = {'Reservations': [{'Instances': [{'State': {'Name': 'running'}}]}]}
        with patch('boto3.client', return_value=ec2), patch.object(batch, 'metrics', return_value={'metadata': 0, 'historical': 0}), patch.object(batch, 'policy', return_value=self.settings), patch('constellation.m7_lifecycle.deployment_hold_active', return_value=False), patch.object(batch, 'remote_control', return_value={'safe_to_stop': False, 'active': ['worker']}) as remote:
            self.assertEqual(batch.tick()['phase'], 'draining')
            ec2.stop_instances.assert_not_called()
            remote.return_value = {'safe_to_stop': True, 'active': []}
            self.assertEqual(batch.tick()['phase'], 'sleeping')
            ec2.stop_instances.assert_called_once()

    def test_draining_dispatch_stays_queued(self):
        batch.save({'phase': 'draining', 'requests': {}})
        self.assertFalse(batch.dispatch_allowed('unit'))
        self.assertIn('unit', batch.read()['requests'])

    def test_remote_failure_keeps_recoverable_drain_state(self):
        batch.save({'phase': 'catchup', 'requests': {}})
        ec2 = Mock()
        ec2.describe_instances.return_value = {'Reservations': [{'Instances': [{'State': {'Name': 'running'}}]}]}
        with patch('boto3.client', return_value=ec2), patch.object(batch, 'metrics', return_value={'metadata': 0, 'historical': 0}), patch.object(batch, 'policy', return_value=self.settings), patch('constellation.m7_lifecycle.deployment_hold_active', return_value=False), patch.object(batch, 'remote_control', side_effect=RuntimeError('SSM failed')):
            with self.assertRaises(RuntimeError): batch.tick()
        self.assertEqual(batch.read()['phase'], 'draining')
        ec2.stop_instances.assert_not_called()


if __name__ == '__main__':
    unittest.main()
