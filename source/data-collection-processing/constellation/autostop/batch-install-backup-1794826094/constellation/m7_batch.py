"""Controller-owned catch-up followed by durable M7 batch sessions.

All callers hold m7-lifecycle.lock. Requests coalesce by unit and survive EC2
stops. Failed validation jobs retain their repair state and are never accepted.
"""
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'constellation/autostop/m7-batch.json'
POLICY = ROOT / 'config/m7-batch-policy.json'

# Start with the small enabled-source table, then use the covering
# (source_key, state) index for each source.  The prior jobs-first join could
# scan the entire historical engine_jobs table and exceed the controller's
# deliberately short statement timeout while a large catch-up was active.
METADATA_PENDING_COUNT = """
SELECT COUNT(*) n
FROM engine_sources s
STRAIGHT_JOIN engine_jobs j FORCE INDEX (source_jobs)
  ON j.source_key=s.source_key AND j.state IN ('queued','retry','running')
WHERE s.state='enabled'
"""


def read():
    if not STATE.exists():
        return {'phase': 'catchup', 'requests': {}}
    return json.loads(STATE.read_text())


def save(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE.with_suffix('.updated')
    temporary.write_text(json.dumps(state, sort_keys=True, indent=2) + '\n')
    temporary.replace(STATE)


def policy():
    return json.loads(POLICY.read_text())


def enqueue(unit):
    state = read()
    state.setdefault('requests', {}).setdefault(unit, time.time())
    save(state)
    return state


def metrics():
    from metadata_engine.runtime_db import Database
    from constellation.control import Control
    db = Database(json.loads((ROOT / 'config/metadata-engine.json').read_text()))
    with db.tx() as c:
        c.execute(METADATA_PENDING_COUNT)
        metadata = int(c.fetchone()['n'])
        publication = None  # Deferred until labelling drains; no full-table count.
        if metadata == 0:
            c.execute("SELECT 1 FROM engine_sources s STRAIGHT_JOIN engine_jobs j FORCE INDEX (source_jobs) ON j.source_key=s.source_key AND j.state='accepted' LEFT JOIN publication_releases r ON r.release_id=UNHEX(SUBSTRING(j.job_id,1,32)) WHERE s.state='enabled' AND j.output_rows>0 AND (r.release_id IS NULL OR r.status<>'published') LIMIT 1")
            publication = bool(c.fetchone())
    control = Control()
    with control.db() as c:
        # Exhausted attempts and blocked evidence are repair work, not runnable
        # capture. The running lease check keeps in-flight work accounted for.
        c.execute("SELECT COUNT(*) n FROM backfill_jobs WHERE source_key<>'__lease_check__' AND ((status IN ('pending','retryable_failed') AND attempts<3) OR (status='running' AND lease_until>=UNIX_TIMESTAMP()))")
        historical = int(c.fetchone()['n'])
    return {'metadata': metadata, 'historical': historical, 'publication': publication}


def wake_reason(state, counts, now, settings):
    if state['phase'] == 'catchup':
        return 'initial_backlog'
    if state['phase'] == 'draining':
        return None
    if state['phase'] == 'running':
        return 'active_batch'
    requests = state.get('requests', {})
    if not requests and not any(counts.values()):
        return None
    off = now - state.get('stopped_at', now)
    if counts['metadata'] >= settings['overflow_jobs']:
        return 'overflow_backlog'
    if off >= settings['off_hours'] * 3600 and counts['metadata'] >= settings['batch_jobs']:
        return 'batch_ready'
    if off >= settings['max_off_hours'] * 3600:
        return 'daily_work_due'
    return None


def should_drain(state, counts, now, settings):
    if state['phase'] == 'draining':
        return True
    if state['phase'] == 'catchup':
        return not any(counts.values())
    if state['phase'] == 'running':
        return (now - state['started_at'] >= settings['session_hours'] * 3600
                or not any(counts.values()) and not state.get('requests'))
    return False


# The marker fences new service starts. Existing bounded payloads finish their
# own commits. Long-lived executors receive their normal systemd stop signal.
REMOTE_CONTROL = r'''
import json, subprocess
from pathlib import Path
marker=Path('/opt/constellation/batch-paused')
if ACTION == 'resume':
    was_paused=marker.exists()
    marker.unlink(missing_ok=True)
    listing=subprocess.check_output(['systemctl','list-unit-files','--plain','--no-legend','constellation-backfill@*.service','constellation-legacy-worker@*.service','constellation-public-worker@*.service'],text=True)
    workers=[line.split()[0] for line in listing.splitlines() if line.strip() and line.split()[1]=='enabled']
    if workers: subprocess.run(['systemctl','start','--no-block',*workers],check=True)
    if was_paused:
        # Calendar timers can fire during boot while their services are gated.
        # Replay their targets once after unpausing so a missed daily trigger
        # does not have to wait until tomorrow. Collection checkpoints dedupe.
        listing=subprocess.check_output(['systemctl','list-units','--state=active','--plain','--no-legend','optima-*.timer'],text=True)
        targets=[]
        for line in listing.splitlines():
            unit=subprocess.check_output(['systemctl','show',line.split()[0],'-p','Unit','--value'],text=True).strip()
            if unit: targets.append(unit)
        if targets: subprocess.run(['systemctl','start','--no-block',*sorted(set(targets))],check=True)
    print(json.dumps({'resumed': True}))
else:
    marker.touch()
    listing=subprocess.check_output(['systemctl','list-units','--state=active,activating,deactivating','--plain','--no-legend','constellation-backfill@*.service','constellation-legacy-worker@*.service','constellation-public-worker@*.service'],text=True)
    workers=[line.split()[0] for line in listing.splitlines() if line.strip()]
    if workers: subprocess.run(['systemctl','stop','--no-block',*workers],check=True)
    listing=subprocess.check_output(['systemctl','list-units','--state=active,activating,deactivating','--plain','--no-legend','optima-*.service','constellation-backfill@*.service','constellation-legacy-worker@*.service','constellation-public-worker@*.service'],text=True)
    active=[]
    for line in listing.splitlines():
        unit=line.split()[0]
        props=dict(s.split('=',1) for s in subprocess.check_output(['systemctl','show',unit,'-p','MainPID','-p','ControlPID','-p','ActiveState'],text=True).splitlines())
        if props.get('ActiveState') in ('activating','deactivating') or int(props.get('MainPID','0')) or int(props.get('ControlPID','0')):
            active.append(unit)
    pending=[]
    for base in (Path('/dev/shm/constellation-legacy'),Path('/dev/shm/optima-s3')):
        if base.exists(): pending.extend(str(p) for p in base.rglob('pending.json'))
    print(json.dumps({'safe_to_stop':not active and not pending,'active':active,'pending_checkpoints':pending}))
'''


def remote_control(action):
    import base64
    import shlex
    from constellation import m7_lifecycle as lifecycle
    session = lifecycle.online()
    code = REMOTE_CONTROL.replace('ACTION', repr(action))
    command = '/opt/constellation/legacy-venv/bin/python -c ' + shlex.quote(
        'import base64;exec(base64.b64decode(' + repr(base64.b64encode(code.encode()).decode()) + '))')
    identity = session.send_command(InstanceIds=[lifecycle.INSTANCE], DocumentName='AWS-RunShellScript',
        Parameters={'commands': [command], 'executionTimeout': ['90']}, TimeoutSeconds=100)['Command']['CommandId']
    for _ in range(50):
        try:
            result = session.get_command_invocation(CommandId=identity, InstanceId=lifecycle.INSTANCE)
        except session.exceptions.InvocationDoesNotExist:
            time.sleep(1)
            continue
        if result['Status'] == 'Success':
            return json.loads(result['StandardOutputContent'])
        if result['Status'] in ('Failed', 'Cancelled', 'TimedOut'):
            raise RuntimeError('M7 batch control failed: ' + identity)
        time.sleep(1)
    raise RuntimeError('M7 batch control pending: ' + identity)


def dispatch_allowed(unit):
    state = enqueue(unit)
    if state['phase'] == 'catchup':
        return True
    # The controller's five-minute lifecycle timer is the sole batch wake path.
    return state['phase'] == 'running'


def acknowledged(unit):
    state = read()
    state.get('requests', {}).pop(unit, None)
    save(state)


def tick():
    import boto3
    from constellation import m7_lifecycle as lifecycle
    state = read()
    if lifecycle.deployment_hold_active():
        return {'phase': state['phase'], 'reason': 'deployment_hold'}
    settings = policy()
    counts = metrics()
    now = time.time()
    ec2 = boto3.client('ec2', region_name='us-east-1')
    instance_state = ec2.describe_instances(InstanceIds=[lifecycle.INSTANCE])['Reservations'][0]['Instances'][0]['State']['Name']
    if instance_state in ('stopping', 'pending'):
        return {'phase': state['phase'], 'instance_state': instance_state}
    if state['phase'] == 'draining' and instance_state == 'stopped':
        state.update(phase='sleeping', stopped_at=now)
        save(state)
    if should_drain(state, counts, now, settings):
        if instance_state == 'stopped':
            state.update(phase='sleeping', stopped_at=now)
            save(state)
        else:
            state.update(phase='draining', last_counts=counts)
            save(state)
            proof = remote_control('drain')
            state['drain_proof'] = proof
            if proof['safe_to_stop']:
                # Persist a recoverable intent before EC2 stop. New dispatches
                # queue throughout draining and sleeping under the same lock.
                ec2.stop_instances(InstanceIds=[lifecycle.INSTANCE])
                state.update(phase='sleeping', stopped_at=now)
            save(state)
            return {'phase': state['phase'], 'counts': counts, 'drain_proof': proof}
    reason = wake_reason(state, counts, now, settings)
    if reason:
        lifecycle.start()
        if state['phase'] == 'sleeping':
            state.update(phase='running', started_at=now, wake_reason=reason)
            save(state)
        if state['phase'] == 'running':
            remote_control('resume')
        # Reissue deferred, coalesced unit requests; successful dispatch acks
        # each request. Failure retains the rest for the next tick.
        for unit in list(read().get('requests', {})):
            lifecycle.dispatch(unit)
    state = read()
    state.update(last_checked_at=now, last_counts=counts)
    save(state)
    return {'phase': state['phase'], 'counts': counts, 'wake_reason': reason}
