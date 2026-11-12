import io
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError

from metadata_engine.sec_documents import DocumentError, archive_submission, retrieve_submission, validate_submission, validate_url
from metadata_engine.labelling import label_observation
from test_metadata_engine import CONTRACT, RECORD

ACCESSION = "0000950170-24-067660"
URL = "https://www.sec.gov/Archives/edgar/data/1674416/" + ACCESSION + ".txt"
BODY = ("<SEC-DOCUMENT>" + ACCESSION + ".txt\n<SEC-HEADER>\nACCESSION NUMBER: " + ACCESSION + "\nCENTRAL INDEX KEY: 0001674416\nCONFORMED SUBMISSION TYPE: 8-K\n</SEC-HEADER>\n<DOCUMENT>\n<TYPE>8-K\n<FILENAME>report.htm\n<TEXT><html>Original filing</html></TEXT>\n</DOCUMENT>\n<DOCUMENT>\n<TYPE>EX-99.1\n<FILENAME>exhibit.htm\n<TEXT>Original exhibit</TEXT>\n</DOCUMENT>\n</SEC-DOCUMENT>\n").encode()
PARENT = {"source_url": URL, "source_record_id": ACCESSION, "payload": {"form": "8-K", "issuer_rows": [{"cik": "0001674416"}]}}


class SecDocumentsTests(unittest.TestCase):
    def test_complete_submission_retains_exhibit_inventory(self):
        info = validate_submission(BODY, ACCESSION, ["0001674416"], "8-K")
        self.assertEqual([r["type"] for r in info["documents"]], ["8-K", "EX-99.1"])

    def test_truncated_submission_rejected(self):
        with self.assertRaisesRegex(DocumentError, "incomplete"):
            validate_submission(BODY[:-20], ACCESSION, ["0001674416"], "8-K")

    def test_wrong_accession_issuer_and_form_rejected(self):
        for accession, ciks, form in [("0000950170-24-067661", ["1674416"], "8-K"), (ACCESSION, ["1"], "8-K"), (ACCESSION, ["1674416"], "10-K")]:
            with self.subTest(accession=accession, ciks=ciks, form=form), self.assertRaises(DocumentError):
                validate_submission(BODY, accession, ciks, form)

    def test_block_page_and_metadata_only_rejected(self):
        for body in (b"<title>Access Denied</title>", b"Date: 2024-06-03; Form: 8-K"):
            with self.subTest(body=body), self.assertRaises(DocumentError):
                validate_submission(body, ACCESSION, ["1674416"], "8-K")

    def test_document_block_truncation_rejected(self):
        with self.assertRaisesRegex(DocumentError, "blocks_incomplete"):
            validate_submission(BODY.replace(b"</DOCUMENT>", b"", 1), ACCESSION, ["1674416"], "8-K")

    def test_only_expected_sec_urls_allowed(self):
        validate_url(URL, ACCESSION, ["1674416"])
        for url in (URL.replace("www.sec.gov", "example.com"), URL + "?token=x", URL.replace("1674416", "999"), URL.replace("https:", "http:")):
            with self.subTest(url=url), self.assertRaises(DocumentError):
                validate_url(url, ACCESSION, ["1674416"])

    def test_http_denial_is_not_retried(self):
        opener = Mock()
        opener.open.side_effect = HTTPError(URL, 403, "Forbidden", {}, io.BytesIO(b"denied"))
        with self.assertRaisesRegex(DocumentError, "http_403"):
            retrieve_submission(PARENT, opener)
        self.assertEqual(opener.open.call_count, 1)

    def test_truncated_http_body_rejected(self):
        response = Mock(status=200, headers={"Content-Length": str(len(BODY) + 1)})
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.geturl.return_value = URL
        response.read.return_value = BODY
        opener = Mock()
        opener.open.return_value = response
        with self.assertRaisesRegex(DocumentError, "length_mismatch"):
            retrieve_submission(PARENT, opener)

    def test_corrupt_s3_readback_rejected(self):
        import hashlib
        s3 = Mock()
        s3.get_object.return_value = {"Body": io.BytesIO(b"corrupt")}
        with self.assertRaisesRegex(DocumentError, "checksum_mismatch"):
            archive_submission(s3, "bucket", BODY, {"sha256": hashlib.sha256(BODY).hexdigest()})

    def test_reprocessing_keeps_identity_despite_labelling_clock(self):
        first = label_observation(RECORD, CONTRACT, labelled_at="2026-10-30T11:00:00+00:00")
        second = label_observation(RECORD, CONTRACT, labelled_at="2026-10-30T12:00:00+00:00")
        self.assertEqual(first["observation_id"], second["observation_id"])
        third = label_observation({**RECORD, "record_id": first["record_id"]}, CONTRACT)
        self.assertEqual(first["record_id"], third["record_id"])


if __name__ == "__main__":
    unittest.main()
