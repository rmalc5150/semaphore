"""Offline source boundary, pagination, resume and provenance tests."""
import copy
from datetime import date
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from collection_storage import LocalStore, StorageSettings
from research_contract import ROOT, load_json, validate_record
import regulatory_collection as core
import regulatory_sources as sources


def study(number=1, sponsor="Example Robotics", updated="2024-06-03"):
    return {"protocolSection": {"identificationModule": {"nctId": f"NCT{number:08d}", "briefTitle": "Synthetic device trial"},
        "statusModule": {"lastUpdatePostDateStruct": {"date": updated}},
        "sponsorCollaboratorsModule": {"leadSponsor": {"name": sponsor}}}}


class FakeClient:
    def __init__(self, responses):
        self.responses, self.evidence, self.calls = list(responses), [], []
    def json(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class CollectionTests(unittest.TestCase):
    def test_rendered_transient_failure_retries_and_saves_evidence(self):
        from decodo_scraping_api import ScrapeError
        client = core.EvidenceClient(self.store, "chictr", sleeper=Mock())
        with patch("decodo_scraping_api.cached_token", return_value="secret"), patch(
                "decodo_scraping_api.scrape_content", side_effect=[ScrapeError("gateway", 503), "<table>trial</table>"]) as fetch:
            self.assertEqual(client.rendered("https://example.test"), "<table>trial</table>")
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(len(client.evidence), 1)

    def test_rendered_persistent_failure_records_safe_diagnostics(self):
        from decodo_scraping_api import ScrapeError
        client = core.EvidenceClient(self.store, "chictr", sleeper=Mock())
        with patch("decodo_scraping_api.cached_token", return_value="secret"), patch(
                "decodo_scraping_api.scrape_content", side_effect=ScrapeError("target", 502)) as fetch:
            with self.assertRaises(core.SourceIssue) as error:
                client.rendered("https://example.test")
        self.assertEqual(fetch.call_count, 4)
        self.assertEqual(error.exception.code, "scrape_target_http_502")
        self.assertEqual(error.exception.diagnostics["attempts"], 4)

    def test_nmpa_empty_body_retries_until_trial_table_is_present(self):
        client = core.EvidenceClient(self.store, "nmpa_trials", sleeper=Mock())
        trial = '<table class="searchDetailTable"><tr><th>登记号</th><td>CTR20240001</td></tr></table>'
        with patch("decodo_scraping_api.cached_token", return_value="secret"), patch(
                "decodo_scraping_api.scrape_content", side_effect=['<title>Trial</title>', '<table>unrelated</table>', trial]) as fetch:
            self.assertEqual(client.rendered('https://www.chinadrugtrials.org.cn/clinicaltrials.searchlistdetail.dhtml?reg_no=CTR20240001'), trial)
        self.assertEqual(fetch.call_count, 3)
        self.assertEqual(len(client.evidence), 3)

    def test_incomplete_rendered_document_never_counts_as_success(self):
        client = core.EvidenceClient(self.store, "nmpa_trials", sleeper=Mock())
        with patch("decodo_scraping_api.cached_token", return_value="secret"), patch(
                "decodo_scraping_api.scrape_content", return_value='<title>Trial</title>') as fetch:
            with self.assertRaisesRegex(core.SourceIssue, "rendered_document_incomplete"):
                client.rendered('https://www.chinadrugtrials.org.cn/clinicaltrials.searchlistdetail.dhtml?reg_no=CTR20240001')
        self.assertEqual(fetch.call_count, 4)

    def test_nmpa_javascript_link_uses_public_registration_endpoint(self):
        rows = sources.nmpa_summaries('<table><tr><td>CTR20240001</td><td><a href="javascript:void(0)">Trial</a></td></tr></table>')
        self.assertEqual(rows[0]["detailUrl"], "https://www.chinadrugtrials.org.cn/clinicaltrials.searchlistdetail.dhtml?reg_no=CTR20240001")

    def test_nmpa_paired_fields_and_company_names(self):
        from nmpa_drug_trials import parse_detail_page
        fields = parse_detail_page('<table><tr><th>登记号</th><td>CTR20240001</td><th>试验状态</th><td>进行中</td></tr>'
            '<tr><th>申请人联系人</th><td>Contact person</td><th>首次公示信息日期</th><td>2024-06-03</td></tr>'
            '<tr><th>申请人名称</th><td>Example Biotech</td></tr></table>')
        self.assertIn({"label": "试验状态", "value": "进行中"}, fields)
        self.assertIn({"label": "首次公示信息日期", "value": "2024-06-03"}, fields)
        self.assertEqual(sources.field_names(fields), ["Example Biotech"])

    def test_nmpa_cohort_resume_is_scoped_and_does_not_complete_full_registry(self):
        def client_for(number):
            client = Mock(evidence=[])
            client.rendered.return_value = ('<table><tr><th>登记号</th><td>' + number + '</td></tr>'
                '<tr><th>首次公示信息日期</th><td>2024-06-03</td></tr></table>')
            return client
        adapter = sources.NMPA(["CTR20240002", "CTR20240001"])
        def run(client, **kwargs):
            return core.collect(self.store, self.settings, self.universe, self.taxonomy, "nmpa", self.start,
                self.end, "historical", adapter, client=client, **kwargs)
        first = run(client_for("CTR20240001"), max_pages=1)
        self.assertEqual(first["status"], "partial")
        second = run(client_for("CTR20240002"))
        self.assertEqual(second["records"], 2)
        manifest = json.loads(self.store.get(second["manifest"]).body)
        self.assertEqual(manifest["task"]["scope"]["registry_ids"], ["CTR20240001", "CTR20240002"])
        self.assertIn("not complete", manifest["task"]["scope"]["coverage"])
        # The unfiltered task must query its listing, even after the cohort completed.
        broad_client = Mock(evidence=[])
        broad_client.rendered.side_effect = core.SourceIssue("expected_listing_request", True)
        broad = core.collect(self.store, self.settings, self.universe, self.taxonomy, "nmpa", self.start,
            self.end, "historical", sources.NMPA(), client=broad_client)
        self.assertEqual(broad["reason"], "expected_listing_request")
        self.assertTrue(self.store.get(broad["diagnostics"]))

    def test_nmpa_wrong_detail_and_ignored_page_are_rejected(self):
        client = Mock()
        client.rendered.return_value = '<table><tr><th>登记号</th><td>CTR20240002</td></tr></table>'
        with self.assertRaisesRegex(core.SourceIssue, "identity_mismatch"):
            sources.NMPA(["CTR20240001"]).page(client, self.start, self.end, "historical", {}, 100)
        client.rendered.return_value = '<table><tr><td>CTR20240001</td><td>Trial</td></tr></table>当前第 1 页，共 2 页'
        with self.assertRaisesRegex(core.SourceIssue, "page_parameter_ignored"):
            sources.NMPA().page(client, self.start, self.end, "historical", {"page": 2}, 100)

    def test_rendered_405_reload_is_bounded_and_verification_keeps_evidence(self):
        from decodo_scraping_api import ScrapeError
        client = core.EvidenceClient(self.store, "chictr", sleeper=Mock())
        with patch("decodo_scraping_api.cached_token", return_value="secret"), patch(
                "decodo_scraping_api.scrape_content", side_effect=ScrapeError("target", 405)) as fetch:
            with self.assertRaises(core.SourceIssue):
                client.rendered("https://example.test")
        self.assertEqual(fetch.call_count, 2)
        with patch("decodo_scraping_api.cached_token", return_value="secret"), patch(
                "decodo_scraping_api.scrape_content", return_value='<html>验证码</html>') as fetch:
            with self.assertRaisesRegex(core.SourceIssue, "verification_required"):
                client.rendered("https://example.test")
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(len(client.evidence), 1)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = LocalStore(self.temp.name)
        self.settings = StorageSettings()
        self.universe = load_json(ROOT / "examples/sec-filings/universe.json")
        self.taxonomy = load_json(ROOT / "config/sectors.v1.json")
        self.start, self.end = date(2024, 6, 3), date(2024, 6, 4)

    def collect(self, client, **kwargs):
        return core.collect(self.store, self.settings, self.universe, self.taxonomy, "clinicaltrials",
            self.start, self.end, "historical", sources.ClinicalTrials(), client=client, **kwargs)

    def records(self, result):
        manifest = json.loads(self.store.get(result["manifest"]).body)
        return [json.loads(line) for p in manifest["pages"] for b in p["batches"] for line in self.store.get(b["key"]).body.splitlines()]

    def test_partial_resume_preserves_provider_cursor(self):
        first = FakeClient([{"totalCount": 2, "studies": [study()], "nextPageToken": "page2"}])
        partial = self.collect(first, max_pages=1, page_size=1)
        self.assertEqual(partial["status"], "partial")
        second = FakeClient([{"studies": [study(2)]}])
        result = self.collect(second, page_size=1)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(second.calls[0][1]["params"]["pageToken"], "page2")
        records = self.records(result)
        self.assertEqual(len(records), 2)
        self.assertEqual(len({r["run_id"] for r in records}), 2)
        for record in records:
            self.assertEqual(validate_record(record, self.universe), [])
        self.assertTrue(self.collect(FakeClient([]), page_size=1)["already_complete"])

    def test_source_total_change_and_duplicate_record_fail(self):
        for second in ({"totalCount": 3, "studies": [study(2)], "nextPageToken": "page3"},
                       {"totalCount": 2, "studies": [study()]}):
            with self.subTest(second=second):
                first = FakeClient([{"totalCount": 2, "studies": [study()], "nextPageToken": "page2"}])
                self.collect(first, max_pages=1, page_size=1, refresh=True)
                result = self.collect(FakeClient([second]), page_size=1)
                self.assertEqual(result["status"], "failed")

    def test_changed_snapshot_restarts_once_and_commits_fresh_result(self):
        self.collect(FakeClient([{'totalCount':2,'studies':[study()],
                                 'nextPageToken':'page2'}]),max_pages=1,page_size=1)
        changed=FakeClient([{'totalCount':1,'studies':[study(2)]},
                            {'totalCount':1,'studies':[study(2)]}])
        result=self.collect(changed,max_pages=1,page_size=1)
        self.assertEqual(result['status'],'complete')
        self.assertEqual(result['records'],1)
        self.assertIn('refreshed_from_manifest',result)
        self.assertEqual(len(changed.calls),2)

    def test_all_sector_names_match_without_promoting_identity(self):
        names = [c["canonical_name"] for c in self.universe["companies"]]
        result = self.collect(FakeClient([{"totalCount": 4, "studies": [study(i+1, name) for i, name in enumerate(names)]}]))
        records = self.records(result)
        self.assertEqual({s for r in records for s in r["payload"]["candidate_sector_ids"]},
                         {"biotech", "robotics", "semiconductors", "energy_storage"})
        self.assertTrue(all(not r["company_ids"] and r["available_at"] is None for r in records))

    def test_unknown_sponsors_retained_in_discovery_mode(self):
        result = self.collect(FakeClient([{"totalCount": 1, "studies": [study(sponsor="Unknown institution")]}]))
        self.assertEqual(len(self.records(result)), 1)
        self.assertEqual(self.records(result)[0]["payload"]["candidate_company_ids"], [])

    def test_filtered_zero_is_complete_after_source_exhaustion(self):
        result = self.collect(FakeClient([{"totalCount": 1, "studies": [study(sponsor="Unknown institution")]}]), selection="universe")
        self.assertEqual(result["status"], "complete")
        self.assertEqual(self.records(result), [])

    def test_filtered_duplicate_is_detected_across_resume(self):
        unknown = study(sponsor="Unknown institution")
        self.collect(FakeClient([{"totalCount": 2, "studies": [unknown], "nextPageToken": "next"}]),
                     selection="universe", max_pages=1)
        result = self.collect(FakeClient([{"studies": [unknown]}]), selection="universe")
        self.assertEqual(result["reason"], "duplicate_provider_record")

    def test_missing_input_receipt_finishes_failed_attempt(self):
        first = self.collect(FakeClient([{"totalCount": 2, "studies": [study()], "nextPageToken": "next"}]), max_pages=1)
        path = self.store.root / first["manifest"].rsplit("/", 1)[0] / "inputs/00000000.json"
        path.unlink()
        result = self.collect(FakeClient([]))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "missing_committed_input_receipt")

    def test_end_exclusive_and_missing_total_fail(self):
        for response in ({"studies": []}, {"totalCount": 1, "studies": [study(updated="2024-06-04")]}):
            result = self.collect(FakeClient([response]), refresh=True)
            self.assertEqual(result["status"], "failed")

    def test_fda_stage_counts_and_ids(self):
        app = {"application_number": "NDA123", "sponsor_name": "Example Biotech", "submissions": [
            {"submission_status": "AP", "submission_status_date": "20240603", "submission_type": "ORIG", "submission_number": "1"}]}
        client = FakeClient([{"meta": {"results": {"total": 1}}, "results": [app]},
            {"meta": {"results": {"total": 1}}, "results": [{"letter_type": "COMPLETE RESPONSE",
              "letter_date": "06/03/2024", "file_name": "CRL_NDA123.pdf", "company_name": "Example Biotech"}]}])
        adapter = sources.FDA()
        records, state, done = adapter.page(client, self.start, self.end, "historical", {}, 10)
        self.assertFalse(done)
        self.assertEqual(records[0]["id"], "approval:NDA123:ORIG:1")
        letters, _, done = adapter.page(client, self.start, self.end, "historical", state, 10)
        self.assertTrue(done)
        self.assertEqual(letters[0]["date"], "2024-06-03")

    def test_fda_limit_is_explicit_partial(self):
        with self.assertRaises(core.SourceIssue) as raised:
            sources.FDA().page(FakeClient([]), self.start, self.end, "historical", {"count": 25001}, 100)
        self.assertTrue(raised.exception.partial)

    def test_ema_application_and_decision_ids_dates(self):
        client = FakeClient([{"pagination": {"totalRecords": 1, "nextPage": False}, "data": [
            {"ctNumber": "2024-123456-12-00", "decisionDateOverall": "03/06/2024", "sponsor": "Example Biotech"}]},
            {"authorizedApplication": {"applicationInfo": [{"id": 12, "submissionDate": "2024-06-03", "decisions": [
                {"id": 34, "decisionDate": "2024-06-03T12:34:56.123", "decision": "not_authorized"}]}]}}])
        rows, _, done = sources.EMA().page(client, self.start, self.end, "historical", {}, 100)
        self.assertTrue(done)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[-1]["id"], "2024-123456-12-00:decision:34")
        self.assertEqual(rows[-1]["data"]["action"], "REJECTED")

    def test_ema_limit_does_not_report_complete(self):
        with self.assertRaises(core.SourceIssue) as raised:
            sources.EMA().page(FakeClient([]), self.start, self.end, "historical", {"page": 101}, 100)
        self.assertTrue(raised.exception.partial)

    def test_chictr_missing_pagination_does_not_report_zero(self):
        client = Mock()
        client.rendered.return_value = "<html>unexpected page</html>"
        with self.assertRaises(core.SourceIssue):
            sources.ChiCTR().page(client, self.start, self.end, "daily", {}, 100)

    def test_nmpa_repeated_page_fails(self):
        rows = [{"registrationNumber": "CTR202400001", "firstPublicDisclosureDate": "2024-06-02"}]
        client = Mock()
        with patch("regulatory_sources.nmpa_summaries", return_value=rows):
            with self.assertRaisesRegex(core.SourceIssue, "pagination_cycle"):
                sources.NMPA().page(client, self.start, self.end, "daily", {"page_hash": sources.digest(rows)}, 100)

    def test_nmpa_date_comes_from_detail_not_listing(self):
        client = Mock()
        client.rendered.side_effect = [
            '<table><tr><td>CTR20240001</td><td><a href="/detail/one">Synthetic trial</a></td></tr></table>当前第 1 页，共 1 页，共 1 条记录',
            '<div>首次公示信息日期：2024-06-03</div><table><tr><th>登记号</th><td>CTR20240001</td></tr><tr><td>申办者</td><td>Example Biotech</td></tr></table>']
        rows, _, done = sources.NMPA().page(client, self.start, self.end, "daily", {}, 100)
        self.assertTrue(done)
        self.assertEqual(rows[0]["date"], "2024-06-03")
        self.assertEqual(rows[0]["company_names"], ["Example Biotech"])

    def test_japan_current_list_is_not_backdated(self):
        client = Mock()
        row = {"listNumber": "1", "designationDate": "2025-01-01", "recordText": "example"}
        with patch("japan_pmda_designations.parse_pdf", return_value=[row]):
            rows, _, done = sources.Japan().page(client, self.start, self.end, "historical", {}, 100)
        self.assertTrue(done)
        self.assertEqual(rows, [])

    def test_japan_reused_list_numbers_have_distinct_identities(self):
        rows = [{"listNumber": "1", "designationDate": value, "recordText": "example"}
                for value in ("2015-10-27", "2017-04-21")]
        with patch("japan_pmda_designations.parse_pdf", return_value=rows):
            result, _, _ = sources.Japan().page(Mock(), self.start, self.end, "daily", {}, 100)
        self.assertEqual(len({row["id"] for row in result}), 2)

    def test_uk_windows_encoding_preserves_names(self):
        client = Mock()
        client.get.side_effect = [b'<a href="/orphan.csv">Orphan Register</a>',
            'Product name ,Company Name,Date\nExample,Compañía,03/06/2024\n'.encode("cp1252")]
        rows, _, done = sources.UK().page(client, self.start, self.end, "daily", {"stage": 1}, 100)
        self.assertTrue(done)
        self.assertEqual(rows[0]["company_names"], ["Compañía"])

    def test_uk_undated_history_is_partial_not_backdated(self):
        client = Mock()
        client.get.side_effect = [b'<a href="/orphan.csv">Orphan Register</a>',
                                 b'Product name ,Company Name\nExample,Sponsor\n']
        with self.assertRaises(core.SourceIssue) as raised:
            sources.UK().page(client, self.start, self.end, "historical", {"stage": 1}, 100)
        self.assertTrue(raised.exception.partial)

    def test_chictr_record_total_pagination_and_date_boundary(self):
        client = Mock()
        client.rendered.return_value = '<span id="data-total">20</span>'
        rows = [{"registrationDate": "2024-06-02", "registrationNumber": "ChiCTR24000001"}]
        with patch("chictr_studies.parse_search_page", return_value=(rows, None)):
            result, following, done = sources.ChiCTR().page(client, self.start, self.end, "daily", {}, 100)
        self.assertFalse(done)
        self.assertEqual(following['page'], 2)
        self.assertEqual(result, [])

    def test_evidence_excludes_api_key(self):
        class Response(io.BytesIO):
            headers = {}
        opener = Mock(return_value=Response(b'{"results":[]}'))
        client = core.EvidenceClient(self.store, "test", opener=opener, sleeper=lambda _: None)
        client.json("https://example.test/api", params={"limit": "1"}, api_key="secret-test-value")
        self.assertNotIn("secret-test-value", json.dumps(client.evidence))
        self.assertNotIn("api_key", client.evidence[0]["source_url"])
        self.assertTrue(self.store.get(client.evidence[0]["key"]))


if __name__ == "__main__":
    unittest.main()
