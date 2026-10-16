import hashlib
import json
import sqlite3
from unittest.mock import Mock, patch

from test_news_collection import NewsTests
from test_finlight_content import BODY
from collection_storage import write_checked
from research_contract import seal_record
from regulatory_collection import SourceIssue
import finlight_content as f
import finlight_content_backfill as b


class BackfillTests(NewsTests):
    def setup_backfill(self):
        result = self.collect()
        parent = self.rows(result)[0]
        parent.update(source='finlight', source_record_id='https://example.org/article', source_url='https://example.org/article')
        parent['payload'].update(provider_id=parent['source_record_id'], data={
            'link': parent['source_record_id'], 'title': 'Battery test', 'summary': 'A summary...',
            'publishDate': '2026-09-23T12:00:00Z', 'content': BODY})
        parent = seal_record(parent)
        raw = (json.dumps(parent) + '\n').encode()
        sha = hashlib.sha256(raw).hexdigest()
        key = 'test/finlight-parent.jsonl'
        write_checked(self.store, key, raw)
        index_path = self.root / 'catalog.sqlite3'
        with sqlite3.connect(index_path) as index:
            index.execute('CREATE TABLE batches (key TEXT,sha256 TEXT,source TEXT,dataset TEXT)')
            index.execute('INSERT INTO batches VALUES (?,?,?,?)', (key, sha, 'finlight', 'news_articles'))
        config = {'start': '2021-01-01', 'end_exclusive': '2026-10-15', 'max_batches_per_invocation': 100,
            'max_articles_per_invocation': 20, 'max_attempts': 3, 'scope_note': 'Scoped full article bodies.',
            'email_topic_arn': 'arn:topic', 'email_recipient': 'owner@example.com'}
        sns = Mock()
        sns.get_paginator.return_value.paginate.return_value = [{'Subscriptions': [
            {'Protocol': 'email', 'Endpoint': 'owner@example.com', 'SubscriptionArn': 'arn:confirmed'}]}]
        sns.publish.return_value = {'MessageId': 'accepted'}
        return parent, config, sns, b.registry(self.root / 'registry.sqlite3'), index_path

    def test_full_content_saved_and_notification_waits_for_discovery(self):
        parent, config, sns, db, index = self.setup_backfill()
        with patch.object(b, 'archive_ready', return_value=False):
            result = b.run(self.store, self.settings, config, self.universe, self.taxonomy, self.client, sns, db, index)
        self.assertEqual(result['counts'], {'captured': 1})
        self.assertEqual(result['status'], 'running')
        sns.publish.assert_not_called()
        manifest = db.execute('SELECT manifest FROM articles').fetchone()[0]
        enriched, = self.rows({'manifest': manifest})
        self.assertEqual(enriched['payload']['data']['content'], BODY)
        self.assertEqual(enriched['payload']['data']['summary'], 'A summary...')
        self.assertEqual(enriched['payload']['full_text']['status'], 'captured')
        with patch.object(b, 'archive_ready', return_value=True):
            self.assertEqual(b.run(self.store, self.settings, config, self.universe, self.taxonomy, self.client, sns, db, index)['status'], 'complete')
            b.run(self.store, self.settings, config, self.universe, self.taxonomy, self.client, sns, db, index)
        self.assertEqual(sns.publish.call_count, 1)
        db.close()

    def test_duplicate_catalog_batch_does_not_fetch_twice(self):
        parent, config, sns, db, index = self.setup_backfill()
        b.discover(self.store, db, config, index)
        self.assertEqual(b.discover(self.store, db, config, index), 0)
        self.assertEqual(db.execute('SELECT count(*) FROM articles').fetchone()[0], 1)
        db.close()

    def test_budget_pause_preserves_pending_article(self):
        parent, config, sns, db, index = self.setup_backfill()
        with patch.object(b.Capture, 'get', side_effect=SourceIssue('run_request_budget_reached', True)), \
             patch.object(b, 'archive_ready', return_value=True):
            result = b.run(self.store, self.settings, config, self.universe, self.taxonomy, self.client, sns, db, index)
        self.assertEqual(result['counts'], {'pending': 1})
        sns.publish.assert_not_called()
        db.close()

    def test_gap_is_reported_as_gap_after_bounded_retries(self):
        parent, config, sns, db, index = self.setup_backfill()
        gap = {'status': 'unavailable', 'version': f.VERSION, 'source_evidence': [], 'text_characters': 0}
        with patch.object(b.Capture, 'get', return_value=gap), patch.object(b, 'archive_ready', return_value=True):
            for _ in range(3):
                db.execute("UPDATE articles SET retry_after=''")
                db.commit()
                result = b.run(self.store, self.settings, config, self.universe, self.taxonomy, self.client, sns, db, index)
        self.assertEqual(result['status'], 'finished_with_gaps')
        self.assertIn('gaps', sns.publish.call_args.kwargs['Subject'])
        db.close()
