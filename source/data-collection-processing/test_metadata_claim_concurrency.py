import unittest
from unittest.mock import MagicMock, patch
from metadata_engine.runtime_db import Database


class ClaimTests(unittest.TestCase):
    def db(self, sources, responses):
        db=Database.__new__(Database)
        db.config={}
        cursor=MagicMock()
        cursor.fetchall.return_value=sources
        cursor.fetchone.side_effect=responses
        db.tx=MagicMock()
        db.tx.return_value.__enter__.return_value=cursor
        return db,cursor

    def test_locked_source_does_not_starve_an_independent_source(self):
        db,c=self.db([{'source_key':'a'},{'source_key':'b'}],
                     [None,{'state':'enabled'},None,{'job_id':'b-job'},{'job_id':'b-job'}])
        job=db.claim()
        self.assertEqual(job['job_id'],'b-job')
        self.assertTrue(job['lease_token'])
        discovery=c.execute.call_args_list[0].args[0]
        self.assertNotIn('FOR UPDATE',discovery)
        self.assertIn('source_key=%s FOR UPDATE SKIP LOCKED',c.execute.call_args_list[1].args[0])

    def test_stale_candidate_is_not_updated(self):
        db,c=self.db([{'source_key':'a'}],[{'state':'enabled'},None,{'job_id':'old'},None])
        self.assertIsNone(db.claim())
        self.assertFalse(any(call.args[0].startswith('UPDATE') for call in c.execute.call_args_list))

    def test_worker_claim_timeout_retries_and_defers_after_three_errors(self):
        from pymysql.err import OperationalError
        from metadata_engine import worker
        db=MagicMock()
        db.claim.side_effect=OperationalError(3024,'statement timed out')
        with patch('sys.argv',['worker']), patch.object(worker.Path,'read_text',return_value='{}'), patch.object(worker,'Database',return_value=db), patch.object(worker,'process') as process, patch.object(worker.time,'sleep') as sleep:
            worker.main()
        self.assertEqual(db.claim.call_count,3)
        self.assertEqual([call.args for call in sleep.call_args_list],[(2,),(4,)])
        process.assert_not_called()

    def test_running_source_is_rechecked_with_current_locking_read(self):
        db,c=self.db([{'source_key':'a'}],[{'state':'enabled'},{'job_id':'already-running'}])
        self.assertIsNone(db.claim())
        self.assertIn('FOR UPDATE',c.execute.call_args_list[2].args[0])
        self.assertFalse(any(call.args[0].startswith('UPDATE') for call in c.execute.call_args_list))

    def test_only_reviewed_edinet_can_claim_three_parallel_jobs(self):
        for reviewed in (False, True):
            db, cursor = self.db([{'source_key': 'edinet_filings'}, {'source_key': 'other'}],
                                 [{'state': 'enabled'}, {'job_id': 'edinet-at-limit'},
                                  {'state': 'enabled'}, {'job_id': 'other-at-limit'}])
            if reviewed:
                db.config['verified_source_failure_handling'] = {'edinet_filings': 'queue_by_source_date'}
            self.assertIsNone(db.claim())
            offset = 2 if reviewed else 0
            self.assertEqual(cursor.execute.call_args_list[0].args[1], (offset,))
            self.assertEqual(cursor.execute.call_args_list[2].args[1], ('edinet_filings', offset))
            self.assertEqual(cursor.execute.call_args_list[4].args[1], ('other', 0))

    def test_configured_parallel_source_fences_the_running_input(self):
        db, cursor = self.db([], [{'state': 'enabled'}, {'job_id': 'next'}, {'job_id': 'next'}])
        db.config = {
            'metadata_source_parallelism': {'qualified': 2, 'unreviewed': 2},
            'verified_source_failure_handling': {'qualified': 'queue_by_source_date'},
        }
        cursor.fetchall.side_effect = [
            [{'source_key': 'qualified'}],
            [{'input_key': 'raw/current.jsonl', 'streaming': 0}],
        ]
        self.assertEqual(db.claim()['job_id'], 'next')
        query, params = cursor.execute.call_args_list[0].args
        self.assertIn('LIMIT 1 OFFSET 1', query)
        self.assertEqual(params, (0, 'qualified'))
        self.assertEqual(cursor.execute.call_args_list[2].args[1], ('qualified', 2))
        query, params = cursor.execute.call_args_list[3].args
        self.assertEqual(query.count('input_key NOT IN (%s)'), 3)
        self.assertEqual(params, ('qualified', 'raw/current.jsonl') * 3)

    def test_parallel_sources_at_capacity_or_streaming_admit_nothing(self):
        inputs = [{'input_key': 'raw/a.jsonl', 'streaming': 0}, {'input_key': 'raw/b.jsonl', 'streaming': 0}]
        for running in (inputs, [{'input_key': 'raw/a.jsonl', 'streaming': 1}]):
            with self.subTest(running=running):
                db, cursor = self.db([], [{'state': 'enabled'}])
                db.config = {
                    'metadata_source_parallelism': {'qualified': 2},
                    'verified_source_failure_handling': {'qualified': 'queue_by_source_date'},
                }
                cursor.fetchall.side_effect = [[{'source_key': 'qualified'}], running]
                self.assertIsNone(db.claim())
                self.assertEqual(cursor.execute.call_count, 3)

    def test_disabled_source_is_not_claimed(self):
        db,c=self.db([{'source_key':'a'}],[{'state':'raw_stopped'}])
        self.assertIsNone(db.claim())
        self.assertEqual(c.execute.call_count,2)

    def test_ordinary_and_streaming_claims_use_disjoint_retry_filters(self):
        from metadata_engine.streaming_worker import claim as claim_streaming
        ordinary,c=self.db([{'source_key':'a'}],[{'state':'enabled'},None,None])
        self.assertIsNone(ordinary.claim())
        self.assertIn("NOT (LOCATE('streaming_lane_required'",c.execute.call_args_list[0].args[0])
        self.assertIn("NOT (LOCATE('streaming_lane_required'",c.execute.call_args_list[3].args[0])
        streaming,c=self.db([],[{'state':'enabled'},None,{'job_id':'streaming'}])
        self.assertEqual(claim_streaming(streaming,'a')['job_id'],'streaming')
        statement=c.execute.call_args_list[2].args[0]
        self.assertIn("j.available_after<=UTC_TIMESTAMP(6)",statement)
        self.assertIn("j.lease_until<UTC_TIMESTAMP(6)",statement)
        self.assertNotIn("NOT (LOCATE",statement)

    def test_oversized_input_routes_once_then_records_unsupported_format(self):
        from metadata_engine import worker
        from metadata_engine.evidence import OversizedArtifact
        from metadata_engine import streaming
        for active in (False,True):
            db,c=self.db([],[{'contract_json':'{}'}])
            db.finish=MagicMock()
            job={'job_id':'job','source_key':'a','input_key':'key','lease_token':'lease','contract_version':'v'}
            with patch.object(worker,'load_input',side_effect=OversizedArtifact('large')), \
                    patch.object(streaming,'active',return_value=active), \
                    patch.object(streaming,'register_source') as register, \
                    patch.object(worker,'put',return_value='s3://bucket/receipt'):
                worker.process(db,object(),{'bucket':'bucket','prefix':'prefix'},job)
            if active:
                register.assert_not_called()
                db.finish.assert_called_once_with(job,'raw_failed','streaming_adapter_required_for_oversized_input',
                    report='s3://bucket/receipt')
            else:
                register.assert_called_once_with(db,'a')
                db.finish.assert_called_once_with(job,'retry','streaming_lane_required')

    def test_worker_retries_transient_empty_claim_within_budget(self):
        from metadata_engine import worker
        db=MagicMock();db.claim.side_effect=[None,{'job_id':'ready'}]
        with patch('sys.argv',['worker','--max-jobs','1','--max-seconds','210']), patch.object(worker.Path,'read_text',return_value='{}'), patch.object(worker,'Database',return_value=db), patch.object(worker,'process') as process, patch.object(worker.time,'monotonic',side_effect=[0,0,1,2,3]), patch.object(worker.time,'sleep') as sleep:
            worker.main()
        self.assertEqual(db.claim.call_count,2)
        process.assert_called_once()
        sleep.assert_called_once_with(2)

    def test_worker_empty_queue_stops_at_time_budget(self):
        from metadata_engine import worker
        db=MagicMock();db.claim.return_value=None
        with patch('sys.argv',['worker','--max-jobs','64','--max-seconds','210']), patch.object(worker.Path,'read_text',return_value='{}'), patch.object(worker,'Database',return_value=db), patch.object(worker,'process') as process, patch.object(worker.time,'monotonic',side_effect=[0,0,211,211]):
            worker.main()
        process.assert_not_called()
