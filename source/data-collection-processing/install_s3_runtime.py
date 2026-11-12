"""Install reversible S3-runtime routing and read-only capture service guards."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import boto3
from s3_runtime import ROOT, BASE, WORK, BUCKET, PREFIX, read_index, put_verified_json

INIT = '''[Unit]
Description=Prepare RAM workspace for S3-backed capture
Before=timers.target
[Service]
Type=oneshot
User=ec2-user
ExecStart=/usr/bin/mkdir -p /dev/shm/optima-s3/locks
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
'''
LEGACY_TIMERS = {'optima-reddit-access.timer', 'optima-s11-content-daily.timer', 'optima-search-capture.timer'}


def effective_command(unit):
    text = subprocess.check_output(['systemctl', 'cat', unit], text=True)
    command = None
    continued = ''
    for line in text.splitlines():
        line = continued + line.strip()
        if line.endswith('\\'):
            continued = line[:-1]
            continue
        continued = ''
        if line.startswith('ExecStart='):
            command = line[len('ExecStart='):]
    if not command:
        raise ValueError('No capture ExecStart for ' + unit)
    if 's3_runtime.py' in command:
        raise ValueError('Runtime already installed for ' + unit)
    # Refuse unsupported systemd expansion rather than changing command semantics.
    if '$' in command or '%' in command or command[0] in '-+!:@':
        raise ValueError('Review ExecStart expansion for ' + unit)
    return command, text


def main(apply):
    s3 = boto3.client('s3', region_name='us-east-1')
    state, etag = read_index(s3)
    if not etag:
        raise RuntimeError('Seeded S3 checkpoint required before installation')
    timers = [line.split()[0] for line in subprocess.check_output(
        ['systemctl', 'list-unit-files', 'optima*.timer', '--no-legend', '--no-pager'], text=True).splitlines()
        if line.startswith('optima-') and line.split()[0] not in LEGACY_TIMERS]
    units = sorted({subprocess.check_output(['systemctl', 'show', timer, '-p', 'Unit', '--value'], text=True).strip()
                    or timer.replace('.timer', '.service') for timer in timers})
    units.append('ec2-code-backup.service')
    commands = {unit: effective_command(unit) for unit in units}
    for unit, (command, text) in commands.items():
        if not shlex.split(command):
            raise ValueError('Empty command')
    if not apply:
        print(json.dumps({'units': units, 'timers_to_resume': timers, 'lazy_state_paths': len(state['paths']),
                          'durable_store': 's3://' + BUCKET + '/' + PREFIX, 'ram_workspace': str(BASE)}))
        return
    BASE.mkdir(mode=0o700, parents=True, exist_ok=True)
    owner = ROOT.stat()
    os.chown(BASE, owner.st_uid, owner.st_gid)
    (BASE / 'locks').mkdir(exist_ok=True)
    os.chown(BASE / 'locks', owner.st_uid, owner.st_gid)
    source = ROOT / 'runtime_source_files'
    source.mkdir(exist_ok=True)
    os.chown(source, owner.st_uid, owner.st_gid)
    directories = [p for p in ROOT.iterdir() if p.name.endswith('-build') or p.name in
                   {'reports', 'mlperf-evidence-cache', 'ted-package-cache', 'collection-output'}]
    for path in directories:
        if path.is_symlink():
            if path.readlink() != WORK / path.name:
                raise ValueError('Unexpected existing symlink: ' + str(path))
            continue
        for file in path.rglob('*'):
            if file.is_file() and file.suffix not in {'.py', '.pyc', '.sh', '.sql', '.md'}:
                raise ValueError('Unmigrated payload prevents routing install: ' + str(file))
        path.rename(source / path.name)
        path.symlink_to(WORK / path.name, target_is_directory=True)
    for rel in state['paths']:
        parts = Path(rel).parts
        if len(parts) > 1 and parts[0] != 'config':
            continue
        path = ROOT / rel
        if path.is_symlink():
            continue
        if path.exists():
            raise ValueError('Refusing to replace local operational file: ' + rel)
        path.symlink_to(WORK / rel)
    for path in ROOT.glob('*.lock'):
        if path.is_symlink():
            continue
        if path.stat().st_size:
            raise ValueError('Unexpected nonempty lock file')
        path.unlink()
        path.symlink_to(BASE / 'locks' / path.name)
    for unit, (command, original) in commands.items():
        put_verified_json(s3, PREFIX + '/installation/original-units/' + unit + '.json',
                          {'unit': unit, 'original_text': original, 'exec_start': command})
        dropin = Path('/etc/systemd/system') / (unit + '.d') / '99-s3-runtime.conf'
        dropin.parent.mkdir(parents=True, exist_ok=True)
        body = ('[Unit]\nRequires=optima-s3-runtime-init.service\nAfter=optima-s3-runtime-init.service\n'
                '[Service]\nExecStart=\nExecStart=/usr/bin/flock --exclusive --timeout 43200 --conflict-exit-code 75 /dev/shm/optima-s3/supervisor.lock ' + str(ROOT / '.venv-athena/bin/python') +
                ' -B ' + str(ROOT / 's3_runtime.py') + ' --unit ' + unit + ' -- ' + command + '\n'
                'ProtectSystem=strict\nReadOnlyPaths=/home/ec2-user /tmp /var/tmp /dev/shm\n'
                'ReadWritePaths=/dev/shm/optima-s3\nPrivateTmp=false\n'
                'Environment=PYTHONDONTWRITEBYTECODE=1\n'
                'MemoryHigh=1700000000\nMemoryMax=1900000000\nMemorySwapMax=0\n'
                'TimeoutStartSec=13h\nTimeoutStopSec=240\nKillMode=mixed\nKillSignal=SIGINT\nSuccessExitStatus=75\n')
        if unit == 'optima-collection-health.service':
            body = (ROOT / 'systemd/s3-runtime/optima-collection-health.service.d/99-s3-runtime.conf').read_text()
        dropin.write_text(body)
        checked_in = ROOT / 'systemd' / 's3-runtime' / (unit + '.d')
        checked_in.mkdir(parents=True, exist_ok=True)
        (checked_in / dropin.name).write_text(body)
    init = Path('/etc/systemd/system/optima-s3-runtime-init.service')
    init.write_text(INIT)
    (ROOT / 'systemd/optima-s3-runtime-init.service').write_text(INIT)
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'enable', '--now', 'optima-s3-runtime-init.service'], check=True)
    put_verified_json(s3, PREFIX + '/installation/manifest.json', {
        'installed_at': datetime.now(timezone.utc).isoformat(), 'units': units, 'timers': timers,
        'legacy_timers_retained_disabled': sorted(LEGACY_TIMERS), 'state_paths': len(state['paths']),
        'schedules_resumed': False, 'ram_workspace': str(BASE), 'disk_write_policy': 'read-only'})
    print(json.dumps({'status': 'installed_schedules_still_paused', 'units': len(units), 'timers': len(timers)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    main(parser.parse_args().apply)
