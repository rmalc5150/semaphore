import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import patent_events


class PatentEventTests(unittest.TestCase):
    def setUp(self):
        self.record = {
            "publication_number": "US-2025000001-A1",
            "application_number": "US-20240123456-A",
            "family_id": "123",
            "publication_date": "2025-01-02",
            "matched_company": "Example Bio",
            "company_sector": "biotech",
            "title": "Example invention",
            "assignees": ["EXAMPLE BIO INC"],
        }

    def events(self, previous, current):
        return patent_events.create_events(previous, current, date(2026, 9, 14), detected_at="2026-09-14T00:00:00+00:00")

    def test_new_application_publication(self):
        event = self.events([], [self.record])[0]
        self.assertEqual(event["eventType"], "PATENT_APPLICATION_PUBLISHED")
        self.assertEqual(event["eventDate"], "2025-01-02")

    def test_status_change(self):
        old = dict(self.record, status="Pending")
        new = dict(self.record, status="Patented Case", status_date="2026-09-13")
        event = self.events([old], [new])[0]
        self.assertEqual(event["eventType"], "PATENT_STATUS_CHANGED")
        self.assertEqual(event["changes"]["previous"], "Pending")

    def test_grant_transition(self):
        new = dict(self.record, grant_date="2026-09-10", kind_code="B2")
        event_types = [event["eventType"] for event in self.events([self.record], [new])]
        self.assertEqual(event_types, ["PATENT_GRANTED"])

    def test_assignment_change(self):
        new = dict(self.record, assignees=["EXAMPLE HOLDINGS INC"], assignment_date="2026-09-11")
        event = self.events([self.record], [new])[0]
        self.assertEqual(event["eventType"], "PATENT_ASSIGNEE_CHANGED")

    def test_event_ids_are_deterministic(self):
        first = self.events([], [self.record])[0]["eventId"]
        second = self.events([], [self.record])[0]["eventId"]
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
