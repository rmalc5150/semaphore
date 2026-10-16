from unittest.mock import Mock
import json

from test_edinet_pipeline import Tests as PipelineTests, metadata
import edinet_backfill as b
from regulatory_collection import SourceIssue


class BackfillTests(PipelineTests):
    def config(self):
        return {'start': '2026-10-07', 'end_exclusive': '2026-10-08', 'max_days_per_invocation': 1,
            'documents_per_invocation': 2, 'email_topic_arn': 'arn:topic', 'email_recipient': 'owner@example.com',
            'scope_note': 'Archive capture and extraction; reviewed internal company mappings may remain incomplete.'}

    def sns(self):
        sns = Mock()
        sns.get_paginator.return_value.paginate.return_value = [{'Subscriptions': [
            {'Protocol': 'email', 'Endpoint': 'owner@example.com', 'SubscriptionArn': 'arn:confirmed'}]}]
        sns.publish.return_value = {'MessageId': 'accepted'}
        return sns

    def test_completion_verifies_documents_queues_and_emails_once(self):
        result = self.collect([metadata()])
        sns, config = self.sns(), self.config()
        collector = Mock(return_value=result)
        done = b.run(self.store, self.settings, config, self.universe, self.taxonomy, sns, collector)
        self.assertEqual(done['status'], 'complete')
        self.assertEqual(done['totals']['reports_captured'], 1)
        self.assertEqual(done['totals']['unresolved_matches'], 1)
        b.run(self.store, self.settings, config, self.universe, self.taxonomy, sns, collector)
        self.assertEqual(collector.call_count, 1)
        self.assertEqual(sns.publish.call_count, 1)
        self.assertEqual(len(list((self.store.root / 'operations/specialists/publication-queue').glob('*.json'))), 1)

    def test_partial_day_does_not_advance_or_email(self):
        sns = self.sns()
        result = b.run(self.store, self.settings, self.config(), self.universe, self.taxonomy, sns,
            Mock(return_value={'status': 'partial', 'reason': 'page_budget'}))
        self.assertEqual(result['next_date'], '2026-10-07')
        sns.publish.assert_not_called()

    def test_corrupted_extracted_text_blocks_completion(self):
        result = self.collect([metadata()])
        record, = self.records(result)
        ref = record['payload']['documents'][0]['extraction']['source_evidence'][0]
        (self.store.root / ref['key']).write_bytes(b'corruption')
        sns = self.sns()
        with self.assertRaisesRegex(SourceIssue, 'checksum'):
            b.run(self.store, self.settings, self.config(), self.universe, self.taxonomy, sns, Mock(return_value=result))
        sns.publish.assert_not_called()

    def test_unavailable_filing_produces_explicit_gap_email(self):
        row = metadata()
        row['disclosureStatus'] = '1'
        result = self.collect([row])
        sns = self.sns()
        done = b.run(self.store, self.settings, self.config(), self.universe, self.taxonomy, sns, Mock(return_value=result))
        self.assertEqual(done['status'], 'finished_with_gaps')
        self.assertEqual(done['totals']['source_gaps'], 1)
        self.assertIn('gaps', sns.publish.call_args.kwargs['Subject'])

    def test_email_retry_does_not_redownload(self):
        result = self.collect([metadata()])
        sns, config = self.sns(), self.config()
        sns.publish.side_effect = RuntimeError('SNS unavailable')
        collector = Mock(return_value=result)
        with self.assertRaises(RuntimeError):
            b.run(self.store, self.settings, config, self.universe, self.taxonomy, sns, collector)
        sns.publish.side_effect = None
        done = b.run(self.store, self.settings, config, self.universe, self.taxonomy, sns, collector)
        self.assertEqual(done['status'], 'complete')
        self.assertEqual(collector.call_count, 1)

    def test_unexpected_email_recipient_blocks_notification(self):
        result = self.collect([metadata()])
        sns = self.sns()
        sns.get_paginator.return_value.paginate.return_value[0]['Subscriptions'][0]['Endpoint'] = 'wrong@example.com'
        with self.assertRaisesRegex(SourceIssue, 'subscription_mismatch'):
            b.run(self.store, self.settings, self.config(), self.universe, self.taxonomy, sns, Mock(return_value=result))
        sns.publish.assert_not_called()
