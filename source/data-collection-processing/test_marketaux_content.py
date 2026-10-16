import json
from unittest.mock import patch
from test_news_collection import NewsTests
from test_finlight_content import BODY
from marketaux_content import Capture, VERSION
from finlight_content_backfill import enrich_one, discover, registry
from regulatory_collection import SourceIssue


class MarketauxContentTests(NewsTests):
    def test_publisher_body_preserves_uuid_and_original_metadata(self):
        self.client.capture_full_text = True
        with patch.object(Capture, 'publisher', return_value=(BODY, 'publisher_html')), \
             patch.object(Capture, 'provider_body', side_effect=AssertionError('no provider full-body API')):
            result = self.collect()
        self.assertEqual(result['status'], 'complete')
        # Read committed observations; UUID and snippet stay intact.
        records = [json.loads(line) for p in self.store.root.rglob('*.jsonl') for line in p.read_text().splitlines()]
        self.assertTrue(records)
        for row in records:
            self.assertEqual(row['payload']['data']['content'], BODY)
            self.assertEqual(row['payload']['full_text']['version'], VERSION)
            self.assertIn('uuid', row['payload']['data'])
            self.assertIn('marketaux_fulltext', row['payload']['full_text']['reference']['key'])

    def test_blocked_publisher_is_gap_without_finlight_fallback(self):
        capture = Capture(self.store, None)
        with patch.object(capture, 'publisher', side_effect=SourceIssue('article_publisher_http_403')), \
             patch.object(capture, 'provider_body', side_effect=AssertionError('no fallback')):
            result = capture.get({'url': 'https://example.org/a', 'description': BODY, 'snippet': BODY})
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['text_characters'], 0)

    def test_saved_marketaux_history_enriched_and_completion_emailed_once(self):
        import hashlib
        import sqlite3
        from unittest.mock import Mock
        import finlight_content_backfill as b
        result = self.collect()
        parent = self.rows(result)[0]
        raw = (json.dumps(parent) + '\n').encode()
        sha = hashlib.sha256(raw).hexdigest()
        from collection_storage import write_checked
        write_checked(self.store, 'test/marketaux.jsonl', raw)
        index = self.root / 'marketaux-index.sqlite3'
        with sqlite3.connect(index) as db:
            db.execute('CREATE TABLE batches (key TEXT,sha256 TEXT,source TEXT,dataset TEXT)')
            db.execute('INSERT INTO batches VALUES (?,?,?,?)', ('test/marketaux.jsonl', sha, 'marketaux', 'news_articles'))
        config = dict(provider='marketaux', start='2021-01-01', end_exclusive='2026-10-15',
            max_batches_per_invocation=100, max_articles_per_invocation=10, max_attempts=3,
            scope_note='Marketaux publisher bodies', email_topic_arn='arn:topic', email_recipient='owner@example.com')
        sns = Mock()
        sns.get_paginator.return_value.paginate.return_value = [{'Subscriptions': [
            dict(Protocol='email', Endpoint='owner@example.com', SubscriptionArn='arn:confirmed')]}]
        sns.publish.return_value = {'MessageId':'accepted'}
        with b.registry(self.root / 'marketaux-registry.sqlite3') as db, \
             patch.object(Capture, 'publisher', return_value=(BODY, 'publisher_html')), \
             patch.object(b, 'archive_ready', return_value=False):
            state = b.run(self.store, self.settings, config, self.universe, self.taxonomy, None, sns, db, index)
            self.assertEqual(state['counts'], {'captured':1})
            sns.publish.assert_not_called()
            manifest = db.execute('SELECT manifest FROM articles').fetchone()[0]
            enriched, = self.rows({'manifest':manifest})
            self.assertEqual(enriched['source'], 'marketaux')
            self.assertEqual(enriched['source_record_id'], parent['source_record_id'])
            self.assertEqual(enriched['payload']['data']['content'], BODY)
            with patch.object(b, 'archive_ready', return_value=True):
                b.run(self.store, self.settings, config, self.universe, self.taxonomy, None, sns, db, index)
                b.run(self.store, self.settings, config, self.universe, self.taxonomy, None, sns, db, index)
            self.assertEqual(sns.publish.call_count, 1)
            self.assertIn('Marketaux', sns.publish.call_args.kwargs['Subject'])

    def test_utf8_chinese_jsonld_without_charset_preserved(self):
        from finlight_content import extract_html
        body = '〔財經頻道／綜合報導〕公司表示：「測試結果仍屬初步，尚未確認商業交付日期。」' * 12
        raw = ('<html><head><script type="application/ld+json">' + json.dumps(
            {'@type':'NewsArticle','articleBody':body},ensure_ascii=False) + '</script></head><body></body></html>').encode('utf-8')
        self.assertEqual(extract_html(raw,'https://example.org/zh','摘要'),body)
