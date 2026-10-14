from contextlib import redirect_stdout
from datetime import date
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from collection_storage import StorageSettings, write_json, write_checked
from research_contract import ROOT, canonical_json, load_json
import patent_backfill as backfill
import patent_backfill_publication as publication
from test_patent_bigquery_collection import Client


class PublicationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.settings = StorageSettings(local_root=str(self.root / "store"), s3_bucket="fixture")
        self.store = self.settings.store()
        config = {**load_json(ROOT / "config/patent-backfill.json"), "max_pages": 5,
                  "page_size": 1, "start_date": "2025-01-01", "end_exclusive": "2025-03-01"}
        with patch.object(backfill, "historical_start", return_value=date(2025, 1, 1)):
            self.raw = backfill.Backfill(self.store, self.settings, config,
                load_json(ROOT / "examples/sec-filings/universe.json"),
                load_json(ROOT / "config/sectors.v1.json"))
        self.config = load_json(ROOT / "config/patent-backfill-athena.json")
        self.publisher = publication.Publisher(self.raw, self.config, self.root / "build")
        self.client = Client()
        self.deploys = []
        deploy = patch.object(publication.curated, "deploy", side_effect=self.deploy)
        deploy.start()
        self.addCleanup(deploy.stop)

    def collect(self):
        with redirect_stdout(io.StringIO()):
            return self.raw.run(None, self.client)

    def run_publication(self, **kwargs):
        with redirect_stdout(io.StringIO()):
            return self.publisher.run(**kwargs)

    def deploy(self, store, settings, root):
        # Real prepare/upload; simulate Athena's already-tested verification and
        # durable evidence. This fixture tests orchestration failure boundaries.
        report = load_json(root / "release.json")
        self.deploys.append(report["release_id"])
        verification = {"status": "verified", "release_id": report["release_id"],
            "publication_month": report["publication_month"], "checked_at": "2026-09-24T00:00:00Z"}
        body = canonical_json(verification) + b"\n"
        key = report["release_prefix"] + "/verifications/" + publication.hashlib.sha256(body).hexdigest() + ".json"
        write_checked(store, key, body)
        return verification

    def test_partial_collection_never_published_and_completed_checkpoint_discovered(self):
        self.raw.config["max_pages"] = 1
        self.collect()
        state = self.run_publication()
        self.assertEqual(state["status"], "waiting_for_collection")
        self.assertEqual(state["verified_months"], 0)
        self.assertEqual(self.deploys, [])
        self.collect()
        before_jobs = len(self.client.jobs)
        state = self.run_publication()
        self.assertEqual(state["verified_months"], 1)
        self.assertEqual(state["next_date"], "2025-02-01")
        self.assertEqual(state["verified_publications"], 2)
        self.assertEqual(len(self.client.jobs), before_jobs)
        self.assertEqual(len(self.deploys), 1)
        self.assertEqual(self.run_publication()["status"], "waiting_for_collection")
        self.assertEqual(len(self.deploys), 1)

    def test_collection_progress_required_even_if_terminal_manifest_exists(self):
        self.collect()
        progress, token = backfill.load_stored(self.store, self.raw.progress_key)
        progress["next_date"] = "2025-01-01"
        write_json(self.store, self.raw.progress_key, progress, token)
        self.assertEqual(self.run_publication()["verified_months"], 0)
        self.assertEqual(self.deploys, [])

    def test_failed_verification_retries_pinned_release_without_recollection(self):
        self.collect()
        raw_before = self.store.get(self.raw.progress_key).body
        with patch.object(publication.curated, "deploy", side_effect=RuntimeError("Athena unavailable")):
            first = self.run_publication()
        self.assertEqual(first["status"], "failed")
        self.assertEqual(first["verified_months"], 0)
        identity = first["active"]["release_id"]
        with patch.object(publication.curated, "prepare", side_effect=AssertionError("should reuse prepared release")):
            final = self.run_publication()
        self.assertEqual(final["verified_months"], 1)
        self.assertEqual(final["last_verified"]["release_id"], identity)
        self.assertEqual(self.store.get(self.raw.progress_key).body, raw_before)

    def test_verification_receipt_recovers_crash_before_progress_without_double_count(self):
        self.collect()
        original = publication.write_json
        def write(store, key, value, *args):
            if key == self.publisher.progress_key and value["verified_months"] == 1:
                raise RuntimeError("crash after immutable receipt")
            return original(store, key, value, *args)
        with patch.object(publication, "write_json", side_effect=write):
            state = self.run_publication()
        self.assertEqual(state["status"], "failed")
        self.assertEqual(state["verified_months"], 0)
        self.assertEqual(len(self.deploys), 1)
        self.assertEqual(self.run_publication()["verified_months"], 1)
        self.assertEqual(len(self.deploys), 1)
        self.assertEqual(self.run_publication()["verified_months"], 1)

    def test_month_bound_and_order_then_complete(self):
        self.collect()
        old_page = self.client.page
        def february(*args):
            result = old_page(*args)
            result["rows"][0]["f"][1]["v"] = "2025-02-06"
            return result
        self.client.page = february
        self.collect()
        self.assertEqual(self.run_publication()["verified_months"], 1)
        final = self.run_publication()
        self.assertEqual(final["status"], "complete")
        self.assertEqual(final["verified_months"], 2)
        self.assertEqual(final["verified_publications"], 4)
        self.assertNotEqual(self.deploys[0], self.deploys[1])
        self.assertEqual(self.run_publication()["verified_months"], 2)

    def test_changed_policy_or_destination_stops_before_publication(self):
        self.run_publication()
        self.publisher.contract_hash = "changed"
        with self.assertRaisesRegex(ValueError, "contract changed"):
            self.run_publication()
        self.assertEqual(self.deploys, [])

    def test_corrupt_raw_evidence_does_not_advance_and_repair_can_retry(self):
        self.collect()
        candidate = self.raw.completed_window(date(2025, 1, 1))
        manifest = json.loads(self.store.get(candidate["manifest"]).body)
        key = manifest["pages"][1]["batches"][0]["key"]
        obj = self.store.get(key)
        token = self.store.put(key, b"corrupt", obj.token)
        state = self.run_publication()
        self.assertEqual(state["status"], "failed")
        self.assertEqual(state["verified_months"], 0)
        self.assertEqual(self.deploys, [])
        self.store.put(key, obj.body, token)
        self.assertEqual(self.run_publication()["verified_months"], 1)

    def test_changed_local_release_is_rejected_on_retry(self):
        self.collect()
        with patch.object(publication.curated, "deploy", side_effect=RuntimeError("temporary")):
            state = self.run_publication()
        path = self.publisher.output_root / state["active"]["release_id"] / "release.json"
        report = load_json(path)
        report["authorities"] = {"wrong": 2}
        path.write_bytes(canonical_json(report))
        final = self.run_publication()
        self.assertEqual(final["status"], "failed")
        self.assertEqual(final["verified_months"], 0)
        self.assertIn("changed during retry", final["last_error"]["message"])

    def test_missing_verification_proof_never_advances_cursor(self):
        self.collect()
        original = self.deploy
        def missing_proof(store, settings, root):
            verification = original(store, settings, root)
            verification["checked_at"] = "different"
            return verification
        with patch.object(publication.curated, "deploy", side_effect=missing_proof):
            state = self.run_publication()
        self.assertEqual(state["status"], "failed")
        self.assertEqual(state["verified_months"], 0)
        self.assertEqual(self.run_publication()["status"], "failed")


if __name__ == "__main__":
    unittest.main()
