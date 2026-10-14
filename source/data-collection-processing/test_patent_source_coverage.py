"""Bounded coverage queries never rebill on an ordinary resume."""
from datetime import date
import json
import tempfile
import unittest
from unittest.mock import Mock, patch

from collection_storage import StorageSettings
import patent_source_coverage as coverage


class CoverageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.store = StorageSettings(local_root=temp.name).store()
        self.plan = coverage.build(date(2026, 9, 23), 5000000000)
        self.metadata = {"id": "patents", "lastModifiedTime": "123", "numRows": "2", "numBytes": "100"}
        self.estimate = {"source_metadata": self.metadata, "estimate_within_ceiling": True}
        self.verify = patch.object(coverage, "verify", return_value=self.estimate).start()
        self.addCleanup(patch.stopall)
        self.client = Mock()
        self.client.job.return_value = {"statistics": {"query": {"totalBytesBilled": "100"}}}
        self.bq = patch.object(coverage, "BigQuery", return_value=self.client).start()
        names = ["country_code", "publications", "missing_or_invalid_dates", "future_dates", "earliest_publication_date",
                 "latest_publication_date", "publications_last_90_days", "publications_last_180_days", "publications_last_365_days"]
        self.client.page.return_value = {"jobComplete": True, "totalRows": "1",
            "schema": {"fields": [{"name": n, "type": "STRING"} for n in names]},
            "rows": [{"f": [{"v": v} for v in ["CN", "2", "0", "0", "2020-01-01", "2026-07-01", "1", "1", "1"]]}]}
        self.http = Mock()
        self.http.get.return_value = Mock(ok=True, status_code=200, json=lambda: self.metadata)

    def test_estimate_does_not_create_billed_job(self):
        self.assertEqual(coverage.check(self.http, self.store, self.plan)["status"], "estimated")
        self.bq.assert_not_called()

    def test_above_ceiling_blocks_billed_job(self):
        self.estimate["estimate_within_ceiling"] = False
        self.assertEqual(coverage.check(self.http, self.store, self.plan, True)["status"], "blocked")
        self.bq.assert_not_called()

    def test_pending_resumes_same_job_and_completed_report_skips_query(self):
        page = self.client.page.return_value
        self.client.page.return_value = {"jobComplete": False}
        first = coverage.check(self.http, self.store, self.plan, True)
        self.client.page.return_value = page
        second = coverage.check(self.http, self.store, self.plan, True)
        self.assertEqual(first["job_id"], second["job_id"])
        self.assertEqual(second["countries"][0]["latest_publication_lag_days"], 84)
        self.assertTrue(coverage.check(self.http, self.store, self.plan, True)["already_complete"])
        self.assertEqual(self.client.page.call_count, 2)

    def test_changed_source_and_count_mismatch_not_complete(self):
        self.http.get.return_value = Mock(ok=True, status_code=200, json=lambda: {**self.metadata, "lastModifiedTime": "456"})
        result = coverage.check(self.http, self.store, self.plan, True)
        self.assertEqual(result["status"], "source_changed")
        self.assertIsNone(self.store.get(f"operations/patents/source-coverage/{result['coverage_id']}/result.json"))
        self.http.get.return_value = Mock(ok=True, status_code=200, json=lambda: self.metadata)
        self.metadata["numRows"] = "3"
        self.assertEqual(coverage.check(self.http, self.store, self.plan, True)["status"], "source_count_mismatch")

    def test_truncated_result_rejected(self):
        self.client.page.return_value["pageToken"] = "extra"
        with self.assertRaises(ValueError):
            coverage.check(self.http, self.store, self.plan, True)

    def test_intent_saved_before_job_submission(self):
        def job(identity, query):
            key = "operations/patents/source-coverage/" + identity.removeprefix("optima_patent_coverage_") + "/intent.json"
            self.assertEqual(json.loads(self.store.get(key).body)["job_id"], identity)
            self.assertEqual(query["maximumBytesBilled"], "5000000000")
            return {}
        self.client.job.side_effect = job
        self.assertEqual(coverage.check(self.http, self.store, self.plan, True)["status"], "complete")


if __name__ == "__main__":
    unittest.main()
