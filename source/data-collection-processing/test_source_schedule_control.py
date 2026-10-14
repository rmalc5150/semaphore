import json
import unittest
from datetime import date
from unittest.mock import Mock

from research_contract import ROOT, load_json
from regulatory_collection import SourceIssue
from specialist_inputs import fetch_page
from specialist_plan import jobs
from source_schedule_control import validate


class PublicSourceTests(unittest.TestCase):
    def test_all_sources_registered_in_both_modes_with_honest_blocks(self):
        rows = validate(load_json(ROOT / 'config/source-schedule-inventory.json'))
        self.assertEqual(68, len(rows))
        for row in rows:
            self.assertFalse(row['full_scope_complete'])
            for route in row['modes'].values():
                if route['status'] == 'blocked_no_capture_route':
                    self.assertIsNone(route['capture_timer'])

    def test_deferred_purchases_and_verified_credentials_have_honest_routes(self):
        rows = {r['source_id']: r for r in validate(load_json(ROOT / 'config/source-schedule-inventory.json'))}
        for sid in ('S12', 'S16', 'S60', 'S61', 'S62'):
            self.assertEqual('normal', rows[sid]['priority'])
            self.assertEqual('blocked_no_capture_route', rows[sid]['modes']['daily']['status'])
        for sid in ('S10', 'S35', 'S41', 'S56'):
            for mode in ('daily', 'historical'):
                self.assertEqual('optima-authenticated-' + mode + '.timer', rows[sid]['modes'][mode]['capture_timer'])
        for mode in ('daily', 'historical'):
            self.assertEqual('optima-reddit-collection.timer', rows['S63']['modes'][mode]['capture_timer'])
        self.assertFalse(rows['S63']['full_scope_complete'])
        for sid in ('S31', 'S66', 'S67'):
            self.assertEqual('blocked_no_capture_route', rows[sid]['modes']['daily']['status'])

    def test_official_new_sources_have_real_2021_jobs_and_daily_jobs(self):
        plan = load_json(ROOT / 'config/specialist-inputs.json')
        universe = load_json(ROOT / 'config/company-universe.v0.5.json')
        expected = {'sec_companyfacts', 'drugsfda_applications', 'ema_medicines', 'pubmed_abstracts'}
        historical = list(jobs(plan, universe, 'historical', date(2026, 10, 9)))
        daily = list(jobs(plan, universe, 'daily', date(2026, 10, 9)))
        self.assertTrue(expected <= {j['source'] for j in historical if j['start'] == '2021-01-01'})
        self.assertTrue(expected <= {j['source'] for j in daily})

    def test_pubmed_cap_never_claims_complete(self):
        client = Mock()
        client.json.return_value = {'esearchresult': {'count': '10000', 'idlist': ['1']}}
        with self.assertRaisesRegex(SourceIssue, 'split_scope'):
            fetch_page(client, {'adapter': 'pubmed', 'parameters': {'url': 'https://example.org', 'query': {}}}, None)
        client.get.assert_not_called()

    def test_pubmed_missing_abstract_response_is_not_complete(self):
        client = Mock()
        client.json.return_value = {'esearchresult': {'count': '2', 'idlist': ['1', '2']}}
        client.get.return_value = b'<PubmedArticleSet><PubmedArticle><PMID>1</PMID></PubmedArticle></PubmedArticleSet>'
        with self.assertRaisesRegex(SourceIssue, 'incomplete_fetch'):
            fetch_page(client, {'adapter': 'pubmed', 'parameters': {'url': 'https://example.org', 'query': {}}}, None)

    def test_pubmed_offset_resumes_remaining_page(self):
        client = Mock()
        client.json.return_value = {'esearchresult': {'count': '102', 'idlist': ['101', '102']}}
        client.get.return_value = b'<PubmedArticleSet><PubmedArticle><PMID>101</PMID></PubmedArticle><PubmedArticle><PMID>102</PMID></PubmedArticle></PubmedArticleSet>'
        rows, cursor = fetch_page(client, {'adapter': 'pubmed', 'parameters': {'url': 'https://example.org', 'query': {}}}, '100')
        self.assertEqual(2, len(rows))
        self.assertIsNone(cursor)
        self.assertEqual(100, client.json.call_args.kwargs['params']['retstart'])

    def test_openfda_missing_page_never_advances(self):
        client = Mock()
        client.json.return_value = {'meta': {'results': {'total': 300}}, 'results': []}
        with self.assertRaisesRegex(SourceIssue, 'missing_page'):
            fetch_page(client, {'adapter': 'drugsfda', 'parameters': {'url': 'https://example.org', 'query': {}}}, '100')

    def test_sec_facts_filter_filing_dates_and_preserve_units(self):
        client = Mock()
        client.json.return_value = {'cik': 1, 'facts': {'us-gaap': {'Cash': {'units': {'USD': [
            {'filed': '2020-12-31', 'val': 10}, {'filed': '2021-02-01', 'val': 12}, {'filed': '2022-01-01', 'val': 15}]}}}}}
        rows, cursor = fetch_page(client, {'adapter': 'sec_companyfacts', 'parameters': {'url': 'https://example.org',
            'cik': '0000000001', 'start': '2021-01-01', 'end': '2022-01-01'}}, None)
        self.assertEqual(1, len(rows))
        self.assertEqual('USD', rows[0]['data']['unit'])
        self.assertEqual('2021-02-01', rows[0]['date'])

    def test_ema_unknown_date_not_invented_for_history(self):
        client = Mock()
        client.get.return_value = json.dumps({'meta': {}, 'data': [
            {'ema_product_number': '1', 'first_published_date': '03/02/2021'},
            {'ema_product_number': '2', 'first_published_date': ''}]}).encode()
        rows, cursor = fetch_page(client, {'adapter': 'ema_json', 'mode': 'historical', 'parameters': {
            'url': 'https://example.org', 'start': '2021-01-01', 'end': '2022-01-01'}}, None)
        self.assertEqual(['1'], [r['id'] for r in rows])
        self.assertEqual('2021-02-03', rows[0]['date'])

    def test_cpsc_ignored_filters_do_not_manufacture_historical_windows(self):
        client = Mock()
        client.get.return_value = b'[{"RecallID":1,"RecallDate":"2026-10-01T00:00:00"}]'
        with self.assertRaisesRegex(SourceIssue, 'ignored_date_filter'):
            fetch_page(client, {'adapter': 'cpsc', 'parameters': {'url': 'https://example.org',
                'start': '2021-01-01', 'end': '2021-02-01'}}, None)

    def test_canada_decisions_keep_only_requested_issue_year(self):
        client = Mock()
        client.get.return_value = b'[{"noc_number":1,"noc_date":"2020-01-01"},{"noc_number":2,"noc_date":"2021-01-01"}]'
        rows, cursor = fetch_page(client, {'adapter': 'canada_noc', 'parameters': {'url': 'https://example.org',
            'start': '2021-01-01', 'end': '2022-01-01'}}, None)
        self.assertEqual(['2'], [r['id'] for r in rows])

    def test_gleif_identifier_mismatch_is_not_accepted(self):
        client = Mock()
        client.json.return_value = {'data': {'id': 'other', 'attributes': {'entity': {}}}}
        with self.assertRaisesRegex(SourceIssue, 'identity_mismatch'):
            fetch_page(client, {'adapter': 'gleif', 'parameters': {'url': 'https://example.org', 'lei': 'expected'}}, None)


if __name__ == '__main__':
    unittest.main()
