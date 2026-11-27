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
        self.retirement = patch.object(batch, 'METADATA_RETIREMENT', Path(self.tmp.name) / 'metadata-retired.json')
        self.retirement.start()
        self.addCleanup(self.retirement.stop)
        self.settings = {'off_hours': 14, 'max_off_hours': 24, 'session_hours': 10,
                         'shutdown_check_minutes': 60, 'batch_jobs': 26000}

    def test_first_install_preserves_backlog_processing(self):
        self.assertTrue(batch.dispatch_allowed('unit'))
        self.assertEqual(batch.read()['phase'], 'catchup')
        self.assertFalse(batch.should_drain(batch.read(), {'metadata': 1, 'historical': 0}, 0, self.settings))
        self.assertFalse(batch.should_drain(batch.read(), {'metadata': 0, 'historical': 0, 'publication': 1}, 0, self.settings))

    def test_retired_metadata_publishers_cannot_be_dispatched(self):
        batch.METADATA_RETIREMENT.touch()
        metadata = 'optima-m7-aux-metadata-publication.service'
        capture = 'optima-m7-capture-assignments-reviewed-historical.service'
        requests = {metadata: 1, capture: 2}
        batch.save({'phase': 'running', 'requests': requests})
        self.assertEqual(batch.runnable_requests(batch.read()), (capture,))
        self.assertEqual(batch.read()['requests'], requests)

    def test_resume_finds_enabled_instances_when_only_indirect_template_is_listed(self):
        import subprocess
        from contextlib import redirect_stdout
        import io
        base=Path(self.tmp.name)
        wanted=base/'etc/multi-user.target.wants';wanted.mkdir(parents=True)
        for instance in (1,2):(wanted/f'constellation-legacy-worker@{instance}.service').touch()
        real_path=Path
        def mapped(value):
            return real_path({'/etc/systemd/system':str(base/'etc'),'/run/systemd/system':str(base/'run'),'/opt/constellation/batch-paused':str(base/'marker')}.get(value,value))
        def result(args,**kwargs):
            if args[1]=='is-enabled':return subprocess.CompletedProcess(args,0 if '@1.'in args[2]else 1,'enabled\n'if '@1.'in args[2]else'masked\n','')
            return subprocess.CompletedProcess(args,0,'','')
        with patch('pathlib.Path',side_effect=mapped),patch('subprocess.check_output',return_value='constellation-legacy-worker@.service indirect disabled\n'),patch('subprocess.run',side_effect=result)as run,redirect_stdout(io.StringIO()):
            exec(batch.REMOTE_CONTROL.replace('ACTION',repr('resume')), {})
        starts=[call.args[0]for call in run.call_args_list if call.args[0][1]=='start']
        self.assertEqual(starts,[['systemctl','start','--no-block','constellation-legacy-worker@1.service']])

    def test_metadata_measurement_uses_enabled_source_first_covering_index(self):
        query=' '.join(batch.METADATA_PENDING_COUNT.split())
        self.assertEqual(query.count('FORCE INDEX (source_jobs)'), 3)
        for state in ('queued','retry','running'):
            self.assertIn(f"source_key=s.source_key AND state='{state}'", query)
        self.assertIn("WHERE s.state='enabled'", query)

    def test_research_history_participates_in_drain_and_resume(self):
        self.assertIn('constellation-research-history@*.timer', batch.REMOTE_CONTROL)
        self.assertIn('constellation-research-history@*.service', batch.REMOTE_CONTROL)

    def test_exact_count_recovers_from_timeout_using_bounded_pages(self):
        from pymysql.err import OperationalError

        cursor = Mock()
        cursor.execute.side_effect = [OperationalError(3024, 'timeout'), None,
                                      OperationalError(3024, 'page timeout'), None, None, None, None]
        cursor.fetchall.return_value = [{'source_key': 'source-a'}]
        cursor.fetchone.side_effect = [
            {'n': 256, 'last_job': 'next'}, {'n': 2, 'last_job': 'end'},
            {'n': 3, 'last_job': 'end'}, {'n': 0, 'last_job': None},
        ]
        self.assertEqual(batch.count_pending_metadata(cursor), 261)
        self.assertEqual(cursor.execute.call_args_list[3].args[1], ('source-a', 'queued', '', 256))
        self.assertEqual(cursor.execute.call_args_list[4].args[1], ('source-a', 'queued', 'next', 256))

    def test_sleep_tick_never_starts_ec2_before_threshold(self):
        batch.save({'phase': 'sleeping', 'requests': {'unit': 0}, 'stopped_at': 0})
        ec2=Mock()
        ec2.describe_instances.return_value={'Reservations':[{'Instances':[{'State':{'Name':'stopped'}}]}]}
        with patch('boto3.client',return_value=ec2), patch.object(batch,'metrics',return_value={'metadata':200000,'historical':0,'publication':0}) as metrics, patch.object(batch,'policy',return_value=self.settings), patch('constellation.m7_lifecycle.deployment_hold_active',return_value=False), patch('constellation.m7_lifecycle.start') as start, patch.object(batch.time,'time',return_value=3600):
            self.assertEqual(batch.tick()['phase'],'sleeping')
            start.assert_not_called()
            metrics.assert_not_called()

    def test_daily_wake_does_not_require_a_full_queue_count(self):
        batch.save({'phase': 'sleeping', 'requests': {}, 'stopped_at': 0})
        ec2 = Mock()
        ec2.describe_instances.return_value = {'Reservations': [{'Instances': [{'State': {'Name': 'stopped'}}]}]}
        with patch('boto3.client', return_value=ec2), patch.object(batch, 'metrics', return_value={'metadata': True, 'historical': 0, 'publication': None}) as metrics, patch.object(batch, 'policy', return_value=self.settings), patch('constellation.m7_lifecycle.deployment_hold_active', return_value=False), patch('constellation.m7_lifecycle.start') as start, patch.object(batch, 'remote_control'), patch.object(batch.time, 'time', return_value=24*3600):
            self.assertEqual(batch.tick()['wake_reason'], 'daily_work_due')
        metrics.assert_called_once_with(count_metadata=False)
        start.assert_called_once()

    def test_sleep_requests_are_durable_coalesced_and_do_not_wake(self):
        batch.save({'phase': 'sleeping', 'requests': {}, 'stopped_at': 0})
        self.assertFalse(batch.dispatch_allowed('unit'))
        first = batch.read()['requests']['unit']
        self.assertFalse(batch.dispatch_allowed('unit'))
        self.assertEqual(batch.read()['requests'], {'unit': first})

    def test_daily_batch_threshold_cannot_shorten_the_off_window(self):
        state = {'phase': 'sleeping', 'requests': {'unit': 0}, 'stopped_at': 0}
        self.assertIsNone(batch.wake_reason(state, {'metadata': 26000}, 13*3600, self.settings))
        self.assertEqual(batch.wake_reason(state, {'metadata': 26000}, 14*3600, self.settings), 'batch_ready')
        self.assertIsNone(batch.wake_reason(state, {'metadata': 200000}, 3600, self.settings))
        self.assertEqual(batch.wake_reason(state, {'metadata': 0}, 24*3600, self.settings), 'daily_work_due')

    def test_empty_sleep_does_not_wake_for_calendar_alone(self):
        self.assertIsNone(batch.wake_reason({'phase': 'sleeping', 'stopped_at': 0}, {'metadata': 0, 'historical': 0}, 48*3600, self.settings))

    def test_ten_hour_budget_drains_even_with_new_arrivals(self):
        state = {'phase': 'running', 'started_at': 0}
        counts = {'metadata': 1000, 'historical': 2}
        self.assertFalse(batch.should_drain(state, counts, 9*3600, self.settings))
        self.assertTrue(batch.should_drain(state, counts, 10*3600, self.settings))

    def test_running_checks_at_one_hour_and_at_session_deadline(self):
        ec2 = Mock()
        ec2.describe_instances.return_value = {'Reservations': [{'Instances': [{'State': {'Name': 'running'}}]}]}
        for last_check, check_at, metadata in ((100, 3700, 0), (35100, 36100, 1000)):
            with self.subTest(check_at=check_at):
                batch.save({'phase': 'running', 'started_at': 100, 'last_checked_at': last_check, 'requests': {}})
                with (
                    patch('boto3.client', return_value=ec2),
                    patch.object(batch, 'policy', return_value=self.settings),
                    patch.object(batch, 'metrics', return_value={'metadata': metadata}) as metrics,
                    patch('constellation.m7_lifecycle.deployment_hold_active', return_value=False),
                    patch.object(batch, 'remote_control', return_value={'safe_to_stop': False}) as remote,
                    patch.object(batch.time, 'time', return_value=check_at - 1) as clock,
                ):
                    self.assertEqual(batch.tick()['shutdown_check_at'], check_at)
                    metrics.assert_not_called()
                    clock.return_value = check_at
                    self.assertEqual(batch.tick()['phase'], 'draining')
                    metrics.assert_called_once_with(count_metadata=False)
                    remote.assert_called_once_with('drain')

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

    def test_historical_focus_retains_metadata_requests_without_dispatching(self):
        metadata = 'optima-m7-aux-metadata-publication.service'
        historical = 'optima-m7-capture-assignments-reviewed-historical.service'
        batch.save({'phase': 'running', 'started_at': 0, 'metadata_processing_paused': True})
        self.assertFalse(batch.dispatch_allowed(metadata))
        state = batch.read()
        self.assertIn(metadata, state['requests'])
        self.assertTrue(batch.should_drain(state, {'historical': 0}, 1, self.settings))
        self.assertIsNone(batch.wake_reason({**state, 'phase': 'sleeping', 'stopped_at': 0},
                                            {'historical': 0}, 26*3600, self.settings))
        self.assertTrue(batch.dispatch_allowed(historical))
        self.assertEqual(batch.runnable_requests(batch.read()), (historical,))

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
