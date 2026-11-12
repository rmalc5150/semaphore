"""Real-document extraction and negative matching boundaries for S22/S23."""
import io
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import japan_pmda_designations as japan
import mhra_product_enrichment as mhra
import regulatory_sources as sources
from datetime import date
from regulatory_collection import EvidenceClient

FIXTURES = Path(__file__).parent / "tests/fixtures/regulatory"


class EnrichmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.japan = japan.parse_pdf((FIXTURES / "pmda-sakigake.pdf").read_bytes())
        cls.spc = (FIXTURES / "spexotras-spc.pdf").read_bytes()

    def test_pmda_real_table_has_separate_roles_dates_and_no_page_headers(self):
        self.assertEqual(len(self.japan), 25)
        rows = {(r["designationDate"], r["listNumber"]): r for r in self.japan}
        sanofi = rows[("2017-04-21", "1")]
        self.assertEqual(sanofi["applicantName"], "サノフィ株式会社")
        self.assertEqual(sanofi["marketingAuthorisationHolder"], "サノフィ株式会社")
        self.assertEqual(sanofi["approvalDate"], "2022-03-28")
        self.assertEqual(sanofi["sourcePage"], 2)
        hospital = rows[("2020-06-19", "1")]
        self.assertEqual(hospital["applicantName"], "大阪大学医学部附属病院")
        self.assertIsNone(hospital["marketingAuthorisationHolder"])
        self.assertIn("R7.12.18", hospital["remarks"])
        for row in self.japan:
            self.assertNotIn("日現在", row["recordText"])
            self.assertNotIn("指定を受けた申請者", row["recordText"])

    def test_pmda_cancellations_and_incomplete_source_name_are_explicit(self):
        rows = {r["designatedProductName"]: r for r in self.japan}
        self.assertEqual(rows["M7824"]["cancellationDate"], "2021-12-24")
        self.assertEqual(rows["M7824"]["designationStatus"], "cancelled")
        self.assertIsNone(rows["M7824"]["approvalDate"])
        self.assertTrue(rows["E7090"]["applicantNameReviewRequired"])
        self.assertEqual(rows["E7090"]["applicantName"], "エーザイ株式会")

    def test_pmda_layout_change_fails_instead_of_flattening(self):
        pdf = Mock()
        pdf.__enter__ = Mock(return_value=pdf)
        pdf.__exit__ = Mock(return_value=False)
        pdf.pages = [Mock(extract_tables=Mock(return_value=[[['wrong headers']]]))]
        with patch("pdfplumber.open", return_value=pdf), self.assertRaisesRegex(RuntimeError, "headers changed"):
            japan.parse_pdf(b"fixture")

    def test_uk_multiple_licences_ranges_and_suffixes(self):
        self.assertEqual(mhra.licence_numbers("PLGB 22352/0012/OD1 &\nPLGB 22352/0017/OD1"),
                         ["PLGB223520012", "PLGB223520017"])
        self.assertEqual(mhra.licence_numbers("PLGB 52779/0001-0005OD1"),
                         [f"PLGB52779{number:04d}" for number in range(1, 6)])
        self.assertEqual(mhra.licence_numbers("PLGB/42338/0016/OD2"), ["PLGB423380016"])
        with self.assertRaisesRegex(Exception, "range_invalid"):
            mhra.licence_numbers("PLGB 52779/0001-9999")

    def test_uk_holder_requires_licence_in_real_spc(self):
        match = mhra.spc_holder(self.spc, "PLGB001011227")
        self.assertEqual(match["name"], "Novartis Pharmaceuticals UK Limited")
        self.assertEqual(match["role"], "marketing_authorisation_holder")
        self.assertIsNone(mhra.spc_holder(self.spc, "PLGB001011101"))

    def test_uk_metadata_mismatch_never_downloads_or_matches(self):
        client = Mock(mhra_search_key="public-query-key")
        client.json.return_value = {"@odata.count": 1, "value": [{"pl_number": ["PLGB001011101"]}]}
        self.assertEqual(mhra.enrich(client, "PLGB00101/1227/OD1")["status"], "unresolved")
        client.get.assert_not_called()

    def test_uk_conflicting_holders_remain_unresolved(self):
        client = Mock(mhra_search_key="public-query-key")
        client.json.return_value = {"@odata.count": 2, "value": [
            {"pl_number": ["PLGB001011227"], "metadata_storage_path": "https://mhraproducts4853.blob.core.windows.net/docs/" + str(i)} for i in range(2)]}
        with patch.object(mhra, "spc_holder", side_effect=[{"name": "A Ltd"}, {"name": "B Ltd"}]):
            result = mhra.enrich(client, "PLGB00101/1227/OD1")
        self.assertEqual(result["status"], "unresolved")
        self.assertEqual(result["companyRelationships"], [])

    def test_query_key_is_absent_from_saved_evidence_url(self):
        class Response(io.BytesIO):
            headers = {}
        client = EvidenceClient(Mock(), "uk_mhra", opener=Mock(return_value=Response(b'{}')), sleeper=Mock())
        client.save = Mock(return_value=b'{}')
        client.get(mhra.INDEX, params={"search": "*"}, api_key="test-key", api_key_parameter="api-key")
        self.assertEqual(client.save.call_args.args[1], mhra.INDEX + "?search=%2A")

    def test_japan_adapter_emits_usable_source_names_and_preserves_identity(self):
        client = Mock()
        client.get.return_value = (FIXTURES / "pmda-sakigake.pdf").read_bytes()
        rows, _, done = sources.Japan().page(client, date(2026, 10, 16), date(2026, 10, 17), "daily", {}, 100)
        self.assertTrue(done)
        sanofi = next(r for r in rows if r["id"] == "sakigake:2017-04-21:1")
        self.assertEqual(sanofi["company_names"], ["サノフィ株式会社"])
        eisai = next(r for r in rows if r["id"] == "sakigake:2019-04-08:5")
        self.assertEqual(eisai["company_names"], [])
        self.assertTrue(eisai["data"]["applicantNameReviewRequired"])

    def test_uk_current_and_expired_are_separate_stages_and_enrich_names(self):
        links = b'<a href="/current.csv">Orphan Register</a><a href="/expired.csv">Expired Orphan Register</a>'
        raw = b'Product name ,Designation number\nSpexotras,PLGB 00101/1227/OD1\n'
        for stage, expected_url, expected_status in (
            (1, "https://www.gov.uk/current.csv", "current_orphan_register"),
            (2, "https://www.gov.uk/expired.csv", "expired_or_removed_orphan_register")):
            client = Mock()
            client.get.side_effect = [links, raw]
            with patch.object(mhra, "enrich", return_value={"status": "verified_source_relationship",
                 "companyRelationships": [{"name": "Novartis Pharmaceuticals UK Limited"}]}):
                rows, _, done = sources.UK().page(client, date(2026, 10, 16), date(2026, 10, 17), "daily", {"stage": stage}, 100)
            self.assertEqual(client.get.call_args.args[0], expected_url)
            self.assertEqual(rows[0]["data"]["registerStatus"], expected_status)
            self.assertEqual(rows[0]["company_names"], ["Novartis Pharmaceuticals UK Limited"])
            self.assertEqual(done, stage == 2)

    def test_uk_secondary_lookup_failure_preserves_unresolved_source_row(self):
        from regulatory_collection import SourceIssue
        client = Mock()
        client.get.side_effect = [b'<a href="/current.csv">Orphan Register</a>',
            b'Product name ,Designation number\nExample,PLGB 00101/1227/OD1\n']
        with patch.object(mhra, "enrich", side_effect=SourceIssue("source_retries_exhausted", True)):
            rows, _, _ = sources.UK().page(client, date(2026, 10, 16), date(2026, 10, 17), "daily", {"stage": 1}, 100)
        self.assertEqual(rows[0]["company_names"], [])
        self.assertEqual(rows[0]["data"]["holderEnrichment"]["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
