"""Package only isolated worker code, then stage it through SSM.

Does not copy legacy scripts, local state, static credentials, or timers.
"""
import hashlib
import io
import json
from pathlib import Path
import shlex
import tarfile

import boto3

ROOT = Path(__file__).resolve().parents[1]


def main():
    config = json.loads((ROOT / 'config/constellation-infrastructure.json').read_text())
    files = [ROOT / 'constellation' / name for name in (
        '__init__.py', 'control.py', 'sources.py', 'worker.py', 'requirements.txt', 'constellation-backfill@.service','constellation-workers.slice')]
    files += [ROOT / 'config/rds-us-east-1-ca-bundle.pem']
    bundle = ROOT / 'constellation/worker-deploy.tar.gz'
    with tarfile.open(bundle, 'w:gz') as archive:
        for path in sorted(files):
            archive.add(path, arcname=path.relative_to(ROOT), recursive=False)
        worker_config = {k: v for k, v in config.items() if k != 'controller_secret_arn'}
        body = json.dumps(worker_config, indent=2).encode()
        info = tarfile.TarInfo('config/constellation-infrastructure.json')
        info.size = len(body)
        info.mode = 0o600
        archive.addfile(info, io.BytesIO(body))
    digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
    key = config['prefix'] + '/deployments/' + digest + '.tar.gz'
    session = boto3.Session(region_name=config['region'])
    s3 = session.client('s3')
    s3.upload_file(str(bundle), config['bucket'], key, ExtraArgs={'ServerSideEncryption': 'AES256'})
    remote = s3.get_object(Bucket=config['bucket'], Key=key)
    try:
        if hashlib.sha256(remote['Body'].read()).hexdigest() != digest:
            raise RuntimeError('Deployment bundle readback mismatch')
    finally:
        remote['Body'].close()
    uri = 's3://' + config['bucket'] + '/' + key
    script = (ROOT / 'constellation/bootstrap-worker.sh').read_text()
    command = 'bash -s -- ' + ' '.join(shlex.quote(x) for x in (config['worker_scratch_volume_id'], uri, digest)) + " <<'CONSTELLATION_BOOTSTRAP'\n" + script + '\nCONSTELLATION_BOOTSTRAP'
    response = session.client('ssm').send_command(InstanceIds=[config['worker_instance_id']],
        DocumentName='AWS-RunShellScript', Parameters={'commands': [command]}, TimeoutSeconds=900)
    receipt = {'command_id': response['Command']['CommandId'], 'bundle_sha256': digest,
        'bundle_uri': uri, 'worker_instance_id': config['worker_instance_id'], 'collection_enabled': False}
    (ROOT / 'constellation/deployment-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
