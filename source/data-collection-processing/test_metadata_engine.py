import unittest
from contextlib import nullcontext
from datetime import datetime
from unittest.mock import Mock

from metadata_engine.labelling import label_observation


CONTRACT = {"source_key": "sec_edgar", "contract_version": "1.0.0", "adapter": "filings_xbrl", "adapter_version": "1.0.0", "record_kind": "filing", "license_policy_id": "public-sec-edgar-v1", "raw_requirements": {"version": "1.0.0", "minimum_completeness": "complete", "required_artifact_kinds": ["provider_record", "primary_document"], "forbidden_shortcuts": ["abstract_only", "index_only", "title_date_only", "third_party_metadata_only"]}}
RECORD = {"source": "sec_edgar", "dataset": "filings", "source_record_id": "0001", "source_record_id_basis": "provider", "raw_s3_uri": "s3://example/raw.json", "raw_sha256": "a" * 64, "raw_completeness_status": "complete", "raw_artifacts": [{"artifact_kind": "provider_record", "s3_uri": "s3://example/raw.json", "sha256": "a" * 64, "origin": "first_party_source"}, {"artifact_kind": "primary_document", "s3_uri": "s3://example/document.html", "sha256": "b" * 64, "origin": "first_party_source"}], "source_url": "https://www.sec.gov/example", "ingested_at": "2026-10-30T10:00:00+00:00", "payload": {"form": "10-K"}}


class MetadataLabellingTests(unittest.TestCase):
    def test_graph_batches_preserve_evidence_and_parent_insert_order(self):
        from metadata_engine.graph import register, stable_id

        original = {
            **RECORD, 'source_record_id': 'first',
            'payload': {'issuer_rows': [{'cik': 17, 'company_name': 'Example   Company'}],
                        'data': {'series': 'test-series', 'period': '2026-01'}},
        }
        records = [
            {**label_observation({**original, 'source_record_id': record_id}, CONTRACT), 'adapter': 'time_series'}
            for record_id in ('first', 'second')
        ]
        cursor = Mock()
        stamp = datetime(2026, 11, 22, 18, 40)
        cursor.fetchone.return_value = {'recorded_at': stamp}
        db = Mock()
        db.tx.return_value = nullcontext(cursor)

        timings = {}
        self.assertEqual(register(db, records, write_stats=timings), 12)
        db.tx.assert_called_once()
        cursor.execute.assert_called_once_with('SELECT UTC_TIMESTAMP(6) AS recorded_at')
        inserts = {call.args[0].split(' INTO ')[1].split('(')[0].split()[0]: call.args[1]
                   for call in cursor.executemany.call_args_list}
        self.assertEqual(list(inserts), ['canonical_events', 'event_versions', 'entities', 'entity_identifiers',
                                        'entity_names', 'event_participants', 'engine_assertions', 'engine_artifacts',
                                        'raw_objects', 'engine_document_links', 'engine_series', 'engine_series_vintages'])
        self.assertTrue(all(row[2] == stamp for row in inserts['canonical_events']))
        self.assertEqual({row[1] for row in inserts['event_versions']},
                         {stable_id(['source_record_event', 'sec_edgar', 'filings', x]).bytes
                          for x in ('first', 'second')})
        self.assertEqual({row[3] for row in inserts['entity_names']}, {'example company'})
        self.assertEqual({(row[0], row[3], row[4]) for row in inserts['engine_document_links']},
                         {(artifact['sha256'], record['source_record_id'], artifact['s3_uri'])
                          for artifact in RECORD['raw_artifacts'] for record in records})
        self.assertEqual([row[1] for row in inserts['raw_objects']],
                         [artifact['s3_uri'] for artifact in RECORD['raw_artifacts']])
        self.assertEqual({table: timings[table]['rows'] for table in ('raw_objects','engine_artifacts')},
                         {'raw_objects': 2, 'engine_artifacts': 2})
        self.assertEqual(len(inserts['engine_series_vintages']), 2)

    def test_replay_is_idempotent(self):
        first = label_observation(RECORD, CONTRACT, labelled_at="2026-10-30T11:00:00+00:00")
        second = label_observation(RECORD, CONTRACT, labelled_at="2026-10-30T11:00:00+00:00")
        self.assertEqual(first["observation_id"], second["observation_id"])
        self.assertEqual(first["entity_match_status"], "unresolved")

    def test_raw_evidence_is_required(self):
        broken = dict(RECORD)
        broken.pop("raw_sha256")
        with self.assertRaisesRegex(ValueError, "raw S3 URI"):
            label_observation(broken, CONTRACT, labelled_at="2026-10-30T11:00:00+00:00")

    def test_source_must_match_contract(self):
        broken = dict(RECORD, source="other")
        with self.assertRaisesRegex(ValueError, "source does not match"):
            label_observation(broken, CONTRACT, labelled_at="2026-10-30T11:00:00+00:00")

    def test_abstract_only_input_is_rejected(self):
        broken = dict(RECORD, raw_limitations=["abstract_only"])
        with self.assertRaisesRegex(ValueError, "forbidden"):
            label_observation(broken, CONTRACT, labelled_at="2026-10-30T11:00:00+00:00")

    def test_missing_required_primary_document_is_rejected(self):
        broken = dict(RECORD, raw_artifacts=RECORD["raw_artifacts"][:1])
        with self.assertRaisesRegex(ValueError, "required raw artifact"):
            label_observation(broken, CONTRACT, labelled_at="2026-10-30T11:00:00+00:00")
