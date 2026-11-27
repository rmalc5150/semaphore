from contextlib import contextmanager
from datetime import datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

from metadata_publication_report import (
    OLD_BASIS, accepted_jobs, athena_counts, athena_sql, receipt_snapshot, refresh, render_overview,
)
from monitoring_overview import publication_context

A = 'a' * 64
B = 'b' * 64
ROOT = 's3://data-testing/metadata'
CONFIG = {'bucket': 'data-testing', 'prefix': 'metadata',
          'athena_workgroup': 'metadata', 'athena_database': 'optima_metadata_engine'}
WHEN = '2026-11-24T22:30:00+00:00'


class ReportingTests(TestCase):
    def test_job_lookup_splits_a_timed_out_page(self):
        from pymysql.err import OperationalError
        ids = tuple(str(i).zfill(64) for i in range(100))
        cur = Mock()
        cur.execute.side_effect = [OperationalError(3024, 'timeout'), 1, 1]
        cur.fetchall.side_effect = [[{'job_id': ids[0]}], [{'job_id': ids[-1]}]]
        self.assertEqual(accepted_jobs(cur, ids), [{'job_id': ids[0]}, {'job_id': ids[-1]}])
        self.assertEqual([len(call.args[1]) for call in cur.execute.call_args_list], [100,50,50])

    def test_receipt_counts_only_match_accepted_published_jobs(self):
        def release(job):
            return {'release_id': bytes.fromhex(job[:32]), 's3_uri': f'{ROOT}/publication/{job}/qid.json',
                    'verified_at': datetime(2026, 11, 24, 22)}
        cursor = Mock()
        cursor.fetchall.side_effect = [
            [{'source_key': 'one'}, {'source_key': 'two'}],
            [release(A), release(B)],
            [{'job_id': A, 'source_key': 'one', 'output_rows': 128}],
        ]
        @contextmanager
        def tx():
            yield cursor
        result = receipt_snapshot(SimpleNamespace(config=CONFIG, tx=tx), lambda: WHEN)
        self.assertEqual(result['totals'], {'rows': 128, 'releases': 1, 'source_count': 1})
        self.assertEqual(result['sources']['two']['rows'], 0)
        calls = cursor.execute.call_args_list
        self.assertIn("status='published'", calls[2].args[0])
        self.assertIn("state='accepted'", calls[3].args[0])
        self.assertEqual(calls[3].args[1], (A, B))

    def test_grouped_athena_submits_once_and_exact_checks_use_job_ids(self):
        client = Mock()
        client.start_query_execution.return_value = {'QueryExecutionId': 'unique'}
        client.get_query_execution.return_value = {
            'QueryExecution': {'Status': {'State': 'SUCCEEDED'}, 'Statistics': {'DataScannedInBytes': 432}}
        }
        def record(*cols):
            return {'Data': [{'VarCharValue': x} for x in cols]}
        client.get_paginator.return_value.paginate.return_value = [
            {'ResultSet': {'Rows': [record('source_key', 'row_count', 'releases'), record('one', '128', '4')]}},
            {'ResultSet': {'Rows': [record('two', '8', '1')]}},
        ]
        result = athena_counts(client, CONFIG, collect=lambda: WHEN)
        client.start_query_execution.assert_called_once()
        self.assertEqual(result['totals'], {'rows': 136, 'releases': 5, 'source_count': 2})
        sql = client.start_query_execution.call_args.kwargs['QueryString']
        self.assertIn('GROUP BY source_key', sql)
        self.assertNotIn('WHERE', sql)
        self.assertIn(f"WHERE job_id IN ('{A}','{B}')", athena_sql(CONFIG, [A, B, A]))
        for ids in ([], ['unknown'], [str(i).zfill(64) for i in range(51)]):
            with self.assertRaises(ValueError):
                athena_sql(CONFIG, ids)

    def test_render_updates_only_labels_is_idempotent_and_shares_snapshot(self):
        report = {'schema_version': 1, 'report_uri': ROOT,
                  'receipts': {'as_of': WHEN, 'totals': {'rows': 20, 'releases': 2},
                               'sources': {'one': {'rows': 20, 'releases': 2}}},
                  'athena': {'as_of': WHEN, 'query_execution_id': 'unique',
                             'totals': {'rows': 22, 'releases': 3},
                             'sources': {'one': {'rows': 22, 'releases': 3}}}}
        document = '\n'.join((OLD_BASIS, '001 One [one]', '    Athena      1 labelled rows / 1 verified metadata releases',
                              '    Metadata    Enabled', '    Raw file description   Retained original.',
                              '', '002 One subset [one]', '    Athena      200 committed rows', '    Metadata    Enabled'))
        output = render_overview(document, report, ROOT)
        self.assertEqual(render_overview(output, report, ROOT), output)
        self.assertEqual(output.count('20 rows / 2 verified metadata releases'), 2)
        self.assertEqual(output.count('22 rows / 3 job partitions'), 2)
        self.assertIn('200 committed rows', output)
        self.assertIn('Retained original.', output)
        text = '\n'.join(publication_context(report, datetime.fromisoformat(WHEN).timestamp()))
        self.assertIn('20 rows in 2 verified releases', text)
        self.assertIn('22 rows in 3 job partitions', text)
        self.assertIn(ROOT, text)

    def test_publishing_saved_snapshots_never_opens_athena_or_database(self):
        session = Mock()
        with TemporaryDirectory() as tmp:
            cache = Path(tmp) / 'report.json'
            document = Path(tmp) / 'overview.txt'
            routine = {'as_of': WHEN, 'totals': {'rows': 8, 'releases': 1}, 'sources': {}}
            grouped = {'as_of': WHEN, 'query_execution_id': 'one', 'totals': {'rows': 9, 'releases': 1}, 'sources': {}}
            document.write_text(OLD_BASIS + '\n001 Registered [one]\n    Metadata    Enabled\n')
            cache.write_text(json.dumps({'schema_version': 1, 'receipts': routine}))
            cache.with_suffix('.athena.json').write_text(json.dumps(grouped))
            result = refresh(session, CONFIG, CONFIG, publish_saved=True, cache=cache, overview=document)
            self.assertEqual(result['receipts'], routine)
            self.assertEqual(result['athena'], grouped)
            self.assertIn('one', document.read_text())
            session.client.assert_called_once_with('s3')
            uploaded = session.client.return_value.put_object.call_args.kwargs['Body']
            self.assertEqual(json.loads(uploaded), json.loads(cache.read_text()))
