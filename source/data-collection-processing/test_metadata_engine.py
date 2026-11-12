import unittest

from metadata_engine.labelling import label_observation


CONTRACT = {"source_key": "sec_edgar", "contract_version": "1.0.0", "adapter": "filings_xbrl", "adapter_version": "1.0.0", "record_kind": "filing", "license_policy_id": "public-sec-edgar-v1", "raw_requirements": {"version": "1.0.0", "minimum_completeness": "complete", "required_artifact_kinds": ["provider_record", "primary_document"], "forbidden_shortcuts": ["abstract_only", "index_only", "title_date_only", "third_party_metadata_only"]}}
RECORD = {"source": "sec_edgar", "dataset": "filings", "source_record_id": "0001", "source_record_id_basis": "provider", "raw_s3_uri": "s3://example/raw.json", "raw_sha256": "a" * 64, "raw_completeness_status": "complete", "raw_artifacts": [{"artifact_kind": "provider_record", "s3_uri": "s3://example/raw.json", "sha256": "a" * 64, "origin": "first_party_source"}, {"artifact_kind": "primary_document", "s3_uri": "s3://example/document.html", "sha256": "b" * 64, "origin": "first_party_source"}], "source_url": "https://www.sec.gov/example", "ingested_at": "2026-10-30T10:00:00+00:00", "payload": {"form": "10-K"}}


class MetadataLabellingTests(unittest.TestCase):
    def test_replay_is_idempotent(self):
        first = label_observation(RECORD, CONTRACT, labelled_at="2026-10-30T11:00:00+00:00")
        second = label_observation(RECORD, CONTRACT, labelled_at="2026-10-30T11:00:00+00:00")
        self.assertEqual(first["observation_id"], second["observation_id"])
        self.assertEqual(first["entity_match_status"], "unresolved")

    def test_raw_evidence_is_required(self):
        broken = dict(RECORD)
        broken.pop("raw_sha256")
        with self.assertRaisesRegex(ValueError, "raw S3 URI"):
            label_observation(broken, CONTRACT, labelled_at="2026-10-30T11:00:00+00:00")

    def test_source_must_match_contract(self):
        broken = dict(RECORD, source="other")
        with self.assertRaisesRegex(ValueError, "source does not match"):
            label_observation(broken, CONTRACT, labelled_at="2026-10-30T11:00:00+00:00")

    def test_abstract_only_input_is_rejected(self):
        broken = dict(RECORD, raw_limitations=["abstract_only"])
        with self.assertRaisesRegex(ValueError, "forbidden"):
            label_observation(broken, CONTRACT, labelled_at="2026-10-30T11:00:00+00:00")

    def test_missing_required_primary_document_is_rejected(self):
        broken = dict(RECORD, raw_artifacts=RECORD["raw_artifacts"][:1])
        with self.assertRaisesRegex(ValueError, "required raw artifact"):
            label_observation(broken, CONTRACT, labelled_at="2026-10-30T11:00:00+00:00")
