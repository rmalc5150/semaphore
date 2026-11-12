"""Validate the event discussion draft without network or production side effects."""
import copy
import json
from pathlib import Path
import unittest
from jsonschema import Draft7Validator, FormatChecker

ROOT = Path(__file__).resolve().parent
SCHEMA = json.loads((ROOT / 'schemas/event.schema.json').read_text())
EXAMPLE = json.loads((ROOT / 'examples/events/patent-publication.event.json').read_text())


class EventSchemaTests(unittest.TestCase):
    def setUp(self):
        self.validator = Draft7Validator(SCHEMA, format_checker=FormatChecker())
        self.event = copy.deepcopy(EXAMPLE)

    def test_example_and_schema_are_valid(self):
        Draft7Validator.check_schema(SCHEMA)
        self.validator.validate(self.event)

    def test_unknown_fields_rejected(self):
        self.event['model_outputs'] = {'return': 0.2}
        self.assertFalse(self.validator.is_valid(self.event))

    def test_invalid_calendar_date_rejected(self):
        self.event['timing']['occurred_at']['value'] = '2026-02-30'
        self.assertFalse(self.validator.is_valid(self.event))

    def test_partial_source_dates_preserve_precision(self):
        self.event['timing']['occurred_at'] = {'value': '2026-08', 'precision': 'month', 'source_timezone': None}
        self.validator.validate(self.event)
        self.event['timing']['occurred_at']['value'] = '2026-08-01'
        self.assertFalse(self.validator.is_valid(self.event))

    def test_sector_subsector_pair_must_match_taxonomy(self):
        self.event['classifications'][0]['subsector_id'] = 'therapeutics'
        self.assertFalse(self.validator.is_valid(self.event))
        self.event['classifications'][0]['subsector_id'] = 'service_robotics'
        self.validator.validate(self.event)

    def test_source_availability_needs_version_evidence(self):
        source = self.event['sources'][0]
        source['available_at'] = {'value': '2026-08-31', 'precision': 'day', 'source_timezone': None}
        self.assertFalse(self.validator.is_valid(self.event))
        source['availability_basis'] = 'source_publication'
        source['availability_evidence'] = [{'reference': 'fixture:archived-publication', 'note': 'Synthetic evidence for schema testing only.'}]
        self.validator.validate(self.event)

    def test_candidates_cannot_be_model_eligible(self):
        self.event['eligibility']['operational_replay'].update(status='eligible', eligible_at='2026-10-20T12:00:00Z')
        self.assertFalse(self.validator.is_valid(self.event))

    def test_acceptance_needs_review_and_review_actor(self):
        self.event['identity']['state'] = 'accepted'
        self.assertFalse(self.validator.is_valid(self.event))
        self.event['review']['status'] = 'approved'
        self.assertFalse(self.validator.is_valid(self.event))
        self.event['review'].update(reviewer='fixture reviewer', reviewed_at='2026-10-20T12:00:00Z', reason='Synthetic decision.')
        self.validator.validate(self.event)

    def test_approved_dispatch_needs_actual_specialist_and_policy(self):
        route = self.event['specialist_routes'][0]
        route['status'] = 'approved'
        self.assertFalse(self.validator.is_valid(self.event))
        route.update(specialist_id='fixture-specialist', routing_policy_version='fixture-policy')
        self.validator.validate(self.event)

    def test_unresolved_entity_needs_at_least_a_reported_identity(self):
        self.event['entities'] = [{'entity_id': None, 'entity_type': 'company', 'reported_name': None,
                                  'role': 'applicant', 'review_status': 'pending', 'evidence_ids': ['evidence_1']}]
        self.assertFalse(self.validator.is_valid(self.event))
        self.event['entities'][0]['reported_name'] = 'Fixture company'
        self.validator.validate(self.event)

    def test_later_version_needs_predecessor_and_reason(self):
        self.event['identity']['event_sequence'] = 2
        self.assertFalse(self.validator.is_valid(self.event))
        self.event['identity'].update(supersedes_version_id='evv_' + 'a' * 64, change_reason='Synthetic correction.')
        self.validator.validate(self.event)

    def test_production_does_not_accept_test_id(self):
        self.event['identity']['environment'] = 'production'
        self.assertFalse(self.validator.is_valid(self.event))
        self.event['identity']['event_id'] = 'evt_12345678-1234-4123-8123-123456789abc'
        self.validator.validate(self.event)


if __name__ == '__main__':
    unittest.main()
