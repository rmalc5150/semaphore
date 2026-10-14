from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import unittest

import pyarrow.parquet as pq

from collection_operations import Operations, universe_windows
from collection_storage import LocalStore, StorageSettings
from patent_universe import promote, ENTITY_ROOT, ATHENA_ROOT
from research_contract import ROOT, load_json, validate_universe


class PromotionTests(unittest.TestCase):
    def setUp(self):
        self.parent = load_json(ROOT / "config/company-universe.v0.2.json")
        self.registry = load_json(ROOT / "config/company-id-registry.v1.json")
        self.entities = [json.loads(s) for s in (ENTITY_ROOT / "entities.jsonl").read_text().splitlines()]
        self.listings = pq.read_table(ATHENA_ROOT / "tables/patent_listing_reviews/part-00000.parquet").to_pylist()
        self.business = {n: {"url": "https://example.com/" + n, "sha256": "abc", "note": "reviewed business"}
            for n in ["lg_energy", "applied_materials", "samsung_display", "lg_display"]}

    def build(self):
        return promote(self.parent, self.registry, self.entities, self.listings, self.business, "2026-09-23T18:00:00Z")

    def test_ids_are_preserved_and_rebuild_uses_same_new_ids(self):
        original = deepcopy(self.parent)
        u, registry, report = self.build()
        for table, key in (("companies", "company_id"), ("listings", "listing_id"), ("company_aliases", "alias_id"), ("external_identifiers", "identifier_id")):
            self.assertTrue({r[key] for r in self.parent[table]} <= {r[key] for r in u[table]})
        self.assertEqual(self.parent, original)
        rebuilt = promote(self.parent, registry, self.entities, self.listings, self.business, "2026-09-23T18:00:00Z")
        self.assertEqual(rebuilt, (u, registry, report))
        self.assertEqual(len(u["companies"]), 498)
        self.assertFalse(validate_universe(u, load_json(ROOT / "config/sectors.v1.json"))[0])

    def test_wrappers_are_not_merged_with_legal_entity_and_dates_stay_distinct(self):
        u, _, report = self.build()
        companies = {c["company_id"]: c for c in u["companies"]}
        for c in report["retired_placeholder_ids"]:
            self.assertFalse(companies[c]["collection_enabled"])
            self.assertEqual(companies[c]["review_status"], "rejected")
        wrappers = [l for l in u["listings"] if l.get("company_role") == "underlying_issuer"]
        self.assertEqual(len(wrappers), 4)
        self.assertEqual(len({l["company_id"] for l in wrappers}), 1)
        self.assertTrue(all(l["depositary_issuer_name"] for l in wrappers))
        thai = next(l for l in wrappers if l["ticker"] == "AMAT01")
        self.assertEqual((thai["valid_from"], thai["trading_from"]), ("2026-06-17", "2026-06-18"))
        self.assertEqual(next(l for l in wrappers if l["exchange_mic"] == "NEOE")["valid_to"], "2025-12-23")

    def test_display_sector_pending_does_not_enable_collection(self):
        u, _, report = self.build()
        pending = [c for c in u["companies"] if c["company_id"] in report["sector_pending_company_ids"]]
        self.assertEqual(len(pending), 2)
        for c in pending:
            self.assertEqual(c["review_status"], "verified")
            self.assertFalse(c["collection_enabled"])
            self.assertEqual(c["sectors"][0]["review_status"], "pending")
            self.assertIsNone(c["sectors"][0]["valid_from"])

    def test_new_names_match_enabled_companies_without_retired_wrappers(self):
        from regulatory_collection import CompanyMatcher
        u, _, report = self.build()
        matcher = CompanyMatcher(u)
        ids, sectors = matcher.match(["LG ENERGY SOLUTION LTD"])
        self.assertIn(report["registry_entity_company_ids"]["lei:988400QX6P286XA6ZS85"], ids)
        self.assertIn("energy_storage", sectors)
        ids, sectors = matcher.match(["APPLIED MATERIALS INC"])
        self.assertIn(report["registry_entity_company_ids"]["lei:41BNNE1AFPNAZELZ6K07"], ids)
        self.assertFalse(set(ids) & set(report["retired_placeholder_ids"]))
        self.assertFalse(matcher.match(["SAMSUNG DISPLAY CO LTD"])[0])

    def test_unverified_entity_cannot_be_promoted(self):
        row = next(r for r in self.entities if r["selected_lei"])
        row["status"] = "ambiguous_registry_name"
        with self.assertRaisesRegex(ValueError, "Unverified"):
            self.build()

    def test_wrong_listing_identity_is_rejected(self):
        next(r for r in self.listings if r["review_status"] == "supported")["ticker"] = "WRONG"
        with self.assertRaisesRegex(ValueError, "Listing review"):
            self.build()

    def test_conflicting_stable_id_is_rejected(self):
        self.registry["company_keys"]["lei:988400QX6P286XA6ZS85"] = self.parent["companies"][0]["company_id"]
        with self.assertRaisesRegex(ValueError, "unrelated"):
            self.build()

    def test_underlying_company_requires_receipt_and_depositary_metadata(self):
        u, _, _ = self.build()
        receipt = next(l for l in u["listings"] if l.get("company_role") == "underlying_issuer")
        receipt["security_type"] = "ordinary_share"
        self.assertTrue(any("underlying issuer" in e for e in validate_universe(u, load_json(ROOT / "config/sectors.v1.json"))[0]))


class CutoverTests(unittest.TestCase):
    def setUp(self):
        self.config = load_json(ROOT / "config/collection-operations.json")
        self.config["daily_universe_epochs"] = [{"effective_from": "2026-09-24", "universe": "config/company-universe.v0.3.json"}]

    def test_pre_cutover_uses_old_universe_and_same_progress_origin(self):
        windows = universe_windows(self.config, "daily", date(2026,9,21), date(2026,9,24), 3)
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0]["universe"], self.config["universe"])
        self.assertEqual(windows[0]["origin"], date(2026,9,21))

    def test_split_has_no_gap_or_overlap_and_old_reconciliation_expires(self):
        windows = universe_windows(self.config, "daily", date(2026,9,21), date(2026,9,29), 3)
        self.assertEqual(len(windows), 2)
        self.assertEqual(windows[0]["end"], windows[1]["origin"])
        self.assertEqual(windows[0]["reconcile_days"], 0)
        self.assertEqual(windows[1]["universe"], "config/company-universe.v0.3.json")
        self.assertEqual(windows[1]["reconcile_days"], 3)

    def test_historical_runs_do_not_silently_change_their_universe(self):
        windows = universe_windows(self.config, "historical", date(2025,1,1), date(2025,2,1))
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0]["universe"], self.config["universe"])

    def test_cutover_configuration_does_not_change_existing_stream_hash(self):
        universe = load_json(ROOT / self.config["universe"])
        taxonomy = load_json(ROOT / self.config["taxonomy"])
        old = deepcopy(self.config); old.pop("daily_universe_epochs")
        store, settings = LocalStore("/tmp/unused-cutover-test"), StorageSettings()
        self.assertEqual(Operations(store, settings, self.config, universe, taxonomy).identity,
                         Operations(store, settings, old, universe, taxonomy).identity)

    def test_duplicate_cutover_boundaries_are_rejected(self):
        self.config["daily_universe_epochs"] *= 2
        with self.assertRaisesRegex(ValueError, "unique"):
            universe_windows(self.config, "daily", date(2026,9,21), date(2026,9,29))


if __name__ == "__main__":
    unittest.main()
