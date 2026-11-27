from unittest import TestCase

from metadata_engine.graph import stable_id
from semiotic_sandbox import encoded, identity, sha
from unified_metadata import replay


class UnifiedMetadataTests(TestCase):
    def test_replay_keeps_provider_uuid_distinct_from_derived_graph_uuid(self):
        provider_id = 'acbc7867-c86f-4d87-9604-7cdcfdeaef30'
        observation = {'observation_id': 'obs_1', 'record_id': 'rec_1', 'source_key': 'ted', 'dataset': 'notices',
                       'source_record_id': provider_id, 'payload': {}}
        batch = {'observations': [observation], 'observations_sha256': sha(encoded([observation]))}
        frozen = {'batches': [batch]}
        graph = {'environment': 'sandbox', 'frozen_sample_sha256': sha(encoded(frozen)),
                 'tables': {'observations': [{'id': 'obs_1'}], 'hybrid_field_values': [
                     {'id': 'value_1', 'observation_id': 'obs_1', 'field': 'publisher_country',
                      'value': 'LU', 'status': 'source_reported'}]}}
        graph['release_id'] = identity('release', graph)
        result = replay(frozen, graph)
        self.assertEqual(replay(frozen, result), result)
        self.assertEqual(result['parent_release_id'], graph['release_id'])
        row, = result['tables']['unified_observations']
        self.assertEqual(row['id'], 'obs_1')
        self.assertEqual(row['regional']['publisher_country'][0]['value'], 'LU')
        refs = {item['uuid']: item for item in result['tables']['uuid_index']}
        self.assertEqual(refs[provider_id]['origin'], 'source_observation')
        self.assertEqual(refs[provider_id]['locator']['path'], '/source_record_id')
        self.assertEqual(refs[str(stable_id(['version', 'obs_1']))]['origin'], 'metadata_graph_reference')
        with self.assertRaisesRegex(ValueError, 'frozen metadata input'):
            replay({'batches': []}, graph)
