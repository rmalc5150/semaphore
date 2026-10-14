from copy import deepcopy
from datetime import date
import unittest

from patent_backfill_plan import plan


class BackfillPlanTests(unittest.TestCase):
    def setUp(self):
        metadata = {"id": "source", "lastModifiedTime": "123", "numRows": "1", "numBytes": "100"}
        self.coverage = {"status": "complete", "coverage_id": "coverage",
            "plan": {"provenance": {"as_of": "2026-09-23"}},
            "source_revision_after": metadata,
            "countries": [{"missing_or_invalid_dates": 2, "future_dates": 1}]}
        self.estimate = {"dry_run": True, "estimate_within_ceiling": True,
            "source_metadata": metadata, "configured_maximum_bytes_billed": 50000000000,
            "provenance": {"universe_hash": "universe", "classification_hash": "rules", "coverage_gaps": []}}

    def test_monthly_windows_preserve_exact_exclusive_range_and_cost_reservation(self):
        result = plan(self.coverage, self.estimate, date(2024, 2, 29), date(2024, 4, 2))
        self.assertEqual([(x["start"], x["end_exclusive"]) for x in result["windows"]],
            [("2024-02-29", "2024-03-01"), ("2024-03-01", "2024-04-01"), ("2024-04-01", "2024-04-02")])
        self.assertEqual(result["initial_queries_reserved_bytes"], 150000000000)
        self.assertEqual(result["status"], "proposed_not_scheduled")

    def test_mismatched_source_revision_and_failed_estimate_rejected(self):
        estimate = deepcopy(self.estimate)
        estimate["source_metadata"]["lastModifiedTime"] = "456"
        with self.assertRaises(ValueError):
            plan(self.coverage, estimate, date(2025, 1, 1), date(2025, 2, 1))
        self.estimate["estimate_within_ceiling"] = False
        with self.assertRaises(ValueError):
            plan(self.coverage, self.estimate, date(2025, 1, 1), date(2025, 2, 1))

    def test_future_or_empty_range_rejected(self):
        for start, end in [(date(2025, 1, 1), date(2026, 9, 24)), (date(2025, 1, 1), date(2025, 1, 1))]:
            with self.assertRaises(ValueError):
                plan(self.coverage, self.estimate, start, end)


if __name__ == "__main__":
    unittest.main()
