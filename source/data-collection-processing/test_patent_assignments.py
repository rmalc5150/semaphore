from datetime import date
import json
import tempfile
import unittest

from collection_storage import StorageSettings
from patent_adjudication import Reviewer, POLICY_PATH
from patent_assignments import assignment_kind, collect, normalize_history
from research_contract import ROOT, load_json
from regulatory_collection import EvidenceClient


class AssignmentsTests(unittest.TestCase):
    def setUp(self):
        self.universe = load_json(ROOT / "examples/sec-filings/universe.json")
        self.taxonomy = load_json(ROOT / "config/sectors.v1.json")
        self.reviewer = Reviewer(self.universe, load_json(POLICY_PATH))

    def test_security_release_and_name_change_are_not_transfers(self):
        self.assertEqual(assignment_kind("SECURITY INTEREST"), "security_interest")
        self.assertEqual(assignment_kind("RELEASE OF SECURITY INTEREST"), "release")
        self.assertEqual(assignment_kind("CHANGE OF NAME"), "name_change")
        self.assertEqual(assignment_kind("ASSIGNMENT OF ASSIGNOR'S INTEREST"), "assignment")

    def test_latest_recorded_transfers_retain_ties_without_asserting_title(self):
        events = [{"assignmentRecordedDate":"2025-01-01", "conveyanceText":"ASSIGNMENT", "reelAndFrameNumber":str(i)} for i in range(2)]
        events.append({"assignmentRecordedDate":"2025-02-01", "conveyanceText":"SECURITY INTEREST"})
        r = normalize_history({"assignmentBag":events}, self.reviewer)
        self.assertEqual(len(r["latest_recorded_assignment_events"]), 2)
        self.assertEqual(r["current_ownership_status"], "not_established")

    def test_missing_dates_are_not_filled_from_collection_day(self):
        r = normalize_history({"assignmentBag":[{"conveyanceText":"ASSIGNMENT"}]}, self.reviewer)
        self.assertIsNone(r["events"][0]["recorded_date"])
        self.assertEqual(r["latest_recorded_assignment_events"], [])

    def test_explicit_cohort_resumes_after_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = StorageSettings(local_root=tmp)
            store = settings.store()
            calls = []
            class Client:
                evidence = []
                def application(self, number):
                    calls.append(number)
                    result = {"count":1,"patentFileWrapperDataBag":[{"applicationNumberText":number,
                        "applicationMetaData":{"filingDate":"2025-01-01"},"assignmentBag":[]}]}
                    e = EvidenceClient(store,"uspto_odp")
                    e.save(json.dumps(result).encode(), "https://api.uspto.gov/example")
                    self.evidence = e.evidence
                    return result
            args = [store,settings,self.universe,self.taxonomy,["16123456","16123457"],date(2026,9,22)]
            result = collect(*args, client=Client(), max_records=1)
            self.assertEqual(result["status"], "partial")
            result = collect(*args, client=Client())
            self.assertEqual(result["records"], 2)
            self.assertEqual(calls, ["16123456","16123457"])
            self.assertTrue(collect(*args, client=Client())["already_complete"])


if __name__ == "__main__":
    unittest.main()
