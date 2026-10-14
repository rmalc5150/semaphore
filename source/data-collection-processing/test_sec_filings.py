"""SEC collector tests using fictional indexes and no network or cloud access."""

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from datetime import date, datetime
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError

import sec_filings as sec
from collection_storage import LocalStore, StorageSettings, read_watermark
from research_contract import ROOT, load_json, validate_record


FIXTURE = ROOT / "examples/sec-filings/master-2024-q2.idx"
UNIVERSE = ROOT / "examples/sec-filings/universe.json"


class Response(io.BytesIO):
    def __init__(self, body, headers=None):
        super().__init__(body)
        self.headers = headers or {}


class SECTests(unittest.TestCase):
    def setUp(self):
        self.raw = FIXTURE.read_bytes()
        self.universe = load_json(UNIVERSE)
        self.taxonomy = load_json(ROOT / "config/sectors.v1.json")
        self.matcher = sec.CompanyMatcher(self.universe)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = LocalStore(self.temp.name)
        self.settings = StorageSettings()
        self.scope = {"selection": "universe", "ciks": [], "forms": []}
        self.client = Mock()
        self.client.fetch.return_value = self.raw
        self.start, self.end = date(2024, 6, 3), date(2024, 6, 8)

    def collect(self, **kwargs):
        return sec.collect_window(self.store, self.settings, self.universe, self.taxonomy,
            self.client, self.start, self.end, "historical", self.scope, self.matcher,
            kwargs.pop("cache", {}), **kwargs)

    def records(self, result):
        manifest = json.loads(self.store.get(result["manifest"]).body)
        return [json.loads(line) for page in manifest["pages"] for batch in page["batches"]
                for line in self.store.get(batch["key"]).body.splitlines()]

    def test_parser_and_accession_grouping_preserve_cofilers(self):
        rows, received = sec.parse_index(self.raw, 2024, 2)
        self.assertEqual(received, date(2024, 6, 28))
        self.assertEqual(len(rows), 7)  # Exact duplicate source row removed.
        filings = sec.select_filings(rows, self.start, self.end, self.matcher)
        self.assertEqual(len(filings), 5)
        cofiled = next(f for f in filings if f["accession_number"].endswith("000005"))
        self.assertEqual(len(cofiled["company_ids"]), 2)
        self.assertEqual(len(cofiled["issuer_rows"]), 2)
        # The accession submitter CIK is 99999, not the issuer CIK.
        self.assertEqual(rows[0]["cik"], "0000001001")

    def test_streamed_index_matches_materialized_and_rejects_bad_tail(self):
        expected, received = sec.parse_index(self.raw, 2024, 2)
        streamed = []
        rows, streamed_received = sec.parse_index(self.raw, 2024, 2, consume=streamed.append)
        self.assertEqual((rows, streamed_received), ([], received))
        self.assertEqual(streamed, expected)
        with self.assertRaises(sec.SourceError):
            sec.parse_index(self.raw + b'\nmalformed\n', 2024, 2, consume=lambda row: None)

    def test_one_accession_with_multiple_index_forms_preserves_both(self):
        lines = self.raw.decode('latin-1').splitlines()
        row = next(line for line in lines if '|' in line and 'edgar/data/' in line)
        parts = row.split('|'); original = parts[2]; parts[2] = 'SC TO-I'
        self.client.fetch.return_value = self.raw + ('\n' + '|'.join(parts) + '\n').encode('latin-1')
        result = self.collect()
        self.assertEqual(result['status'], 'complete')
        multiple = [r for r in self.records(result) if r['payload'].get('index_forms')]
        self.assertEqual(len(multiple), 1)
        self.assertEqual(multiple[0]['payload']['index_forms'], sorted([original, 'SC TO-I']))
        self.assertEqual(len(multiple[0]['payload']['issuer_rows']), 2)

    def test_all_four_sectors_match_by_verified_cik(self):
        result = self.collect()
        records = self.records(result)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["filings_by_configured_sector_including_candidates"],
                         {"biotech": 1, "robotics": 2, "semiconductors": 1, "energy_storage": 2})
        ids = {cid for r in records for cid in r["company_ids"]}
        self.assertEqual(ids, {c["company_id"] for c in self.universe["companies"]})
        for record in records:
            self.assertEqual(validate_record(record, self.universe), [])
            self.assertIsNone(record["available_at"])
            self.assertEqual(record["availability_basis"], "unknown")

    def test_name_matches_are_candidates_not_confirmed_entities(self):
        self.universe["external_identifiers"] = []
        self.matcher = sec.CompanyMatcher(self.universe)
        result = self.collect()
        self.assertEqual(result["candidate_only_filings"], 5)
        for record in self.records(result):
            self.assertEqual(record["entity_match_status"], "unresolved")
            self.assertEqual(record["company_ids"], [])
            self.assertTrue(record["payload"]["candidate_company_ids"])

    def test_unmatched_records_retained_when_all_selected(self):
        self.scope["selection"] = "all"
        result = self.collect()
        self.assertEqual(len(self.records(result)), 6)
        self.assertEqual(result["unmatched_filings"], 1)

    def test_exact_end_exclusive_and_filters(self):
        rows, _ = sec.parse_index(self.raw, 2024, 2)
        filings = sec.select_filings(rows, date(2024, 6, 3), date(2024, 6, 4), self.matcher)
        self.assertEqual(len(filings), 2)
        filings = sec.select_filings(rows, self.start, self.end, self.matcher, ciks=["0000001004"], forms=["S-4"])
        self.assertEqual(len(filings), 1)
        self.assertEqual(len(filings[0]["issuer_rows"]), 2)

    def test_sector_filter(self):
        rows, _ = sec.parse_index(self.raw, 2024, 2)
        matcher = sec.CompanyMatcher(self.universe, sectors=["semiconductors"])
        filings = sec.select_filings(rows, self.start, self.end, matcher)
        self.assertEqual(len(filings), 1)
        self.assertEqual(filings[0]["issuer_rows"][0]["cik"], "0000001003")

    def test_nonlatin_names_do_not_collapse_to_empty_matches(self):
        self.assertNotEqual(sec.normalize_name("示例机器人"), sec.normalize_name("示例储能"))
        self.assertEqual(sec.normalize_name("ＮVIDIA Corp."), "nvidia")

    def test_valid_final_row_without_newline_is_preserved(self):
        self.assertEqual(sec.parse_index(self.raw.rstrip(b"\n"), 2024, 2),
                         sec.parse_index(self.raw, 2024, 2))

    def test_missing_and_malformed_index_never_count_as_empty(self):
        for body in [b"<html>blocked</html>\n", self.raw.rstrip(b"\n")[:-2], self.raw + b"broken|line\n",
                     self.raw.replace(b"2024-06-03", b"2024-02-30"),
                     self.raw.replace(b"Last Data Received:", b"Unknown:")]:
            with self.subTest(body=body[:30]):
                with self.assertRaises(sec.SourceError):
                    sec.parse_index(body, 2024, 2)

    def test_missing_source_is_partial_not_complete_zero(self):
        self.client.fetch.side_effect = sec.SourceError("index_unavailable")
        result = self.collect()
        self.assertEqual(result["status"], "partial")
        manifest = json.loads(self.store.get(result["manifest"]).body)
        self.assertFalse(manifest["exhausted"])

    def test_failed_source_records_failure(self):
        self.client.fetch.return_value = b"broken\n"
        result = self.collect()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "index_header_missing")

    def test_weekend_and_unconfirmed_weekday_coverage(self):
        sec.assert_coverage(date(2024, 6, 28), date(2024, 6, 29), date(2024, 7, 1))
        with self.assertRaises(sec.SourceError):
            sec.assert_coverage(date(2024, 6, 27), date(2024, 6, 28), date(2024, 6, 29))

    def test_incomplete_coverage_with_no_pages_fetches_a_new_snapshot(self):
        lines = self.raw.decode().splitlines()
        early = [line.replace("June 28, 2024", "June 04, 2024") for line in lines
                 if not line[:1].isdigit() or line.split("|")[3] <= "2024-06-04"]
        self.client.fetch.return_value = ("\n".join(early) + "\n").encode()
        first = self.collect()
        self.assertEqual(first["reason"], "index_coverage_incomplete")
        self.client.fetch.return_value = self.raw
        resumed = self.collect()
        self.assertEqual(resumed["status"], "complete")
        self.assertEqual(self.client.fetch.call_count, 2)

    def test_resume_pins_snapshot_even_if_source_changes(self):
        partial = self.collect(max_records=2, page_size=1)
        self.assertEqual(partial["status"], "partial")
        self.client.fetch.side_effect = AssertionError("resume must not fetch source")
        result = self.collect(page_size=3)
        self.assertEqual(result["status"], "complete")
        records = self.records(result)
        self.assertEqual(len(records), 5)
        self.assertEqual(len({r["record_id"] for r in records}), 5)
        self.assertEqual(len({r["run_id"] for r in records}), 2)
        self.assertEqual(self.client.fetch.call_count, 1)

    def test_completed_rerun_does_not_fetch_and_refresh_does(self):
        first = self.collect()
        second = self.collect()
        self.assertTrue(second["already_complete"])
        self.assertEqual(self.client.fetch.call_count, 1)
        fresh = self.collect(refresh=True)
        self.assertEqual(self.client.fetch.call_count, 2)
        self.assertNotEqual(first["manifest"], fresh["manifest"])
        self.assertEqual(self.records(first)[0]["record_id"], self.records(fresh)[0]["record_id"])

    def test_bulk_cache_retains_only_one_quarter(self):
        cache = {}
        self.collect(cache=cache)
        self.assertEqual(set(cache), {(2024, 2)})
        self.client.fetch.return_value = self.raw.replace(b"June 28, 2024", b"September 30, 2024").replace(b"2024-06-", b"2024-09-")
        self.start, self.end = date(2024, 9, 3), date(2024, 9, 8)
        result = self.collect(cache=cache)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(set(cache), {(2024, 3)})

    def test_known_empty_selection_is_complete(self):
        self.scope["forms"] = ["NONEXISTENT-FIXTURE-FORM"]
        result = self.collect()
        self.assertEqual(result["status"], "complete")
        self.assertEqual(self.records(result), [])

    def test_failed_page_does_not_skip_on_resume(self):
        from collection_storage import CollectionRun
        original = CollectionRun.commit_page

        def fail_second(run, *args, **kwargs):
            if len(run.state["pages"]) == 1:
                raise OSError("simulated local failure")
            return original(run, *args, **kwargs)
        with patch.object(CollectionRun, "commit_page", fail_second):
            with self.assertRaises(OSError):
                self.collect(page_size=1)
        self.client.fetch.side_effect = AssertionError("source should stay pinned")
        result = self.collect()
        self.assertEqual(len(self.records(result)), 5)

    def test_calendar_windows_and_daylight_savings(self):
        self.assertEqual(list(sec.windows(date(2024, 3, 29), date(2024, 4, 3), "historical")),
                         [(date(2024, 3, 29), date(2024, 4, 1)), (date(2024, 4, 1), date(2024, 4, 3))])
        self.assertEqual(sec.midnight(date(2024, 3, 10)), "2024-03-10T05:00:00Z")
        self.assertEqual(sec.midnight(date(2024, 3, 11)), "2024-03-11T04:00:00Z")

    def test_offline_fixture_cannot_write_to_s3(self):
        with redirect_stderr(io.StringIO()):
            code = sec.main(["daily", "2024-06-03", "--index-file", str(FIXTURE),
                             "--backend", "s3", "--s3-bucket", "must-not-be-used"])
        self.assertEqual(code, 1)

    def test_legacy_cli_delegates_to_existing_pipeline(self):
        with patch("sec_filings_legacy.main", return_value=0) as legacy, redirect_stderr(io.StringIO()):
            self.assertEqual(sec.main(["day", "2024-06-03"]), 0)
        legacy.assert_called_once_with(["day", "2024-06-03"])

    def test_daily_requires_initial_origin_and_refreshes_overlap(self):
        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2024, 6, 9, 12, tzinfo=sec.NY)
        args = ["daily", "--index-file", str(FIXTURE), "--universe", str(UNIVERSE),
                "--output-root", self.temp.name]
        with patch.object(sec, "datetime", FixedDateTime), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(sec.main(args), 1)
            self.assertEqual(sec.main(args + ["--origin", "2024-06-03"]), 0)
            first = list(Path(self.temp.name).rglob("final.json"))
            self.assertEqual(len(first), 6)
            self.assertEqual(sec.main(args), 0)
            self.assertEqual(len(list(Path(self.temp.name).rglob("final.json"))), 9)
            self.assertEqual(sec.main(args + ["--overlap-days", "0"]), 0)


class SECRequestTests(unittest.TestCase):
    def test_missing_or_placeholder_contact_rejected(self):
        for agent in (None, "Robot", "Robot contact@example.com", "contact@research.invalid"):
            with self.assertRaises(ValueError):
                sec.SECClient(agent)

    def test_retry_after_and_user_agent(self):
        body = FIXTURE.read_bytes()
        opener = Mock(side_effect=[HTTPError("https://www.sec.gov", 429, "limit", {"Retry-After": "2"}, None), Response(body)])
        sleep = Mock()
        client = sec.SECClient("Fixture research@test.invalid", opener=opener, sleeper=sleep)
        self.assertEqual(client.fetch(2024, 2), body)
        self.assertTrue(any(call.args == (2.0,) for call in sleep.call_args_list))
        self.assertEqual(opener.call_args.args[0].get_header("User-agent"), "Fixture research@test.invalid")

    def test_forbidden_not_retried_and_missing_not_empty(self):
        for status, expected in [(403, "sec_http_error"), (404, "index_unavailable")]:
            opener = Mock(side_effect=HTTPError("https://www.sec.gov", status, "error", {}, None))
            client = sec.SECClient("Fixture research@test.invalid", opener=opener)
            with self.assertRaises(sec.SourceError) as caught:
                client.fetch(2024, 2)
            self.assertEqual(caught.exception.code, expected)
            self.assertEqual(opener.call_count, 1)

    def test_incomplete_http_body_is_rejected(self):
        client = sec.SECClient("Fixture research@test.invalid", opener=Mock(return_value=Response(b"short", {"Content-Length": "900"})))
        with self.assertRaises(sec.SourceError):
            client.fetch(2024, 2)


if __name__ == "__main__":
    unittest.main()
