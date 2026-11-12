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
    def test_partial_patent_child_requires_matching_scope_and_verified_pages(self):
        raw = b'{"record":1}\n'
        page = {'sequence':0,'run_id':'child-run','record_count':1,
                'batches':[{'key':'batch','sha256':hashlib.sha256(raw).hexdigest(),'records':1}]}
        receipt = 'manifests/child-run/pages/00000000-'+digest(page)+'.json'
        task = {'source':'uspto_odp','dataset':'patent_records','mode':'daily',
                'collector_version':'patents-1.0','universe_hash':'u','taxonomy_hash':'t',
                'window':{'start':'2026-11-10T00:00:00Z','end':'2026-11-11T00:00:00Z'}}
        parent_task = {**task,'scope':{'partition_strategy':'hourly-v1'}}
        child_task = {**task,'scope':{'query_bounds':['2026-11-10T04:00:00','2026-11-10T04:30:00']}}
        docs = {'parent':{'task_id':'parent-id','task':parent_task},
                'child':{'task_id':'child-id','task':child_task},
                'checkpoints/parent-id/head.json':{'task':parent_task,'pages':[],'exhausted':False},
                'checkpoints/child-id/head.json':{'task':child_task,'pages':[page],
                    'manifest_prefix':'manifests/child-run','exhausted':False},receipt:page}
        def get(**kwargs):
            key=kwargs['Key'].removeprefix('data/')
            body=raw if key=='batch'else json.dumps(docs[key]).encode()
            return {'Body':io.BytesIO(body),'ContentLength':len(body),
                    'LastModified':datetime(2026,11,12,12,tzinfo=timezone.utc)}
        s3=Mock();s3.get_object.side_effect=get
        outcome={'manifest':'parent','partition_manifest':'child'}
        observed,pending=StoredEvidence(s3,'bucket','data').checkpoint_commits(outcome)
        self.assertEqual(observed,[(receipt,'2026-11-12T12:00:00Z')]);self.assertTrue(pending)
        child_task['universe_hash']='other'
        with self.assertRaisesRegex(ValueError,'partition task/window mismatch'):
            StoredEvidence(s3,'bucket','data').checkpoint_commits(outcome)
        child_task['universe_hash']='u'
        raw=b'corrupt\n'
        with self.assertRaisesRegex(ValueError,'batch verification failed'):
            StoredEvidence(s3,'bucket','data').checkpoint_commits(outcome)

    def test_never_started_service_uses_timer_activation_for_schedule_grace(self):
        e = Mock()
        e.confirmed.return_value = []
        props = [{'ExecMainStartTimestampMonotonic':'0'},
                 {'ActiveEnterTimestampMonotonic':'100000000', 'ActiveState':'active', 'UnitFileState':'enabled'}]
        with patch('collection_health_exporter.properties', side_effect=props), \
             patch('collection_health_exporter.activity', return_value=('idle',0)), \
             patch('collection_health_exporter.json_reports', return_value=([],[],None)), \
             patch('collection_health_exporter.time.clock_gettime', return_value=200):
            result=inspect_job('example.service',{},e,0,time.time())
        self.assertEqual(result['last_start_age_seconds'],100)
        self.assertIsNone(result['progress']['last_verified_at'])


    def test_only_owner_excepted_exact_patent_endpoint_alert_is_cleared(self):
        from collection_health_exporter import apply_document_exceptions
        from collection_alerts import outcome_issues
        d = [{'status': 'active', 'dataset': 'patent_office_actions', 'application_number': '16545140'}]
        v = {'status': 'partial', 'reason': 'source_http_403', 'diagnostics': {'host': 'api.uspto.gov', 'http_status': 403, 'path': '/api/v1/patent/applications/16545140/documents'}}
        self.assertFalse(outcome_issues(apply_document_exceptions(v, d)))
        self.assertTrue(outcome_issues(apply_document_exceptions(v, [])))
        other = {**v, 'diagnostics': {**v['diagnostics'], 'path': '/api/v1/patent/applications/15123456/documents'}}
        self.assertTrue(outcome_issues(apply_document_exceptions(other, d)))
        self.assertEqual(v['status'], 'partial')

    def test_new_runtime_lock_is_queued_even_for_legacy_nonserialized_job(self):
        from collection_health_exporter import activity
        def read(path):
            return '42\n' if path.name == 'cgroup.procs' else 'flock\n'
        with patch('pathlib.Path.read_text', read):
            state, _ = activity({'ActiveState':'activating', 'ControlGroup':'/test',
                'ExecMainStartTimestampMonotonic':'1'}, False)
        self.assertEqual(state, 'queued')

    def test_search_runtime_pointer_checksum_is_required(self):
        evidence = Mock(prefix='data/')
        evidence.confirmed.return_value = []
        evidence.read.side_effect = [({'paths': {'reports/search-capture-2026-10-21/publication.json':
            {'key':'data/snapshot/publication.json', 'sha256':'expected'}}}, None, None),
            ({'release_id':'r'}, 'different', None)]
        with patch('collection_health_exporter.properties', return_value={}), \
             patch('collection_health_exporter.activity', return_value=('idle',0)), \
             patch('collection_health_exporter.json_reports', return_value=([],[],None)):
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                inspect_job('optima-search-capture.service', {}, evidence, 0, time.time())

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

    def test_closed_universe_epoch_uses_its_own_end_boundary(self):
        with patch.object(Evidence, 'read', return_value=({'next_date': '2026-09-24'}, None, '2026-09-24T00:00:00Z')):
            policy = {'progress_keys': ['old-epoch'], 'progress_end_exclusive': {'old-epoch': '2026-09-24'}}
            self.assertFalse(self.inspect({}, [], policy)['progress']['pending'])
            self.assertTrue(self.inspect({}, [], {'progress_keys': ['old-epoch']})['progress']['pending'])

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
