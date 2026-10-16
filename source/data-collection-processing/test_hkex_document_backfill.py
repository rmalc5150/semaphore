import unittest
from unittest.mock import Mock

from regulatory_collection import SourceIssue
from test_disclosure_collection import DisclosureTests, Client, row, page
import disclosure_collection as disclosure
import hkex_document_backfill as backfill


class BackfillTests(DisclosureTests):
    def config(self):
        return {'start': str(self.start), 'end_exclusive': str(self.end), 'selection': 'all',
            'page_size': 100, 'max_pages_per_day_per_invocation': 2, 'max_days_per_invocation': 1,
            'email_topic_arn': 'arn:test', 'email_recipient': 'owner@example.com', 'scope_note': 'Scoped original reports.'}

    def sns(self):
        sns = Mock()
        sns.get_paginator.return_value.paginate.return_value = [{'Subscriptions': [
            {'Protocol': 'email', 'Endpoint': 'owner@example.com', 'SubscriptionArn': 'arn:confirmed'}]}]
        sns.publish.return_value = {'MessageId': 'accepted-message'}
        return sns

    def captured(self):
        source = row()
        url = disclosure.urljoin(disclosure.HKEX_API, source['FILE_LINK'])
        return disclosure.collect_hkex(self.store, self.settings, self.universe, self.taxonomy,
            self.start, self.end, 'historical', client=Client(self.store, [page([source])],
                {url: b'<html><body>Original company report with sufficient text for downstream processing.</body></html>'}))

    def test_only_verified_completion_notifies_and_retry_does_not_repeat(self):
        config, sns = self.config(), self.sns()
        collector = Mock(return_value=self.captured())
        first = backfill.run(self.store, self.settings, config, self.universe, self.taxonomy, sns, collector)
        self.assertEqual(first['status'], 'complete')
        self.assertEqual(first['reports_captured'], 1)
        self.assertIn('Reports captured: 1', sns.publish.call_args.kwargs['Message'])
        backfill.run(self.store, self.settings, config, self.universe, self.taxonomy, sns, collector)
        self.assertEqual(sns.publish.call_count, 1)
        self.assertEqual(collector.call_count, 1)

    def test_download_gap_keeps_cursor_and_does_not_notify(self):
        config, sns = self.config(), self.sns()
        collector = Mock(return_value={'status': 'partial', 'reason': 'page_limit'})
        result = backfill.run(self.store, self.settings, config, self.universe, self.taxonomy, sns, collector)
        self.assertEqual(result['next_date'], str(self.start))
        sns.publish.assert_not_called()
        collector.return_value = self.captured()
        result = backfill.run(self.store, self.settings, config, self.universe, self.taxonomy, sns, collector)
        self.assertEqual(result['status'], 'complete')

    def test_metadata_only_or_corrupt_document_cannot_complete(self):
        config, sns = self.config(), self.sns()
        metadata = self.collect([page([row()])])
        with self.assertRaises(SourceIssue):
            backfill.run(self.store, self.settings, config, self.universe, self.taxonomy, sns, Mock(return_value=metadata))
        result = self.captured()
        record = self.read(result)[0]['record']
        key = record['payload']['document_capture']['source_evidence'][0]['key']
        (self.store.root / key).write_bytes(b'corrupted')
        with self.assertRaisesRegex(SourceIssue, 'checksum'):
            backfill.run(self.store, self.settings, config, self.universe, self.taxonomy, sns, Mock(return_value=result))
        sns.publish.assert_not_called()

    def test_email_failure_retries_without_redownloading(self):
        config, sns = self.config(), self.sns()
        collector = Mock(return_value=self.captured())
        sns.publish.side_effect = RuntimeError('email unavailable')
        with self.assertRaises(RuntimeError):
            backfill.run(self.store, self.settings, config, self.universe, self.taxonomy, sns, collector)
        sns.publish.side_effect = None
        result = backfill.run(self.store, self.settings, config, self.universe, self.taxonomy, sns, collector)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(collector.call_count, 1)

    def test_unexpected_email_recipient_prevents_notification(self):
        config, sns = self.config(), self.sns()
        sns.get_paginator.return_value.paginate.return_value[0]['Subscriptions'][0]['Endpoint'] = 'someone-else@example.com'
        with self.assertRaisesRegex(SourceIssue, 'subscription_mismatch'):
            backfill.run(self.store, self.settings, config, self.universe, self.taxonomy, sns,
                Mock(return_value=self.captured()))
        sns.publish.assert_not_called()


if __name__ == '__main__':
    unittest.main()
