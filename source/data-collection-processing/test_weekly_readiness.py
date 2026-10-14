import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import weekly_readiness as collector
import readiness_publication as publication


class ReadinessContracts(unittest.TestCase):
    def test_replay_does_not_issue_a_paid_request(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'captures').mkdir()
            saved = {'raw_s3_key': 'saved', 'http_status': 200, 'url': 'https://api.dataforseo.com/test', 'request': [{}]}
            (root / 'captures/task.json').write_text(json.dumps(saved))
            with patch.object(collector, 'OUT', root), patch.object(collector.requests, 'request') as request:
                self.assertEqual(collector.capture('task', 'S65', 'https://api.dataforseo.com/test', [{}], 'Basic test'), saved)
                request.assert_not_called()

    def test_ambiguous_paid_request_is_not_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'captures').mkdir()
            (root / 'captures/task.pending').write_text('prior unacknowledged request')
            with patch.object(collector, 'OUT', root), patch.object(collector.requests, 'request') as request:
                with self.assertRaisesRegex(RuntimeError, 'Unacknowledged'):
                    collector.capture('task', 'S65', 'https://api.dataforseo.com/test', [{}], 'Basic test')
                request.assert_not_called()

    def test_failed_http_is_not_normalized_as_accepted_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'captures').mkdir()
            (root / 'scope.json').write_text(json.dumps({'pilot': []}))
            (root / 'captures/blocked.json').write_text(json.dumps({'raw_s3_key': 'saved', 'source_id': 'S64', 'http_status': 403}))
            with patch.object(publication, 'OUT', root), patch.object(publication, 'save'):
                rows, _ = publication.normalize()
                self.assertEqual(rows, [])

    def test_two_paths_with_same_blob_remain_two_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'captures').mkdir()
            (root / 'scope.json').write_text(json.dumps({'pilot': []}))
            receipt = {'source_id': 'S48', 'raw_s3_key': 'saved', 'sha256': 'same', 'http_status': 200,
                       'url': 'https://api.github.com/contents', 'observed_at': '2026-10-09',
                       'data': [{'path': 'a/file', 'sha': 'same'}, {'path': 'b/file', 'sha': 'same'}]}
            (root / 'captures/artifacts.json').write_text(json.dumps(receipt))
            with patch.object(publication, 'OUT', root), patch.object(publication, 'save'):
                rows, _ = publication.normalize()
                self.assertEqual({r['provider_id'] for r in rows}, {'a/file', 'b/file'})
                self.assertTrue(all(not r['point_in_time_eligible'] for r in rows))

    def test_html_200_is_not_accepted_as_an_eia_workbook(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'captures').mkdir()
            (root / 'scope.json').write_text(json.dumps({'pilot': []}))
            receipt = {'source_id': 'S56', 'raw_s3_key': 'saved', 'sha256': 'html', 'http_status': 200,
                       'url': 'https://www.eia.gov/test.xlsx', 'observed_at': '2026-10-09', 'data': None}
            (root / 'captures/task.json').write_text(json.dumps(receipt))
            (root / 'captures/html.raw').write_bytes(b'<html>not a workbook</html>')
            with patch.object(publication, 'OUT', root), patch.object(publication, 'save'):
                rows, _ = publication.normalize()
                self.assertEqual(rows, [])


if __name__ == '__main__':
    unittest.main()
