import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import patent_landscape


class PatentLandscapeTests(unittest.TestCase):
    def test_normalize_org_removes_only_trailing_legal_suffixes(self):
        self.assertEqual(patent_landscape.normalize_org("ModernaTX, Inc."), "modernatx")
        self.assertEqual(patent_landscape.normalize_org("Form Energy, Inc."), "form energy")

    def test_alias_matching_is_exact_after_normalization(self):
        companies = [{"name": "Arm", "sector": "semiconductor", "normalized_aliases": ["arm"]}]
        self.assertEqual(patent_landscape.match_companies(["ARM Limited"], companies)[0]["name"], "Arm")
        self.assertEqual(patent_landscape.match_companies(["Armature Systems"], companies), [])

    def test_battery_classification_uses_cpc_and_text(self):
        result = patent_landscape.classify({
            "title": "Solid-state lithium battery electrolyte",
            "abstract": "An energy storage cell",
            "cpc_codes": ["H01M 10/052"],
        })
        battery = next(item for item in result if item["sector"] == "battery")
        self.assertEqual(battery["confidence"], 1.0)
        self.assertEqual(battery["cpc_hits"], ["H01M"])

    def test_company_sector_and_technology_are_separate(self):
        companies = [{"name": "Example Bio", "sector": "biotech", "normalized_aliases": ["example bio"]}]
        rows = patent_landscape.process([{
            "publication_number": "US-1-A1", "assignees": ["Example Bio, Inc."],
            "title": "A robotic manipulator", "abstract": "Robot arm control",
            "cpc_codes": ["B25J 9/16"],
        }], companies)
        self.assertFalse(rows[0]["target_sector_match"])
        self.assertTrue(rows[0]["review_required"])


if __name__ == "__main__":
    unittest.main()
