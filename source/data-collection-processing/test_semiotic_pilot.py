from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from semiotic_pilot import StagedReader, qualify
from semiotic_sandbox import encoded, sha


class PilotAdmissionTests(TestCase):
    def test_news_envelope_cannot_pass_as_original_article(self):
        original = b'<html><body><p>Provider excerpt used only to discover the original.</p></body></html>'
        digest = sha(original)
        artifact = {'artifact_kind': 'provider_record', 'origin': 'first_party_source',
                    's3_uri': 's3://fixture/excerpt', 'sha256': digest}
        rows = [{'observation_id': 'obs_1', 'source_key': 'news', 'source_record_id': 'provider_1',
                 'raw_artifacts': [artifact], 'payload': {}}]
        snapshot = {'observations': rows, 'observations_sha256': sha(encoded(rows))}
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / digest).write_bytes(original)
            reader = StagedReader(root)
            profile = {'source_key': 'news', 'input_kind': 'article', 'profile_version': '1.0.0'}
            self.assertEqual(qualify(snapshot, profile, reader), (None, 'complete_document_not_supported_or_not_collected'))
            artifact['artifact_kind'] = 'primary_document'
            snapshot['observations_sha256'] = sha(encoded(rows))
            result, reason = qualify(snapshot, profile, reader)
            self.assertIsNone(reason)
            self.assertEqual(result['observations'][0]['extracted_pages'][0]['artifact_sha256'], digest)
