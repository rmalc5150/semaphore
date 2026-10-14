from copy import deepcopy
import unittest

from patent_adjudication import Reviewer, POLICY_PATH
from research_contract import ROOT, load_json


class AdjudicationTests(unittest.TestCase):
    def setUp(self):
        self.universe = load_json(ROOT / "examples/sec-filings/universe.json")
        company = self.universe["companies"][0]
        company["canonical_name"] = "Example Biotech Inc."
        self.cid = company["company_id"]
        self.universe["external_identifiers"].append({"entity_id": self.cid, "system": "lei", "value": "fixture",
            "review_status": "verified", "evidence": [{"source": "fixture", "reference": "fixture://lei", "note": "Fixture"}]})
        self.policy = load_json(POLICY_PATH)
        self.reviewer = Reviewer(self.universe, self.policy)

    def test_exact_registered_name_links_without_asserting_ownership(self):
        result = self.reviewer.party("EXAMPLE BIOTECH INC", "publication_assignee", "2025-01-06")
        self.assertEqual(result["status"], "registry_name_supported")
        self.assertEqual(result["company_id"], self.cid)
        self.assertEqual(result["current_ownership_status"], "not_established")
        self.assertEqual(result["historical_identity_status"], "not_established")

    def test_legal_suffix_and_subsidiary_are_not_interchangeable(self):
        for name in ("Example Biotech Ltd", "Example Biotech Research Inc", "Example Biotech"):
            self.assertIsNone(self.reviewer.party(name, "publication_assignee", "2025-01-06")["company_id"])

    def test_pending_alias_cannot_verify_party(self):
        self.universe["company_aliases"].append({"alias":"Other name", "company_id":self.cid,
            "review_status":"pending", "valid_from":"2020-01-01", "valid_to":None})
        reviewer = Reviewer(self.universe, self.policy)
        self.assertIsNone(reviewer.party("Other name", "publication_assignee", "2025-01-06")["company_id"])

    def test_verified_alias_requires_valid_historical_bounds(self):
        self.universe["company_aliases"].append({"alias":"Other name", "company_id":self.cid,
            "review_status":"verified", "valid_from":"2020-01-01", "valid_to":"2025-01-01"})
        reviewer = Reviewer(self.universe, self.policy)
        self.assertEqual(reviewer.party("Other name", "publication_assignee", "2024-01-01")["company_id"], self.cid)
        self.assertIsNone(reviewer.party("Other name", "publication_assignee", "2025-01-01")["company_id"])

    def test_two_verified_entities_with_same_name_remain_ambiguous(self):
        other = self.universe["companies"][1]
        other["canonical_name"] = "Example Biotech Inc."
        self.universe["external_identifiers"].append({"entity_id":other["company_id"],"system":"lei","review_status":"verified"})
        result = Reviewer(self.universe,self.policy).party("Example Biotech Inc", "publication_assignee", "2025-01-06")
        self.assertEqual(result["status"], "ambiguous")
        self.assertIsNone(result["company_id"])

    def classify(self, codes, discovery=()):
        return self.reviewer.sectors({"payload":{"data":{"cpc_codes":codes},"technology_classifications":list(discovery)}})

    def test_broad_guidance_and_manual_manipulator_not_auto_robotics(self):
        for code in ("G05D 1/00", "B25J 1/02"):
            self.assertEqual(self.classify([code])[0], [])
        self.assertEqual(self.classify(["B25J 9/16"])[0][0]["sector_id"], "robotics")

    def test_fuel_cell_electrodes_and_text_only_do_not_auto_become_batteries(self):
        discovery = [{"sector_id":"energy_storage","category":"batteries","term_hits":["electrode"]}]
        supported, pending = self.classify(["H01M 4/86"], discovery)
        self.assertFalse(supported)
        self.assertEqual(len(pending), 1)
        self.assertEqual(self.classify(["H01M 10/052"])[0][0]["category"], "batteries")

    def test_mechanical_and_hydrogen_have_specific_cpc_evidence(self):
        for code, category in (("Y02E 60/16","mechanical_storage"),("F17C 11/005","hydrogen_storage"),
                               ("Y02E 60/32","hydrogen_storage"),("F28D 20/00","thermal_storage"),
                               ("H01G 11/00","supercapacitors")):
            self.assertTrue(any(r["category"]==category for r in self.classify([code])[0]))

    def test_compact_codes_preserve_group_boundaries(self):
        self.assertFalse(self.classify(["F28D2001/00"])[0])
        self.assertTrue(self.classify(["F28D20/0034"])[0])

    def test_multiple_sector_memberships_preserved(self):
        rows, _ = self.classify(["C12Q 1/68", "H01L 21/00"])
        self.assertEqual({r["sector_id"] for r in rows}, {"biotech", "semiconductors"})


if __name__ == "__main__":
    unittest.main()
