#!/usr/bin/env python3
"""Inspect SMS routing and enable SNS delivery logs without sending messages."""
import json
from pathlib import Path

import boto3
from deploy_collection_monitoring import allow, role

ROOT = Path(__file__).resolve().parent


def main():
    config = json.loads((ROOT/'config/collection-monitoring.json').read_text())
    region = config['region']
    account = boto3.client('sts').get_caller_identity()['Account']
    sns = boto3.client('sns', region_name=region)
    report = {'origination_numbers': [], 'opted_out': {}}
    token = None
    while True:
        response = sns.list_origination_numbers(**({'NextToken': token} if token else {}))
        report['origination_numbers'].extend(response.get('PhoneNumbers', []))
        token = response.get('NextToken')
        if not token:
            break
    for phone in config.get('sms_recipients', [config['sms']]):
        report['opted_out'][phone] = sns.check_if_phone_number_is_opted_out(phoneNumber=phone)['isOptedOut']
    attributes = sns.get_sms_attributes()['attributes']
    report['previous_logging_role'] = attributes.get('DeliveryStatusIAMRole')
    logging_role = report['previous_logging_role']
    if not logging_role:
        logging_role = role(boto3.client('iam'), 'optima-collection-sms-delivery', 'sns.amazonaws.com', [
            allow(['logs:CreateLogGroup', 'logs:CreateLogStream', 'logs:PutLogEvents'],
                  f'arn:aws:logs:{region}:{account}:log-group:sns/{region}/{account}/*')], account)
    sns.set_sms_attributes(attributes={'DeliveryStatusIAMRole': logging_role, 'DeliveryStatusSuccessSamplingRate': '100'})
    report['logging_role'] = logging_role
    report['sms_attributes'] = sns.get_sms_attributes()['attributes']
    path = ROOT/'reports/collection-monitoring-sms-diagnostics.json'
    path.write_text(json.dumps(report, indent=2, default=str)+'\n')
    print(json.dumps(report, indent=2, default=str))


if __name__ == '__main__':
    main()
