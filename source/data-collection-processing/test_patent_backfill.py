from contextlib import redirect_stdout
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import io
import json
import tempfile
import unittest
from unittest.mock import Mock, patch

from collection_storage import StorageSettings
from patent_collection import SourceIssue
from patent_query_plan import build
from research_contract import ROOT, load_json
import patent_backfill as backfill
from test_patent_bigquery_collection import Client


class BackfillTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.settings = StorageSettings(local_root=temp.name)
        self.store = self.settings.store()
        self.config = {**load_json(ROOT / "config/patent-backfill.json"), "page_size": 1, "max_pages": 1}
        self.config.pop("start_date", None)
        self.universe = load_json(ROOT / "examples/sec-filings/universe.json")
        self.taxonomy = load_json(ROOT / "config/sectors.v1.json")
        clock = patch.object(backfill, "historical_start", return_value=date(2025, 1, 1))
        clock.start()
        self.addCleanup(clock.stop)
        self.runner = backfill.Backfill(self.store, self.settings, self.config, self.universe, self.taxonomy)
        self.client = Client()
        self.plan = build(self.universe, self.runner.rules, date(2025,1,1), date(2025,2,1), self.config["maximum_bytes_billed"])

    def run_slice(self):
        with redirect_stdout(io.StringIO()):
            return self.runner.run(None, self.client)

    def test_partial_resumes_same_job_and_complete_advances_only_one_month(self):
        first = self.run_slice()
        self.assertEqual(first["next_date"], "2025-01-01")
        self.assertEqual(first["completed_windows"], 0)
        second = self.run_slice()
        self.assertEqual(second["next_date"], "2025-02-01")
        self.assertEqual(second["completed_records"], 2)
        self.assertEqual(len(set(self.client.jobs)), 1)
        self.assertEqual(self.client.pages, [None, "1"])

    def test_uncommitted_completion_does_not_advance(self):
        with patch.object(backfill, "collect", return_value={"status": "complete", "manifest": "missing"}):
            result = self.run_slice()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["next_date"], "2025-01-01")

    def test_audit_checks_completed_batches_and_source_evidence(self):
        self.config["max_pages"] = 5
        self.run_slice()
        progress, token = backfill.load_stored(self.store, self.runner.progress_key)
        progress.pop("last_complete")  # earlier progress records only had last_attempt
        backfill.write_json(self.store, self.runner.progress_key, progress, token)
        with patch.object(backfill, "collect", return_value={"status": "partial", "reason": "page_limit"}):
            self.run_slice()
        report = self.runner.audit()
        self.assertEqual(report["records"], 2)
        self.assertEqual(report["authorities"], {"CN": 2})
        self.assertFalse(report["athena_published"])
        manifest, _ = backfill.load_stored(self.store, report["manifest"])
        batch = manifest["pages"][1]["batches"][0]
        obj = self.store.get(batch["key"])
        self.store.put(batch["key"], b"corrupt", expected=obj.token)
        with self.assertRaises(SourceIssue) as error:
            self.runner.audit()
        self.assertEqual(error.exception.code, "raw_batch_hash_mismatch")

    def test_progress_write_crash_recovers_completed_collector_without_rebilling(self):
        self.config["max_pages"] = 5
        original = backfill.write_json
        def write(store, key, value, *args):
            if key == self.runner.progress_key:
                raise RuntimeError("crash before progress commit")
            return original(store, key, value, *args)
        with patch.object(backfill, "write_json", side_effect=write), self.assertRaises(RuntimeError):
            self.run_slice()
        calls = len(self.client.jobs)
        result = self.run_slice()
        self.assertEqual(result["next_date"], "2025-02-01")
        self.assertEqual(len(self.client.jobs), calls)

    def test_page_limit_change_preserves_stream_but_universe_change_does_not(self):
        other = backfill.Backfill(self.store, self.settings, {**self.config, "max_pages": 100}, self.universe, self.taxonomy)
        self.assertEqual(other.identity, self.runner.identity)
        changed = deepcopy(self.universe)
        changed["universe_version"] = "99.0.0"
        other = backfill.Backfill(self.store, self.settings, self.config, changed, self.taxonomy)
        self.assertNotEqual(other.identity, self.runner.identity)

    def test_start_override_isolates_progress_and_keeps_daily_budget(self):
        self.run_slice()
        old_progress = self.store.get(self.runner.progress_key).body
        config = {**self.config, "start_date": "2021-01-01"}
        revised = backfill.Backfill(self.store, self.settings, config, self.universe, self.taxonomy)
        self.assertNotEqual(revised.identity, self.runner.identity)
        self.assertEqual(revised.status()["next_date"], "2021-01-01")
        self.assertEqual(revised.status()["completed_windows"], 0)
        self.assertEqual(self.store.get(self.runner.progress_key).body, old_progress)
        old_client = backfill.BudgetedBigQuery(None, self.store, self.config, self.plan)
        new_client = backfill.BudgetedBigQuery(None, self.store, config, self.plan)
        for i in range(self.config["max_new_jobs_per_day"]):
            old_client.reserve("old-job-" + str(i))
        with self.assertRaises(SourceIssue) as error:
            new_client.reserve("new-stream-job")
        self.assertEqual(error.exception.code, "daily_query_budget_reached")

    def test_override_rejects_partial_first_month(self):
        with self.assertRaises(ValueError):
            backfill.Backfill(self.store, self.settings,
                {**self.config, "start_date": "2021-01-02"}, self.universe, self.taxonomy)

    def guard(self):
        http = Mock()
        client = backfill.BudgetedBigQuery(http, self.store, self.config, self.plan)
        estimate = {"estimate_within_ceiling": True, "location": "US"}
        verify = patch.object(backfill, "verify", return_value=estimate)
        verify.start()
        self.addCleanup(verify.stop)
        query = {**self.plan["configuration"]["query"], "useQueryCache": True}
        return client, http, query, estimate

    def test_daily_budget_blocks_fifth_new_job_and_resume_does_not_spend_twice(self):
        guard, http, query, _ = self.guard()
        for n in range(4):
            guard.authorize(str(n), query)
        guard.authorize("0", query)
        with self.assertRaises(SourceIssue) as error:
            guard.authorize("4", query)
        self.assertEqual(error.exception.code, "daily_query_budget_reached")
        self.assertTrue(error.exception.partial)
        http.post.assert_not_called()

    def test_expired_missing_job_never_resubmitted(self):
        guard, http, query, _ = self.guard()
        with patch.object(backfill, "now", return_value="2020-01-01T12:00:00Z"):
            guard.authorize("old", query)
        http.get.return_value = Mock(status_code=404)
        with self.assertRaises(SourceIssue) as error:
            guard.job("old", query)
        self.assertEqual(error.exception.code, "missing_old_job_manual_review_required")
        http.post.assert_not_called()

    def test_submission_retry_reserves_on_new_utc_day(self):
        guard, http, query, _ = self.guard()
        today = datetime.now(timezone.utc)
        yesterday = today - timedelta(hours=1)
        with patch.object(backfill, "now", return_value=yesterday.isoformat()):
            guard.authorize("retry", query)
        tomorrow_label = (today + timedelta(days=1)).isoformat()
        with patch.object(backfill, "now", return_value=tomorrow_label):
            guard.authorize("retry", query)
            key = backfill.PREFIX + "/budgets/" + tomorrow_label[:10] + ".json"
            budget, _ = backfill.load_stored(self.store, key)
            self.assertIn("retry", budget["jobs"])

    def test_existing_job_reused_without_dry_run_or_reservation(self):
        guard, http, query, _ = self.guard()
        http.get.return_value = Mock(status_code=200, ok=True, json=lambda: {"configuration": {"query": query}})
        guard.job("existing", query)
        http.post.assert_not_called()
        backfill.verify.assert_not_called()

    def test_over_cap_and_expired_results_fail_closed(self):
        guard, http, query, estimate = self.guard()
        estimate["estimate_within_ceiling"] = False
        http.get.return_value = Mock(status_code=404)
        with self.assertRaises(SourceIssue):
            guard.job("new", query)
        http.post.assert_not_called()
        with self.assertRaises(SourceIssue) as error:
            guard.page("expired", None, 10)
        self.assertEqual(error.exception.code, "query_results_unavailable_manual_review_required")

    def test_submission_reserves_budget_and_recovers_conflict(self):
        guard, http, query, _ = self.guard()
        def post(url, **kwargs):
            auth, _ = backfill.load_stored(self.store, backfill.PREFIX + "/jobs/fixed.json")
            self.assertEqual(auth["query_hash"], backfill.digest(query))
            budget, _ = backfill.load_stored(self.store, auth["budget_key"])
            self.assertEqual(budget["jobs"]["fixed"], self.config["maximum_bytes_billed"])
            return Mock(status_code=409)
        http.post.side_effect = post
        http.get.side_effect = [Mock(status_code=404), Mock(status_code=200, ok=True, json=lambda: {"configuration": {"query": query}})]
        guard.job("fixed", query)
        self.assertEqual(http.post.call_count, 1)


if __name__ == "__main__":
    unittest.main()
