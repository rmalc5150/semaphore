from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from collection_storage import StorageSettings
from people_social_collection import collect_feed, collect_social, event_timestamp
from regulatory_collection import EvidenceClient
from research_contract import ROOT, canonical_json, load_json
from source_observation_athena import prepare


class SourceTests(unittest.TestCase):
    def test_fractional_social_timestamp_keeps_matching_precision(self):
        result = event_timestamp('2026-10-11T12:30:00.123Z')
        self.assertEqual(result['precision'], 'microsecond')
        self.assertEqual(result['value'], '2026-10-11T12:30:00.123000Z')
        self.assertEqual(event_timestamp('2026-10-11T12:30:00Z')['precision'], 'second')

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name); self.settings = StorageSettings(local_root=str(self.root / 'store'), s3_bucket='test')
        self.store = self.settings.store()
        self.u = load_json(ROOT / 'examples/sec-filings/universe.json'); self.t = load_json(ROOT / 'config/sectors.v1.json')
        self.day = datetime.now(timezone.utc).date()

    def feed(self, raw, day=None):
        client = EvidenceClient(self.store, 'people_rss')
        def get(url):
            return client.save(raw, url)
        with patch.object(client, 'get', side_effect=get):
            return collect_feed(self.store, self.settings, self.u, self.t, 'test', 'https://example.com/feed', day or self.day, client)

    def test_feed_raw_verified_and_curated(self):
        result = self.feed(b'<rss><channel><item><title>Appointment</title><link>https://example.com/news</link><pubDate>Thu, 24 Sep 2026 12:00:00 GMT</pubDate></item></channel></rss>')
        self.assertEqual(result['status'], 'complete', result)
        config = load_json(ROOT / 'config/people-observations-athena.json')
        root = prepare(self.store, self.settings, {**config, 'source_manifests': [result['manifest']]}, self.root / 'build')
        self.assertEqual(load_json(root / 'release.json')['files']['source_observations']['rows'], 1)

    def test_html_error_is_not_empty_feed(self):
        self.assertEqual(self.feed(b'<html><body>Access denied</body></html>')['status'], 'failed')

    def test_no_backdating(self):
        with self.assertRaises(Exception):
            self.feed(b'<rss/>', self.day - timedelta(days=1))
        self.assertIsNone(event_timestamp('2021-01-01T01:00:00'))

    def social(self, pages, max_pages=10):
        client = EvidenceClient(self.store, 'bluesky_search'); calls = []
        def get(url, params):
            calls.append(params)
            return client.save(canonical_json(pages.pop(0)), url)
        with patch.object(client, 'get', side_effect=get):
            result = collect_social(self.store, self.settings, self.u, self.t, 'robotics', 'robotics',
                self.day - timedelta(days=1), client, max_pages)
        return result, calls

    def post(self, key):
        return {'uri': 'at://did:plc:test/app.bsky.feed.post/' + key, 'author': {'did': 'did:plc:test'},
                'record': {'text': 'robotics news', 'createdAt': '2026-09-01T00:00:00Z'}}

    def test_social_cursor_cap_resumes_and_sortat_is_not_createdat(self):
        result, _ = self.social([{'posts': [self.post('a')], 'cursor': 'next'}], max_pages=1)
        self.assertEqual(result['status'], 'partial', result)
        result, calls = self.social([{'posts': [self.post('b')]}])
        self.assertEqual(result['status'], 'complete', result)
        self.assertEqual(result['records'], 2)
        self.assertEqual(calls[0]['cursor'], 'next')

    def test_social_duplicate_is_not_silently_counted(self):
        result, _ = self.social([{'posts': [self.post('a')], 'cursor': 'next'}, {'posts': [self.post('a')]}])
        self.assertEqual(result['status'], 'failed', result)


if __name__ == '__main__':
    unittest.main()
