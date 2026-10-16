from datetime import date
import unittest
from unittest.mock import Mock, patch
import io
import json
from specialist_authenticated import fetch, scopes, table_rows
from specialist_inputs import item
from regulatory_collection import SourceIssue


class AuthenticatedTests(unittest.TestCase):
    def test_eia_echo_redacted_before_persistence(self):
        from specialist_authenticated import request
        response = io.BytesIO(json.dumps({'request': {'api_key': 'test-only-secret'}, 'response': {'data': []}}).encode())
        client = Mock()
        with patch('specialist_authenticated.credentials', return_value=('test-only-secret',)), patch('specialist_authenticated.build_opener') as opener:
            opener.return_value.open.return_value = response
            request(client, 'eia', 'https://api.eia.gov/v2/example', {'length': 1})
        saved, url = client.save.call_args.args
        self.assertNotIn(b'test-only-secret', saved)
        self.assertNotIn('api_key', url)
        self.assertIn(b'[REDACTED]', saved)

    def job(self, kind):
        return {'adapter': kind, 'parameters': {'url': 'https://example.org/',
                'start': '2021-01-01', 'end': '2021-02-01', 'date_field': 'InspectionEndDate'}}

    @patch('specialist_authenticated.request')
    def test_dashboard_resume_and_date_bounds(self, request):
        request.return_value = {'statuscode': 400, 'resultcount': 1, 'totalrecordcount': 102,
                                'result': [{'InspectionEndDate': '2021-01-05', 'InspectionID': 4}]}
        rows, cursor = fetch(Mock(), self.job('fda_dashboard'), '100', item)
        self.assertEqual('101', cursor)
        self.assertEqual(101, request.call_args.kwargs['body']['start'])
        self.assertEqual('2021-01-05', rows[0]['date'])
        request.return_value['result'][0]['InspectionEndDate'] = '2026-10-29'
        with self.assertRaisesRegex(SourceIssue, 'outside_window'):
            fetch(Mock(), self.job('fda_dashboard'), None, item)

    @patch('specialist_authenticated.request')
    def test_missing_page_does_not_exhaust(self, request):
        request.return_value = {'statuscode': 400, 'resultcount': 0, 'totalrecordcount': 5, 'result': []}
        with self.assertRaisesRegex(SourceIssue, 'missing_page'):
            fetch(Mock(), self.job('fda_dashboard'), None, item)

    def test_fda_column_rows_and_errors(self):
        self.assertEqual([{'id': 1}], table_rows({'APIRETURNCODE': 400, 'RESULT': {'COLUMNS': ['id'], 'DATA': [[1]]}}))
        with self.assertRaisesRegex(SourceIssue, 'status'):
            table_rows({'STATUSCODE': 401, 'RESULT': []})
        with self.assertRaisesRegex(SourceIssue, 'width'):
            table_rows({'STATUSCODE': 400, 'RESULT': {'COLUMNS': ['id'], 'DATA': [[1, 2]]}})

    @patch('specialist_authenticated.request')
    def test_edinet_count_and_ids(self, request):
        request.return_value = {'metadata': {'status': '200', 'resultset': {'count': 2}}, 'results': [{'docID': 'ABC'}]}
        job = self.job('edinet'); job['parameters']['date'] = '2021-01-04'
        with self.assertRaisesRegex(SourceIssue, 'count'):
            fetch(Mock(), job, None, item)

    def test_no_pcb_historical_vintages(self):
        self.assertEqual([], list(scopes({'adapter': 'fda_productcodes'}, date(2021, 1, 1), date(2021, 2, 1), 'historical')))

    def test_edinet_daily_captures_only_the_completed_previous_day(self):
        rows = list(scopes({'adapter': 'edinet', 'api': 'https://api.edinet-fsa.go.jp/api/v2/documents.json'},
            date(2026, 10, 8), date(2026, 10, 16), 'daily'))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][2]['date'], '2026-10-14')
        self.assertIn('pipeline_version', rows[0][2])

    @patch('specialist_authenticated.request')
    def test_ires_total_is_not_returned_count(self, request):
        request.return_value = {'STATUSCODE': 400, 'RESULTCOUNT': 291, 'RESULT': [{'productid': 42}]}
        rows, cursor = fetch(Mock(), self.job('fda_enforcement'), None, item)
        self.assertEqual('1', cursor)
        self.assertEqual('42', rows[0]['id'])

    @patch('specialist_authenticated.request')
    def test_eia_retains_month_without_invented_day(self, request):
        request.return_value = {'response': {'total': '1', 'data': [{'period': '2021-01', 'stateid': 'US', 'sectorid': 'ALL', 'price': '10.29'}]}}
        rows, cursor = fetch(Mock(), self.job('eia_api'), None, item)
        self.assertIsNone(cursor)
        self.assertIsNone(rows[0]['date'])

