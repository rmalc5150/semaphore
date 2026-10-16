import copy
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from test_news_collection import NewsTests
import finlight_content as f
from regulatory_collection import SourceIssue

BODY = ('The company said, “Our battery remained stable during the entire flight.” '
    'It reported an endurance of 118 minutes at the Queensland test site. '
    'Engineers recorded voltage and temperature continuously throughout the trial. '
    'The company described the results as preliminary and said further testing was required. '
    'It did not provide a date for commercial deliveries or a binding sales forecast.')


class ContentTests(NewsTests):
    def article(self):
        return {'link': 'https://example.org/article', 'title': 'Battery test', 'summary': 'Battery test summary...',
            'publishDate': '2024-06-03T12:00:00Z', 'language': 'en'}

    def capture(self):
        return f.Capture(self.store, SimpleNamespace(reserve=Mock(), key='test-secret', sleep=lambda _: None))

    def test_summary_or_truncated_text_is_not_full_content(self):
        self.assertFalse(f.usable(BODY, BODY))
        self.assertFalse(f.usable(BODY + '...', 'Summary'))
        self.assertFalse(f.usable('Short summary', 'Summary'))

    def test_extract_preserves_qualifying_language_and_quotes(self):
        raw = ('<html><head><script type="application/ld+json">' + json.dumps({'@type': 'NewsArticle',
            'articleBody': BODY}) + '</script></head><body><article><p>' + BODY + '</p></article></body></html>').encode()
        text = f.extract_html(raw, 'https://example.org/article', 'Summary')
        self.assertIn('“Our battery remained stable during the entire flight.”', text)
        self.assertIn('preliminary', text)
        self.assertIn('did not provide a date', text)

    def test_restricted_page_is_not_treated_as_an_article(self):
        raw = ('<script type="application/ld+json">' + json.dumps({'@type': 'NewsArticle',
            'isAccessibleForFree': False, 'articleBody': BODY}) + '</script>').encode()
        with self.assertRaisesRegex(SourceIssue, 'restricted'):
            f.extract_html(raw, 'https://example.org/a', 'Summary')

    def test_body_is_saved_verbatim_cached_and_checksum_checked(self):
        row = {**self.article(), 'content': BODY}
        capture = self.capture()
        with patch.object(capture, 'publisher', side_effect=AssertionError('must not fetch existing full content')):
            result = capture.get(row)
        self.assertEqual(result['status'], 'captured')
        ref = result['reference']
        artifact = json.loads(self.store.get(ref['key']).body)
        self.assertEqual(artifact['text'], BODY)
        self.assertEqual(artifact['text_sha256'], hashlib.sha256(BODY.encode()).hexdigest())
        capture2 = self.capture()
        with patch.object(capture2, 'publisher', side_effect=AssertionError('cache should be reused')):
            self.assertEqual(capture2.get(self.article())['reference'], ref)
        (self.store.root / ref['key']).write_bytes(b'corrupt')
        with self.assertRaisesRegex(SourceIssue, 'checksum'):
            capture2.get(self.article())

    def test_provider_fallback_and_explicit_gap(self):
        capture = self.capture()
        with patch.object(capture, 'publisher', side_effect=SourceIssue('article_publisher_http_403')), \
             patch.object(capture, 'provider_body', return_value=(BODY, 'finlight_by_link')):
            result = capture.get(self.article())
        self.assertEqual(result['capture_basis'], 'finlight_by_link')
        other = {**self.article(), 'link': 'https://example.org/blocked'}
        with patch.object(capture, 'publisher', side_effect=SourceIssue('article_publisher_http_403')), \
             patch.object(capture, 'provider_body', side_effect=SourceIssue('article_provider_full_body_unavailable')):
            result = capture.get(other)
        self.assertEqual(result['status'], 'unavailable')
        self.assertNotIn('reference', result)

    def test_temporary_quota_does_not_turn_into_a_permanent_gap(self):
        capture = self.capture()
        with patch.object(capture, 'publisher', side_effect=SourceIssue('fulltext_run_budget_reached')):
            with self.assertRaises(SourceIssue) as exc:
                capture.get(self.article())
        self.assertTrue(exc.exception.partial)

    def test_private_addresses_are_rejected(self):
        with patch('socket.getaddrinfo', return_value=[(2,1,6,'',('169.254.169.254',80))]):
            with self.assertRaisesRegex(SourceIssue, 'not_public'):
                f.public_url('http://169.254.169.254/latest/meta-data')

    def test_current_collection_saves_body_and_summary_separately(self):
        import news_collection as news
        row = {**self.article(), 'publishDate': '2026-09-23T12:00:00Z', 'content': BODY}
        self.pages = {1: {'status': 'ok', 'page': 1, 'pageSize': 1, 'articles': [row]},
                      2: {'status': 'ok', 'page': 2, 'pageSize': 0, 'articles': []}}
        client = news.NewsClient(self.store, 'finlight', 'test-key', 40, opener=self.opener, sleeper=lambda _: None)
        result = self.collect(provider='finlight', language='en', client=client)
        self.assertEqual(result['status'], 'complete', result)
        record, = self.rows(result)
        self.assertEqual(record['payload']['data']['content'], BODY)
        self.assertEqual(record['payload']['data']['summary'], row['summary'])
        self.assertEqual(record['payload']['data']['full_text_status'], 'captured')
        self.assertTrue(record['payload']['data']['full_content_reference'])

    def test_content_quota_defers_body_without_losing_discovery(self):
        import news_collection as news
        row = {**self.article(), 'publishDate': '2026-09-23T12:00:00Z'}
        self.pages = {1: {'status': 'ok', 'page': 1, 'pageSize': 1, 'articles': [row]},
                      2: {'status': 'ok', 'page': 2, 'pageSize': 0, 'articles': []}}
        client = news.NewsClient(self.store, 'finlight', 'test-key', 40, opener=self.opener, sleeper=lambda _: None)
        with patch.object(f.Capture, 'get', side_effect=SourceIssue('run_request_budget_reached', True)):
            result = self.collect(provider='finlight', language='en', client=client)
        self.assertEqual(result['status'], 'complete', result)
        record, = self.rows(result)
        self.assertEqual(record['payload']['data']['full_text_status'], 'pending')
        self.assertNotIn('content', record['payload']['data'])
