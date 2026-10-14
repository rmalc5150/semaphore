"""Offline verification of clinical/regulatory curation and source integrity."""
import copy
from datetime import date
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from collection_storage import LocalStore, StorageSettings
from research_contract import ROOT, load_json, seal_record
from regulatory_collection import EvidenceClient, collect
from regulatory_sources import ClinicalTrials
from test_regulatory_collection import study
import regulatory_athena as curate


class CurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = LocalStore(self.temp.name)
        self.universe = load_json(ROOT / "examples/sec-filings/universe.json")
        taxonomy = load_json(ROOT / "config/sectors.v1.json")
        self.manifests = []
        for mode in ("historical", "daily"):
            class Response(io.BytesIO):
                headers = {}
            body = json.dumps({"totalCount": 1, "studies": [study()]}).encode()
            client = EvidenceClient(self.store, "clinicaltrials_gov", opener=Mock(return_value=Response(body)), sleeper=lambda _: None)
            result = collect(self.store, StorageSettings(), self.universe, taxonomy, "clinicaltrials", date(2024,6,3), date(2024,6,4), mode,
                             ClinicalTrials(), client=client)
            self.manifests.append(result["manifest"])

    def test_repeated_evidence_retrieval_is_one_version_two_observations(self):
        entries, universe, _ = curate.read_inputs(self.store, self.manifests)
        tables = curate.curate(entries, universe)
        self.assertEqual(len(tables["research_records"]), 1)
        self.assertEqual(len(tables["record_versions"]), 1)
        self.assertEqual(len(tables["record_observations"]), 2)
        self.assertEqual(len(tables["clinical_trials"]), 1)
        self.assertEqual(tables["record_companies"][0]["match_status"], "candidate")
        self.assertIsNone(tables["clinical_trials"][0]["available_at"])

    def test_real_content_revision_is_preserved(self):
        entries, universe, _ = curate.read_inputs(self.store, self.manifests)
        new = copy.deepcopy(next(iter(entries.values())))
        new["record"]["payload"]["data"]["protocolSection"]["statusModule"]["overallStatus"] = "COMPLETED"
        new["record"]["ingested_at"] = "2099-01-01T00:00:00Z"
        new["record"] = seal_record(new["record"])
        entries[new["record"]["observation_id"]] = new
        tables = curate.curate(entries, universe)
        self.assertEqual(len(tables["record_versions"]), 2)
        self.assertEqual(tables["research_records"][0]["version_count"], 2)

    def test_partial_manifest_never_curated(self):
        path = self.store.root / self.manifests[0]
        document = json.loads(path.read_text())
        document["status"] = "partial"
        path.write_text(json.dumps(document))
        with self.assertRaisesRegex(ValueError, "complete"):
            curate.read_inputs(self.store, self.manifests)

    def test_evidence_corruption_rejected(self):
        entries, _, _ = curate.read_inputs(self.store, self.manifests)
        key = next(iter(entries.values()))["record"]["payload"]["source_evidence"][0]["key"]
        (self.store.root / key).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "evidence checksum"):
            curate.read_inputs(self.store, self.manifests)

    def test_release_round_trip_and_expected_queries(self):
        config = {"database": "optima_regulatory_pilot", "workgroup": "optima-regulatory-pilot", "region": "us-east-1",
                  "curated_prefix": "curated/regulatory_pilot/releases", "query_results_prefix": "athena-results/regulatory-pilot",
                  "source_manifests": self.manifests}
        root = curate.prepare(self.store, StorageSettings(backend="s3", s3_bucket="test-bucket"), config, Path(self.temp.name) / "curated")
        report = load_json(root / "release.json")
        self.assertEqual(report["expected_results"]["quality"], [["1", "1", "2", "0"]])
        self.assertEqual(len(report["files"]), 9)
        self.assertEqual(report["catalog_owner"], "regulatory")


if __name__ == "__main__":
    unittest.main()
