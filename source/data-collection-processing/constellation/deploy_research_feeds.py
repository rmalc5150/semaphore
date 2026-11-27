"""Stage, validate and activate only the two research-feed service templates."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shlex
import time
import uuid

from constellation.control import Control
from constellation.research_feeds import Evidence, FIELDS, KAKEN, OPENALEX
from constellation.worker import put_verified

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = 'constellation/research_feeds.py'
LIFECYCLE_FILE = 'constellation/m7_batch.py'
SOURCES = (OPENALEX, KAKEN)


def mirror_kaken(session):
    """Copy one field through an atomic AWSCURRENT move for the worker secret."""
    client = session.client('secretsmanager')
    source = json.loads(client.get_secret_value(SecretId='newKeys')['SecretString'])
    identifier = source[FIELDS[KAKEN]]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError('KAKEN field is empty')
    secret_id = 'dataSourceAPIkeys'
    previous = client.get_secret_value(SecretId=secret_id)
    payload = json.loads(previous['SecretString'])
    if payload.get(FIELDS[KAKEN]) == identifier:
        return 'already current'
    payload[FIELDS[KAKEN]] = identifier
    stage = 'constellation-kaken-' + uuid.uuid4().hex
    staged = client.put_secret_value(SecretId=secret_id, SecretString=json.dumps(payload), VersionStages=[stage])
    client.update_secret_version_stage(
        SecretId=secret_id, VersionStage='AWSCURRENT',
        RemoveFromVersionId=previous['VersionId'], MoveToVersionId=staged['VersionId'],
    )
    client.update_secret_version_stage(SecretId=secret_id, VersionStage=stage, RemoveFromVersionId=staged['VersionId'])
    return 'field copied'


def stage(control, files):
    objects = {}
    for file in files:
        body = (ROOT / file).read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        key = f"{control.config['prefix']}/deployments/research-feeds/{digest}/{Path(file).name}"
        objects[file] = put_verified(control, key, body, 'application/octet-stream')
    return objects


def units(label):
    stem = f'constellation-research-{label}'
    return [f'{stem}@{source}.timer' for source in SOURCES]


def install_commands(label, objects):
    if label == 'daily':
        root = '/home/ec2-user/data-collection-processing'
        dropin_source, budget = OPENALEX, 400
    else:
        root = '/opt/constellation/source'
        dropin_source, budget = KAKEN, 60
    stem = f'constellation-research-{label}'
    destination = {
        SOURCE_FILE: f'{root}/{SOURCE_FILE}',
        f'systemd/{stem}@.service': f'/etc/systemd/system/{stem}@.service',
        f'systemd/{stem}@.timer': f'/etc/systemd/system/{stem}@.timer',
    }
    if label == 'daily':
        destination[LIFECYCLE_FILE] = f'{root}/{LIFECYCLE_FILE}'
    dropin = f'/etc/systemd/system/{stem}@{dropin_source}.service.d'
    script = [
        'set -euo pipefail',
        'work=$(mktemp -d /tmp/constellation-research-feeds.XXXXXX)',
        'trap \'rm -rf "$work"\' EXIT',
    ]
    for name, target in destination.items():
        remote = objects[name]
        temporary = '"$work"/' + shlex.quote(Path(name).name)
        script.extend([
            f'aws s3 cp {shlex.quote(remote["uri"])} {temporary} --only-show-errors --region us-east-1',
            f'printf "%s  %s\\n" {remote["sha256"]} {temporary} | sha256sum -c -',
        ])
    for name, target in destination.items():
        temporary = '"$work"/' + shlex.quote(Path(name).name)
        user = '-o ec2-user -g ec2-user' if name.startswith('constellation/') else '-o root -g root'
        script.extend([
            f'install -m 0644 {user} {temporary} {shlex.quote(target + ".new")}',
            f'mv -f {shlex.quote(target + ".new")} {shlex.quote(target)}',
        ])
    script.extend([
        f'install -d -m 0755 {shlex.quote(dropin)}',
        f'printf "[Service]\\nEnvironment=RESEARCH_FEED_BUDGET={budget}\\n" > {shlex.quote(dropin + "/budget.conf")}',
        'systemctl daemon-reload',
        'systemd-analyze verify ' + ' '.join(shlex.quote(path) for name, path in destination.items() if name.startswith('systemd/')),
    ])
    return script


def execute(ssm, instance, commands, timeout):
    result = ssm.send_command(InstanceIds=[instance], DocumentName='AWS-RunShellScript',
                              Parameters={'commands': commands}, TimeoutSeconds=timeout)
    identifier = result['Command']['CommandId']
    print(f'{instance} SSM command {identifier}', flush=True)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            status = ssm.get_command_invocation(CommandId=identifier, InstanceId=instance)
        except ssm.exceptions.InvocationDoesNotExist:
            time.sleep(2)
            continue
        if status['Status'] in {'Pending', 'InProgress', 'Delayed', 'Cancelling'}:
            time.sleep(2)
            continue
        print(status['StandardOutputContent'], flush=True)
        if status['Status'] != 'Success':
            print(status['StandardErrorContent'], flush=True)
            raise RuntimeError(f'{instance} SSM status {status["Status"]}')
        return
    raise TimeoutError(f'SSM command {identifier} is still running')


def canary_commands(label):
    if label == 'daily':
        root, python = '/home/ec2-user/data-collection-processing', '.venv-athena/bin/python'
        role, mode = 'controller', 'daily'
    else:
        root, python = '/opt/constellation/source', '/opt/constellation/.venv/bin/python'
        role, mode = 'worker', 'historical'
    base = f'sudo -u ec2-user env CONSTELLATION_ROLE={role} {python} -B -m constellation.research_feeds'
    return ['set -euo pipefail', f'cd {root}'] + [
        f'{base} {source} {mode} --canary' for source in SOURCES
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=('stage', 'canary', 'enable'))
    args = parser.parse_args()
    control = Control()
    hosts = {'daily': control.config['controller_instance_id'], 'history': control.config['worker_instance_id']}
    ssm = control.session.client('ssm')
    if args.step == 'stage':
        print('KAKEN worker secret:', mirror_kaken(control.session), flush=True)
        files = [SOURCE_FILE, LIFECYCLE_FILE] + [
            f'systemd/constellation-research-{label}@.{suffix}' for label in hosts for suffix in ('service', 'timer')
        ]
        objects = stage(control, files)
        commands = {label: install_commands(label, objects) for label in hosts}
    elif args.step == 'canary':
        commands = {label: canary_commands(label) for label in hosts}
    else:
        commands = {label: ['set -euo pipefail',
                            'systemctl enable --now ' + ' '.join(units(label)),
                            'systemctl is-active ' + ' '.join(units(label))] for label in hosts}
    with ThreadPoolExecutor(max_workers=2) as pool:
        calls = [pool.submit(execute, ssm, host, commands[label], 120) for label, host in hosts.items()]
        for call in calls:
            call.result()
    if args.step == 'enable':
        evidence = Evidence(control)
        current, token = evidence.state('control.json')
        evidence.save('control.json', {**(current or {}), 'historical_enabled': True}, token)


if __name__ == '__main__':
    main()
