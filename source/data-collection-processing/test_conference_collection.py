from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from collection_storage import StorageSettings
from conference_collection import collect, SOURCE
from conference_athena import prepare
from regulatory_collection import EvidenceClient
from research_contract import ROOT, canonical_json, load_json


class ConferenceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.settings = StorageSettings(local_root=str(self.root / 'store'), s3_bucket='test')
        self.store = self.settings.store()
        self.u = load_json(ROOT / 'examples/sec-filings/universe.json')
        self.t = load_json(ROOT / 'config/sectors.v1.json')
        self.client = EvidenceClient(self.store, SOURCE)
        self.calls = []

    def page(self, dois, total, cursor='next'):
        return {'status': 'ok', 'message': {'items': [{'DOI': doi, 'type': 'proceedings-article',
            'published': {'date-parts': [[2021, 1, 1]]}, 'title': ['A study']} for doi in dois],
            'total-results': total, 'next-cursor': cursor}}

    def run_pages(self, pages, mode='historical', **kwargs):
        def get(url, params):
            self.calls.append(params)
            raw = canonical_json(pages.pop(0))
            self.client.save(raw, url)
            return raw
        with patch.object(self.client, 'get', side_effect=get):
            return collect(self.store, self.settings, self.u, self.t, date(2021, 1, 1),
                date(2021, 1, 2), mode, self.client, rows=2, **kwargs)

    def test_cursor_exhaustion_and_verified_curation(self):
        result = self.run_pages([self.page(['10.1/a', '10.1/b'], 3), self.page(['10.1/c'], 3)])
        self.assertEqual(result['status'], 'complete', result)
        self.assertEqual(self.calls[1]['cursor'], 'next')
        root = prepare(self.store, self.settings, load_json(ROOT / 'config/conference-athena.json'), [result['manifest']], self.root / 'build')
        self.assertEqual(load_json(root / 'release.json')['files']['conference_observations']['rows'], 3)
        self.assertTrue(self.run_pages([])['already_complete'])

    def test_mismatched_totals_not_complete(self):
        result = self.run_pages([self.page(['10.1/a'], 4)])
        self.assertEqual(result['status'], 'failed', result)

    def test_partial_restart_uses_fresh_cursor(self):
        result = self.run_pages([self.page(['10.1/a', '10.1/b'], 3)], max_pages=1)
        self.assertEqual(result['status'], 'partial', result)
        self.calls = []
        result = self.run_pages([self.page(['10.1/a', '10.1/b'], 3), self.page(['10.1/c'], 3)])
        self.assertEqual(result['status'], 'complete', result)
        self.assertEqual(self.calls[0]['cursor'], '*')

    def test_daily_uses_update_date(self):
        result = self.run_pages([self.page([], 0)], mode='daily')
        self.assertEqual(result['status'], 'complete', result)
        self.assertIn('from-update-date:2021-01-01', self.calls[0]['filter'])

    def test_partial_publication_date_is_not_fabricated(self):
        page = self.page(['10.1/a'], 1)
        page['message']['items'][0]['published']['date-parts'] = [[2021]]
        result = self.run_pages([page])
        self.assertEqual(result['status'], 'complete', result)
        root = prepare(self.store, self.settings, load_json(ROOT / 'config/conference-athena.json'), [result['manifest']], self.root / 'build')
        import pyarrow.parquet as pq
        row = pq.ParquetFile(root / 'tables/conference_observations/part-00000.parquet').read().to_pylist()[0]
        self.assertIsNone(row['publication_date'])
        self.assertFalse(row['point_in_time_eligible'])


if __name__ == '__main__':
    unittest.main()
