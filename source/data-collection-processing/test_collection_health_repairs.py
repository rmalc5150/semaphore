import unittest
import io
import json
import time
from unittest.mock import patch, Mock
from collection_health_exporter import inspect_job, json_reports, Evidence as StoredEvidence
from research_contract import digest
import hashlib
from datetime import datetime, timezone


class Evidence:
    def confirmed(self, value):
        if not isinstance(value, dict):
            return []
        if value.get('status') == 'complete' and value.get('manifest'):
            return [(value['manifest'], '2026-09-27T07:00:00Z')]
        return self.confirmed(value.get('last_result'))

    def read(self, key):
        return {'symbols': {
            'success': {'last_attempt': '2026-09-27T07:00:00Z',
                        'last_result': {'status': 'complete', 'manifest': 'verified'}},
            **{str(n): {'last_attempt': '2026-09-27T08:00:00Z',
                       'last_result': {'status': 'partial'}} for n in range(4)}
        }}, None, '2026-09-27T08:00:00Z'


class HealthRepairTests(unittest.TestCase):
    def test_partial_progress_requires_reachable_receipt_and_valid_batches(self):
        raw = b'{"record": 1}\n'
        page = {'sequence': 0, 'run_id': 'old-run', 'record_count': 1,
                'batches': [{'key': 'batch', 'sha256': hashlib.sha256(raw).hexdigest(), 'records': 1}]}
        receipt = 'manifests/old-run/pages/00000000-'+digest(page)+'.json'
        docs = {'manifest': {'task_id': 't', 'task': {'source': 'nmpa_trials'}},
                'checkpoints/t/head.json': {'task': {'source': 'nmpa_trials'}, 'pages': [page],
                    'exhausted': False, 'manifest_prefix': 'manifests/new-resume-attempt'},
                receipt: page}
        def get(**kwargs):
            key = kwargs['Key'].removeprefix('data/')
            body = raw if key == 'batch' else json.dumps(docs[key]).encode()
            return {'Body': io.BytesIO(body), 'ContentLength': len(body),
                    'LastModified': datetime(2026,10,5,10,tzinfo=timezone.utc)}
        s3 = Mock(); s3.get_object.side_effect = get
        evidence = StoredEvidence(s3, 'bucket', 'data')
        outcome = {'status': 'partial', 'manifest': 'manifest'}
        commits, pending = evidence.checkpoint_commits(outcome)
        self.assertTrue(pending)
        self.assertEqual(commits, [(receipt, '2026-10-05T10:00:00Z')])
        # A new run ID/head write alone must retain the original page token/time.
        self.assertEqual(evidence.checkpoint_commits(outcome), (commits, pending))
        raw = b'corrupt\n'
        with self.assertRaisesRegex(ValueError, 'batch verification failed'):
            evidence.checkpoint_commits(outcome)
        docs[receipt] = {'wrong': 'receipt'}
        with self.assertRaisesRegex(ValueError, 'receipt mismatch'):
            StoredEvidence(s3, 'bucket', 'data').checkpoint_commits(outcome)

    def test_started_checkpoint_without_committed_pages_is_not_progress(self):
        evidence = StoredEvidence(Mock(), 'bucket', 'data')
        with patch.object(evidence, 'read', side_effect=[
                ({'task_id': 't', 'task': {'source': 'nmpa_trials'}}, None, None),
                ({'task': {'source': 'nmpa_trials'}, 'pages': [], 'exhausted': False}, None, None)]):
            self.assertEqual(evidence.checkpoint_commits({'manifest': 'm'}), ([], True))

    def test_journal_tails_before_applying_age_bound(self):
        now = time.time()
        process = Mock()
        process.stdout = io.StringIO('\n'.join(json.dumps({
            '__REALTIME_TIMESTAMP': str(int(at*1e6)),
            '_SYSTEMD_INVOCATION_ID': invocation,
            'MESSAGE': json.dumps({'status': 'complete', 'manifest': invocation})
        }) for at, invocation in [(now-4*86400, 'old'), (now, 'current')]))
        process.wait.return_value = 0
        process.poll.return_value = 0
        with patch('collection_health_exporter.subprocess.Popen', return_value=process) as launch:
            reports, _, commit = json_reports('test.service')
        self.assertNotIn('--since', launch.call_args.args[0])
        self.assertEqual(len(reports), 1)
        self.assertEqual(commit['manifest'], 'current')

    def inspect(self, service, reports, policy=None, unit='test.service'):
        timer = {'UnitFileState': 'enabled', 'ActiveState': 'active'}
        with patch('collection_health_exporter.properties', side_effect=[service, timer]), \
             patch('collection_health_exporter.json_reports', return_value=(reports, [], None)), \
             patch('collection_health_exporter.time.clock_gettime', return_value=100):
            return inspect_job(unit, policy or {}, Evidence(), 0, 1790492460)

    def test_verified_page_recovers_only_older_source_failure(self):
        for at, expected in [('2026-09-27T06:00:00Z', []),
                             ('2026-09-27T08:00:00Z', ['scrape_target_http_202'])]:
            reports = [{'at': at, 'value': {'status': 'failed', 'reason': 'scrape_target_http_202'}}]
            with patch.object(Evidence, 'checkpoint_commits', create=True,
                              return_value=([('page-receipt', '2026-09-27T07:00:00Z')], True)):
                result = self.inspect({}, reports, unit='optima-nmpa-inventory.service')
            self.assertEqual([i['code'] for i in result['issues']], expected)
            self.assertTrue(result['progress']['pending'])

    def test_newer_failures_do_not_hide_market_success(self):
        result = self.inspect({}, [], {'progress_keys': ['market']})
        self.assertEqual(result['progress']['last_verified_at'], '2026-09-27T07:00:00Z')

    def test_success_requires_completed_process_and_verified_invocation_output(self):
        props = {'ActiveState': 'inactive', 'Result': 'success', 'ExecMainStatus': '0',
                 'ExecMainStartTimestampMonotonic': '50000000',
                 'ExecMainExitTimestampMonotonic': '90000000'}
        reports = [{'at': '2026-09-27T07:00:50Z', 'value': {'status': 'complete', 'manifest': 'verified'}}]
        self.assertIn('successful_execution_at', self.inspect(props, reports))
        self.assertNotIn('successful_execution_at', self.inspect(props, []))
        props['ExecMainStatus'] = '75'
        self.assertNotIn('successful_execution_at', self.inspect(props, reports))

    def test_empty_publication_recovers_only_with_verified_receipt_and_clear_queue(self):
        props = {'ActiveState': 'inactive', 'Result': 'success', 'ExecMainStatus': '0',
                 'ExecMainStartTimestampMonotonic': '50000000',
                 'ExecMainExitTimestampMonotonic': '90000000'}
        reports = [{'at': '2026-09-27T07:00:50Z', 'value': {'status': 'complete', 'results': []}}]
        receipt = {'operations/market/publication-receipts/a': {'LastModified': 1, 'ETag': 'one'}}
        with patch.object(Evidence, 'inventory', create=True, side_effect=[{}, receipt]), \
             patch.object(Evidence, 'read', return_value=({'status': 'complete', 'manifest': 'verified'}, None, None)):
            result = self.inspect(props, reports, {'publication_owners': ['market']})
        self.assertIn('successful_execution_at', result)
        with patch.object(Evidence, 'inventory', create=True, side_effect=[{}, {}]):
            result = self.inspect(props, reports, {'publication_owners': ['market']})
        self.assertNotIn('successful_execution_at', result)
