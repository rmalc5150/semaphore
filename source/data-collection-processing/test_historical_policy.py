"""Verify the shared start reaches actual CLIs without changing daily scopes."""
from contextlib import redirect_stdout, redirect_stderr
from datetime import date
import io
import json
import unittest
from unittest.mock import Mock, patch

from historical_policy import historical_start
import collection_operations
import disclosure_collection
import patent_collection
import patent_operations
import regulatory_collection
import sec_filings
import news_collection
from research_contract import ROOT, load_json


class HistoricalPolicyTests(unittest.TestCase):
    def test_approved_start(self):
        self.assertEqual(historical_start(), date(2021, 1, 1))
        self.assertEqual(load_json(ROOT / "config/patent-backfill.json")["start_date"], "2021-01-01")
        self.assertEqual(load_json(ROOT / "config/model-data-policy.json")["model_start_date"], "2021-01-01")

    def test_news_providers_default_to_2021(self):
        for config in ("config/news-collection.json", "config/news-history-marketaux.json"):
            output = io.StringIO()
            with self.subTest(config=config), redirect_stdout(output), patch("sys.argv", [
                    "news_collection.py", "historical", "--end", "2021-02-01",
                    "--config", str(ROOT / config), "--dry-run"]):
                news_collection.main()
            report = json.loads(output.getvalue())
            self.assertEqual(report["start"], "2021-01-01")
            self.assertEqual(set(report["providers"]), {"finlight", "marketaux"})

    def test_shared_runner_defaults_all_selected_sources_and_preserves_daily(self):
        output = io.StringIO()
        with redirect_stdout(output):
            collection_operations.main("historical", ["--end-date", "2026-09-23", "--dry-run"])
        report = json.loads(output.getvalue())
        self.assertEqual(report["origin"], "2021-01-01")
        self.assertIn("clinicaltrials", report["sources_in_dependency_order"])
        self.assertIn("strategic-transactions", report["sources_in_dependency_order"])
        output = io.StringIO()
        with redirect_stdout(output):
            collection_operations.main("daily", ["--dry-run"])
        self.assertEqual(json.loads(output.getvalue())["origin"], "2026-09-21")

    def test_sec_defaults_and_explicit_retry_window_unchanged(self):
        args = sec_filings.arguments(["historical", "--end-date", "2026-09-23"])
        self.assertEqual(args.start, date(2021, 1, 1))
        args = sec_filings.arguments(["historical", "2024-06-03", "2024-06-04"])
        self.assertEqual((args.start, args.end), (date(2024, 6, 3), date(2024, 6, 4)))
        args = sec_filings.arguments(["daily", "2026-09-21"])
        self.assertEqual(args.start, date(2026, 9, 21))

    def test_all_regulatory_adapters_receive_2021_first_month(self):
        from regulatory_sources import ADAPTERS
        for source in ADAPTERS:
            with self.subTest(source=source), redirect_stdout(io.StringIO()), patch.object(regulatory_collection.StorageSettings, "load", return_value=Mock()), patch.object(regulatory_collection, "collect", return_value={"status": "partial"}) as collect, patch.dict(ADAPTERS, {source: Mock()}):
                regulatory_collection.main(source, ["historical", "--end-date", "2026-09-23"])
                self.assertEqual(collect.call_args.args[5:8], (date(2021, 1, 1), date(2021, 2, 1), "historical"))

    def test_disclosure_hkex_and_derived_stages_receive_default(self):
        for stage in ("hkex", "documents", *disclosure_collection.CATEGORIES):
            args = ["historical", "--end-date", "2021-02-01"]
            if stage != "hkex":
                args += ["--source-manifest", "fixture.json"]
            target = "collect_hkex" if stage == "hkex" else "collect_derived"
            with self.subTest(stage=stage), redirect_stdout(io.StringIO()), patch.object(disclosure_collection.StorageSettings, "load", return_value=Mock()), patch.object(disclosure_collection, target, return_value={"status": "partial"}) as collect:
                disclosure_collection.main(stage, args)
                self.assertEqual(collect.call_args.args[4:7], (date(2021, 1, 1), date(2021, 2, 1), "historical"))

    def test_patent_runner_default_and_direct_collector(self):
        output = io.StringIO()
        with redirect_stdout(output):
            patent_operations.main(["historical", "--end", "2026-09-23", "--dry-run"])
        self.assertEqual(json.loads(output.getvalue())["origin"], "2021-01-01")
        with redirect_stdout(io.StringIO()), patch.object(patent_collection.StorageSettings, "load", return_value=Mock()), patch.object(patent_collection, "collect_uspto", return_value={"status": "partial"}) as collect:
            patent_collection.main(["uspto", "--mode", "historical", "--end", "2021-02-01"])
            self.assertEqual(collect.call_args.args[4:7], (date(2021, 1, 1), date(2021, 2, 1), "historical"))

    def test_unpinned_end_and_daily_historical_option_rejected(self):
        for args in (["historical"], ["historical", "2021-01-01", "2021-02-01", "--end-date", "2021-03-01"], ["daily", "--end-date", "2026-09-23"]):
            with self.subTest(args=args), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                sec_filings.arguments(args)
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            patent_collection.main(["uspto", "--mode", "daily", "--end", "2026-09-23"])


if __name__ == "__main__":
    unittest.main()
