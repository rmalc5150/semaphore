#!/usr/bin/env python3
"""Idempotent AWS deployment; --permissions writes a scoped administrator handoff.

Run with the normal instance identity after its administrator grants the missing
deployment permissions. Never assumes an unrelated or more privileged role.
"""
import argparse
import io
import json
from pathlib import Path
import time
import zipfile

import boto3
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parent
NAME = 'optima-collection-watchdog'
SCHEDULE = 'optima-collection-watchdog-30min'


def policy(statements):
    return {'Version': '2012-10-17', 'Statement': statements}


def allow(actions, resources, **extra):
    return {'Effect': 'Allow', 'Action': actions, 'Resource': resources, **extra}


def sms_permissions():
    return allow(['sms-voice:DescribeAccountAttributes', 'sms-voice:DescribeVerifiedDestinationNumbers',
                  'sms-voice:DescribeSpendLimits', 'sms-voice:DescribePhoneNumbers', 'sms-voice:DescribeOptedOutNumbers',
                  'sms-voice:CreateVerifiedDestinationNumber', 'sms-voice:SendDestinationNumberVerificationCode',
                  'sms-voice:VerifyDestinationNumber', 'sms-voice:SendTextMessage'], '*',
                 Condition={'StringEquals': {'aws:CalledViaLast': 'sns.amazonaws.com'}})


def required_permissions(config, account):
    region = config['region']
    roles = [f'arn:aws:iam::{account}:role/{NAME}', f'arn:aws:iam::{account}:role/{NAME}-scheduler',
             f'arn:aws:iam::{account}:role/optima-collection-sms-delivery']
    topics = [f'arn:aws:sns:{region}:{account}:optima-collection-alerts-{kind}' for kind in ('email', 'sms')]
    function = f'arn:aws:lambda:{region}:{account}:function:{NAME}'
    log = f'arn:aws:logs:{region}:{account}:log-group:/aws/lambda/{NAME}'
    bucket = 'arn:aws:s3:::'+config['bucket']
    data_prefix = config['data_prefix'].rstrip('/')+'/'
    monitoring = config['prefix'].rstrip('/')+'/'
    sms_logs = f'arn:aws:logs:{region}:{account}:log-group:sns/{region}/{account}/*'
    return policy([
        sms_permissions(),
        allow(['iam:CreateRole', 'iam:GetRole', 'iam:PutRolePolicy', 'iam:TagRole'], roles),
        allow('iam:PassRole', roles[0], Condition={'StringEquals': {'iam:PassedToService': 'lambda.amazonaws.com'}}),
        allow('iam:PassRole', roles[1], Condition={'StringEquals': {'iam:PassedToService': 'scheduler.amazonaws.com'}}),
        allow('iam:PassRole', roles[2], Condition={'StringEquals': {'iam:PassedToService': 'sns.amazonaws.com'}}),
        allow(['sns:CreateTopic', 'sns:GetTopicAttributes', 'sns:SetTopicAttributes', 'sns:TagResource',
               'sns:Subscribe', 'sns:Unsubscribe', 'sns:ListSubscriptionsByTopic', 'sns:GetSubscriptionAttributes', 'sns:Publish'], topics),
        allow(['sns:GetSMSSandboxAccountStatus', 'sns:ListSMSSandboxPhoneNumbers', 'sns:CreateSMSSandboxPhoneNumber',
               'sns:VerifySMSSandboxPhoneNumber', 'sns:GetSMSAttributes', 'sns:SetSMSAttributes',
               'sns:ListOriginationNumbers', 'sns:CheckIfPhoneNumberIsOptedOut'], '*'),
        allow(['scheduler:CreateSchedule', 'scheduler:GetSchedule', 'scheduler:UpdateSchedule'],
              f'arn:aws:scheduler:{region}:{account}:schedule/default/{SCHEDULE}'),
        allow(['lambda:CreateFunction', 'lambda:GetFunction', 'lambda:GetFunctionConfiguration',
               'lambda:UpdateFunctionCode', 'lambda:UpdateFunctionConfiguration', 'lambda:PutFunctionConcurrency',
               'lambda:PutFunctionEventInvokeConfig', 'lambda:InvokeFunction', 'lambda:TagResource'], function),
        allow(['logs:CreateLogGroup', 'logs:PutRetentionPolicy'], [log, log+':*']),
        allow(['logs:PutRetentionPolicy', 'logs:FilterLogEvents', 'logs:GetLogEvents', 'logs:DescribeLogStreams'],
              [log, log+':*', sms_logs]),
        allow('logs:DescribeLogGroups', '*'),
        allow(['cloudwatch:GetMetricStatistics', 'cloudwatch:GetMetricData', 'cloudwatch:ListMetrics'], '*'),
        allow(['cloudwatch:PutMetricAlarm', 'cloudwatch:DescribeAlarms'],
              f'arn:aws:cloudwatch:{region}:{account}:alarm:optima-collection-watchdog-*'),
        allow(['s3:GetBucketVersioning', 's3:GetLifecycleConfiguration', 's3:PutLifecycleConfiguration'], bucket),
        allow('s3:ListBucket', bucket, Condition={'StringLike': {'s3:prefix': [data_prefix+'*']}}),
        allow('s3:GetObject', bucket+'/'+data_prefix+'*'),
        allow('s3:PutObject', bucket+'/'+monitoring+'*'),
        allow('s3:DeleteObject', [bucket+'/'+monitoring+'alerts/*', bucket+'/'+monitoring+'checks/*']),
        allow(['sms-voice:DescribeRegistration*', 'sms-voice:DescribePhoneNumbers', 'sms-voice:GetResourcePolicy'], '*',
              Condition={'StringEquals': {'aws:RequestedRegion': region}}),
        allow(['sms-voice:CreateRegistration', 'sms-voice:CreateRegistrationAttachment', 'sms-voice:RequestPhoneNumber'], '*',
              Condition={'StringEquals': {'aws:RequestedRegion': region, 'aws:RequestTag/Project': 'OptimaCollectionMonitoring'}}),
        # Phone allocation authorizes phone-number/* separately without request-tag context.
        allow('sms-voice:RequestPhoneNumber', f'arn:aws:sms-voice:{region}:{account}:phone-number/*',
              Condition={'StringEquals': {'aws:RequestedRegion': region}}),
        allow(['sms-voice:TagResource'],
              [f'arn:aws:sms-voice:{region}:{account}:{kind}/*' for kind in ('registration', 'registration-attachment', 'phone-number')],
              Condition={'StringEquals': {'aws:RequestTag/Project': 'OptimaCollectionMonitoring'}}),
        allow(['sms-voice:PutRegistrationFieldValue', 'sms-voice:CreateRegistrationAssociation',
               'sms-voice:CreateRegistrationVersion', 'sms-voice:SubmitRegistrationVersion', 'sms-voice:PutResourcePolicy'],
              [f'arn:aws:sms-voice:{region}:{account}:{kind}/*' for kind in ('registration', 'registration-attachment', 'phone-number')],
              Condition={'StringEquals': {'aws:ResourceTag/Project': 'OptimaCollectionMonitoring'}}),

    ])


def role(iam, name, service, statements, account):
    trust = policy([{'Effect': 'Allow', 'Principal': {'Service': service}, 'Action': 'sts:AssumeRole'}])
    if service == 'scheduler.amazonaws.com':
        trust['Statement'][0]['Condition'] = {'StringEquals': {'aws:SourceAccount': account},
                                             'ArnLike': {'aws:SourceArn': f'arn:aws:scheduler:*:{account}:schedule-group/default'}}
    try:
        response = iam.create_role(RoleName=name, AssumeRolePolicyDocument=json.dumps(trust),
                                   Description='Optima collection monitoring only')
        arn = response['Role']['Arn']
    except ClientError as exc:
        if exc.response['Error']['Code'] != 'EntityAlreadyExists':
            raise
        existing = iam.get_role(RoleName=name)['Role']
        # Do not take over an unrelated role with a colliding name.
        services = [s.get('Principal', {}).get('Service') for s in existing['AssumeRolePolicyDocument']['Statement']]
        if services != [service]:
            raise ValueError('Existing monitoring role has an unexpected trust policy')
        arn = existing['Arn']
    iam.put_role_policy(RoleName=name, PolicyName='CollectionMonitoringOnly', PolicyDocument=json.dumps(policy(statements)))
    return arn


def retention(s3, config):
    bucket, prefix = config['bucket'], config['prefix'].rstrip('/')+'/'
    versioning = s3.get_bucket_versioning(Bucket=bucket).get('Status')
    if versioning in ('Enabled', 'Suspended'):
        raise ValueError('Versioned monitoring bucket needs explicit version cleanup before guaranteeing 30-day erasure')
    try:
        rules = s3.get_bucket_lifecycle_configuration(Bucket=bucket)['Rules']
    except ClientError as exc:
        if exc.response['Error']['Code'] != 'NoSuchLifecycleConfiguration':
            raise
        rules = []
    ids = {'optima-monitoring-alerts-30-days', 'optima-monitoring-checks-30-days'}
    rules = [r for r in rules if r['ID'] not in ids]
    for folder in ('alerts', 'checks'):
        rules.append({'ID': f'optima-monitoring-{folder}-30-days', 'Status': 'Enabled',
                      'Filter': {'Prefix': prefix+folder+'/'}, 'Expiration': {'Days': config['retention_days']}})
    s3.put_bucket_lifecycle_configuration(Bucket=bucket, LifecycleConfiguration={'Rules': rules})
    return s3.get_bucket_lifecycle_configuration(Bucket=bucket)['Rules']


def sms_readiness(sns, phone):
    report = {}
    try:
        report['sms_sandbox'] = sns.get_sms_sandbox_account_status()['IsInSandbox']
        if report['sms_sandbox']:
            numbers = sns.list_sms_sandbox_phone_numbers()['PhoneNumbers']
            report['sms_number_verified'] = any(n['PhoneNumber'] == phone and n['Status'] == 'Verified' for n in numbers)
            if not report['sms_number_verified']:
                sns.create_sms_sandbox_phone_number(PhoneNumber=phone, LanguageCode='en-US')
                report['sms_action_required'] = 'Recipient must provide the verification code sent by AWS; sender/origination setup may also be required.'
    except ClientError as exc:
        report['sms_readiness_error'] = str(exc)
    return report


def deploy(config, account):
    region = config['region']
    client = lambda name: boto3.client(name, region_name=region)
    sns, iam, lam, scheduler, s3, cw, logs = map(client, ['sns', 'iam', 'lambda', 'scheduler', 's3', 'cloudwatch', 'logs'])
    report = {'region': region, 'account': account, 'subscriptions': {}}
    for route in ('email', 'sms'):
        arn = sns.create_topic(Name='optima-collection-alerts-'+route, Tags=[{'Key': 'Purpose', 'Value': 'collection-monitoring'}])['TopicArn']
        config[route+'_topic_arn'] = arn
        attributes = sns.get_topic_attributes(TopicArn=arn)['Attributes']
        topic_policy = json.loads(attributes['Policy'])
        topic_policy['Statement'] = [s for s in topic_policy['Statement'] if s.get('Sid') != 'OptimaWatchdogAlarms']
        topic_policy['Statement'].append({'Sid': 'OptimaWatchdogAlarms', 'Effect': 'Allow',
            'Principal': {'Service': 'cloudwatch.amazonaws.com'}, 'Action': 'sns:Publish', 'Resource': arn,
            'Condition': {'StringEquals': {'aws:SourceAccount': account},
                          'ArnLike': {'aws:SourceArn': f'arn:aws:cloudwatch:{region}:{account}:alarm:{NAME}-*'}}})
        sns.set_topic_attributes(TopicArn=arn, AttributeName='Policy', AttributeValue=json.dumps(topic_policy))
        subscribers = []
        for page in sns.get_paginator('list_subscriptions_by_topic').paginate(TopicArn=arn):
            subscribers.extend(page['Subscriptions'])
        endpoints = config.get('sms_recipients', [config['sms']]) if route == 'sms' else [config['email']]
        subscriptions = {}
        for endpoint in dict.fromkeys(endpoints):
            found = [s for s in subscribers if s['Protocol'] == route and s['Endpoint'] == endpoint]
            if not found:
                subscription = sns.subscribe(TopicArn=arn, Protocol=route, Endpoint=endpoint, ReturnSubscriptionArn=True)['SubscriptionArn']
            else:
                subscription = found[0]['SubscriptionArn']
            subscriptions[endpoint] = subscription
        report['subscriptions'][route] = subscriptions
    report['sms_readiness'] = {phone: sms_readiness(sns, phone) for phone in config.get('sms_recipients', [config['sms']])}
    for phone, readiness in report['sms_readiness'].items():
        if readiness.get('sms_readiness_error'):
            print(json.dumps({'phone': phone, 'sms_readiness_pending': readiness['sms_readiness_error']}), flush=True)
    bucket_arn = 'arn:aws:s3:::'+config['bucket']
    prefix = config['prefix'].rstrip('/')+'/'
    topics = [config['email_topic_arn'], config['sms_topic_arn']]
    log_arn = f'arn:aws:logs:{region}:{account}:log-group:/aws/lambda/{NAME}:*'
    execution = role(iam, NAME, 'lambda.amazonaws.com', [
        allow(['s3:GetObject', 's3:PutObject'], bucket_arn+'/'+prefix+'*'),
        allow('s3:DeleteObject', [bucket_arn+'/'+prefix+'alerts/*', bucket_arn+'/'+prefix+'checks/*']),
        allow('s3:ListBucket', bucket_arn, Condition={'StringLike': {'s3:prefix': [prefix+'alerts/*', prefix+'checks/*']}}),
        allow('sns:Publish', topics),
        allow('sms-voice:SendTextMessage', '*', Condition={'StringEquals': {'aws:CalledViaLast': 'sns.amazonaws.com'}}), allow(['logs:CreateLogStream', 'logs:PutLogEvents'], log_arn),
        allow('cloudwatch:DescribeAlarms', f'arn:aws:cloudwatch:{region}:{account}:alarm:optima-collection-watchdog-*'),
        allow('cloudwatch:PutMetricData', '*', Condition={'StringEquals': {'cloudwatch:namespace': 'Optima/CollectionMonitoring'}}),
    ], account)
    function_arn = f'arn:aws:lambda:{region}:{account}:function:{NAME}'
    schedule_role = role(iam, NAME+'-scheduler', 'scheduler.amazonaws.com', [allow('lambda:InvokeFunction', function_arn)], account)
    try:
        logs.create_log_group(logGroupName='/aws/lambda/'+NAME)
    except logs.exceptions.ResourceAlreadyExistsException:
        pass
    logs.put_retention_policy(logGroupName='/aws/lambda/'+NAME, retentionInDays=30)
    (ROOT/'config/collection-monitoring.json').write_text(json.dumps(config, indent=2)+'\n')
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as package:
        package.write(ROOT/'collection_alerts.py', 'collection_alerts.py')
        package.write(ROOT/'monitoring_overview.py', 'monitoring_overview.py')
        package.writestr('collection-monitoring.json', json.dumps(config))
    runtime = {'Runtime': 'python3.12', 'Role': execution, 'Handler': 'collection_alerts.handler',
               'Timeout': 120, 'MemorySize': 128, 'Description': '30-minute collection watchdog; S3-only state and 30-day alert history'}
    try:
        lam.get_function(FunctionName=NAME)
    except lam.exceptions.ResourceNotFoundException:
        for attempt in range(12):
            try:
                lam.create_function(FunctionName=NAME, Code={'ZipFile': archive.getvalue()}, **runtime)
                break
            except lam.exceptions.InvalidParameterValueException as exc:
                if 'cannot be assumed' not in str(exc) or attempt == 11:
                    raise
                time.sleep(5)
    else:
        lam.update_function_code(FunctionName=NAME, ZipFile=archive.getvalue())
        lam.get_waiter('function_updated_v2').wait(FunctionName=NAME)
        lam.update_function_configuration(FunctionName=NAME, **runtime)
    lam.get_waiter('function_active_v2').wait(FunctionName=NAME)
    lam.get_waiter('function_updated_v2').wait(FunctionName=NAME)
    lam.put_function_concurrency(FunctionName=NAME, ReservedConcurrentExecutions=1)
    lam.put_function_event_invoke_config(FunctionName=NAME, MaximumEventAgeInSeconds=900, MaximumRetryAttempts=1)
    report['lifecycle'] = retention(s3, config)
    for suffix, metric, namespace, period, threshold, comparison, missing, dimensions in [
        ('failed', 'Errors', 'AWS/Lambda', 1800, 1, 'GreaterThanOrEqualToThreshold', 'notBreaching', [{'Name': 'FunctionName', 'Value': NAME}]),
        ('missing', 'WatchdogCompleted', 'Optima/CollectionMonitoring', 3600, 1, 'LessThanThreshold', 'breaching', []),
        ('delivery', 'NotificationErrors', 'Optima/CollectionMonitoring', 1800, 1, 'GreaterThanOrEqualToThreshold', 'notBreaching', []),
    ]:
        cw.put_metric_alarm(AlarmName=NAME+'-'+suffix, AlarmDescription='Collection monitoring infrastructure requires attention',
            Namespace=namespace, MetricName=metric, Dimensions=dimensions, Period=period,
            EvaluationPeriods=1, DatapointsToAlarm=1, Statistic='Sum', Threshold=threshold,
            ComparisonOperator=comparison, TreatMissingData=missing, AlarmActions=[topics[1]] if config.get('email_digest_seconds') else topics, OKActions=[] if config.get('email_digest_seconds') else [topics[0]])
    for country in config.get('sms_countries', ['US']):
        cw.put_metric_alarm(AlarmName=NAME+'-sms-'+country.lower()+'-delivery',
            AlarmDescription='SMS carrier delivery failed; notify by email to avoid an SMS failure loop',
            Namespace='AWS/SNS', MetricName='SMSSuccessRate',
            Dimensions=[{'Name': 'SMSType', 'Value': 'Transactional'}, {'Name': 'Country', 'Value': country}],
            Period=1800, EvaluationPeriods=1, DatapointsToAlarm=1, Statistic='Average', Threshold=1,
            ComparisonOperator='LessThanThreshold', TreatMissingData='notBreaching',
            AlarmActions=[] if config.get('email_digest_seconds') else [config['email_topic_arn']], OKActions=[] if config.get('email_digest_seconds') else [config['email_topic_arn']])
    # Stop the temporary local state writer before enabling the independent writer.
    import subprocess
    subprocess.run(['sudo', '-n', 'rm', '-f', '/etc/systemd/system/optima-collection-health.service.d/local-recorder.conf'], check=True)
    subprocess.run(['sudo', '-n', 'systemctl', 'daemon-reload'], check=True)
    while subprocess.check_output(['systemctl', 'show', '--property=ActiveState', '--value', 'optima-collection-health.service'], text=True).strip() in {'active', 'activating', 'deactivating'}:
        time.sleep(2)
    invocation = lam.invoke(FunctionName=NAME, InvocationType='RequestResponse', Payload=b'{}')
    report['verification'] = json.loads(invocation['Payload'].read())
    if invocation.get('FunctionError'):
        raise RuntimeError('Watchdog live verification failed: '+json.dumps(report['verification']))
    schedule_args = {'Name': SCHEDULE, 'GroupName': 'default', 'ScheduleExpression': config['schedule'],
                     'ScheduleExpressionTimezone': 'UTC', 'FlexibleTimeWindow': {'Mode': 'OFF'}, 'State': 'ENABLED',
                     'Target': {'Arn': function_arn, 'RoleArn': schedule_role,
                                'RetryPolicy': {'MaximumEventAgeInSeconds': 900, 'MaximumRetryAttempts': 1}, 'Input': '{}'}}
    try:
        scheduler.get_schedule(Name=SCHEDULE, GroupName='default')
    except scheduler.exceptions.ResourceNotFoundException:
        scheduler.create_schedule(**schedule_args)
    else:
        scheduler.update_schedule(**schedule_args)
    report['schedule'] = scheduler.get_schedule(Name=SCHEDULE, GroupName='default')['ScheduleExpression']
    report['function_arn'] = function_arn
    path = ROOT/'reports/collection-monitoring-deployment.json'
    path.write_text(json.dumps(report, indent=2, default=str)+'\n')
    print(json.dumps(report, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--permissions', action='store_true')
    parser.add_argument('--retention-only', action='store_true')
    args = parser.parse_args()
    config = json.loads((ROOT/'config/collection-monitoring.json').read_text())
    if args.retention_only:
        print(json.dumps(retention(boto3.client('s3', region_name=config['region']), config), indent=2))
        return
    account = '059416028963' if args.permissions else boto3.client('sts').get_caller_identity()['Account']
    if args.permissions:
        path = ROOT/'config/collection-monitoring-permissions.json'
        path.write_text(json.dumps(required_permissions(config, account), indent=2)+'\n')
        print(path)
    else:
        deploy(config, account)


if __name__ == '__main__':
    main()
