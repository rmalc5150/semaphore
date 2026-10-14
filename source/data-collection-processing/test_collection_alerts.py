import copy
from datetime import datetime, timezone
import io
import json
import unittest
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError
from collection_alerts import Watchdog, evaluate, outcome_issues, stamp
from collection_health_exporter import Evidence
from deploy_collection_monitoring import retention, sms_readiness

NOW = 1790418000
UNIT = 'optima-example.service'
CONFIG = {'bucket': 'test-bucket', 'prefix': 'research-data/monitoring', 'retention_days': 30,
          'heartbeat_max_age_seconds': 2700, 'reminder_seconds': 21600,
          'email_topic_arn': 'email-topic', 'sms_topic_arn': 'sms-topic',
          'jobs': {UNIT: {'queue_timeout_seconds': 21600, 'execution_timeout_seconds': 2700,
                          'max_start_gap_seconds': 43200, 'stale_progress_seconds': 43200}}}


def health(**changes):
    job = {'timer_enabled': 'enabled', 'timer_state': 'active', 'activity': 'idle',
           'last_start_age_seconds': 60, 'result': 'success', 'exit_status': 0,
           'progress': {'token': 'one', 'pending': False, 'last_verified_at': stamp(NOW-60)}}
    job.update(changes)
    return {'checked_at': stamp(NOW), 'jobs': {UNIT: job}}


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.deleted = []
        self.lifecycle = [{'ID': 'unrelated', 'Status': 'Enabled', 'Filter': {'Prefix': 'other/'}, 'Expiration': {'Days': 90}}]

    def put_object(self, Bucket, Key, Body, **kwargs):
        self.objects[Key] = {'Body': bytes(Body), 'LastModified': datetime.fromtimestamp(NOW, timezone.utc)}

    def get_object(self, Bucket, Key):
        if Key not in self.objects:
            raise ClientError({'Error': {'Code': 'NoSuchKey'}}, 'GetObject')
        obj = self.objects[Key]
        return {'Body': io.BytesIO(obj['Body']), 'ContentLength': len(obj['Body']), 'LastModified': obj['LastModified']}

    def get_paginator(self, name):
        return self

    def paginate(self, Bucket, Prefix):
        rows = [dict(Key=k, LastModified=v['LastModified']) for k,v in self.objects.items() if k.startswith(Prefix)]
        # Deliberately split pages to exercise pagination and deletion during iteration.
        for offset in range(0, len(rows), 2):
            yield {'Contents': rows[offset:offset+2]}

    def delete_objects(self, Bucket, Delete):
        for row in Delete['Objects']:
            self.deleted.append(row['Key'])
            del self.objects[row['Key']]
        return {}

    def get_bucket_versioning(self, **kwargs):
        return {}

    def get_bucket_lifecycle_configuration(self, **kwargs):
        return {'Rules': self.lifecycle}

    def put_bucket_lifecycle_configuration(self, Bucket, LifecycleConfiguration):
        self.lifecycle = LifecycleConfiguration['Rules']


class FakeSNS:
    def __init__(self):
        self.messages = []
        self.fail = None

    def publish(self, **kwargs):
        if kwargs['TopicArn'] == self.fail:
            raise RuntimeError('delivery denied')
        self.messages.append(kwargs)
        return {'MessageId': str(len(self.messages))}


class EvaluationTests(unittest.TestCase):
    def test_sms_permission_failure_does_not_block_watchdog_deployment(self):
        sns = Mock()
        sns.get_sms_sandbox_account_status.side_effect = ClientError({'Error': {'Code': 'AuthorizationError', 'Message': 'sms-voice:DescribeAccountAttributes denied'}}, 'GetSMSSandboxAccountStatus')
        self.assertIn('DescribeAccountAttributes', sms_readiness(sns, '+13104033167')['sms_readiness_error'])
        sns.create_sms_sandbox_phone_number.assert_not_called()

    def test_sms_verified_destination_does_not_resend_code(self):
        sns = Mock()
        sns.get_sms_sandbox_account_status.return_value = {'IsInSandbox': True}
        sns.list_sms_sandbox_phone_numbers.return_value = {'PhoneNumbers': [{'PhoneNumber': '+13104033167', 'Status': 'Verified'}]}
        self.assertTrue(sms_readiness(sns, '+13104033167')['sms_number_verified'])
        sns.create_sms_sandbox_phone_number.assert_not_called()

    def test_sms_unverified_destination_requests_code(self):
        sns = Mock()
        sns.get_sms_sandbox_account_status.return_value = {'IsInSandbox': True}
        sns.list_sms_sandbox_phone_numbers.return_value = {'PhoneNumbers': []}
        self.assertIn('sms_action_required', sms_readiness(sns, '+13104033167'))
        sns.create_sms_sandbox_phone_number.assert_called_once_with(PhoneNumber='+13104033167', LanguageCode='en-US')

    def test_nested_partial_failures_and_expected_quota(self):
        result = {'status': 'partial', 'sources': {'news': {'status': 'partial', 'reason': 'daily_request_budget_reached'},
                  'nmpa': {'status': 'partial', 'reason': 'rendered_source_unavailable'}}}
        self.assertEqual(outcome_issues(result), {('rendered_source_unavailable', 'low')})

    def test_integrity_failure_high(self):
        self.assertIn(('ValueError', 'high'), outcome_issues({'status': 'failed', 'error_type': 'ValueError', 'message': 'roundtrip hash mismatch'}))

    def test_readback_integrity_failure_high(self):
        alerts, _ = evaluate({'checked_at': stamp(NOW), 'jobs': {UNIT: {'inspection_error': 'Publication verification checksum mismatch'}}}, {}, CONFIG, NOW)
        self.assertEqual(alerts[UNIT+':inspection_failed']['severity'], 'high')

    def test_patent_budget_is_expected(self):
        self.assertFalse(outcome_issues({'status': 'partial', 'reason': 'daily_query_budget_reached'}))

    def test_queue_not_running_timeout(self):
        alerts, _ = evaluate(health(activity='queued', activity_seconds=7200), {}, CONFIG, NOW)
        self.assertFalse(alerts)
        alerts, _ = evaluate(health(activity='running', activity_seconds=7200), {}, CONFIG, NOW)
        self.assertIn(UNIT+':execution_timeout', alerts)

    def test_success_exit_75_is_queue_failure(self):
        alerts, _ = evaluate(health(exit_status=75), {}, CONFIG, NOW)
        self.assertIn(UNIT+':queue_timeout', alerts)

    def test_missed_timer_and_disabled_timer(self):
        alerts, _ = evaluate(health(timer_state='inactive', last_start_age_seconds=50000), {}, CONFIG, NOW)
        self.assertIn(UNIT+':timer_disabled', alerts)
        self.assertIn(UNIT+':missed_run', alerts)

    def test_missing_host_keeps_existing_incidents(self):
        prior = {'active': {'x': {'unit': UNIT, 'code': 'source_failed'}}}
        alerts, _ = evaluate(None, prior, CONFIG, NOW)
        self.assertIn('host:heartbeat_missing', alerts)
        self.assertIn('x', alerts)

    def test_restart_does_not_resolve_failure(self):
        prior = {'active': {UNIT+':service_failed': {'unit': UNIT, 'code': 'service_failed', 'severity': 'low', 'evidence_at': stamp(NOW-10)}}}
        alerts, _ = evaluate(health(activity='running'), prior, CONFIG, NOW)
        self.assertIn(UNIT+':service_failed', alerts)
        snapshot = health()
        snapshot['jobs'][UNIT]['progress']['last_verified_at'] = stamp(NOW)
        alerts, _ = evaluate(snapshot, prior, CONFIG, NOW)
        self.assertFalse(alerts)

    def test_verified_successful_execution_recovers_only_process_failure(self):
        prior = {'active': {UNIT+':'+code: {'unit': UNIT, 'code': code,
                 'severity': 'low', 'evidence_at': stamp(NOW-10)}
                 for code in ('service_failed', 'source_failed')}}
        alerts, _ = evaluate(health(successful_execution_at=stamp(NOW)), prior, CONFIG, NOW)
        self.assertNotIn(UNIT+':service_failed', alerts)
        self.assertIn(UNIT+':source_failed', alerts)

    def test_page_limit_is_expected_but_stalled_backlog_still_alerts(self):
        self.assertFalse(outcome_issues({'status': 'partial', 'reason': 'page_limit'}))
        prior = {'observations': {UNIT: {'token': 'one', 'last_change': NOW-50000}}}
        snapshot = health(progress={'token': 'one', 'pending': True, 'last_verified_at': stamp(NOW-50000)})
        self.assertIn(UNIT+':progress_stalled', evaluate(snapshot, prior, CONFIG, NOW)[0])

    def test_pending_backlog_stalls_but_caught_up_does_not(self):
        prior = {'observations': {UNIT: {'token': 'one', 'last_change': NOW-50000}}}
        progress = {'token': 'one', 'pending': True, 'last_verified_at': stamp(NOW-50000)}
        alerts, _ = evaluate(health(progress=progress), prior, CONFIG, NOW)
        self.assertIn(UNIT+':progress_stalled', alerts)
        progress['pending'] = False
        self.assertFalse(evaluate(health(progress=progress), prior, CONFIG, NOW)[0])

    def test_daily_quota_gets_reset_grace(self):
        prior = {'observations': {UNIT: {'token': 'one', 'last_change': NOW-50000}}}
        progress = {'token': 'one', 'pending': True, 'last_verified_at': stamp(NOW-50000)}
        self.assertFalse(evaluate(health(progress=progress, quota_wait=True), prior, CONFIG, NOW)[0])
        prior['observations'][UNIT]['last_change'] = NOW-140000
        progress['last_verified_at'] = stamp(NOW-140000)
        self.assertIn(UNIT+':progress_stalled', evaluate(health(progress=progress, quota_wait=True), prior, CONFIG, NOW)[0])


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.s3, self.sns = FakeS3(), FakeSNS()
        self.watch = Watchdog(self.s3, self.sns, copy.deepcopy(CONFIG))

    def test_high_routes_both_and_deduplicates(self):
        self.watch.run(NOW)  # missing host
        self.assertEqual({x['TopicArn'] for x in self.sns.messages}, {'email-topic', 'sms-topic'})
        self.watch.run(NOW+1800)
        self.assertEqual(len(self.sns.messages), 2)
        self.watch.run(NOW+21601)
        self.assertEqual(len(self.sns.messages), 4)

    def test_low_routes_email_only(self):
        self.watch.put('health/latest.json', health(timer_state='inactive'))
        self.watch.run(NOW)
        self.assertEqual([x['TopicArn'] for x in self.sns.messages], ['email-topic'])

    def test_failed_sms_retries_without_repeating_email(self):
        self.sns.fail = 'sms-topic'
        result = self.watch.run(NOW)
        self.assertEqual(len(result['notification_errors']), 1)
        self.sns.fail = None
        self.watch.run(NOW+1800)
        self.assertEqual([x['TopicArn'] for x in self.sns.messages], ['email-topic', 'sms-topic'])

    def test_recovery_is_emailed_and_persisted(self):
        self.watch.run(NOW)
        self.watch.put('health/latest.json', health())
        self.watch.run(NOW+60)
        self.assertIn('RECOVERED', self.sns.messages[-1]['Subject'])
        self.assertFalse(self.watch.get('state/latest.json')['active'])

    def test_recorder_never_sends_and_preserves_pending_delivery(self):
        self.watch.run(NOW, notifications=False)
        self.assertFalse(self.sns.messages)
        self.assertFalse(self.watch.get('state/latest.json')['active']['host:heartbeat_missing']['last_notified'])
        self.watch.run(NOW+60)
        self.assertEqual(len(self.sns.messages), 2)

    def test_retention_only_removes_older_history(self):
        for path in ['alerts/old.json', 'checks/old.json', 'state/latest.json', 'health/latest.json']:
            self.watch.put(path, {})
            self.s3.objects[self.watch.prefix+path]['LastModified'] = datetime.fromtimestamp(NOW-31*86400, timezone.utc)
        self.watch.put('alerts/recent.json', {})
        self.assertEqual(self.watch.purge(NOW), 2)
        self.assertIn(self.watch.prefix+'state/latest.json', self.s3.objects)
        self.assertIn(self.watch.prefix+'health/latest.json', self.s3.objects)
        self.assertIn(self.watch.prefix+'alerts/recent.json', self.s3.objects)

    def test_deletion_errors_are_not_silently_ignored(self):
        self.watch.put('alerts/old.json', {})
        self.s3.objects[self.watch.prefix+'alerts/old.json']['LastModified'] = datetime.fromtimestamp(NOW-31*86400, timezone.utc)
        with patch.object(self.s3, 'delete_objects', return_value={'Errors': [{'Code': 'AccessDenied'}]}):
            with self.assertRaisesRegex(RuntimeError, 'retention deletion failed'):
                self.watch.purge(NOW)

    def test_recovery_delivery_failure_retries(self):
        self.watch.run(NOW)
        self.watch.put('health/latest.json', health())
        self.sns.fail = 'email-topic'
        self.watch.run(NOW+60)
        self.assertTrue(self.watch.get('state/latest.json')['pending_recoveries'])
        self.sns.fail = None
        self.watch.run(NOW+120)
        self.assertFalse(self.watch.get('state/latest.json')['pending_recoveries'])
        self.assertIn('RECOVERED', self.sns.messages[-1]['Subject'])

    def test_lifecycle_preserves_unrelated_rules(self):
        rules = retention(self.s3, CONFIG)
        self.assertEqual(len(rules), 3)
        self.assertEqual(rules[0]['ID'], 'unrelated')
        self.assertEqual(len(retention(self.s3, CONFIG)), 3)

    def test_corrupt_receipt_fails_closed(self):
        evidence = Evidence(self.s3, CONFIG['bucket'], 'research-data')
        self.s3.put_object(Bucket=CONFIG['bucket'], Key='research-data/verified.json', Body=b'{"status":"verified"}')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            evidence.confirmed({'verification_key': 'verified.json', 'verification_sha256': 'wrong'})


if __name__ == '__main__':
    unittest.main()
