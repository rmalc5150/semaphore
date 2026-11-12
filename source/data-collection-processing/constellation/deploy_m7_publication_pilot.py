"""Stage the isolated m7 patent-petition publication pilot without starting it."""
import hashlib
import io
import json
from pathlib import Path
import tarfile

import boto3

from constellation.deploy_legacy import dependencies


ROOT = Path(__file__).resolve().parents[1]
BUCKET = 'data-collection-059416028963-us-east-1-an'
INSTANCE_ID = 'i-06241bd1c4e91c2fc'


def add(archive, name, body, mode=0o644):
    data = body.encode() if isinstance(body, str) else body
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = mode
    archive.addfile(info, io.BytesIO(data))


def main():
    files = dependencies(['research_publication.py'])
    bundle = Path('/tmp/optima-m7-research-publication.tar.gz')
    with tarfile.open(bundle, 'w:gz') as archive:
        for name, body in files.items():
            add(archive, 'source/' + name, body)
        for name in ('collection-storage.s3.json', 'sec-athena-pilot.json', 'regulatory-athena-pilot.json',
                     'disclosure-athena-pilot.json', 'eodhd-observations-athena.json',
                     'people-observations-athena.json', 'social-observations-athena.json',
                     'patent-office-actions-athena.json', 'patent-petition-decisions-athena.json'):
            add(archive, 'source/config/' + name, (ROOT / 'config' / name).read_bytes())
        add(archive, 'systemd/optima-m7-research-publication.service',
            (ROOT / 'constellation/optima-m7-research-publication.service').read_bytes())
    digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
    key = 'research-data/constellation-backfill/deployments/m7-research-publication-' + digest + '.tar.gz'
    boto3.client('s3', region_name='us-east-1').upload_file(str(bundle), BUCKET, key,
        ExtraArgs={'ServerSideEncryption': 'AES256'})
    command = f'''set -eu
mkdir -p /opt/constellation/research-publication/build
aws s3 cp s3://{BUCKET}/{key} /tmp/optima-m7-research-publication.tar.gz --region us-east-1 --only-show-errors
echo "{digest}  /tmp/optima-m7-research-publication.tar.gz" | sha256sum --check --status
tar -xzf /tmp/optima-m7-research-publication.tar.gz -C /opt/constellation/research-publication --no-same-owner
chown -R ec2-user:ec2-user /opt/constellation/research-publication
install -m 0644 /opt/constellation/research-publication/systemd/optima-m7-research-publication.service /etc/systemd/system/
systemctl daemon-reload
systemd-analyze verify /etc/systemd/system/optima-m7-patent-petition-publication.service
systemctl disable optima-m7-research-publication.timer 2>/dev/null || true
echo staged
'''
    response = boto3.client('ssm', region_name='us-east-1').send_command(
        InstanceIds=[INSTANCE_ID], DocumentName='AWS-RunShellScript',
        Parameters={'commands': [command]}, TimeoutSeconds=300)
    print(json.dumps({'bundle_sha256': digest, 'bundle_key': key,
                      'command_id': response['Command']['CommandId']}, indent=2))


if __name__ == '__main__':
    main()
