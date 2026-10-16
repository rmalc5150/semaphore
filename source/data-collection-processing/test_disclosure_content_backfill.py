from datetime import date
import json
from unittest.mock import Mock

from research_contract import ROOT
from regulatory_collection import SourceIssue
from test_disclosure_collection import DisclosureTests, Client, row, page
import disclosure_content_backfill as b
import sec_filings as sec


class BackfillTests(DisclosureTests):
    def config(self):
        return {'start': str(self.start), 'end_exclusive': str(self.end), 'daily_start': str(self.start),
            'max_days_per_invocation': 1, 'email_topic_arn': 'arn:topic', 'email_recipient': 'owner@example.com',
            'scope_note': 'Scoped full content, candidate passages and explicit extraction gaps.'}

    def sns(self):
        sns = Mock()
        sns.get_paginator.return_value.paginate.return_value = [{'Subscriptions': [
            {'Protocol': 'email', 'Endpoint': 'owner@example.com', 'SubscriptionArn': 'arn:confirmed'}]}]
        sns.publish.return_value = {'MessageId': 'accepted'}
        return sns

    def stages(self):
        matcher = sec.CompanyMatcher(self.universe)
        client = Mock()
        client.fetch.return_value = (ROOT / 'examples/sec-filings/master-2024-q2.idx').read_bytes()
        scope = {'selection': 'universe', 'forms': [], 'ciks': []}
        sec_result = sec.collect_window(self.store, self.settings, self.universe, self.taxonomy,
            client, self.start, self.end, 'historical', scope, matcher, {})
        hkex = self.collect([page([row()])])
        url = self.read(hkex)[0]['record']['source_url']
        docs = self.derive('documents', [hkex['manifest']], Client(self.store,
            documents={url: b'<html>Example Robotics issued a press release announcing an exclusive license agreement.</html>'}))
        stages = {'sec': sec_result, 'hkex': hkex, 'documents': docs}
        for category in b.d.CATEGORIES:
            stages[category] = self.derive(category, [docs['manifest']])
        return stages

    def test_verification_and_email_only_after_all_stages(self):
        stages, sns, config = self.stages(), self.sns(), self.config()
        runner = Mock(side_effect=lambda stage, *args: stages[stage])
        result = b.run(self.store, self.settings, config, self.universe, self.taxonomy, sns, stage_runner=runner)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['totals']['documents'], 1)
        self.assertGreaterEqual(result['totals']['candidates'], 2)
        self.assertEqual(runner.call_count, len(b.STAGES))
        b.run(self.store, self.settings, config, self.universe, self.taxonomy, sns, stage_runner=runner)
        self.assertEqual(sns.publish.call_count, 1)

    def test_partial_stage_retains_prior_stages_and_does_not_email(self):
        stages, sns, config = self.stages(), self.sns(), self.config()
        first = Mock(side_effect=lambda stage, *args: {'status': 'partial', 'reason': 'record_limit'}
                     if stage == 'documents' else stages[stage])
        result = b.run(self.store, self.settings, config, self.universe, self.taxonomy, sns, stage_runner=first)
        self.assertEqual(result['next_date'], str(self.start))
        sns.publish.assert_not_called()
        resume = Mock(side_effect=lambda stage, *args: stages[stage])
        b.run(self.store, self.settings, config, self.universe, self.taxonomy, sns, stage_runner=resume)
        self.assertNotIn('sec', [call.args[0] for call in resume.call_args_list])
        self.assertNotIn('hkex', [call.args[0] for call in resume.call_args_list])
        self.assertEqual(sns.publish.call_count, 1)

    def test_corrupt_full_content_blocks_completion_notification(self):
        stages, sns = self.stages(), self.sns()
        record = self.read(stages['documents'])[0]['record']
        (self.store.root / record['payload']['content_reference']['key']).write_bytes(b'corruption')
        with self.assertRaisesRegex(SourceIssue, 'checksum'):
            b.run(self.store, self.settings, self.config(), self.universe, self.taxonomy, sns,
                stage_runner=Mock(side_effect=lambda stage, *args: stages[stage]))
        sns.publish.assert_not_called()

    def test_email_failure_retries_without_recollecting(self):
        stages, sns, config = self.stages(), self.sns(), self.config()
        runner = Mock(side_effect=lambda stage, *args: stages[stage])
        sns.publish.side_effect = RuntimeError('SNS unavailable')
        with self.assertRaises(RuntimeError):
            b.run(self.store, self.settings, config, self.universe, self.taxonomy, sns, stage_runner=runner)
        sns.publish.side_effect = None
        b.run(self.store, self.settings, config, self.universe, self.taxonomy, sns, stage_runner=runner)
        self.assertEqual(runner.call_count, len(b.STAGES))

    def test_recipient_change_blocks_email(self):
        stages, sns = self.stages(), self.sns()
        sns.get_paginator.return_value.paginate.return_value[0]['Subscriptions'][0]['Endpoint'] = 'someone-else@example.com'
        with self.assertRaisesRegex(SourceIssue, 'subscription_mismatch'):
            b.run(self.store, self.settings, self.config(), self.universe, self.taxonomy, sns,
                stage_runner=Mock(side_effect=lambda stage, *args: stages[stage]))
        sns.publish.assert_not_called()
