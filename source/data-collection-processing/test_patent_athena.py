import copy
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest

import pyarrow as pa
import pyarrow.parquet as pq

from collection_storage import LocalStore, write_checked
from patent_athena import SCHEMAS, assignment_rows, listing_reviews, publication_rows, read_review, reconcile
from patent_entity_review import put_local
from research_contract import ROOT, canonical_json, digest, load_json
from sec_athena_pilot import ARROW_TYPES


def decision():
    return {"observation_id": "obs", "record_id": "rec", "source": "google_patents_bigquery",
        "publication_number": "US-2025000001-A1", "application_number": "US-202412345678-A", "title": "Example",
        "source_url": "https://example.com/patent", "source_payload_hash": "hash", "source_evidence": [],
        "publication_date": "2025-01-01", "point_in_time_eligible": False, "current_owner_company_ids": [],
        "reported_parties": [{"reported_name": "Example Inc", "role": "publication_assignee", "status": "ambiguous",
            "company_id": None, "candidate_company_ids": ["listing_company1", "listing_company2"], "reason": "multiple_candidates"}],
        "supported_technology": [{"sector_id": "energy_storage", "category": "batteries", "basis": "cpc", "cpc_codes": ["H01M10/00"]}],
        "pending_technology": [{"sector_id": "robotics", "category": "robotics", "reason": "broad_term", "cpc_hits": ["G05D1"]}],
        "research_sector_ids": ["energy_storage"], "review_reasons": ["multiple_company_entities_require_identifier_reconciliation", "technology_document_review_needed"]}


def entity():
    return {"reported_name": "Example Inc", "selected_lei": "EXAMPLE", "registry_entity_id": "lei:EXAMPLE",
        "status": "registry_name_supported", "candidates": [{"lei": "EXAMPLE", "legal_name": "Example Inc"}]}


class PatentAthenaTests(unittest.TestCase):
    def test_supported_registry_name_does_not_merge_listing_company_ids(self):
        rows = list(publication_rows([decision()], [entity()], []))
        publication = next(r for n, r in rows if n == "patent_publications")
        party = next(r for n, r in rows if n == "patent_party_links")
        self.assertTrue(publication["has_supported_name_link"])
        self.assertEqual(publication["supported_company_ids"], [])
        self.assertEqual(publication["registry_entity_ids"], ["lei:EXAMPLE"])
        self.assertEqual(party["candidate_company_ids"], ["listing_company1", "listing_company2"])
        self.assertEqual(publication["current_ownership_status"], "not_established")
        self.assertFalse(publication["point_in_time_eligible"])
        self.assertIsNone(publication["available_at"])

    def test_pending_sector_does_not_enter_supported_sector_array(self):
        rows = list(publication_rows([decision()], [], []))
        sectors = [r for n, r in rows if n == "patent_sector_reviews"]
        self.assertEqual([s["review_status"] for s in sectors], ["supported", "pending"])
        self.assertEqual(sectors[1]["cpc_codes"], ["G05D1"])
        publication = next(r for n, r in rows if n == "patent_publications")
        self.assertEqual(publication["supported_sector_ids"], ["energy_storage"])

    def test_ambiguous_registry_evidence_clears_previous_company_claim(self):
        d, e = decision(), entity()
        d["reported_parties"][0].update(company_id="old", status="registry_name_supported")
        e.update(status="ambiguous_registry_name", registry_entity_id=None, selected_lei=None)
        publication = next(r for n, r in publication_rows([d], [e], []) if n == "patent_publications")
        self.assertFalse(publication["has_supported_name_link"])
        self.assertEqual(publication["supported_company_ids"], [])

    def test_exact_verified_identifier_can_link_existing_company(self):
        u = {"companies": [{"company_id": "company", "canonical_name": "Example Inc", "review_status": "verified", "entity_type": "legal_entity"}],
             "external_identifiers": [{"entity_id": "company", "system": "lei", "value": "EXAMPLE", "review_status": "verified"}]}
        reconciled = reconcile(u, [entity()], [])
        self.assertEqual(reconciled[0]["company_id"], "company")
        u["external_identifiers"][0]["review_status"] = "pending"
        self.assertIsNone(reconcile(u, [entity()], [])[0]["company_id"])

    def test_duplicate_verified_ids_remain_a_conflict(self):
        u = {"companies": [{"company_id": c, "canonical_name": "Example Inc", "review_status": "verified", "entity_type": "legal_entity"} for c in ("one", "two")],
             "external_identifiers": [{"entity_id": c, "system": "lei", "value": "EXAMPLE", "review_status": "verified"} for c in ("one", "two")]}
        row = reconcile(u, [entity()], [])[0]
        self.assertIsNone(row["company_id"])
        self.assertEqual(row["review_status"], "identifier_conflict")

    def test_duplicate_observations_and_title_inference_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            list(publication_rows([decision(), decision()], [], []))
        d = decision(); d["current_owner_company_ids"] = ["invented"]
        with self.assertRaisesRegex(ValueError, "title"):
            list(publication_rows([d], [], []))

    def test_published_evidence_checks_all_file_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "review"; root.mkdir()
            store = LocalStore(Path(temp) / "store")
            meta = put_local(root, "rows.jsonl", b"{}\n")
            report = {"release_id": "id", "files": {"rows.jsonl": meta}}
            raw = canonical_json(report) + b"\n"
            (root / "review.json").write_bytes(raw)
            write_checked(store, "prefix/id/review.json", raw)
            write_checked(store, "prefix/id/rows.jsonl", b"{}\n")
            self.assertEqual(read_review(store, root, "prefix", "id"), report)
            (store.root / "prefix/id/rows.jsonl").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "checksum"):
                read_review(store, root, "prefix", "id")

    def test_exchange_review_preserves_wrappers_and_historical_bounds(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            body = b"Example Co CDR exchange bulletin"
            meta = put_local(root, "source.html", body)
            put_local(root, "manifest.json", canonical_json([{"name": "exchange", "file": "source.html", "url": "https://example.com/notice", "retrieved_at": "2026-09-23T00:00:00Z", **meta}]))
            u = {"companies": [{"company_id": "wrapper", "canonical_name": "Example Inc"}], "listings": [
                {"listing_id": "listing", "company_id": "wrapper", "exchange_mic": "NEOE", "ticker": "EX", "security_type": "ordinary_share"}]}
            original = copy.deepcopy(u)
            policy = {"universe_hash": digest(u), "decisions": [{"listing_id": "listing", "exchange_mic": "NEOE", "ticker": "EX", "registry_entity_id": "lei:EXAMPLE",
                "relationship_type": "depositary_receipt_on_underlying_issuer", "security_type": "canadian_depositary_receipt", "depositary_issuer_name": "Bank",
                "listed_from": "2025-02-04", "trading_from": "2025-02-04", "valid_to_exclusive": "2025-12-23", "source_date": "2025-12-23",
                "source_name": "exchange", "required_text": ["Example Co", "CDR"]}]}
            row = listing_reviews(u, [entity()], policy, root)[0]
            self.assertEqual(row["review_status"], "supported")
            self.assertEqual(row["valid_to_exclusive"], date(2025,12,23))
            self.assertEqual(row["original_company_id"], "wrapper")
            self.assertEqual(u, original)
            policy["decisions"][0]["ticker"] = "OTHER"
            with self.assertRaisesRegex(ValueError, "identity"):
                listing_reviews(u, [entity()], policy, root)

    def test_assignment_events_preserve_tied_recipients_and_missing_history(self):
        event = {"reel_frame": "1/1", "event_kind": "assignment", "conveyance": "ASSIGNMENT", "document_url": None,
                 "assignees": [{"assigneeNameText": "Example Inc"}], "assignors": [], "recorded_date": "2025-01-01", "received_date": None}
        history = {"events": [event, event], "latest_recorded_assignment_events": [event, event], "chain_completeness": "not_established"}
        r = {"observation_id": "obs", "source_record_id": "12345678", "source_url": "https://example.com", "payload": {"source_evidence": [], "data": {"assignment_history": history}}}
        rows = list(assignment_rows({"obs": {"record": r}}, {}))
        self.assertEqual(sum(n == "patent_assignment_events" for n,r in rows), 2)
        self.assertTrue(all(r["is_latest_recorded_assignment"] for n,r in rows if n == "patent_assignment_events"))
        self.assertEqual(rows[0][1]["comparison_status"], "outside_registry_comparison_cohort")

    def test_publication_sector_party_parquet_schema_round_trip(self):
        tables = {n: [] for n in SCHEMAS}
        for name, row in publication_rows([decision()], [entity()], []):
            tables[name].append(row)
        with tempfile.TemporaryDirectory() as temp:
            for name, rows in tables.items():
                table = pa.Table.from_pylist(rows, schema=pa.schema([(n, ARROW_TYPES[k]) for n,k in SCHEMAS[name]]))
                path = Path(temp) / (name + ".parquet")
                pq.write_table(table, path)
                self.assertTrue(pq.ParquetFile(path).read().equals(table))


if __name__ == "__main__":
    unittest.main()
