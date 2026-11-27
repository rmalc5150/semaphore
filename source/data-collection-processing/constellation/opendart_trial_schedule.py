"""Control the temporary backlog worker within the EC2 trial."""

from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import re
import time

import boto3

from constellation import m7_batch, m7_lifecycle


STATE = m7_batch.STATE.parent / 'opendart-trial-instance.json'
CUTOFF = datetime(2026, 12, 31, 23, 45, tzinfo=timezone.utc).timestamp()
MARGIN = 15 * 60


def deadline(now, state, compute_state, off_hours):
    if compute_state != 'stopped' or state.get('phase') != 'sleeping':
        return None
    stopped_at = state.get('stopped_at')
    if not stopped_at:
        return None
    end = min(stopped_at + off_hours * 3600 - MARGIN, CUTOFF)
    # Leave enough time to complete a bounded repair or metadata run.
    return int(end) if stopped_at <= now < end - 10 * 60 else None


def arm(ssm, instance, until):
    information = ssm.describe_instance_information(
        Filters=[{'Key': 'InstanceIds', 'Values': [instance]}])['InstanceInformationList']
    if not information or information[0]['PingStatus'] != 'Online':
        return False
    command = (
        "test -f /opt/constellation/bootstrap-ready && "
        f"printf '%s\\n' {int(until)} >/opt/constellation/trial-window.new && "
        "mv /opt/constellation/trial-window.new /opt/constellation/trial-window && "
        "rm -f /opt/constellation/batch-paused && "
        "systemctl start --no-block optima-opendart-arm.timer"
    )
    response = ssm.send_command(InstanceIds=[instance], DocumentName='AWS-RunShellScript',
                                Parameters={'commands': [command]}, TimeoutSeconds=40)
    command_id = response['Command']['CommandId']
    for _ in range(18):
        try:
            status = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance)['Status']
        except ssm.exceptions.InvocationDoesNotExist:
            time.sleep(1)
            continue
        if status == 'Success':
            return True
        if status in ('Failed', 'Cancelled', 'TimedOut'):
            raise RuntimeError(f'OpenDART window activation failed: {command_id}')
        time.sleep(1)
    return False


def main():
    if not STATE.exists():
        return
    with STATE.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        config = json.loads(STATE.read_text())
        if config.get('closed') or config.get('lifecycle_mode') == 'always_on_historical':
            return
        instance = config['instance_id']
        if not re.fullmatch(r'i-[0-9a-f]{17}', instance) or instance == m7_lifecycle.INSTANCE:
            raise ValueError('Invalid trial instance')
        session = boto3.Session(region_name='us-east-1')
        ec2 = session.client('ec2')
        response = ec2.describe_instances(InstanceIds=[instance, m7_lifecycle.INSTANCE])
        machines = {i['InstanceId']: i for r in response['Reservations'] for i in r['Instances']}
        trial = machines[instance]
        tags = {item['Key']: item['Value'] for item in trial.get('Tags', [])}
        if trial['InstanceType'] != 't4g.small' or tags.get('Name') != 'optima-t4g-backlog-trial':
            raise ValueError('Configured instance is outside the OpenDART trial')
        now = time.time()
        current = trial['State']['Name']
        policy = m7_batch.policy()
        main_state = machines[m7_lifecycle.INSTANCE]['State']['Name']
        continuous = config.get('continuous') is True
        until = (int(CUTOFF) if now < CUTOFF else None) if continuous else deadline(
            now, m7_batch.read(), main_state, min(policy['off_hours'], 12))
        armed = config.get('armed_until', 0)
        # Once armed, leave the running worker time to finish before its deadline.
        if not continuous and now < armed <= CUTOFF and main_state == 'stopped' and m7_batch.read()['phase'] == 'sleeping':
            until = armed
        action = 'waiting'
        if until is None:
            if current in ('pending', 'running'):
                ec2.stop_instances(InstanceIds=[instance])
                action = 'stop_requested'
            elif current == 'stopped' and now >= CUTOFF:
                config['closed'] = True
                action = 'closed'
            config['armed_until'] = 0
        elif current == 'stopped':
            ec2.start_instances(InstanceIds=[instance])
            config['armed_until'] = 0
            action = 'start_requested'
        elif current == 'running' and armed != until:
            if arm(session.client('ssm'), instance, until):
                config['armed_until'] = until
                action = 'armed'
        temporary = STATE.with_suffix('.tmp')
        temporary.write_text(json.dumps(config, indent=2) + '\n')
        temporary.replace(STATE)
        print(json.dumps({'trial': current, 'primary': main_state, 'action': action, 'deadline': until}), flush=True)


if __name__ == '__main__':
    main()
