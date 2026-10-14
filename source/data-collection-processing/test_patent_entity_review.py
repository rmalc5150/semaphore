import copy
import json
from pathlib import Path
import tempfile
import unittest

from patent_entity_review import build, checked_body, name_key, put_local, resolve
from research_contract import canonical_json, digest


def registry(lei="EXAMPLE1", name="Example Company Limited", **changes):
    value = {"lei": lei, "entity": {"legalName": {"name": name}, "status": "ACTIVE", "jurisdiction": "GB",
        "otherNames": [], "transliteratedOtherNames": []},
        "registration": {"status": "ISSUED", "corroborationLevel": "FULLY_CORROBORATED"}}
    value.update(changes)
    return {"attributes": value}


def response(*rows, total=None):
    return {"data": list(rows), "meta": {"pagination": {"total": len(rows) if total is None else total}}, "links": {"next": None}}


class EntityReviewTests(unittest.TestCase):
    def test_suffix_expansion_preserves_entity_distinctions(self):
        self.assertEqual(name_key("Example Co., Ltd."), name_key("Example Company Limited"))
        self.assertNotEqual(name_key("Example Ltd"), name_key("Example Co Ltd"))
        self.assertNotEqual(name_key("Example HK Co Ltd"), name_key("Example Co Ltd"))
        self.assertNotEqual(name_key("Example MFG Co Ltd"), name_key("Example Manufacturing Co Ltd"))
        self.assertNotEqual(name_key("CO Research Ltd"), name_key("Company Research Ltd"))

    def test_same_name_in_another_jurisdiction_is_ambiguous(self):
        second = registry("EXAMPLE2")
        second["attributes"]["entity"]["jurisdiction"] = "IN"
        result = resolve("Example Co Ltd", response(registry(), second))
        self.assertEqual(result["status"], "ambiguous_registry_name")
        self.assertIsNone(result["selected_lei"])

    def test_unique_full_match_does_not_claim_historical_identity_or_title(self):
        result = resolve("Example Co Ltd", response(registry(), registry("SUB", "Example HK Co Ltd")))
        self.assertEqual(result["selected_lei"], "EXAMPLE1")
        self.assertEqual(result["historical_identity_status"], "not_established")
        self.assertEqual(result["current_ownership_status"], "not_established")

    def test_previous_name_and_lapsed_registration_do_not_support_current_link(self):
        old = registry(name="Renamed Company Limited")
        old["attributes"]["entity"]["otherNames"] = [{"name": "Example Company Limited", "type": "PREVIOUS_LEGAL_NAME"}]
        self.assertEqual(resolve("Example Co Ltd", response(old))["status"], "registry_status_or_name_review")
        lapsed = registry()
        lapsed["attributes"]["registration"]["status"] = "LAPSED"
        self.assertIsNone(resolve("Example Co Ltd", response(lapsed))["selected_lei"])

    def test_lapsed_competitor_still_blocks_unique_match(self):
        second = registry("EXAMPLE2")
        second["attributes"]["registration"]["status"] = "LAPSED"
        self.assertEqual(resolve("Example Co Ltd", response(registry(), second))["status"], "ambiguous_registry_name")

    def test_partial_search_cannot_establish_unique_entity(self):
        self.assertEqual(resolve("Example Co Ltd", response(registry(), total=201))["status"], "search_incomplete")
        self.assertEqual(resolve("Example Co Ltd", {"data": [registry()]})["status"], "search_incomplete")

    def test_registry_translation_is_retained_as_match_evidence(self):
        row = registry(name="示例有限公司")
        row["attributes"]["entity"]["otherNames"] = [{"name": "Example Company Limited", "type": "ALTERNATIVE_LANGUAGE_LEGAL_NAME"}]
        result = resolve("Example Co Ltd", response(row))
        self.assertEqual(result["selected_lei"], "EXAMPLE1")
        self.assertEqual(result["candidates"][0]["matched_names"][0]["type"], "ALTERNATIVE_LANGUAGE_LEGAL_NAME")

    def test_evidence_tamper_and_artifact_overwrite_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            meta = put_local(root, "raw.json", b"original")
            with self.assertRaisesRegex(ValueError, "Immutable"):
                put_local(root, "raw.json", b"changed")
            (root / "raw.json").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "checksum"):
                checked_body(root / "raw.json", meta)

    def test_release_keeps_listing_candidates_and_bounds_deduplicated_us_cohort(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            parent, evidence = root / "parent", root / "evidence"
            parent.mkdir(); evidence.mkdir()
            universe = {"external_identifiers": []}
            original = copy.deepcopy(universe)
            decisions = [{"observation_id": str(i), "publication_number": "US-202500000" + str(i) + "-A1",
                "publication_date": "2025-01-01", "application_number": "US-20241800000" + str(i // 2) + "-A",
                "reported_parties": [{"reported_name": "Example Co Ltd", "role": "publication_assignee", "candidate_company_ids": ["listing1", "listing2"]}],
                "reported_party_company_ids": []} for i in range(6)]
            meta = put_local(parent, "decisions.jsonl", b"".join(canonical_json(d) + b"\n" for d in decisions))
            put_local(parent, "review.json", canonical_json({"release_id": "parent", "universe_hash": digest(universe), "files": {"decisions.jsonl": meta}}))
            raw_meta = put_local(evidence, "evidence/raw.json", canonical_json(response(registry())))
            fetch = {"status": "complete", "scope": {"parent_review_id": "parent", "names": ["Example Co Ltd"]},
                     "queries": [{"reported_name": "Example Co Ltd", "file": "evidence/raw.json", **raw_meta}]}
            put_local(evidence, "fetch.json", canonical_json(fetch))
            output, report = build(parent, evidence, root / "output", universe, per_entity=2)
            self.assertEqual(report["registry_linked_publications"], 6)
            self.assertEqual(report["assignment_cohort_applications"], 2)
            self.assertEqual(universe, original)
            self.assertFalse(report["shared_universe_updated"])
            link = json.loads((output / "publication-links.jsonl").read_text().splitlines()[0])
            self.assertEqual(link["parties"][0]["original_candidate_company_ids"], ["listing1", "listing2"])
            self.assertEqual(build(parent, evidence, root / "output", universe, per_entity=2)[0], output)


if __name__ == "__main__":
    unittest.main()
