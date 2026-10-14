"""Offline patent source, provenance, checkpoint and classification tests."""
from copy import deepcopy
from datetime import date
import io
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError

from collection_storage import StorageSettings
from research_contract import ROOT, load_json
import patent_collection as pc
import patent_landscape


class FakeODP:
    def __init__(self, store, rows, total=None):
        self.store, self.rows, self.total = store, rows, total
        self.evidence, self.calls = [], []

    def search(self, query):
        self.calls.append(query)
        offset, limit = query["pagination"]["offset"], query["pagination"]["limit"]
        rows = self.rows[offset:offset + limit]
        result = {"count": len(self.rows) if self.total is None else self.total, "patentFileWrapperDataBag": rows}
        client = pc.EvidenceClient(self.store, "uspto_odp")
        client.save(json.dumps(result).encode(), pc.SEARCH_URL)
        self.evidence = client.evidence
        return result


def odp(number="16123456", filing="2025-01-06", updated="2025-01-06T12:00:00"):
    return {"applicationNumberText": number, "lastIngestionDateTime": updated,
        "applicationMetaData": {"filingDate": filing, "inventionTitle": "Robot manipulator",
            "firstApplicantName": "Example Biotech, Inc.", "cpcClassificationBag": ["B25J 9/00"]}}


class PatentCollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = StorageSettings(local_root=self.temp.name + "/store")
        self.store = self.settings.store()
        self.universe = load_json(ROOT / "examples/sec-filings/universe.json")
        self.taxonomy = load_json(ROOT / "config/sectors.v1.json")
        self.rules = load_json(pc.RULES_PATH)
        self.start, self.end = date(2025, 1, 6), date(2025, 1, 7)

    def collect(self, rows, **kwargs):
        client = kwargs.pop("client", FakeODP(self.store, rows))
        result = pc.collect_uspto(self.store, self.settings, self.universe, self.taxonomy,
            self.start, self.end, kwargs.pop("mode", "historical"), client=client, **kwargs)
        return result, client

    def records(self, result):
        manifest = json.loads(self.store.get(result["manifest"]).body)
        return [json.loads(line) for p in manifest["pages"] for b in p["batches"]
                for line in self.store.get(b["key"]).body.splitlines()]

    def export(self, rows, **kwargs):
        path = Path(self.temp.name) / "export.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        return pc.import_export(self.store, self.settings, self.universe, self.taxonomy,
            path, self.start, self.end, **kwargs)

    def test_partial_resume_and_completed_skip(self):
        rows = [odp("16123456"), odp("16123457"), odp("16123458")]
        partial, _ = self.collect(rows, page_size=1, max_pages=1)
        self.assertEqual(partial["status"], "partial")
        done, client = self.collect(rows, page_size=1, max_pages=3)
        self.assertEqual(done["records"], 3)
        self.assertEqual(client.calls[0]["pagination"]["offset"], 1)
        skipped, client = self.collect(rows, page_size=1)
        self.assertTrue(skipped["already_complete"])
        self.assertEqual(client.calls, [])

    def test_413_reduces_page_at_same_offset_and_resumes_without_duplicates(self):
        rows = [odp(str(16123456 + i)) for i in range(9)]
        first, _ = self.collect(rows, page_size=4, max_pages=1)
        client = FakeODP(self.store, rows)
        original = client.search
        requests = []
        def limited(query):
            requests.append(dict(query['pagination']))
            if query['pagination']['limit'] > 2:
                raise pc.SourceIssue('source_http_413')
            return original(query)
        client.search = limited
        partial, _ = self.collect(rows, client=client, page_size=4, max_pages=2)
        self.assertEqual(partial['reason'], 'page_limit')
        self.assertEqual(partial['pages_requested'], 2)
        self.assertEqual(requests, [{'offset': 4, 'limit': 4}, {'offset': 4, 'limit': 2}])
        resumed = FakeODP(self.store, rows)
        complete, _ = self.collect(rows, client=resumed, page_size=4, max_pages=2)
        self.assertEqual(complete['status'], 'complete')
        self.assertEqual(resumed.calls[0]['pagination'], {'offset': 6, 'limit': 2})
        self.assertEqual(len(self.records(complete)), 9)
        self.assertEqual(len({r['source_record_id'] for r in self.records(complete)}), 9)
        self.assertEqual(json.loads(self.store.get(first['manifest']).body)['task_id'],
                         json.loads(self.store.get(complete['manifest']).body)['task_id'])

    def test_413_at_single_record_stops_without_skipping_or_looping(self):
        client = FakeODP(self.store, [])
        def rejected(query):
            client.calls.append(query)
            raise pc.SourceIssue('source_http_413')
        client.search = rejected
        result, _ = self.collect([], client=client, page_size=4, max_pages=10)
        self.assertEqual((result['status'], result['reason'], result['pages_requested']),
                         ('failed', 'source_http_413', 3))
        self.assertEqual([q['pagination']['limit'] for q in client.calls], [4, 2, 1])
        self.assertEqual(result['records'], 0)

    def test_company_sector_separate_from_patent_technology_and_no_ownership_claim(self):
        result, _ = self.collect([odp()])
        record = self.records(result)[0]
        self.assertEqual(record["company_ids"], [])
        self.assertEqual(record["payload"]["candidate_sector_ids"], ["biotech"])
        self.assertEqual(record["payload"]["technology_classifications"][0]["sector_id"], "robotics")
        self.assertIsNone(record["event_at"])
        self.assertIsNone(record["available_at"])
        self.assertTrue(record["payload"]["source_evidence"])

    def partition_client(self, rows):
        client = FakeODP(self.store, rows)
        original = client.search
        def search(query):
            lower, upper = query['q'].split('[')[1][:-1].split(' TO ')
            client.rows = sorted((r for r in rows if lower <= r['lastIngestionDateTime'] < upper),
                                 key=lambda r: r['applicationNumberText'])
            return original(query)
        client.search = search
        return client

    def partitioned(self, client, **kwargs):
        return pc.collect_uspto_partitioned(self.store, self.settings, self.universe,
            self.taxonomy, self.start, self.end, client=client, **kwargs)

    def test_partitioned_budget_resume_boundaries_and_completion(self):
        rows = [odp('16123456', updated='2025-01-06T00:00:00'),
                odp('16123457', updated='2025-01-06T01:00:00'),
                odp('16123458', updated='2025-01-07T00:00:00')]
        client = self.partition_client(rows)
        first = self.partitioned(client, max_pages=1)
        self.assertEqual((first['reason'], first['records']), ('page_limit', 1))
        result = self.partitioned(client, max_pages=23)
        self.assertEqual((result['status'], result['records']), ('complete', 2))
        self.assertEqual(len(client.calls), 24)
        self.assertEqual(len(self.records(result)), 2)
        self.assertTrue(all(r['payload']['partition_manifest'] for r in self.records(result)))
        self.assertTrue(self.partitioned(client)['already_complete'])
        self.assertEqual(len(client.calls), 24)
        self.partitioned(client, max_pages=1, refresh=True)
        self.assertEqual(len(client.calls), 25)
        self.assertIn('T00:00:00', client.calls[-1]['q'])

    def test_changed_hour_restarts_without_refetching_completed_hours(self):
        rows = [odp('16123456', updated='2025-01-06T00:00:00'),
                odp('16123457', updated='2025-01-06T01:00:00'),
                odp('16123458', updated='2025-01-06T01:05:00')]
        client = self.partition_client(rows)
        self.partitioned(client, page_size=1, max_pages=2)
        rows.append(odp('16123459', updated='2025-01-06T01:10:00'))
        drift = self.partitioned(client, page_size=1, max_pages=30)
        self.assertEqual(drift['reason'], 'source_changed_refresh_required')
        self.assertEqual(drift['partition_hour'], 1)
        result = self.partitioned(client, page_size=1, max_pages=30)
        self.assertEqual((result['status'], result['records']), ('complete', 4))
        self.assertEqual(sum('T00:00:00 TO' in q['q'] for q in client.calls), 1)
        self.assertEqual([q['pagination']['offset'] for q in client.calls[:4]], [0, 0, 1, 0])

    def test_adaptive_split_preserves_completed_subranges_after_further_drift(self):
        rows = [odp('16123456', updated='2025-01-06T00:00:00'),
                odp('16123457', updated='2025-01-06T01:05:00'),
                odp('16123458', updated='2025-01-06T01:45:00'),
                odp('16123459', updated='2025-01-06T01:46:00')]
        client = self.partition_client(rows)
        self.partitioned(client, page_size=1, max_pages=2)
        rows.append(odp('16123460', updated='2025-01-06T01:47:00'))
        self.assertEqual(self.partitioned(client, page_size=1, max_pages=30)['reason'],
                         'source_changed_refresh_required')
        split = self.partitioned(client, page_size=1, max_pages=2)
        self.assertEqual(split['reason'], 'page_limit')
        rows.append(odp('16123461', updated='2025-01-06T01:48:00'))
        self.assertEqual(self.partitioned(client, page_size=1, max_pages=30)['reason'],
                         'source_changed_refresh_required')
        result = self.partitioned(client, page_size=1, max_pages=30)
        self.assertEqual((result['status'], result['records']), ('complete', 6))
        queries = [q['q'] for q in client.calls]
        self.assertEqual(sum('T01:00:00 TO 2025-01-06T01:30:00}' in q for q in queries), 1)
        self.assertTrue(any('T01:45:00 TO 2025-01-06T02:00:00}' in q for q in queries))
        self.assertEqual(len({r['source_record_id'] for r in self.records(result)}), 6)

    def test_partition_ignored_filter_never_commits(self):
        result = self.partitioned(FakeODP(self.store, [odp()]), max_pages=30)
        self.assertEqual(result['reason'], 'source_ignored_partition_filter')
        self.assertEqual(result['records'], 0)

    def test_parent_resumes_completed_child_after_commit_interruption(self):
        from unittest.mock import patch
        client = self.partition_client([odp(updated='2025-01-06T00:00:00')])
        original = pc.CollectionRun.commit_page
        def commit(run, *args, **kwargs):
            if run.spec['scope'].get('partition_strategy'):
                raise RuntimeError('interrupted parent')
            return original(run, *args, **kwargs)
        with patch.object(pc.CollectionRun, 'commit_page', commit):
            with self.assertRaises(RuntimeError):
                self.partitioned(client, max_pages=1)
        result = self.partitioned(client, max_pages=23)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(len(client.calls), 24)

    def test_parent_recovers_after_last_page_before_final_manifest(self):
        from unittest.mock import patch
        client = self.partition_client([])
        original = pc.outcome
        def finish(run, status, reason=None):
            if run.spec['scope'].get('partition_strategy') and status == 'complete':
                raise RuntimeError('interrupted finalization')
            return original(run, status, reason)
        with patch.object(pc, 'outcome', finish):
            with self.assertRaises(RuntimeError):
                self.partitioned(client, max_pages=24)
        result = self.partitioned(client, max_pages=1)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(len(client.calls), 24)

    def test_daily_catches_old_filings_by_ingestion_date(self):
        result, client = self.collect([odp(filing="2003-01-01")], mode="daily")
        self.assertEqual(result["status"], "complete")
        self.assertIn("lastIngestionDateTime:[2025-01-06T00:00:00 TO 2025-01-07T00:00:00}", client.calls[0]["q"])

    def test_ignored_filter_and_exclusive_end_fail(self):
        for filing in ("2024-01-01", "2025-01-07"):
            with self.subTest(filing=filing):
                result, _ = self.collect([odp(filing=filing)], refresh=True)
                self.assertEqual(result["reason"], "source_ignored_date_filter")
                self.assertEqual(result["records"], 0)

    def test_drifting_total_requires_refresh(self):
        self.collect([odp(), odp("16123457")], page_size=1, max_pages=1)
        result, _ = self.collect([odp(), odp("16123457"), odp("16123458")], page_size=1)
        self.assertEqual(result["reason"], "source_changed_refresh_required")
        self.assertEqual(result["status"], "partial")

    def test_duplicate_or_nonmonotonic_page_fails(self):
        result, _ = self.collect([odp(), odp()])
        self.assertEqual(result["reason"], "nonmonotonic_pagination")
        self.assertEqual(result["records"], 0)

    def test_short_page_cannot_be_complete(self):
        client = FakeODP(self.store, [odp()], total=5)
        result, _ = self.collect([], client=client)
        self.assertEqual(result["reason"], "incomplete_page")

    def test_empty_source_complete(self):
        result, _ = self.collect([])
        self.assertEqual((result["status"], result["records"]), ("complete", 0))

    def test_pct_identifiers_are_retained(self):
        result, _ = self.collect([odp("PCTUS2025010385")])
        self.assertEqual(result["status"], "complete")
        data = self.records(result)[0]["payload"]["data"]
        self.assertEqual(data["application_number"], "PCTUS2025010385")
        self.assertEqual(data["country_code"], "WO")

    def test_review_verifies_evidence_and_rejects_partial(self):
        from patent_review import review
        result, _ = self.collect([odp(), odp("16123457")], page_size=1, max_pages=1)
        with self.assertRaises(ValueError):
            review(self.store, [result["manifest"]])
        result, _ = self.collect([odp(), odp("16123457")], page_size=1)
        report = review(self.store, [result["manifest"]])
        self.assertEqual(report["observations"], 2)
        self.assertEqual(report["point_in_time_eligible"], 0)
        evidence = self.records(result)[0]["payload"]["source_evidence"][0]
        target = Path(self.settings.local_root) / evidence["key"]
        target.write_bytes(b"tampered")
        with self.assertRaises(ValueError):
            review(self.store, [result["manifest"]])

    def test_global_query_parameters_use_current_universe_and_cost_ceiling(self):
        from patent_query_plan import build
        result = build(self.universe, self.rules, self.start, self.end, 1000000)
        config = result["configuration"]
        self.assertTrue(config["dryRun"])
        self.assertEqual(config["query"]["maximumBytesBilled"], "1000000")
        params = {p["name"]:p["parameterValue"] for p in config["query"]["queryParameters"]}
        names = [v["value"] for v in params["company_names"]["arrayValues"]]
        self.assertIn("example biotech", names)
        self.assertNotIn("moderna", names)
        terms = [v["value"] for v in params["technology_terms"]["arrayValues"]]
        self.assertIn("hydrogen storage", terms)
        self.assertIn("thermal energy storage", terms)

    def test_all_storage_categories_and_canonical_sectors(self):
        cases = {"thermal energy storage": "thermal_storage", "flywheel": "mechanical_storage",
            "hydrogen storage": "hydrogen_storage", "supercapacitor": "supercapacitors", "battery": "batteries"}
        for title, category in cases.items():
            result = pc.classify({"title": title}, self.rules)
            self.assertTrue(any(r["category"] == category and r["sector_id"] == "energy_storage" for r in result))
        self.assertEqual(pc.classify({"title": "A wafer"}, self.rules)[0]["sector_id"], "semiconductors")
        self.assertEqual(pc.classify({"title": "Internal display"}, self.rules), [])

    def test_unicode_and_empty_name_matching(self):
        self.assertEqual(patent_landscape.normalize_org("宁德时代"), "宁德时代")
        self.assertNotEqual(patent_landscape.normalize_org("宁德时代"), patent_landscape.normalize_org("比亚迪"))
        self.assertEqual(patent_landscape.match_companies([""], [{"normalized_aliases": [""]}]), [])

    def test_export_deduplicates_rows_preserves_evidence_and_unknown_dates(self):
        row = {"publication_number": "CN-123456-A", "filing_date": "2025-01-06", "assignees": ["Unknown company"],
               "matched_company": "Example Biotech", "title": "Battery"}
        result = self.export([row, row])
        record = self.records(result)[0]
        self.assertEqual(result["records"], 1)
        self.assertEqual(record["payload"]["candidate_company_ids"], [])
        self.assertIsNone(record["payload"]["data"]["publication_date"])
        self.assertIsNone(record["available_at"])
        self.assertIsNone(record["payload"]["source_evidence"][0]["retrieved_at"])

    def test_conflicting_export_rows_not_silently_overwritten(self):
        row = {"publication_number": "CN-123456-A", "filing_date": "2025-01-06", "title": "First title"}
        result = self.export([row, dict(row, title="Corrected title")])
        records = self.records(result)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["record_id"], records[1]["record_id"])
        self.assertNotEqual(records[0]["payload_hash"], records[1]["payload_hash"])

    def test_import_resume(self):
        rows = [{"publication_number": f"CN-{i}-A", "filing_date": "2025-01-06"} for i in range(3)]
        partial = self.export(rows, page_size=1, max_pages=1)
        self.assertEqual(partial["status"], "partial")
        complete = self.export(rows, page_size=1, max_pages=5)
        self.assertEqual(complete["records"], 3)

    def test_invalid_export_dates_rejected_before_run(self):
        for field in (None, "2025-02-30", "2025-01-07"):
            with self.assertRaises((ValueError, pc.SourceIssue)):
                self.export([{"publication_number": "CN-1-A", "filing_date": field}])
        self.assertFalse(list(Path(self.settings.local_root).glob("manifests/collection_runs/**/*")))

    def test_changed_rules_change_task_identity(self):
        first, _ = self.collect([odp()])
        rules = deepcopy(self.rules)
        rules["version"] = "test-version"
        second, client = self.collect([odp()], rules=rules)
        self.assertNotEqual(first["manifest"], second["manifest"])
        self.assertEqual(len(client.calls), 1)

    def test_client_credentials_only_in_header_and_exact_empty_response(self):
        calls = []
        class Response(io.BytesIO):
            headers = {}
        def opener(request, timeout):
            calls.append(request)
            return Response(b'{"count":0,"patentFileWrapperDataBag":[]}')
        client = pc.ODPClient(self.store, key_loader=lambda: "test-secret", opener=opener, sleeper=lambda _: None)
        client.search({"q": "test"})
        self.assertEqual(calls[0].get_header("X-api-key"), "test-secret")
        self.assertNotIn("test-secret", str(client.evidence))
        for p in Path(self.settings.local_root).rglob("*"):
            if p.is_file():
                self.assertNotIn(b"test-secret", p.read_bytes())
        def missing(request, timeout):
            raise HTTPError(pc.SEARCH_URL, 404, "Not Found", {}, io.BytesIO(b'{"message":"unknown route"}'))
        client.opener = missing
        with self.assertRaises(pc.SourceIssue) as exc:
            client.search({"q": "test"})
        self.assertEqual(exc.exception.code, "source_http_404")


if __name__ == "__main__":
    unittest.main()
