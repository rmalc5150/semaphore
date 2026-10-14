"""Offline tests for committed-source curation and immutable publication."""
import copy
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import pyarrow.parquet as pq

from collection_storage import LocalStore, StorageSettings
from research_contract import ROOT, load_json, seal_record
import sec_filings as sec
import sec_athena_pilot as pilot


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = LocalStore(self.root / "raw")
        self.universe = load_json(ROOT / "examples/sec-filings/universe.json")
        self.taxonomy = load_json(ROOT / "config/sectors.v1.json")
        client = Mock()
        client.fetch.return_value = (ROOT / "examples/sec-filings/master-2024-q2.idx").read_bytes()
        self.manifests = []
        for mode in ("historical", "daily"):
            result = sec.collect_window(self.store, StorageSettings(), self.universe, self.taxonomy,
                client, date(2024, 6, 3), date(2024, 6, 8), mode,
                {"selection": "universe", "ciks": [], "forms": []}, sec.CompanyMatcher(self.universe), {})
            self.manifests.append(result["manifest"])
        self.settings = StorageSettings(backend="s3", s3_bucket="test-bucket")
        self.config = {"database": "optima_sec_pilot", "workgroup": "optima-sec-pilot",
            "region": "us-east-1", "curated_prefix": "curated/sec_pilot/releases",
            "query_results_prefix": "athena-results/sec-pilot", "source_manifests": self.manifests}

    def inputs(self):
        return pilot.read_inputs(self.store, self.manifests)

    def change_json(self, key, mutate):
        path = self.store.root / key
        value = json.loads(path.read_text())
        mutate(value)
        path.write_text(json.dumps(value))

    def test_deduplicates_filings_preserves_observations_and_cofilers(self):
        entries, universe, _ = self.inputs()
        tables = pilot.curate(entries, universe)
        self.assertEqual(len(tables["sec_filings"]), 5)
        self.assertEqual(len(tables["sec_filing_versions"]), 5)
        self.assertEqual(len(tables["sec_observations"]), 10)
        self.assertEqual(len(tables["sec_filing_companies"]), 6)
        self.assertEqual(pilot.sector_counts(tables), {"biotech": 1, "energy_storage": 2, "robotics": 2, "semiconductors": 1})
        self.assertTrue(all(r["available_at"] is None for r in tables["sec_filings"]))

    def test_multi_form_accession_is_verified_against_both_source_rows(self):
        raw = (ROOT / 'examples/sec-filings/master-2024-q2.idx').read_bytes()
        line = next(line for line in raw.decode('latin-1').splitlines() if 'edgar/data/' in line)
        parts = line.split('|'); original = parts[2]; parts[2] = 'SC TO-I'
        client = Mock()
        client.fetch.return_value = raw + ('\n' + '|'.join(parts) + '\n').encode('latin-1')
        result = sec.collect_window(self.store, StorageSettings(), self.universe, self.taxonomy,
            client, date(2024,6,3), date(2024,6,8), 'daily',
            {'selection': 'universe', 'ciks': [], 'forms': []}, sec.CompanyMatcher(self.universe), {}, refresh=True)
        entries, universe, _ = pilot.read_inputs(self.store, [result['manifest']])
        records = [entry['record'] for entry in entries.values() if entry['record']['payload'].get('index_forms')]
        self.assertEqual(records[0]['payload']['index_forms'], sorted([original, 'SC TO-I']))
        tables = pilot.curate(entries, universe)
        self.assertTrue(any(row['form'] == ' / '.join(sorted([original, 'SC TO-I'])) for row in tables['sec_filings']))

    def test_revision_preserved_and_latest_observed_selected(self):
        entries, universe, _ = self.inputs()
        entry = copy.deepcopy(next(iter(entries.values())))
        record = entry["record"]
        record["payload"]["form"] = "8-K/A"
        record["ingested_at"] = "2099-01-01T00:00:00Z"
        entry["record"] = seal_record(record)
        entries[entry["record"]["observation_id"]] = entry
        tables = pilot.curate(entries, universe)
        self.assertEqual(len(tables["sec_filing_versions"]), 6)
        revised = next(r for r in tables["sec_filings"] if r["record_id"] == record["record_id"])
        self.assertEqual(revised["form"], "8-K/A")
        self.assertEqual(revised["version_count"], 2)
        self.assertEqual(revised["observation_count"], 3)

    def test_candidates_not_promoted_and_rejected_sectors_not_counted(self):
        entries, universe, _ = self.inputs()
        for entry in entries.values():
            record = entry["record"]
            record["payload"]["candidate_company_ids"] = record["company_ids"]
            record["company_ids"] = []
            record["entity_match_status"] = "unresolved"
        universe["companies"][0]["sectors"][0]["review_status"] = "rejected"
        tables = pilot.curate(entries, universe)
        self.assertTrue(all(link["match_status"] == "candidate" for link in tables["sec_filing_companies"]))
        self.assertNotIn(universe["companies"][0]["sectors"][0]["sector_id"], pilot.sector_counts(tables))

    def test_failed_run_rejected(self):
        self.change_json(self.manifests[0], lambda v: v.update(status="failed"))
        with self.assertRaisesRegex(ValueError, "not complete"):
            self.inputs()

    def test_orphan_final_manifest_rejected(self):
        final = json.loads(self.store.get(self.manifests[0]).body)
        self.change_json("checkpoints/" + final["task_id"] + "/head.json", lambda v: v.update(terminal_history=[]))
        with self.assertRaisesRegex(ValueError, "not committed"):
            self.inputs()

    def test_corrupt_batch_rejected(self):
        final = json.loads(self.store.get(self.manifests[0]).body)
        key = final["pages"][0]["batches"][0]["key"]
        (self.store.root / key).write_bytes(b"{}\n")
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.inputs()

    def test_corrupt_source_evidence_rejected(self):
        snapshot = json.loads(self.store.get(self.manifests[0].rsplit("/", 1)[0] + "/input.json").body)
        (self.store.root / snapshot["key"]).write_bytes(b"changed\n")
        with self.assertRaisesRegex(ValueError, "snapshot hash"):
            self.inputs()

    def test_inherited_or_repeated_manifest_does_not_duplicate_observations(self):
        entries, _, inputs = pilot.read_inputs(self.store, self.manifests + self.manifests)
        self.assertEqual(len(entries), 10)
        self.assertEqual(len(inputs), 2)

    def test_prepare_publish_rerun_is_idempotent_and_parquet_typed(self):
        root = pilot.prepare(self.store, self.settings, self.config, self.root / "build")
        again = pilot.prepare(self.store, self.settings, self.config, self.root / "build")
        self.assertEqual(root, again)
        table = pq.ParquetFile(root / "tables/sec_filings/part-00000.parquet").read()
        self.assertEqual(table.num_rows, 5)
        self.assertEqual(str(table.schema.field("filing_date").type), "date32[day]")
        destination = LocalStore(self.root / "published")
        pilot.publish(destination, self.settings, root)
        pilot.publish(destination, self.settings, root)
        report = load_json(root / "release.json")
        self.assertIsNotNone(destination.get(report["release_prefix"] + "/release.json"))

    def test_local_changes_rejected_before_publication(self):
        root = pilot.prepare(self.store, self.settings, self.config, self.root / "build")
        (root / "tables/sec_filings/part-00000.parquet").write_bytes(b"bad")
        destination = LocalStore(self.root / "published")
        with self.assertRaisesRegex(ValueError, "Local release changed"):
            pilot.publish(destination, self.settings, root)
        self.assertFalse(destination.root.exists())

    def test_chunked_release_preserves_every_curated_value(self):
        entries, universe, inputs = self.inputs()
        template = next(iter(entries.values()))
        expanded = {}
        for i in range(600):
            entry = copy.deepcopy(template)
            entry['record']['observation_id'] = f'observation_{i:06d}'
            expanded[entry['record']['observation_id']] = entry
        expected = pilot.curate(expanded, universe)
        with patch.object(pilot, 'read_inputs', return_value=(expanded, universe, inputs)):
            root = pilot.prepare(self.store, self.settings, self.config, self.root / 'chunked')
        for name, rows in expected.items():
            actual = pq.ParquetFile(root / f'tables/{name}/part-00000.parquet').read().to_pylist()
            self.assertEqual(actual, rows, name)
        observations = pq.ParquetFile(root / 'tables/sec_observations/part-00000.parquet')
        self.assertEqual(observations.num_row_groups, 3)


if __name__ == "__main__":
    unittest.main()
