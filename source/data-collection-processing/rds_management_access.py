"""Controller-only RDS management access for current schema provisioning."""
import json
from pathlib import Path
import boto3

ROOT=Path(__file__).resolve().parent
SECRET='arn:aws:secretsmanager:us-east-1:059416028963:secret:rds!db-85014375-d9c9-4480-8626-aae2310bface-pyk3Ae'
def settings():
    session=boto3.Session(region_name='us-east-1')
    matches=[d for d in session.client('rds').describe_db_instances()['DBInstances']if d.get('MasterUserSecret',{}).get('SecretArn')==SECRET]
    if len(matches)!=1:raise RuntimeError('Ambiguous managed RDS instance')
    admin=json.loads(session.client('secretsmanager').get_secret_value(SecretId=SECRET)['SecretString'])
    if admin.get('username')!='admin':raise RuntimeError('Unexpected management username')
    return session,matches[0],admin,json.loads((ROOT/'config/constellation-infrastructure.json').read_text())['bucket']
def ca_bundle():return ROOT/'config/rds-us-east-1-ca-bundle.pem'
