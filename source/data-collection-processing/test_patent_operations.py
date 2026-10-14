"""Exercise scheduler recovery with real local manifests and fake providers."""
from copy import deepcopy
from datetime import date, timedelta
import json
import tempfile
import unittest
from unittest.mock import patch

from collection_storage import StorageSettings
from research_contract import ROOT, load_json
from test_patent_collection import FakeODP, odp
from patent_operations import PatentOperations, load_stored, monitor_global


class PatentOperationsTests(unittest.TestCase):
    def setUp(self):
        # Fixed baseline day: reconciliation tests advance the clock explicitly.
        for target in ("patent_operations.now", "collection_operations.now"):
            clock = patch(target, return_value="2026-09-23T12:00:00Z")
            clock.start()
            self.addCleanup(clock.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = StorageSettings(local_root=self.temp.name)
        self.store = self.settings.store()
        self.config = {**load_json(ROOT / "config/patent-operations.json"), "page_size": 1, "max_pages": 1, "daily_partition_strategy": None}
        self.universe = load_json(ROOT / "examples/sec-filings/universe.json")
        self.taxonomy = load_json(ROOT / "config/sectors.v1.json")
        self.client = FakeODP(self.store, [odp(), odp("16123457")])
        self.ops = PatentOperations(self.store, self.settings, self.config, self.universe, self.taxonomy, self.client)
        self.start, self.end = date(2025, 1, 6), date(2025, 1, 7)

    def run_daily(self, **kwargs):
        return self.ops.run(["uspto"], "daily", self.start, self.end, 1, **kwargs)

    def test_partitioned_scheduler_preserves_stream_and_verifies_completed_day(self):
        from test_patent_collection import PatentCollectionTests
        identity = self.ops.identity
        self.config['daily_partition_strategy'] = 'hourly-v1'
        self.config['max_pages'] = 30
        rows = [odp(updated='2025-01-06T00:00:00')]
        helper = PatentCollectionTests()
        helper.store = self.store
        self.ops.client = helper.partition_client(rows)
        self.assertEqual(self.ops.identity, identity)
        result = self.run_daily()
        self.assertEqual(result['sources']['uspto']['next_date'], str(self.end))
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(len(self.ops.client.calls), 24)
        self.assertEqual(self.run_daily()['status'], 'complete')
        self.assertEqual(len(self.ops.client.calls), 24)

    def test_partial_does_not_advance_and_resumes_exact_offset(self):
        first = self.run_daily()
        self.assertEqual(first["sources"]["uspto"]["next_date"], str(self.start))
        second = self.run_daily()
        self.assertEqual(second["sources"]["uspto"]["next_date"], str(self.end))
        self.assertEqual([c["pagination"]["offset"] for c in self.client.calls], [0, 1])
        self.assertEqual(self.run_daily()["status"], "complete")
        self.assertEqual(len(self.client.calls), 2)

    def test_changed_count_restart_is_bounded_and_retains_old_manifest(self):
        first = self.run_daily()["sources"]["uspto"]["windows"][0]
        self.client.rows.append(odp("16123458"))
        drift = self.run_daily()["sources"]["uspto"]["windows"][0]
        self.assertEqual(drift["reason"], "source_changed_refresh_required")
        self.run_daily()  # restart offset zero
        self.assertEqual(self.client.calls[-1]["pagination"]["offset"], 0)
        self.assertIsNotNone(self.store.get(first["manifest"]))
        self.client.rows.append(odp("16123459"))
        self.run_daily()  # drift again
        calls = len(self.client.calls)
        self.run_daily()  # cannot restart twice inside cooldown, nor retry invalid cursor
        self.assertEqual(len(self.client.calls), calls)
        self.assertEqual(self.client.calls[-1]["pagination"]["offset"], 1)

    def test_changed_source_restarts_after_six_hour_cooldown(self):
        self.config['source_change_restart_hours'] = 6
        self.run_daily()
        self.client.rows.append(odp('16123458'))
        self.run_daily()
        self.run_daily()
        self.client.rows.append(odp('16123459'))
        self.run_daily()
        with patch('patent_operations.now', return_value='2026-09-23T18:00:00Z'):
            self.run_daily()
        self.assertEqual(self.client.calls[-1]['pagination']['offset'], 0)

    def test_refresh_partial_resumes_without_repeated_restart(self):
        self.run_daily()
        self.run_daily()
        with patch("patent_operations.now", return_value="2026-09-24T12:00:00Z"):
            first = self.run_daily(reconcile_days=1)
            self.assertEqual(first["status"], "partial")
            second = self.run_daily(reconcile_days=1)
            self.assertEqual(second["status"], "complete")
        self.assertEqual([c["pagination"]["offset"] for c in self.client.calls], [0, 1, 0, 1])

    def test_completed_same_day_is_not_repeated_by_hourly_timer(self):
        self.run_daily()
        self.run_daily()
        self.run_daily(reconcile_days=1)
        self.run_daily(reconcile_days=1)
        self.assertEqual(len(self.client.calls), 2)

    def test_reconciliation_budget_does_not_starve_second_day(self):
        original = self.client.search
        def search(query):
            day = query["q"].split("[")[1][:10]
            self.client.rows = [odp(updated=day + "T12:00:00")]
            return original(query)
        self.client.search = search
        end = self.end + timedelta(days=1)
        self.ops.run(["uspto"], "daily", self.start, end, 2)
        with patch("patent_operations.now", return_value="2026-09-24T12:00:00Z"), patch("collection_operations.now", return_value="2026-09-24T12:00:00Z"):
            first = self.ops.run(["uspto"], "daily", self.start, end, 1, 2)
            self.assertEqual(first["sources"]["uspto"]["pending_reconciliation_dates"], [str(self.end)])
            self.assertEqual(first["status"], "partial")
            second = self.ops.run(["uspto"], "daily", self.start, end, 1, 2)
            self.assertEqual(second["status"], "complete")
            self.ops.run(["uspto"], "daily", self.start, end, 1, 2)
        self.assertEqual(len(self.client.calls), 4)

    def test_manifest_from_another_universe_or_page_size_rejected(self):
        self.run_daily()
        result = self.run_daily()["sources"]["uspto"]["windows"][0]
        self.assertTrue(self.ops.completed(result, "uspto", self.start, self.end, "daily"))
        other = PatentOperations(self.store, self.settings, {**self.config, "page_size": 2}, self.universe, self.taxonomy)
        self.assertNotEqual(other.identity, self.ops.identity)
        self.assertFalse(other.completed(result, "uspto", self.start, self.end, "daily"))
        universe = deepcopy(self.universe)
        universe["universe_version"] = "9.0.0"
        other = PatentOperations(self.store, self.settings, self.config, universe, self.taxonomy)
        self.assertFalse(other.completed(result, "uspto", self.start, self.end, "daily"))

    def test_failed_source_does_not_advance(self):
        self.client.rows = [odp(updated="2024-01-01T12:00:00")]
        result = self.run_daily()
        self.assertEqual(result["sources"]["uspto"]["next_date"], str(self.start))
        self.assertEqual(result["sources"]["uspto"]["windows"][0]["status"], "failed")

    def test_historical_and_daily_progress_are_independent(self):
        self.ops.run(["uspto"], "historical", self.start, self.end, 1)
        self.run_daily()
        self.assertEqual([c["pagination"]["offset"] for c in self.client.calls], [0, 0])

    def test_crash_after_committed_collection_before_progress_recovers(self):
        self.config["max_pages"] = 5
        with patch("patent_operations.write_json", side_effect=RuntimeError("crash")):
            with self.assertRaises(RuntimeError):
                self.run_daily()
        done = self.run_daily()
        self.assertEqual(done["status"], "complete")
        self.assertEqual(len(self.client.calls), 2)

    def test_source_monitor_only_gets_metadata_and_never_marks_collection(self):
        from patent_bigquery_access import REQUIRED_FIELDS
        class Response:
            ok, status_code = True, 200
            def json(self):
                return {"id": "publications", "lastModifiedTime": "123", "numRows": "3", "numBytes": "100",
                    "schema": {"fields": [{"name": n} for n in REQUIRED_FIELDS]}}
        class HTTP:
            def get(self, *args, **kwargs):
                return Response()
        first = monitor_global(self.store, HTTP())
        second = monitor_global(self.store, HTTP())
        self.assertIsNone(first["changed_since_previous_observation"])
        self.assertFalse(second["changed_since_previous_observation"])
        self.assertFalse(second["data_query_executed"])
        self.assertEqual(second["collection_status"], "not_scheduled")


if __name__ == "__main__":
    unittest.main()
