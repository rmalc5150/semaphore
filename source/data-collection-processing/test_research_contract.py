"""Offline contract tests focused on identity, historical dates, and entity joins."""

import copy
import json
import unittest
from pathlib import Path
from uuid import uuid4

from jsonschema import Draft7Validator

from research_contract import (
    ROOT, SCHEMA_PATH, load_json, record_id, seal_record, validate_record,
    validate_taxonomy, validate_universe,
)


class ResearchContractTests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = load_json(ROOT / "config/sectors.v1.json")
        self.universe = load_json(ROOT / "examples/research-contract/universe.json")
        path = ROOT / "examples/research-contract/records.jsonl"
        self.records = [json.loads(line) for line in path.read_text().splitlines()]

    def test_schema_and_all_fixtures(self):
        Draft7Validator.check_schema(load_json(SCHEMA_PATH))
        self.assertEqual(validate_universe(self.universe, self.taxonomy), ([], []))
        for record in self.records:
            self.assertEqual(validate_record(record, self.universe), [])

    def test_pilot_is_global_provisional_and_covers_all_sectors(self):
        pilot = load_json(ROOT / "config/company-universe.v0.1.json")
        errors, warnings = validate_universe(pilot, self.taxonomy)
        self.assertEqual(errors, [])
        self.assertTrue(warnings)
        self.assertEqual(len(pilot["companies"]), 20)
        self.assertEqual(pilot["scope"]["geography"], "global")
        self.assertTrue(pilot["scope"]["include_private_companies"])
        self.assertEqual({c["review_status"] for c in pilot["companies"]}, {"pending"})
        self.assertEqual({m["sector_id"] for c in pilot["companies"] for m in c["sectors"]},
                         {"biotech", "robotics", "semiconductors", "energy_storage"})

    def test_storage_scope_cannot_silently_drop_hydrogen(self):
        energy = next(s for s in self.taxonomy["sectors"] if s["sector_id"] == "energy_storage")
        energy["subsectors"] = [s for s in energy["subsectors"] if s["subsector_id"] != "hydrogen_storage"]
        self.assertTrue(validate_taxonomy(self.taxonomy))

    def test_duplicate_ids_and_broken_references(self):
        self.universe["companies"].append(copy.deepcopy(self.universe["companies"][0]))
        self.universe["listings"][0]["company_id"] = "cmp_" + str(uuid4())
        errors, _ = validate_universe(self.universe, self.taxonomy)
        self.assertTrue(any("duplicate ID" in e for e in errors))
        self.assertTrue(any("unknown company_id" in e for e in errors))

    def test_bad_relationship_endpoint_type(self):
        relationship = self.universe["relationships"][0]
        relationship["subject_id"] = self.universe["people"][0]["person_id"]
        errors, _ = validate_universe(self.universe, self.taxonomy)
        self.assertTrue(any("endpoint types" in e for e in errors))

    def test_invalid_calendar_date_and_interval(self):
        alias = self.universe["company_aliases"][0]
        alias["valid_from"] = "2025-02-30"
        self.assertTrue(validate_universe(self.universe, self.taxonomy)[0])
        alias["valid_from"] = alias["valid_to"]
        self.assertTrue(validate_universe(self.universe, self.taxonomy)[0])

    def test_subsector_must_belong_to_sector(self):
        self.universe["companies"][0]["sectors"][0]["subsector_ids"] = ["hydrogen_storage"]
        errors, _ = validate_universe(self.universe, self.taxonomy)
        self.assertTrue(any("subsector" in e for e in errors))

    def test_ticker_reuse_allowed_only_in_nonoverlapping_intervals(self):
        old = self.universe["listings"][0]
        new = copy.deepcopy(old)
        new["listing_id"] = "lst_" + str(uuid4())
        new["company_id"] = self.universe["companies"][1]["company_id"]
        self.universe["listings"].append(new)
        self.assertTrue(validate_universe(self.universe, self.taxonomy)[0])
        old["valid_to"] = "2025-01-01"
        new["valid_from"] = "2025-01-01"
        self.assertEqual(validate_universe(self.universe, self.taxonomy)[0], [])

    def test_conflicting_verified_external_identifier(self):
        other = copy.deepcopy(self.universe["external_identifiers"][0])
        other["identifier_id"] = "xid_" + str(uuid4())
        other["entity_id"] = self.universe["companies"][1]["company_id"]
        self.universe["external_identifiers"].append(other)
        self.assertTrue(validate_universe(self.universe, self.taxonomy)[0])

    def test_shared_alias_is_ambiguous_not_an_automatic_merge(self):
        alias = copy.deepcopy(self.universe["company_aliases"][0])
        alias["alias_id"] = "als_" + str(uuid4())
        alias["company_id"] = self.universe["companies"][1]["company_id"]
        self.universe["company_aliases"].append(alias)
        errors, warnings = validate_universe(self.universe, self.taxonomy)
        self.assertEqual(errors, [])
        self.assertTrue(any("ambiguous alias" in w for w in warnings))

    def test_revision_preserves_record_identity_but_changes_observation(self):
        original, revision = self.records[:2]
        self.assertEqual(original["record_id"], revision["record_id"])
        self.assertNotEqual(original["observation_id"], revision["observation_id"])
        self.assertNotEqual(original["payload_hash"], revision["payload_hash"])
        self.assertEqual(seal_record(original), original)

    def test_identity_is_unambiguous_and_source_scoped(self):
        self.assertNotEqual(record_id("a", "b", "c|d"), record_id("a", "b|c", "d"))
        self.assertNotEqual(record_id("a", "b", "c"), record_id("different", "b", "c"))

    def test_payload_tampering_is_detected(self):
        record = self.records[0]
        record["payload"]["version"] = 99
        errors = validate_record(record, self.universe)
        self.assertTrue(any("payload_hash" in e for e in errors))
        self.assertTrue(any("observation_id" in e for e in errors))

    def test_availability_requires_evidence_and_known_basis(self):
        record = self.records[0]
        record["availability_evidence"] = []
        self.assertTrue(validate_record(seal_record(record), self.universe))
        record["available_at"] = None
        self.assertTrue(validate_record(seal_record(record), self.universe))

    def test_date_precision_and_timezone_are_not_invented(self):
        record = self.records[0]
        self.assertEqual(record["event_at"]["precision"], "day")
        self.assertIsNone(record["event_at"]["source_timezone"])
        record["event_at"]["precision"] = "second"
        self.assertTrue(validate_record(seal_record(record), self.universe))
        record["event_at"] = {"value": "2024-06-03T10:00:00", "precision": "second", "source_timezone": None}
        self.assertTrue(validate_record(seal_record(record), self.universe))

    def test_unknown_availability_is_preserved(self):
        record = self.records[2]
        self.assertEqual(validate_record(record, self.universe), [])
        self.assertIsNone(record["available_at"])

    def test_record_references_and_universe_version(self):
        record = self.records[0]
        record["company_ids"] = ["cmp_" + str(uuid4())]
        record["universe_version"] = "99.0.0"
        errors = validate_record(seal_record(record), self.universe)
        self.assertTrue(any("unknown entity" in e for e in errors))
        self.assertTrue(any("universe_version" in e for e in errors))

    def test_listing_company_must_be_linked(self):
        record = self.records[0]
        record["company_ids"] = []
        record["listing_ids"] = [self.universe["listings"][0]["listing_id"]]
        self.assertTrue(validate_record(seal_record(record), self.universe))

    def test_nonfinite_numbers_are_not_valid_payloads(self):
        record = self.records[0]
        record["payload"]["bad"] = float("nan")
        self.assertTrue(validate_record(record, self.universe))


if __name__ == "__main__":
    unittest.main()
