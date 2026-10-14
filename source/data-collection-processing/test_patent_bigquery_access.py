"""Ensure access checks cannot submit a billed query and preserve cost policy."""
from copy import deepcopy
import unittest
from unittest.mock import Mock

import patent_bigquery_access as access


def response(value, status=200):
    return Mock(ok=status < 400, status_code=status, json=lambda: value)


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.plan = {"configuration": {"dryRun": True, "query": {
            "query": "SELECT 1", "useLegacySql": False, "maximumBytesBilled": "1000"}}}

    def test_dry_run_enforced_and_original_ceiling_preserved(self):
        config, ceiling = access.dry_configuration(self.plan)
        self.assertTrue(config["dryRun"])
        self.assertEqual(ceiling, 1000)
        self.assertNotIn("maximumBytesBilled", config["query"])
        self.assertEqual(self.plan["configuration"]["query"]["maximumBytesBilled"], "1000")
        for change in ({"dryRun": False}, {"dryRun": "true"}, {"load": {}}):
            other = deepcopy(self.plan)
            other["configuration"].update(change)
            with self.assertRaises(ValueError):
                access.dry_configuration(other)

    def test_positive_execution_ceiling_required(self):
        self.plan["configuration"]["query"]["maximumBytesBilled"] = "0"
        with self.assertRaises(ValueError):
            access.dry_configuration(self.plan)

    def http(self, stats=None):
        http = Mock()
        http.get.side_effect = [response({"schema": {"fields": [{"name": n} for n in access.REQUIRED_FIELDS]}}),
                                response({"location": "US"})]
        http.post.return_value = response({"statistics": {"query": stats if stats is not None else {"totalBytesProcessed": "5000"}}})
        return http

    def test_report_above_ceiling_is_not_an_execution(self):
        http = self.http()
        result = access.verify(http, self.plan)
        self.assertFalse(result["estimate_within_ceiling"])
        self.assertFalse(result["data_query_executed"])
        http.post.assert_called_once()
        submitted = http.post.call_args.kwargs["json"]
        self.assertTrue(submitted["configuration"]["dryRun"])
        self.assertEqual(submitted["jobReference"]["location"], "US")

    def test_missing_schema_prevents_job_submission(self):
        http = self.http()
        http.get.side_effect = [response({"schema": {"fields": []}}), response({"location": "US"})]
        with self.assertRaises(ValueError):
            access.verify(http, self.plan)
        http.post.assert_not_called()

    def test_missing_estimate_not_reported_as_zero(self):
        with self.assertRaises(ValueError):
            access.verify(self.http(stats={}), self.plan)

    def test_provider_error_prevents_success_report(self):
        http = self.http()
        http.post.return_value = response({"error": {"status": "PERMISSION_DENIED", "message": "No job permission"}}, 403)
        with self.assertRaises(RuntimeError):
            access.verify(http, self.plan)


if __name__ == "__main__":
    unittest.main()
