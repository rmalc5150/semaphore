"""Offline acceptance tests for the deterministic graph boundary."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from semiotic_sandbox import build, capture, encoded, query, sha, write_release, publish


def fixture():
    row = {'observation_id': 'fixture_obs_1', 'record_id': 'fixture_rec_1',
        'quality_status': 'accepted', 'raw_completeness_status': 'complete',
        'raw_s3_uri': 's3://fixture-only/document', 'raw_sha256': 'a' * 64,
        'ingested_at': '2026-11-16T10:00:00Z', 'available_at': None,
        'payload': {'pages': [{'page': 1, 'text': 'Synthetic company CIK 12345 references trial NCT01234567.'}]}}
    observations = [row]
    return {'environment': 'sandbox', 'observations': observations,
            'observations_sha256': sha(encoded(observations))}


REGISTRY = {'snapshot_id': 'fixture-current-registry', 'identifiers': [
    {'namespace': 'CIK', 'value': '0000012345', 'entity_id': 'fixture_company', 'review_status': 'verified'}]}


class SandboxTests(unittest.TestCase):
    def test_recapture_result_order_and_query_id_do_not_change_release(self):
        job = 'a' * 64
        row = fixture()['observations'][0]
        rows = [[job, encoded(row).decode()],
                [job, encoded(dict(row, observation_id='fixture_obs_2')).decode()]]
        with patch('semiotic_sandbox.query', side_effect=[('q1', rows[:]), ('q2', rows[::-1])]):
            first = capture(None, [job], 'test')
            second = capture(None, [job], 'test')
        self.assertEqual(build(first, REGISTRY), build(second, REGISTRY))

    def test_reader_stops_at_byte_budget_across_pages(self):
        client = Mock()
        client.start_query_execution.return_value = {'QueryExecutionId': 'q'}
        client.get_query_execution.return_value = {'QueryExecution': {'Status': {'State': 'SUCCEEDED'}}}
        def page(*values):
            return {'ResultSet': {'Rows': [{'Data': [{'VarCharValue': value}]} for value in values]}}
        def pages():
            yield page('header', 'abc')
            yield page('éé')
            self.fail('reader fetched beyond the byte budget')
        client.get_paginator.return_value.paginate.return_value = pages()
        with self.assertRaisesRegex(ValueError, 'exceeds 6 bytes'):
            query(client, 'SELECT example', 'test', max_rows=10, max_bytes=6)

    def test_replay_and_evidence_coordinates(self):
        snapshot = fixture()
        first = build(snapshot, REGISTRY, chunk_size=32)
        self.assertEqual(first, build(snapshot, REGISTRY, chunk_size=32))
        for mention in first['tables']['mentions']:
            text = snapshot['observations'][0]['payload']['pages'][0]['text']
            self.assertEqual(text[mention['start']:mention['end']], mention['quote'])
        self.assertEqual(len(first['tables']['edges']), 1)
        self.assertFalse(first['tables']['edges'][0]['historically_eligible'])
        self.assertEqual({b['status'] for b in first['tables']['bindings']}, {'matched_current', 'unresolved'})

    def test_collision_abstains(self):
        registry = copy.deepcopy(REGISTRY)
        registry['identifiers'].append(dict(registry['identifiers'][0], entity_id='fixture_other'))
        release = build(fixture(), registry)
        self.assertEqual(release['tables']['edges'], [])

    def test_input_tampering_fails(self):
        snapshot = fixture()
        snapshot['observations'][0]['raw_sha256'] = 'b' * 64
        with self.assertRaises(ValueError):
            build(snapshot, REGISTRY)

    def test_release_readback_and_replay(self):
        import pyarrow.parquet as pq
        with tempfile.TemporaryDirectory() as directory:
            release = build(fixture(), REGISTRY)
            root = write_release(release, directory)
            original = (root / 'manifest.json').read_bytes()
            with patch('pyarrow.parquet.ParquetWriter', side_effect=AssertionError('replay rewrote Parquet')):
                write_release(release, directory)
            self.assertEqual(original, (root / 'manifest.json').read_bytes())
            for item in json.loads(original)['files']:
                self.assertEqual(pq.read_table(root / item['path']).num_rows, item['rows'])

    def test_production_prefix_rejected_before_clients_used(self):
        with self.assertRaises(ValueError):
            publish('/nonexistent', None, None, 'bucket', 'research-data/production', 'wg')


if __name__ == '__main__':
    unittest.main()
