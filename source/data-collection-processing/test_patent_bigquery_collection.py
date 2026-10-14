from contextlib import redirect_stdout
from datetime import date
import io
import json
import tempfile
import unittest
from unittest.mock import Mock

from collection_storage import StorageSettings
import patent_bigquery_collection as bq
from patent_collection import RULES_PATH
from patent_query_plan import build
from research_contract import ROOT, load_json


class Client:
    def __init__(self):
        self.jobs, self.pages = [], []
        self.pending = False

    def job(self, identity, query):
        self.jobs.append(identity)
        return {"configuration": {"query": query}, "status": {"state": "DONE"}, "statistics": {"query": {"totalBytesBilled": "10000"}}}

    def page(self, identity, token, size):
        self.pages.append(token)
        if self.pending:
            return {"jobComplete": False}
        offset = int(token or 0)
        result = {"jobComplete": True, "totalRows": "2",
            "schema": {"fields": [{"name": n, "type": "STRING"} for n in ("publication_number", "publication_date", "title")]},
            "rows": [{"f": [{"v": f"CN-{offset + 1}-A"}, {"v": "2025-01-06"}, {"v": "Battery"}]}]}
        if offset == 0:
            result["pageToken"] = "1"
        return result


class BigQueryCollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = StorageSettings(local_root=self.temp.name)
        self.store = self.settings.store()
        self.universe = load_json(ROOT / "examples/sec-filings/universe.json")
        self.taxonomy = load_json(ROOT / "config/sectors.v1.json")
        self.plan = build(self.universe, load_json(RULES_PATH), date(2025,1,1), date(2025,2,1), 1000000)
        self.client = Client()

    def run_collect(self, **kw):
        with redirect_stdout(io.StringIO()):
            return bq.collect(self.store, self.settings, self.universe, self.taxonomy,
                              self.plan, 1000000, self.client, page_size=1, **kw)

    def test_partial_resume_reuses_job_and_page_token(self):
        first = self.run_collect(max_pages=1)
        self.assertEqual(first["status"], "partial")
        final = self.run_collect(max_pages=5)
        self.assertEqual(final["status"], "complete")
        self.assertEqual(final["records"], 2)
        self.assertEqual(len(set(self.client.jobs)), 1)
        self.assertEqual(self.client.pages, [None, "1"])
        meta = json.loads(self.store.get(final["export_prefix"] + "/export-metadata.json").body)
        self.assertEqual(meta["row_count"], 2)
        self.assertTrue(self.run_collect()["already_complete"])

    def test_pending_job_remains_partial_and_reuses_identity(self):
        self.client.pending = True
        first = self.run_collect()
        self.assertEqual(first["reason"], "bigquery_job_pending")
        self.client.pending = False
        final = self.run_collect()
        self.assertEqual(final["status"], "complete")
        self.assertEqual(len(set(self.client.jobs)), 1)

    def test_modified_plan_rejected_before_billed_job(self):
        self.plan["configuration"]["query"]["query"] = "SELECT 1"
        with self.assertRaises(bq.SourceIssue):
            self.run_collect()
        self.assertEqual(self.client.jobs, [])

    def test_repeated_fields_and_nulls_decode_without_losing_ids(self):
        field = {"name": "assignees", "type": "STRING", "mode": "REPEATED"}
        self.assertEqual(bq.decode_value(field, [{"v":"宁德时代"}]), ["宁德时代"])
        self.assertIsNone(bq.decode_value(field, None))
        self.assertEqual(bq.decode_value({"type": "INTEGER"}, "123456789012345678"), "123456789012345678")

    def test_refresh_starts_a_new_job(self):
        self.run_collect()
        self.run_collect(refresh=True)
        self.assertEqual(len(set(self.client.jobs)), 2)

    def test_job_conflict_recovers_existing_job_without_new_identity(self):
        def reply(code, value):
            return Mock(status_code=code, ok=code < 400, json=lambda: value)
        query = {"query": "SELECT 1", "maximumBytesBilled": "1000", "useLegacySql": False}
        http = Mock()
        http.get.side_effect = [reply(404, {}), reply(200, {"configuration": {"query": query}})]
        http.post.return_value = reply(409, {})
        self.assertEqual(bq.BigQuery(http).job("fixed-job", query)["configuration"]["query"], query)
        submitted = http.post.call_args.kwargs["json"]
        self.assertEqual(submitted["jobReference"]["jobId"], "fixed-job")
        self.assertEqual(submitted["configuration"]["query"]["maximumBytesBilled"], "1000")
        self.assertEqual(http.post.call_count, 1)

    def test_existing_job_with_different_query_is_rejected(self):
        http = Mock()
        http.get.return_value = Mock(status_code=200, ok=True,
            json=lambda: {"configuration": {"query": {"query": "SELECT 2"}}})
        with self.assertRaises(bq.SourceIssue):
            bq.BigQuery(http).job("fixed-job", {"query": "SELECT 1"})
        http.post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
