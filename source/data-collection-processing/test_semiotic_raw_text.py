import io
from unittest import TestCase
from unittest.mock import Mock

from semiotic_batch import extract
from semiotic_raw_text import ArchivedEvidenceReader
from semiotic_sandbox import encoded, sha
from test_semiotic_sandbox import REGISTRY, fixture


class RawTextTests(TestCase):
    def test_native_entry_text_and_original_lineage(self):
        raw = (b'<feed xmlns="http://www.w3.org/2005/Atom">'
               b'<entry><id>paper-1</id><title>First exact title</title></entry>'
               b'<entry><id>paper-2</id><summary>Second exact summary</summary></entry></feed>')
        observation = {**fixture()['observations'][0], 'source_key': 'arxiv', 'source_record_id': 'paper-1'}
        observation['raw_artifacts'] = [{
            's3_uri': 's3://fixture-bucket/research-data/original.atom', 'sha256': sha(raw),
            'origin': 'first_party_source', 'artifact_kind': 'provider_record',
        }]
        second = {**observation, 'observation_id': 'fixture_obs_2', 'source_record_id': 'paper-2'}
        observations = [observation, second]
        snapshot = {'environment': 'sandbox', 'observations': observations,
                    'observations_sha256': sha(encoded(observations))}
        s3 = Mock()
        s3.get_object.return_value = {'Body': io.BytesIO(raw), 'ContentLength': len(raw)}
        reader = ArchivedEvidenceReader(s3, 'fixture-bucket')
        hydrated = reader.hydrate(snapshot)
        s3.get_object.assert_called_once()
        self.assertEqual(hydrated, reader.hydrate(hydrated))
        self.assertEqual(hydrated['observations'][0]['payload'], observation['payload'])
        graph, _, _ = extract(hydrated, REGISTRY, 100000)
        units = {row['observation_id']: row for row in graph['tables']['evidence_units']
                 if row['kind'] == 'extracted_passage'}
        self.assertEqual(units['fixture_obs_1']['value'], 'First exact title')
        self.assertEqual(units['fixture_obs_2']['value'], 'Second exact summary')
        self.assertEqual(units['fixture_obs_2']['locator']['source_locator']['xml_path'],
                         '/a:feed/a:entry[2]/a:summary')
        self.assertEqual(units['fixture_obs_2']['artifact']['sha256'], sha(raw))

    def test_checksum_mismatch_fails_before_parsing(self):
        s3 = Mock()
        s3.get_object.return_value = {'Body': io.BytesIO(b'corrupt'), 'ContentLength': 7}
        with self.assertRaisesRegex(ValueError, 'checksum'):
            ArchivedEvidenceReader(s3, 'fixture-bucket').fetch({
                's3_uri': 's3://fixture-bucket/research-data/original.html', 'sha256': 'a' * 64,
            })
