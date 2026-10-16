from contextlib import redirect_stdout
from copy import deepcopy
from datetime import date
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from collection_storage import StorageSettings
from research_contract import ROOT, canonical_json, load_json, validate_record
import news_collection as news


def article(identity="one", stamp="2026-09-23T12:00:00Z"):
    return {"uuid": identity, "url": "https://example.org/" + identity,
        "title": "Battery research", "published_at": stamp,
        "entities": [{"name": "Unknown Private Company"}]}


def market(rows, page=1, limit=2, total=None):
    return {"meta": {"page": page, "limit": limit, "found": len(rows) if total is None else total,
                     "returned": len(rows)}, "data": rows}


class Response:
    def __init__(self, data): self.body = canonical_json(data)
    def __enter__(self): return self
    def __exit__(self, *args): return None
    def read(self, size): return self.body


class NewsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.settings = StorageSettings(local_root=str(self.root))
        self.store = self.settings.store()
        self.universe = load_json(ROOT / "examples/sec-filings/universe.json")
        self.taxonomy = load_json(ROOT / "config/sectors.v1.json")
        self.config = load_json(ROOT / "config/news-collection.json")
        self.target = news.targets(self.config, self.universe, ["energy_storage"], [])[0]
        self.calls = []
        self.pages = {1: market([article()])}
        def opener(request, **kwargs):
            self.calls.append(request)
            from urllib.parse import parse_qs, urlsplit
            params = json.loads(request.data) if request.data else parse_qs(urlsplit(request.full_url).query)
            page = params["page"] if request.data else int(params["page"][0])
            value = self.pages[page]
            if isinstance(value, Exception): raise value
            return Response(value)
        self.opener = opener
        self.client = news.NewsClient(self.store, "marketaux", "SECRET_TOKEN_12345", 40,
                                     max_requests=12, opener=opener, sleeper=lambda _: None, capture_full_text=False)

    def collect(self, **kwargs):
        return news.collect(self.store, self.settings, self.universe, self.taxonomy,
            self.config, kwargs.pop("provider", "marketaux"), self.target,
            kwargs.pop("language", None), kwargs.pop("start", date(2026, 9, 23)),
            kwargs.pop("end", date(2026, 9, 24)), kwargs.pop("mode", "daily"),
            kwargs.pop("client", self.client), **kwargs)

    def rows(self, result):
        manifest = json.loads(self.store.get(result["manifest"]).body)
        return [json.loads(line) for p in manifest["pages"] for b in p["batches"] for line in self.store.get(b["key"]).body.splitlines()]

    def test_daily_shared_record_evidence_and_unresolved_identity(self):
        result = self.collect()
        self.assertEqual(result["status"], "complete")
        row, = self.rows(result)
        self.assertEqual(validate_record(row, self.universe), [])
        self.assertEqual(row["company_ids"], [])
        self.assertEqual(row["payload"]["candidate_sector_ids"], ["energy_storage"])
        self.assertIsNone(row["available_at"])
        self.assertEqual(len(row["payload"]["source_evidence"]), 2)
        self.assertNotIn("SECRET_TOKEN", json.dumps(row))
        self.assertEqual(self.collect()["already_complete"], True)
        self.assertEqual(len(self.calls), 1)

    def test_plan_capped_page_size_resumes_and_rechecks_previous_page(self):
        self.pages = {1: market([article("one"), article("two")], total=3),
                      2: market([article("three")], page=2, total=3)}
        first = self.collect(max_pages=1)
        self.assertEqual(first["reason"], "page_limit")
        second = self.collect(max_pages=1)
        self.assertEqual(second["status"], "complete")
        self.assertEqual(len(self.rows(second)), 3)
        self.assertEqual(len(self.calls), 3)

    def test_changed_page_on_resume_fails_without_advancing(self):
        self.pages[1] = market([article("one"), article("two")], total=3)
        self.collect(max_pages=1)
        self.pages[1] = market([article("new"), article("two")], total=3)
        result = self.collect()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "news_source_changed_refresh_required")
        self.assertEqual(len(self.rows(result)), 2)

    def test_duplicate_ids_do_not_create_false_complete_window(self):
        self.pages = {1: market([article("one"), article("two")], total=3),
                      2: market([article("one")], page=2, total=3)}
        result = self.collect()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "news_duplicate_page_refresh_required")

    def test_historical_unknown_entitlement_does_not_make_network_call(self):
        result = self.collect(mode="historical", start=date(2015, 1, 1), end=date(2015, 2, 1))
        self.assertEqual(result["reason"], "history_entitlement_unverified")
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(self.calls), 0)

    def test_empty_historical_probe_never_claims_coverage(self):
        self.pages[1] = market([])
        result = self.collect(mode="historical", start=date(2015, 1, 1), end=date(2015, 2, 1), probe_history=True)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["reason"], "history_entitlement_unverified")
        self.assertEqual(len(self.calls), 1)

    def test_documented_history_boundary_and_valid_complete_history(self):
        pc = self.config["providers"]["marketaux"]
        pc.update(history_start="2020-01-01", history_evidence="documented fixture entitlement")
        old = self.collect(mode="historical", start=date(2015, 1, 1), end=date(2015, 2, 1))
        self.assertEqual(old["reason"], "provider_history_unavailable")
        self.assertEqual(len(self.calls), 0)
        self.assertEqual(self.collect(mode="historical")["status"], "complete")

    def test_observed_marketaux_archive_preserves_older_gap(self):
        self.config = load_json(ROOT / "config/news-history-marketaux.json")
        old = self.collect(mode="historical", start=date(2015, 1, 1), end=date(2015, 2, 1))
        self.assertEqual(old["reason"], "history_before_observed_archive_boundary")
        self.assertEqual(old["status"], "partial")
        self.assertEqual(self.calls, [])
        self.pages[1] = market([article(stamp="2021-01-01T12:00:00Z")])
        result = self.collect(mode="historical", start=date(2021, 1, 1), end=date(2021, 1, 2))
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(self.rows(result)), 1)

    def test_archive_probe_rejects_ignored_date_filters(self):
        from marketaux_history_probe import probe
        self.pages[1] = market([article(stamp="2026-09-23T12:00:00Z")])
        with self.assertRaisesRegex(news.SourceIssue, "date_filter_not_respected"):
            probe(self.client, date(2015, 1, 1), date(2016, 1, 1))

    def test_archive_probe_uses_no_sector_company_or_language_filter(self):
        from marketaux_history_probe import probe
        from urllib.parse import parse_qs, urlsplit
        self.pages[1] = market([article(stamp="2021-01-01T12:00:00Z")])
        result = probe(self.client, date(2021, 1, 1), date(2021, 1, 2))
        self.assertEqual(result["status"], "historical_articles_returned")
        params = parse_qs(urlsplit(self.calls[0].full_url).query)
        self.assertFalse({"search", "symbols", "language", "countries"}.intersection(params))
        self.assertEqual(params["group_similar"], ["false"])

    def test_exclusive_end_filtered_but_raw_evidence_retained(self):
        self.pages[1] = market([article(), article("boundary", "2026-09-24T00:00:00Z")])
        result = self.collect()
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(self.rows(result)), 1)
        evidence = self.rows(result)[0]["payload"]["source_evidence"][0]
        self.assertIn(b"boundary", self.store.get(evidence["key"]).body)

    def test_ignored_date_filters_and_missing_timestamps_fail(self):
        self.pages[1] = market([article(stamp="2020-01-01T00:00:00Z")])
        self.assertEqual(self.collect()["reason"], "news_date_filter_ignored")

    def test_empty_error_and_truncated_pages_never_complete(self):
        for data in ({"error": {"code": "quota"}}, {"meta": {"page": 1}}, market([], total=3)):
            with self.subTest(data=data):
                self.pages[1] = data
                self.assertEqual(self.collect()["status"], "failed")

    def test_429_is_partial_and_never_echoes_private_error(self):
        self.pages[1] = HTTPError("https://x?token=SECRET_TOKEN_12345", 429,
            "SECRET_TOKEN_12345", {}, io.BytesIO(b"SECRET_TOKEN_12345"))
        result = self.collect()
        self.assertEqual(result["status"], "partial")
        self.assertNotIn("SECRET_TOKEN", json.dumps(result))
        self.assertEqual(len(self.calls), 1)

    def test_credentials_echoed_by_provider_are_not_saved(self):
        self.pages[1]["echo"] = "SECRET_TOKEN_12345"
        self.assertEqual(self.collect()["reason"], "news_response_contains_credential")
        self.assertFalse((self.root / "source_documents").exists())

    def test_request_budgets_count_transport_attempts_and_defer(self):
        self.client.remaining = 0
        result = self.collect()
        self.assertEqual(result["reason"], "run_request_budget_reached")
        self.assertEqual(len(self.calls), 0)
        self.client.remaining = 12
        self.client.cap = 1
        self.pages[1] = HTTPError("https://x", 503, "bad", {}, io.BytesIO())
        result = self.collect()
        self.assertEqual(result["reason"], "daily_request_budget_reached")
        self.assertEqual(len(self.calls), 1)

    def test_finlight_explicit_chinese_language_and_empty_terminal_page(self):
        self.pages = {1: {"status": "ok", "page": 1, "pageSize": 1,
            "articles": [{"link": "https://example.org/zh", "publishDate": "2026-09-23T12:00:00Z", "title": "储能"}]},
            2: {"status": "ok", "page": 2, "pageSize": 0, "articles": []}}
        client = news.NewsClient(self.store, "finlight", "SECRET_TOKEN_12345", 40, opener=self.opener, sleeper=lambda _: None, capture_full_text=False)
        result = self.collect(provider="finlight", language="zh", client=client)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(self.rows(result)), 1)
        self.assertEqual(json.loads(self.calls[0].data)["language"], "zh")
        self.assertEqual(json.loads(self.calls[0].data)["orderBy"], "publishDate")

    def test_finlight_pro_light_old_history_is_explicitly_unavailable(self):
        client = news.NewsClient(self.store, "finlight", "SECRET_TOKEN_12345", 40, opener=self.opener, sleeper=lambda _: None, capture_full_text=False)
        result = self.collect(provider="finlight", language="en", client=client,
            mode="historical", start=date(2015, 1, 1), end=date(2015, 2, 1), probe_history=True)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["reason"], "provider_history_unavailable")
        self.assertEqual(self.calls, [])

    def test_finlight_short_page_is_not_a_false_end(self):
        rows, limit, total, done = news.page_info("finlight",
            {"status": "ok", "page": 1, "pageSize": 1, "articles": [{"link": "x"}]}, 1, 100)
        self.assertFalse(done)
        self.assertEqual(limit, 100)

    def test_audit_validates_partial_batches_and_empty_evidence(self):
        from news_audit import audit
        self.pages[1] = market([article("one"), article("two")], total=3)
        result = self.collect(max_pages=1)
        checked = audit(self.store, {"results": [result]})
        self.assertEqual(checked["records_verified"], 2)
        self.assertEqual(checked["results"][0]["status"], "partial")
        manifest = json.loads(self.store.get(result["manifest"]).body)
        key = manifest["pages"][0]["batches"][0]["key"]
        obj = self.store.get(key)
        self.store.put(key, b"corrupt", obj.token)
        with self.assertRaises(news.SourceIssue):
            audit(self.store, {"results": [result]})

    def test_source_total_drift_and_result_cap(self):
        self.pages = {1: market([article("one"), article("two")], total=3),
                      2: market([article("three")], page=2, total=4)}
        self.assertEqual(self.collect()["reason"], "news_source_changed_refresh_required")
        with self.assertRaises(news.SourceIssue):
            news.page_info("marketaux", market([], page=1, total=20001), 1, 100)

    def test_all_sectors_storage_categories_and_company_candidates(self):
        targets = news.targets(self.config, self.universe, [], [])
        self.assertEqual({s for t in targets for s in t["sector_ids"]}, {"biotech", "robotics", "semiconductors", "energy_storage"})
        self.assertTrue({"thermal storage", "flywheel", "hydrogen storage", "supercapacitor"} <= set(self.target["terms"]))
        company = next(c for c in self.universe["companies"] if c["collection_enabled"])
        target, = news.targets(self.config, self.universe, [], [company["company_id"]])
        self.assertIn(company["canonical_name"], target["terms"])
        self.assertEqual(target["company_ids"], [company["company_id"]])

    def test_athena_deduplicates_query_hits_without_inventing_article_revisions(self):
        import news_athena
        import pyarrow.parquet as pq
        first = self.collect()
        self.target = news.targets(self.config, self.universe, ["robotics"], [])[0]
        second = self.collect()
        with redirect_stdout(io.StringIO()):
            root = news_athena.prepare(self.store, self.settings, load_json(ROOT / "config/news-athena.json"),
                [first["manifest"], second["manifest"]], self.root / "curated")
        report = load_json(root / "release.json")
        self.assertEqual(report["files"]["news_articles"]["rows"], 1)
        self.assertEqual(report["files"]["news_observations"]["rows"], 2)
        row, = pq.read_table(root / report["files"]["news_articles"]["path"]).to_pylist()
        self.assertEqual(row["version_count"], 1)
        self.assertEqual(row["candidate_sector_ids"], ["energy_storage", "robotics"])
        self.assertFalse(row["point_in_time_eligible"])
        self.assertIsNone(row["available_at"])

    def test_athena_rejects_partial_and_preserves_real_revisions(self):
        import news_athena
        self.pages[1] = market([article("one"), article("two")], total=3)
        partial = self.collect(max_pages=1)
        with self.assertRaises(ValueError):
            news_athena.prepare(self.store, self.settings, load_json(ROOT / "config/news-athena.json"),
                [partial["manifest"]], self.root / "curated")
        self.pages[1] = market([article()])
        first = self.collect(refresh=True)
        self.pages[1]["data"][0]["title"] = "Corrected title"
        second = self.collect(refresh=True)
        with redirect_stdout(io.StringIO()):
            root = news_athena.prepare(self.store, self.settings, load_json(ROOT / "config/news-athena.json"),
                [first["manifest"], second["manifest"]], self.root / "curated")
        import pyarrow.parquet as pq
        report = load_json(root / "release.json")
        row, = pq.read_table(root / report["files"]["news_articles"]["path"]).to_pylist()
        self.assertEqual(row["version_count"], 2)
        self.assertEqual(row["title"], "Corrected title")


if __name__ == "__main__":
    unittest.main()
