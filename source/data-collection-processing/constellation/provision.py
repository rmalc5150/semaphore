"""Provision isolated RDS operational tables, encrypted scratch and worker IAM.

No DynamoDB or SQS. No change to legacy tables, schedules or controller IAM.
"""
import argparse
from contextlib import closing
import json
from pathlib import Path
import secrets
import time

import boto3
from botocore.exceptions import ClientError
import pymysql

ROOT = Path(__file__).resolve().parents[1]
REGION = 'us-east-1'
WORKER = 'i-06241bd1c4e91c2fc'
CONTROLLER = 'i-070bab0b09f794629'
BUCKET = 'data-collection-059416028963-us-east-1-an'
PREFIX = 'research-data/constellation-backfill'
NAME = 'constellation-backfill'
MASTER = 'arn:aws:secretsmanager:us-east-1:059416028963:secret:rds!db-85014375-d9c9-4480-8626-aae2310bface-pyk3Ae'


def credentials(sm, role):
    name = 'constellation/backfill/' + role
    try:
        response = sm.get_secret_value(SecretId=name)
        return response['ARN'], json.loads(response['SecretString'])
    except sm.exceptions.ResourceNotFoundException:
        value = {'username': 'constellation_' + role, 'password': secrets.token_urlsafe(40)}
        response = sm.create_secret(Name=name, SecretString=json.dumps(value),
            Description='Restricted Constellation RDS operations user; no raw evidence or application-table access',
            Tags=[{'Key': 'Project', 'Value': 'Constellation'}])
        return response['ARN'], value


def database(session):
    sm = session.client('secretsmanager')
    master = json.loads(sm.get_secret_value(SecretId=MASTER)['SecretString'])
    matches = [d for d in session.client('rds').describe_db_instances()['DBInstances']
        if d.get('MasterUserSecret', {}).get('SecretArn') == MASTER]
    if len(matches) != 1 or matches[0]['Engine'] != 'mysql':
        raise RuntimeError('Unexpected operational database')
    db = matches[0]
    if not db['StorageEncrypted']:
        raise RuntimeError('Expected encrypted RDS')
    host = db['Endpoint']['Address']
    config = {'db_host': host, 'database': 'constellation_operations'}
    with closing(pymysql.connect(host=host, user=master['username'], password=master['password'],
            port=3306, connect_timeout=10, read_timeout=30, write_timeout=30, autocommit=True,
            ssl_ca=str(ROOT / 'config/rds-us-east-1-ca-bundle.pem'), ssl_verify_cert=True, ssl_verify_identity=True)) as conn:
        with conn.cursor() as cur:
            for statement in (ROOT / 'constellation/schema.sql').read_text().split(';'):
                if statement.strip():
                    cur.execute(statement)
            cur.execute('INSERT IGNORE INTO constellation_operations.backfill_control VALUES(1,FALSE,%s,%s)',
                ('[]', int(time.time()) + 20 * 86400))
            for role in ('controller', 'worker'):
                arn, value = credentials(sm, role)
                config[role + '_secret_arn'] = arn
                user = value['username']
                if user != 'constellation_' + role:
                    raise RuntimeError('Unexpected managed database username')
                cur.execute('CREATE USER IF NOT EXISTS %s@%s IDENTIFIED BY %s REQUIRE SSL', (user, '%', value['password']))
                if role == 'controller':
                    for table in ('backfill_jobs', 'backfill_control', 'backfill_sources', 'backfill_coverage'):
                        cur.execute('GRANT SELECT, INSERT, UPDATE ON constellation_operations.' + table + ' TO %s@%s', (user, '%'))
                    cur.execute('GRANT SELECT, INSERT, UPDATE ON constellation_operations.backfill_quotas TO %s@%s', (user, '%'))
                else:
                    for table in ('backfill_jobs', 'backfill_control', 'backfill_quotas', 'backfill_sources', 'backfill_coverage'):
                        cur.execute('GRANT SELECT ON constellation_operations.' + table + ' TO %s@%s', (user, '%'))
                    cur.execute('GRANT UPDATE(status,attempts,worker_id,lease_token,lease_until,next_attempt_at,updated_at,result_json) ON constellation_operations.backfill_jobs TO %s@%s', (user, '%'))
                    cur.execute('GRANT INSERT, UPDATE ON constellation_operations.backfill_quotas TO %s@%s', (user, '%'))
                cur.execute('GRANT SELECT, INSERT, UPDATE ON constellation_operations.backfill_http_limits TO %s@%s', (user, '%'))
    return config


def worker_role(session, worker_secret, config):
    iam, ec2 = session.client('iam'), session.client('ec2')
    role = NAME + '-worker'
    trust = {'Version': '2012-10-17', 'Statement': [{'Effect': 'Allow', 'Principal': {'Service': 'ec2.amazonaws.com'}, 'Action': 'sts:AssumeRole'}]}
    try:
        iam.create_role(RoleName=role, AssumeRolePolicyDocument=json.dumps(trust))
    except iam.exceptions.EntityAlreadyExistsException:
        pass
    iam.attach_role_policy(RoleName=role, PolicyArn='arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore')
    policy = {'Version': '2012-10-17', 'Statement': [
        {'Effect': 'Allow', 'Action': ['secretsmanager:GetSecretValue'], 'Resource': worker_secret},
        {'Effect': 'Allow', 'Action': ['s3:GetObject', 's3:PutObject'], 'Resource': f'arn:aws:s3:::{BUCKET}/{PREFIX}/*'},
        {'Effect': 'Allow', 'Action': ['logs:CreateLogStream', 'logs:PutLogEvents'],
            'Resource': f"arn:aws:logs:{REGION}:{config['account_id']}:log-group:/constellation/backfill:*"}]}
    if config.get('legacy_runtime_enabled'):
        # Validation needs only three immutable public universe objects. Broader
        # artifact/checkpoint and credential permissions require owner review;
        # they are deliberately not applied by this provisioning path.
        keys=config.get('legacy_snapshot_read_keys',[])
        allowed={f'research-data/operations/s3-runtime/snapshots/migration-seed/config/company-universe.v0.{v}.json' for v in (2,3,5)}
        if set(keys)-allowed:
            raise RuntimeError('Unreviewed legacy snapshot access')
        if keys:
            policy['Statement'].append({'Effect':'Allow','Action':['s3:GetObject'],
                'Resource':[f'arn:aws:s3:::{BUCKET}/{key}' for key in keys]})
    (ROOT / 'constellation/worker-runtime-policy.json').write_text(json.dumps(policy, indent=2) + '\n')
    iam.put_role_policy(RoleName=role, PolicyName=NAME, PolicyDocument=json.dumps(policy))
    try:
        iam.create_instance_profile(InstanceProfileName=role)
    except iam.exceptions.EntityAlreadyExistsException:
        pass
    profile = iam.get_instance_profile(InstanceProfileName=role)['InstanceProfile']
    if not any(r['RoleName'] == role for r in profile['Roles']):
        iam.add_role_to_instance_profile(InstanceProfileName=role, RoleName=role)
    associations = ec2.describe_iam_instance_profile_associations(Filters=[{'Name': 'instance-id', 'Values': [WORKER]}])['IamInstanceProfileAssociations']
    if len(associations) != 1:
        raise RuntimeError('Expected one worker profile association')
    if associations[0]['IamInstanceProfile']['Arn'].split('/')[-1] != role:
        for attempt in range(12):
            try:
                ec2.replace_iam_instance_profile_association(AssociationId=associations[0]['AssociationId'], IamInstanceProfile={'Name': role})
                break
            except ClientError as exc:
                if attempt == 11 or exc.response['Error']['Code'] not in {'InvalidParameterValue', 'InvalidIamInstanceProfile.NotFound'}:
                    raise
                time.sleep(5)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configure-role', action='store_true')
    args = parser.parse_args()
    session = boto3.Session(region_name=REGION)
    account = session.client('sts').get_caller_identity()['Account']
    if account != '059416028963':
        raise RuntimeError('Unexpected AWS account')
    ec2 = session.client('ec2')
    worker = ec2.describe_instances(InstanceIds=[WORKER])['Reservations'][0]['Instances'][0]
    if worker['InstanceType'] != 'c7i.4xlarge' or worker['State']['Name'] != 'running':
        raise RuntimeError('Expected the existing running c7i.4xlarge')
    prior_path=ROOT/'config/constellation-infrastructure.json'
    prior=json.loads(prior_path.read_text()) if prior_path.exists() else {}
    config = {**prior,'schema_version': 1, 'region': REGION, 'account_id': account,
        'controller_instance_id': CONTROLLER, 'worker_instance_id': WORKER,
        'bucket': BUCKET, 'prefix': PREFIX, 'concurrency': 2, 'collection_enabled': False,
        'queue_backend': 'rds_mysql', 'legacy_checkpoint_access': False, **database(session)}
    tags = [{'Key': 'Project', 'Value': 'Constellation'}, {'Key': 'Purpose', 'Value': 'historical-backfill'}]
    volumes = ec2.describe_volumes(Filters=[{'Name': 'tag:Name', 'Values': [NAME + '-scratch']},
        {'Name': 'availability-zone', 'Values': [worker['Placement']['AvailabilityZone']]}])['Volumes']
    if len(volumes) > 1:
        raise RuntimeError('Ambiguous scratch volume')
    if not volumes:
        volume = ec2.create_volume(AvailabilityZone=worker['Placement']['AvailabilityZone'], Size=8,
            VolumeType='gp3', Encrypted=True, ClientToken=NAME + '-scratch-v1',
            TagSpecifications=[{'ResourceType': 'volume', 'Tags': tags + [{'Key': 'Name', 'Value': NAME + '-scratch'}]}])
        ec2.get_waiter('volume_available').wait(VolumeIds=[volume['VolumeId']])
    else:
        volume = volumes[0]
    if not volume['Encrypted']:
        raise RuntimeError('Refusing unencrypted scratch')
    attachments = volume.get('Attachments', [])
    if not attachments:
        ec2.attach_volume(VolumeId=volume['VolumeId'], InstanceId=WORKER, Device='/dev/sdf')
    elif any(a['InstanceId'] != WORKER for a in attachments):
        raise RuntimeError('Scratch attached to another instance')
    config['worker_scratch_volume_id'] = volume['VolumeId']
    ec2.create_tags(Resources=[WORKER], Tags=tags)
    config['worker_role_ready'] = False
    if args.configure_role:
        config['worker_role_ready'] = worker_role(session, config['worker_secret_arn'], config)
    (ROOT / 'config/constellation-infrastructure.json').write_text(json.dumps(config, indent=2) + '\n')
    print(json.dumps(config))


if __name__ == '__main__':
    main()
