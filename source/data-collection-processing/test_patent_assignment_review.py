import unittest

from patent_assignment_review import compare, entity_index


class AssignmentReviewTests(unittest.TestCase):
    def comparison(self, events):
        cohort = {"application_number": "12345678", "registry_entity_ids": ["lei:example"]}
        record = {"observation_id": "obs", "source_url": "source", "payload_hash": "hash",
                  "payload": {"source_evidence": [], "data": {"assignment_history": {
                      "events": events, "latest_recorded_assignment_events": events}}}}
        return compare(cohort, record, {"example incorporated": {"lei:example"}})

    def test_matching_recipient_does_not_establish_title(self):
        result = self.comparison([{"assignees": [{"assigneeNameText": "Example Inc"}]}])
        self.assertEqual(result["comparison_status"], "reported_recipient_matches_registry_entity")
        self.assertEqual(result["current_ownership_status"], "not_established")
        self.assertFalse(result["point_in_time_eligible"])

    def test_missing_recipient_is_not_vacuously_a_match(self):
        self.assertEqual(self.comparison([{"assignees": []}])["comparison_status"], "latest_assignment_recipient_missing")

    def test_tied_latest_events_need_review_even_if_same_recipient(self):
        event = {"assignees": [{"assigneeNameText": "Example Inc"}]}
        self.assertEqual(self.comparison([event, event])["comparison_status"], "multiple_latest_assignment_events_review")

    def test_unknown_recipient_or_additional_assignee_needs_review(self):
        event = {"assignees": [{"assigneeNameText": "Example Inc"}, {"assigneeNameText": "Subsidiary Inc"}]}
        self.assertEqual(self.comparison([event])["comparison_status"], "recipient_identity_or_difference_review")

    def test_no_recorded_transfer_is_not_proof_of_no_ownership(self):
        result = self.comparison([])
        self.assertEqual(result["comparison_status"], "no_dated_assignment_in_response")
        self.assertEqual(result["current_ownership_status"], "not_established")

    def test_ambiguous_registry_rows_cannot_enter_recipient_index(self):
        self.assertEqual(dict(entity_index([{"selected_lei": None}])), {})


if __name__ == "__main__":
    unittest.main()
