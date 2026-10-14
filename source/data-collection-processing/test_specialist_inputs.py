import io
import json
import tempfile
import unittest
import zipfile
from datetime import date
from unittest.mock import patch

from collection_storage import LocalStore, StorageSettings, CollectionRun, task_spec
from research_contract import ROOT, load_json, validate_record
from regulatory_collection import SourceIssue
from specialist_inputs import fetch_page, collect, normalized, item
from specialist_plan import jobs


class Client:
    evidence = []
    def __init__(self, value): self.value = value
    def json(self, *args, **kwargs): return self.value
    def get(self, *args, **kwargs): return self.value


class SpecialistTests(unittest.TestCase):
    def test_usaspending_cursor_exhausts_each_recipient_before_next(self):
        from unittest.mock import Mock
        client=Mock()
        client.json.side_effect=[{'results':[],'page_metadata':{'hasNext':True}},
                                 {'results':[],'page_metadata':{'hasNext':False}},
                                 {'results':[],'page_metadata':{'hasNext':False}}]
        job={'adapter':'usaspending','parameters':{'url':'https://example.com',
             'filters':{'recipient_search_text':['first','second']},'fields':[]}}
        _,cursor=fetch_page(client,job,None)
        self.assertEqual(json.loads(cursor),{'recipient':0,'page':2})
        _,cursor=fetch_page(client,job,cursor)
        self.assertEqual(json.loads(cursor),{'recipient':1,'page':1})
        _,cursor=fetch_page(client,job,cursor)
        self.assertIsNone(cursor)
        self.assertEqual([c.kwargs['body']['filters']['recipient_search_text'] for c in client.json.call_args_list],
                         [['first'],['first'],['second']])

    @classmethod
    def setUpClass(cls):
        cls.universe = load_json(ROOT / 'config/company-universe.v0.5.json')
        cls.taxonomy = load_json(ROOT / 'config/sectors.v1.json')
    def test_preview_cap_is_never_complete(self):
        with self.assertRaisesRegex(SourceIssue, 'truncation'):
            fetch_page(Client({'data': [{}] * 500}), {'adapter': 'comtrade', 'parameters':
                {'url': 'https://example.org', 'query': {'maxRecords': 500, 'period': 2021}}}, None)
    def test_ted_timeout_not_empty_success(self):
        with self.assertRaisesRegex(SourceIssue, 'timeout'):
            fetch_page(Client({'timedOut': True, 'notices': [], 'totalNoticeCount': 0}),
                {'adapter': 'ted', 'parameters': {'url': 'https://example.org', 'query': 'a', 'fields': []}}, None)
    def test_caiso_zip_error_is_not_data(self):
        b = io.BytesIO()
        with zipfile.ZipFile(b, 'w') as z: z.writestr('error.xml', '<error>no data</error>')
        with self.assertRaisesRegex(SourceIssue, 'non_csv'):
            fetch_page(Client(b.getvalue()), {'adapter': 'caiso', 'parameters': {'url': 'https://example.org', 'query': {}}}, None)
    def test_battery_html_download_is_not_workbook(self):
        with self.assertRaisesRegex(SourceIssue, 'html_instead'):
            fetch_page(Client(b'<html>404</html>'), {'adapter': 'eia_xlsx', 'parameters': {'url': 'https://example.org'}}, None)
    def test_record_satisfies_contract_without_false_links(self):
        with tempfile.TemporaryDirectory() as d:
            spec = task_spec('source_test', 'specialist_inputs', 'daily', '2026-10-09T00:00:00Z',
                '2026-10-10T00:00:00Z', {'source_id': 'S53', 'parameters': {}, 'coverage_note': 'text only'},
                'test', self.universe, self.taxonomy)
            run = CollectionRun.start(LocalStore(d), spec, self.universe, self.taxonomy)
            row = normalized(item('doc:1', {'text': 'example'}, 'https://example.org', basis='derived'), run,
                [{'key': 'source_documents/source_test/a', 'sha256': 'a' * 64, 'source_url': 'https://example.org', 'retrieved_at': '2026-10-09T00:00:00Z'}])
            errors = validate_record(row, self.universe)
            self.assertEqual([], errors)
            self.assertEqual([], row['company_ids'])
            self.assertIsNone(row['available_at'])
    def test_current_registries_never_generate_fake_backfill(self):
        plan = load_json(ROOT / 'config/specialist-inputs.json')
        history = list(jobs(plan, self.universe, 'historical', date(2026, 10, 9)))
        self.assertNotIn('trade_screening', {j['source'] for j in history})
        self.assertNotIn('ror_institutions', {j['source'] for j in history})
    def test_partial_page_resumes_and_complete_replay_does_not_call_provider(self):
        job = {'source': 'source_test', 'source_id': 'S53', 'adapter': 'pdf', 'parameters': {},
               'mode': 'historical', 'start': '2021-01-01', 'end': '2022-01-01', 'coverage_note': 'bounded test'}
        with tempfile.TemporaryDirectory() as d:
            settings = StorageSettings(local_root=d); store = settings.store()
            with patch('specialist_inputs.time.sleep'), patch('specialist_inputs.fetch_page', return_value=([item('first', {}, 'https://example.org')], 'page2')):
                first = collect(job, store, settings, self.universe, self.taxonomy, 1)
            self.assertEqual('partial', first['status'])
            with patch('specialist_inputs.time.sleep'), patch('specialist_inputs.fetch_page', return_value=([item('second', {}, 'https://example.org')], None)) as provider:
                second = collect(job, store, settings, self.universe, self.taxonomy, 1)
                self.assertEqual('page2', provider.call_args.args[2])
            self.assertEqual('complete', second['status'])
            self.assertEqual(2, second['records'])
            with patch('specialist_inputs.fetch_page') as provider:
                replay = collect(job, store, settings, self.universe, self.taxonomy, 1)
                provider.assert_not_called()
            self.assertTrue(replay['already_complete'])
    def test_october_nih_uses_current_fiscal_year_and_incremental_additions(self):
        plan = load_json(ROOT / 'config/specialist-inputs.json')
        daily = [j for j in jobs(plan, self.universe, 'daily', date(2026, 10, 9)) if j['source'] == 'nih_reporter']
        self.assertTrue(daily)
        for job in daily:
            self.assertEqual([2027], job['parameters']['criteria']['fiscal_years'])
            self.assertEqual('2026-10-02', job['parameters']['criteria']['date_added']['from_date'])


if __name__ == '__main__': unittest.main()
