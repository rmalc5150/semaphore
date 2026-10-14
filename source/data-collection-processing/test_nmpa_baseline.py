import json
from pathlib import Path
import tempfile
import unittest

from collection_storage import LocalStore, StorageSettings
import nmpa_baseline as baseline
from research_contract import ROOT, load_json


def page(number, pages, records, ids):
    rows = "".join(
        f'<tr><td>{registration}</td><td><a href="javascript:void(0)">Trial {registration}</a></td></tr>'
        for registration in ids)
    return (f'<table class="searchTable">{rows}</table>'
            f'当前第 {number} 页，共 {pages} 页，共 {records} 条记录')


class FakeClient:
    def __init__(self, documents):
        self.documents = list(documents)
        self.evidence = []
        self.urls = []

    def rendered(self, url, **kwargs):
        self.urls.append(url)
        return self.documents.pop(0)


class NMPABaselineTests(unittest.TestCase):
    def test_gateway_throttling_is_deferred_without_repeating_request(self):
        from unittest.mock import patch, Mock
        from regulatory_collection import EvidenceClient
        from decodo_scraping_api import ScrapeError
        client = EvidenceClient(self.store, 'nmpa_trials', sleeper=Mock())
        with patch('decodo_scraping_api.cached_token', return_value='secret'), patch(
                'decodo_scraping_api.scrape_content', side_effect=ScrapeError('gateway',429)) as fetch:
            result = baseline.inventory(self.store,self.settings,self.universe,
                self.taxonomy,self.day,max_pages=1,client=client)
        self.assertEqual(result['reason'],'scrape_gateway_http_429')
        self.assertEqual(fetch.call_count,1)
        manifest=json.loads(self.store.get(result['manifest']).body)
        self.assertEqual(manifest['record_count'],0)
        self.assertFalse(manifest['exhausted'])

    def test_trial_document_page_count_is_not_registry_pagination(self):
        document = ('<p>Protocol 第25页/共 72 页，共 12 条记录</p>' +
                    page(149, 1837, 36740, ['CTR20260001']))
        rows, pages, records = baseline.listing_page(document, 149)
        self.assertEqual((len(rows), pages, records), (1, 1837, 36740))

    def test_rendered_202_requires_exact_complete_page_and_preserves_evidence(self):
        from unittest.mock import patch, Mock
        from regulatory_collection import EvidenceClient
        document = page(1, 1, 2, ['CTR20260001', 'CTR20260002'])
        client = EvidenceClient(self.store, 'nmpa_trials', sleeper=Mock())
        with patch('decodo_scraping_api.cached_token', return_value='secret'), patch(
                'decodo_scraping_api.scrape', return_value={'results': [{'status_code': 202, 'content': document}]}) as fetch:
            result = baseline.inventory(self.store, self.settings, self.universe,
                self.taxonomy, self.day, max_pages=1, client=client)
        self.assertEqual((result['status'], result['records']), ('complete', 2))
        self.assertEqual(fetch.call_count, 1)
        self.assertNotIn('geo', fetch.call_args.kwargs['parameters'])
        self.assertNotIn('pending_validator', fetch.call_args.kwargs['parameters'])
        self.assertTrue(client.evidence)

    def test_rendered_202_shell_wrong_page_and_truncated_page_are_rejected(self):
        from unittest.mock import patch, Mock
        from regulatory_collection import EvidenceClient
        for document in ['<table class="searchTable"></table>',
                         page(2, 2, 21, ['CTR20260001']),
                         page(1, 1, 2, ['CTR20260001'])]:
            with self.subTest(document=document):
                client = EvidenceClient(self.store, 'nmpa_trials', sleeper=Mock())
                with patch('decodo_scraping_api.cached_token', return_value='secret'), patch(
                        'decodo_scraping_api.scrape', return_value={'results': [{'status_code': 202, 'content': document}]}) as fetch:
                    result = baseline.inventory(self.store, self.settings, self.universe,
                        self.taxonomy, self.day, max_pages=1, client=client)
                self.assertEqual(result['reason'], 'scrape_target_http_202')
                self.assertEqual(fetch.call_count, 4)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = LocalStore(self.temp.name)
        self.settings = StorageSettings(local_root=self.temp.name)
        self.universe = load_json(ROOT / "config/company-universe.v0.2.json")
        self.taxonomy = load_json(ROOT / "config/sectors.v1.json")
        self.day = __import__("datetime").date(2026, 9, 22)

    def test_inventory_resumes_and_deduplicates_shifted_page(self):
        first = baseline.inventory(self.store, self.settings, self.universe,
            self.taxonomy, self.day, max_pages=1,
            client=FakeClient([page(1, 2, 3, ["CTR20260001", "CTR20260002"])]))
        self.assertEqual(first["status"], "partial")
        second = baseline.inventory(self.store, self.settings, self.universe,
            self.taxonomy, self.day,
            client=FakeClient([page(2, 2, 3, ["CTR20260002", "CTR20260003"])]))
        self.assertEqual(second["status"], "complete")
        self.assertEqual(second["records"], 3)
        manifest = json.loads(self.store.get(second["manifest"]).body)
        self.assertEqual(manifest["duplicates_dropped"], 0)
        self.assertEqual(baseline.committed_ids(self.store, manifest),
                         {"CTR20260001", "CTR20260002", "CTR20260003"})

    def test_completed_inventory_builds_stable_cohorts(self):
        result = baseline.inventory(self.store, self.settings, self.universe,
            self.taxonomy, self.day,
            client=FakeClient([page(1, 1, 3,
                ["CTR20260003", "CTR20260001", "CTR20260002"])]))
        key, plan = baseline.build_plan(self.store, result["manifest"],
                                        self.universe, 2)
        self.assertEqual(plan["cohort_count"], 2)
        self.assertEqual(plan["cohorts"][0]["registration_ids"],
                         ["CTR20260001", "CTR20260002"])
        self.assertIsNotNone(self.store.get(key))

    def test_incomplete_inventory_cannot_be_planned(self):
        result = baseline.inventory(self.store, self.settings, self.universe,
            self.taxonomy, self.day, max_pages=1,
            client=FakeClient([page(1, 2, 3, ["CTR20260001"])]))
        with self.assertRaisesRegex(ValueError, "complete and exhausted"):
            baseline.build_plan(self.store, result["manifest"], self.universe, 2)


if __name__ == "__main__":
    unittest.main()
