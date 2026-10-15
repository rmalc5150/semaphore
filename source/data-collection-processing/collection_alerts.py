"""S3-backed collection watchdog. No collector mutations and no database.

Used by the independent Lambda and, until cloud deployment, the local recorder.
Alert history is append-only; state/latest.json is the most recent complete check.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from uuid import uuid4

DAY = 86400
NON_ALERTING = {"document_requires_ocr_or_page_review"}
EXPECTED = {
    'daily_quota_reserve', 'shared_eodhd_quota_reserve',
    'daily_request_budget_reached', 'run_request_budget_reached',
    'market_daily_request_budget_reached', 'market_run_request_budget_reached',
    'eodhd_shared_quota_reached', 'eodhd_quota_refresh_required',
    'daily_query_budget_reached', 'daily_bytes_budget_reached',
    'runner_already_active', 'publisher_already_active',
    'max_pages_reached', 'max_records_reached', 'page_budget_reached', 'page_limit',
}
CRITICAL = ('hash mismatch', 'hash_mismatch', 'checksum', 'integrity',
            'roundtrip', 'round-trip', 'missing publication receipt evidence')


def stamp(value=None):
    return datetime.fromtimestamp(value, timezone.utc).isoformat().replace('+00:00', 'Z') if value is not None else datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def epoch(value):
    if not value:
        return 0
    if isinstance(value, (int, float)):
        return value
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def outcome_issues(value):
    """Inspect nested source outcomes, including failures hidden by exit code 2."""
    found = set()
    if isinstance(value, list):
        for item in value:
            found.update(outcome_issues(item))
    elif isinstance(value, dict):
        reason = str(value.get('reason') or value.get('reason_code') or value.get('capture_error') or value.get('error_type') or value.get('error') or '')
        message = str(value.get('message') or '')
        status = value.get('status')
        if reason and reason not in EXPECTED | NON_ALERTING and status in {'failed', 'partial', 'blocked'}:
            found.add((reason, 'high' if any(x in (reason+' '+message).lower() for x in CRITICAL) else 'low'))
        if value.get('exit_code', 0) not in (0, 2):
            found.add(('subprocess_exit_' + str(value['exit_code']), 'low'))
        if any(value.get('symbols_with_unresolved_windows', {}).values()):
            found.add(('unresolved_market_coverage', 'low'))
        children = set()
        for item in value.values():
            if isinstance(item, (dict, list)):
                children.update(outcome_issues(item))
        found.update(children)
        if status in {'failed', 'blocked'} and not reason and not children:
            found.add((status, 'low'))
    return found


def evaluate(snapshot, prior, config, now):
    """Pure incident evaluation; queue time and payload execution are separate."""
    prior = {**prior, 'active': {k: v for k, v in prior.get('active', {}).items() if v['code'] not in NON_ALERTING}}
    incidents = {}
    observations = dict(prior.get('observations', {}))

    def add(unit, code, severity, detail, evidence_at=None):
        if code in NON_ALERTING:
            return
        key = unit + ':' + code
        incidents[key] = {'unit': unit, 'code': code, 'severity': severity,
                          'detail': detail, 'evidence_at': evidence_at or stamp(now)}

    if not snapshot or now - epoch(snapshot.get('checked_at')) > config['heartbeat_max_age_seconds']:
        add('host', 'heartbeat_missing', 'high', 'Collection server health report is missing or older than 45 minutes.')
        # Absence of evidence cannot resolve pre-existing incidents.
        for key, item in prior.get('active', {}).items():
            if item['unit'] != 'host':
                incidents[key] = item
        return incidents, observations
    for error in snapshot.get('errors', []):
        add('monitor', 'inspection_failed', 'high', str(error)[:500])
    if config.get('daily_health_required'):
        audit=snapshot.get('daily_audit')
        if not audit or now-epoch(audit.get('checked_at'))>26*3600:
            add('optima-daily-health-audit.service','daily_audit_missing_or_stale','low','Fresh daily S3/Athena audit is missing or older than 26 hours.')
        else:
            failures=[r for r in audit.get('query_failures',[]) if r['name'] not in audit.get('expected_unpublished_routes',[])]
            if failures or audit.get('s3_failures') or audit.get('receipt_query_failures'):
                add('optima-daily-health-audit.service','daily_audit_verification_failed','low',f'{len(failures)} readback failures; {len(audit.get("s3_failures",[]))} S3 failures; {len(audit.get("receipt_query_failures",[]))} receipt query failures.',audit['checked_at'])
    for name,stage in snapshot.get('pipeline_stages',{}).items():
        if stage.get('status')=='verification_failed':
            add('pipeline:'+name,'pipeline_output_verification_failed','low',str(stage)[:500])
    for unit, policy in config['jobs'].items():
        job = snapshot.get('jobs', {}).get(unit)
        if not job or job.get('inspection_error'):
            detail = (job or {}).get('inspection_error', 'Job absent from report')
            add(unit, 'inspection_failed', 'high' if any(x in detail.lower() for x in CRITICAL) else 'low', detail)
            for key, item in prior.get('active', {}).items():
                if item['unit'] == unit:
                    incidents[key] = item
            continue
        if job.get('timer_enabled') != 'enabled' or job.get('timer_state') != 'active':
            add(unit, 'timer_disabled', 'low', 'Scheduled timer is disabled or inactive.')
        state = job.get('activity', 'idle')
        elapsed = job.get('activity_seconds', 0)
        if state == 'queued' and elapsed > policy.get('queue_timeout_seconds', 0) + 1800:
            add(unit, 'queue_timeout', 'low', f'Waiting for shared collection lock for {int(elapsed/60)} minutes.')
        if state == 'running' and elapsed > policy['execution_timeout_seconds'] + 1800:
            add(unit, 'execution_timeout', 'low', f'Payload has run for {int(elapsed/60)} minutes.')
        if state == 'idle' and job.get('last_start_age_seconds', now) > policy['max_start_gap_seconds']:
            add(unit, 'missed_run', 'low', 'No invocation within the configured schedule and queue grace period.')
        if job.get('result') not in ('success', None, '') and state == 'idle':
            add(unit, 'service_failed', 'high' if job['result'] == 'oom-kill' else 'low',
                'systemd result: '+job['result'])
        if job.get('exit_status') == 75 and state == 'idle':
            add(unit, 'queue_timeout', 'low', 'The shared collection lock timed out; accepted systemd exit 75 is not completion.')
        for event in job.get('failure_events', []):
            add(unit, event['code'], event['severity'], event['detail'], event['at'])
        for issue in job.get('issues', []):
            add(unit, issue['code'], issue['severity'], issue['detail'], issue.get('at'))
        progress = job.get('progress', {})
        old = observations.get(unit, {})
        token = progress.get('token')
        changed = token is not None and token != old.get('token')
        last_change = now if changed else old.get('last_change', now)
        verified = max((progress.get('last_verified_at'), old.get('last_verified_at')), key=epoch)
        observations[unit] = {'token': token or old.get('token'), 'last_change': last_change,
                              'last_verified_at': verified}
        stall_limit = max(policy['stale_progress_seconds'], 36*3600) if job.get('quota_wait') else policy['stale_progress_seconds']
        if progress.get('pending') and now - max(last_change, epoch(verified)) > stall_limit:
            add(unit, 'progress_stalled', 'low', 'Outstanding work with no committed progress beyond the job-specific threshold.')
        # A restart or an empty successful invocation does not prove recovery.
        for key, incident in prior.get('active', {}).items():
            if incident['unit'] != unit or key in incidents:
                continue
            if incident['code'] in EXPECTED:
                continue
            structural = incident['code'] in {'timer_disabled', 'queue_timeout', 'execution_timeout', 'missed_run', 'inspection_failed',
                'daily_audit_missing_or_stale','daily_audit_verification_failed'}
            recovered = epoch(progress.get('last_verified_at')) > epoch(incident.get('evidence_at'))
            if (unit == 'optima-market-collection.service' and incident['code'] in
                    {'market_empty_price_window_unverified', 'unresolved_market_coverage'}):
                resolution = job.get('coverage_resolutions', {}).get(incident['code'], {})
                recovered |= (resolution.get('basis') == 'reviewed_scoped_exclusions' and
                              bool(resolution.get('registry_keys')) and
                              epoch(resolution.get('at')) > epoch(incident.get('evidence_at')))
            if incident['code'] == 'service_failed':
                recovered |= epoch(job.get('successful_execution_at')) > epoch(incident.get('evidence_at'))
            if not structural and not recovered:
                incidents[key] = incident
    return incidents, observations


class Watchdog:
    def __init__(self, s3, sns, config, cloudwatch=None):
        self.s3, self.sns, self.config, self.cloudwatch = s3, sns, config, cloudwatch
        self.bucket, self.prefix = config['bucket'], config['prefix'].rstrip('/') + '/'

    def get(self, suffix):
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=self.prefix+suffix)
            return json.loads(response['Body'].read())
        except Exception as exc:
            if getattr(exc, 'response', {}).get('Error', {}).get('Code') in {'NoSuchKey', '404'}:
                return None
            raise

    def put(self, suffix, value):
        self.s3.put_object(Bucket=self.bucket, Key=self.prefix+suffix,
                           Body=(json.dumps(value, sort_keys=True)+'\n').encode(),
                           ContentType='application/json', ServerSideEncryption='AES256')

    def purge(self, now):
        """Only the dedicated immutable history prefixes are eligible for deletion."""
        deleted = 0
        for folder in ('alerts/', 'checks/'):
            for page in self.s3.get_paginator('list_objects_v2').paginate(Bucket=self.bucket, Prefix=self.prefix+folder):
                expired = [{'Key': o['Key']} for o in page.get('Contents', [])
                           if o['LastModified'].timestamp() < now - self.config['retention_days']*DAY]
                if expired:
                    result = self.s3.delete_objects(Bucket=self.bucket, Delete={'Objects': expired, 'Quiet': True})
                    if result.get('Errors'):
                        raise RuntimeError('Alert retention deletion failed: '+json.dumps(result['Errors'])[:500])
                    deleted += len(expired)
        return deleted

    def email_digest(self, prior, active, pending, now, notifications):
        interval = self.config['email_digest_seconds']
        digest = prior.get('email_digest') or {'period_started_at': stamp(now), 'incidents': {}}
        entries = {k: v for k, v in digest.get('incidents', {}).items() if v['incident']['code'] not in NON_ALERTING}
        for key, item in active.items():
            old = entries.get(key, {})
            entries[key] = {'incident': item, 'status': 'open',
                            'first_observed_at': old.get('first_observed_at', stamp(now)),
                            'last_observed_at': stamp(now)}
        for key, item, route, transition in pending:
            if route == 'email' and transition == 'recovered':
                old = entries.get(key, {})
                entries[key] = {'incident': item, 'status': 'recovered',
                                'first_observed_at': old.get('first_observed_at', item.get('first_seen', stamp(now))),
                                'last_observed_at': stamp(now)}
        digest['incidents'] = entries
        errors = []
        if now - epoch(digest['period_started_at']) < interval:
            return digest, errors
        topic = self.config.get('email_topic_arn')
        if not notifications or not topic:
            return digest, errors
        from monitoring_overview import overview
        subject, body = overview(active, now, digest['period_started_at'], self.get('health/latest.json'))
        history = 'alerts/'+stamp(now)[:10]+'/'+stamp(now).replace(':', '')+'-digest-'+uuid4().hex+'.json'
        notice = {'at': stamp(now), 'channel': 'email', 'transition': 'digest', 'subject': subject, 'body': body,
                  'period_started_at': digest['period_started_at'], 'incidents': entries, 'delivery': 'pending'}
        self.put(history, notice)
        if len(body.encode('utf-8')) > 200000:
            body = body.encode('utf-8')[:200000].decode('utf-8', errors='ignore')+'\nSummary truncated; full details in S3.'
        body += '\nFull report: s3://'+self.bucket+'/'+self.prefix+history
        try:
            response = self.sns.publish(TopicArn=topic, Subject=subject, Message=body)
            notice.update(delivery='accepted_by_sns', message_id=response['MessageId'])
            digest = {'period_started_at': stamp(now), 'last_sent_at': stamp(now), 'incidents': {}}
        except Exception as exc:
            notice.update(delivery='failed', error=str(exc)[:500])
            errors.append('email: '+str(exc)[:500])
        self.put(history, notice)
        return digest, errors

    def run(self, now=None, notifications=True):
        now = now if now is not None else datetime.now(timezone.utc).timestamp()
        prior = self.get('state/latest.json') or {}
        # Retire the obsolete page-review alert under the user's skip policy,
        # without sending a misleading recovery notice. History remains in S3.
        prior['active'] = {k: v for k, v in prior.get('active', {}).items() if v['code'] not in NON_ALERTING}
        prior['pending_recoveries'] = [p for p in prior.get('pending_recoveries', []) if p['incident']['code'] not in NON_ALERTING]
        snapshot = self.get('health/latest.json')
        current, observations = evaluate(snapshot, prior, self.config, now)
        if self.cloudwatch and self.config.get('digest_alarm_names'):
            try:
                alarms = self.cloudwatch.describe_alarms(AlarmNames=self.config['digest_alarm_names'])['MetricAlarms']
                for alarm in alarms:
                    from monitoring_overview import sms_delivery_confirmed
                    alarm_key = 'aws:' + alarm['AlarmName']
                    previous = prior.get('active', {}).get(alarm_key) or prior.get('email_digest', {}).get('incidents', {}).get(alarm_key, {}).get('incident')
                    unverified_sms = ('-sms-' in alarm['AlarmName'] and previous and not sms_delivery_confirmed(alarm))
                    if alarm['StateValue'] == 'ALARM' or unverified_sms:
                        key = 'aws:' + alarm['AlarmName']
                        current[key] = {'unit': 'aws', 'code': alarm['AlarmName'], 'severity': 'high' if not '-sms-' in alarm['AlarmName'] else 'low',
                                        'detail': ('SMS delivery remains unverified after a failure; no subsequent positive delivery datapoint.' if unverified_sms and alarm['StateValue'] != 'ALARM' else alarm.get('StateReason', 'AWS monitoring alarm')), 'evidence_at': stamp(now)}
            except Exception as exc:
                current['monitor:alarm_inspection_failed'] = {'unit': 'monitor', 'code': 'alarm_inspection_failed', 'severity': 'low', 'detail': str(exc)[:500], 'evidence_at': stamp(now)}
        active = {}
        pending = []
        for key, incident in current.items():
            old = prior.get('active', {}).get(key, {})
            item = {**incident, 'first_seen': old.get('first_seen', stamp(now)),
                    'last_notified': old.get('last_notified', {}), 'last_seen': stamp(now)}
            active[key] = item
            routes = ['email'] + (['sms'] if item['severity'] == 'high' else [])
            for route in routes:
                if now - epoch(item['last_notified'].get(route)) >= self.config['reminder_seconds']:
                    pending.append((key, item, route, 'open'))
        for key, item in prior.get('active', {}).items():
            if key not in current and (item.get('last_notified') or self.config.get('email_digest_seconds')):
                pending.append((key, item, 'email', 'recovered'))
        # Retain recoveries whose delivery failed; do not silently drop them.
        for entry in prior.get('pending_recoveries', []):
            if entry['key'] not in current:
                pending.append((entry['key'], entry['incident'], 'email', 'recovered'))
        from monitoring_overview import overview
        overview_subject, overview_body = overview(active, now, stamp(now), snapshot)
        self.put('overview/latest.json', {'checked_at': stamp(now), 'subject': overview_subject, 'body': overview_body})
        errors, recoveries = [], []
        digest = None
        if self.config.get('email_digest_seconds'):
            digest, errors = self.email_digest(prior, active, pending, now, notifications)
            pending = [entry for entry in pending if entry[2] != 'email']
        for key, item, route, transition in pending:
            topic = self.config.get(route+'_topic_arn')
            notice = {'at': stamp(now), 'incident_id': key, 'transition': transition,
                      'channel': route, 'incident': item, 'delivery': 'pending'}
            history_key = 'alerts/'+stamp(now)[:10]+'/'+stamp(now).replace(':', '')+'-'+uuid4().hex+'.json'
            self.put(history_key, notice)  # Durable intent before external notification.
            if not notifications or not topic:
                notice['delivery'] = 'not_configured' if not topic else 'disabled'
            else:
                unit = item['unit'].removeprefix('optima-').removesuffix('.service')
                subject = f"Optima {transition.upper()} {item['severity'].upper()}: {unit}"[:100]
                if route == 'sms':
                    message = f"Optima HIGH: {unit}: {item['code']}. See alert email and S3 monitoring history."[:160]
                else:
                    message = (subject+'\n\n'+item['detail']+'\n\nIncident: '+key+
                               '\nEvidence at: '+str(item.get('evidence_at'))+
                               '\nLast verified progress: '+str(observations.get(item['unit'], {}).get('last_verified_at'))+
                               '\nStatus: s3://'+self.bucket+'/'+self.prefix+'state/latest.json'+
                               '\nHistory: s3://'+self.bucket+'/'+self.prefix+history_key+
                               '\nAction: inspect the named service journal and the source checkpoint; verify committed progress before closing.')
                try:
                    response = self.sns.publish(TopicArn=topic, Subject=subject, Message=message,
                        MessageAttributes={'AWS.SNS.SMS.SMSType': {'DataType': 'String', 'StringValue': 'Transactional'}} if route == 'sms' else {})
                    notice.update(delivery='accepted_by_sns', message_id=response['MessageId'])
                    if transition == 'open':
                        active[key]['last_notified'][route] = stamp(now)
                except Exception as exc:
                    notice.update(delivery='failed', error=str(exc)[:500])
                    errors.append(route+': '+str(exc)[:500])
            if transition == 'recovered' and notice['delivery'] != 'accepted_by_sns':
                recoveries.append({'key': key, 'incident': item})
            self.put(history_key, notice)
        deleted = self.purge(now)
        result = {'schema_version': 1, 'checked_at': stamp(now), 'active': active,
                  'observations': observations, 'pending_recoveries': recoveries,
                  'notification_errors': errors, 'notifications_enabled': notifications,
                  'notification_topics_configured': bool(self.config.get('email_topic_arn') and self.config.get('sms_topic_arn')),
                  'health_checked_at': (snapshot or {}).get('checked_at'), 'expired_files_deleted': deleted}
        if digest is not None:
            result['email_digest'] = digest
        self.put('checks/'+stamp(now)[:10]+'/'+stamp(now).replace(':', '')+'.json', result)
        self.put('state/latest.json', result)
        if self.cloudwatch:
            self.cloudwatch.put_metric_data(Namespace='Optima/CollectionMonitoring', MetricData=[
                {'MetricName': 'WatchdogCompleted', 'Value': 1, 'Unit': 'Count'},
                {'MetricName': 'NotificationErrors', 'Value': len(errors), 'Unit': 'Count'}])
        return {'checked_at': result['checked_at'], 'active_alerts': len(active),
                'notification_errors': errors, 'expired_files_deleted': deleted}


def handler(event, context):
    import boto3
    with open('collection-monitoring.json') as f:
        config = json.load(f)
    region = config['region']
    return Watchdog(boto3.client('s3', region_name=region), boto3.client('sns', region_name=region),
                    config, boto3.client('cloudwatch', region_name=region)).run()
