import io
from unittest import TestCase
from unittest.mock import Mock

from semiotic_batch import extract, read_parquet, run_batches
from semiotic_sandbox import encoded, sha
from semiotic_sectors import ISIC, native_industry_pair
from test_semiotic_sandbox import fixture, REGISTRY


def appointment_snapshot(name, *, role='permanent', root='release'):
    snapshot = fixture()
    obs = snapshot['observations'][0]
    obs['observation_id'] = name
    quote = f'Avery Morgan appointed {role} CEO.'
    text = f'CIK 12345. {quote}'
    obs['payload']['pages'][0]['text'] = text
    snapshot['observations_sha256'] = sha(encoded(snapshot['observations']))
    snapshot['reviewed_appointments'] = [{
        'organization_id': 'fixture_company', 'observation_id': name, 'reported_appointee': 'Avery Morgan',
        'role': role, 'effective_on': '2024-09-09', 'page': 1, 'start': text.index(quote),
        'end': len(text), 'quote': quote, 'provenance_root': root,
    }]
    return snapshot


class BatchTests(TestCase):
    def test_nasa_fill_and_units_link_to_original_provider_field(self):
        snapshot = fixture()
        obs = snapshot['observations'][0]
        obs['source_key'] = 'nasa_power_weather_and_solar_resource'
        obs['raw_artifacts'] = [{
            's3_uri': obs['raw_s3_uri'], 'sha256': obs['raw_sha256'], 'artifact_kind': 'provider_record',
            'validation': 'original bytes checked', 'origin': 'first_party_source',
            'source_url': 'https://power.larc.nasa.gov/api/temporal/daily/point',
        }]
        obs['payload']['source_evidence'] = [{'sha256': obs['raw_sha256']}]
        obs['payload']['data'] = {
            'date': '2025-01-01', 'reference_location': 'Test cell', 'latitude': 10, 'longitude': 20,
            'provider_values': {'T2M': -999}, 'values': {'T2M': None}, 'missing_parameters': ['T2M'],
            'parameters': {'T2M': {'units': 'C'}}, 'header': {'time_standard': 'UTC'},
        }
        snapshot['observations_sha256'] = sha(encoded(snapshot['observations']))
        graph, _, _ = extract(snapshot, REGISTRY, 100000)
        measurement, = graph['tables']['measurements']
        evidence = next(row for row in graph['tables']['evidence_units'] if row['id'] == measurement['evidence_id'])
        self.assertEqual(evidence['locator']['path'], '/properties/parameter/T2M/20250101')
        self.assertEqual(measurement['original_value'], -999)
        self.assertEqual(measurement['unit'], 'C')
        self.assertIsNone(measurement['value'])
        self.assertIsNone(evidence['eligible_at'])
        self.assertEqual(next(row for row in graph['tables']['sector_coverage']
                              if row['point_id'] == measurement['id'])['status'], 'unclassified')

    def test_sector_labels_preserve_source_grain_and_validate_taxonomy(self):
        snapshot = fixture()
        observation = snapshot['observations'][0]
        observation['payload']['sector_classifications'] = [
            {'sector_id': 'robotics', 'subsector_id': 'medical_robotics'},
            {'sector_id': 'semiconductors', 'subsector_id': None},
        ]
        snapshot['observations_sha256'] = sha(encoded(snapshot['observations']))
        graph, _, _ = extract(snapshot, REGISTRY, 100000)
        self.assertEqual({(row['sector_id'], row['subsector_id'], row['status'])
                          for row in graph['tables']['sector_attributions']},
                         {('robotics', 'medical_robotics', 'reported'), ('semiconductors', None, 'reported')})
        self.assertEqual(next(row for row in graph['tables']['sector_coverage']
                              if row['point_type'] == 'chunk')['status'], 'unclassified')
        observation['payload']['sector_classifications'][0]['subsector_id'] = 'batteries'
        snapshot['observations_sha256'] = sha(encoded(snapshot['observations']))
        with self.assertRaisesRegex(ValueError, 'invalid sector/subsector pair'):
            extract(snapshot, REGISTRY, 100000)

    def test_global_isic_hierarchy_and_legacy_source_codes(self):
        self.assertEqual({level: sum(node['level'] == level for node in ISIC.values())
                          for level in ('section', 'division', 'group', 'class')},
                         {'section': 22, 'division': 87, 'group': 258, 'class': 463})
        self.assertEqual(native_industry_pair('0111'), ('isic_A', 'isic_01'))
        self.assertEqual(native_industry_pair('A'), ('isic_A', None))
        self.assertEqual(native_industry_pair('6419'), ('isic_L', 'isic_64'))
        snapshot = fixture()
        snapshot['observations'][0]['payload']['sector_classifications'] = [
            {'naics_code': '522', 'naics_edition': '2022'},
            {'sector_id': 'naics_31-33', 'subsector_id': 'naics_336'},
            {'isic_code': '6419', 'isic_revision': 5},
            {'sector_id': 'energy_storage', 'subsector_id': 'batteries'},
        ]
        snapshot['observations_sha256'] = sha(encoded(snapshot['observations']))
        graph, _, _ = extract(snapshot, REGISTRY, 100000)
        self.assertEqual({(row['taxonomy_namespace'], row['sector_id'], row['subsector_id'])
                          for row in graph['tables']['sector_attributions']},
                         {('isic_rev5', 'isic_L', 'isic_64'),
                          ('research', 'energy_storage', 'batteries')})
        self.assertEqual({row['code'] for row in graph['tables']['sector_source_codes']}, {'522', '336'})
        self.assertTrue(all(row['mapping_status'] == 'unmapped_to_isic'
                            for row in graph['tables']['sector_source_codes']))
        isic = next(row for row in graph['tables']['sector_attributions'] if row['taxonomy_namespace'] == 'isic_rev5')
        self.assertEqual(isic['native_isic_code'], '6419')

    def test_parallel_batches_and_later_release_reconcile(self):
        release, metrics = run_batches(
            [appointment_snapshot('release'), appointment_snapshot('filing', root='filing')], REGISTRY)
        self.assertEqual(len(metrics), 2)
        first = release['tables']['event_versions'][0]
        later, _ = run_batches(
            [appointment_snapshot('interim', role='interim', root='interim'), appointment_snapshot('news')],
            REGISTRY, previous=release)
        rows = {event['role']: event for event in later['tables']['event_versions']}
        self.assertEqual(set(rows), {'interim', 'permanent'})
        self.assertEqual(first['event_id'], rows['permanent']['event_id'])
        self.assertNotEqual(first['id'], rows['permanent']['id'])
        self.assertEqual(len(first['evidence']), 2)
        self.assertEqual({item['observation_id']: item['provenance_root'] for item in rows['permanent']['evidence']},
                         {'release': 'release', 'news': 'release', 'filing': 'filing'})
        self.assertEqual(later['parent_release_id'], release['release_id'])

    def test_s3_uses_exact_glue_partition_and_checks_content(self):
        import pyarrow as pa
        import pyarrow.parquet as pq
        job = 'f' * 64
        observations = fixture()['observations']
        buffer = io.BytesIO()
        pq.write_table(pa.table({'labelled_json': [encoded(row).decode() for row in observations]}), buffer)
        blob = buffer.getvalue()
        location = f's3://pilot-bucket/metadata/jobs/{job}/data/{sha(blob)}/'
        glue, s3 = Mock(), Mock()
        glue.get_partition.return_value = {'Partition': {'Values': [job], 'StorageDescriptor': {'Location': location}}}
        s3.get_object.return_value = {'ContentLength': len(blob), 'Body': io.BytesIO(blob)}
        snapshot, _ = read_parquet(glue, s3, [job], 'pilot-bucket', 'metadata')
        self.assertEqual(snapshot['observations'], observations)
        self.assertEqual(glue.get_partition.call_args.kwargs['TableName'], 'source_observations')
        s3.get_object.return_value = {'ContentLength': len(blob), 'Body': io.BytesIO(blob[::-1])}
        with self.assertRaisesRegex(ValueError, 'checksum'):
            read_parquet(glue, s3, [job], 'pilot-bucket', 'metadata')
