"""Install dispatch-only historical units and daily-only mixed units.

All timers must already be disabled. No schedule or collector is started.
"""
import json
from pathlib import Path
import shlex
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SYSTEM=Path('/etc/systemd/system')


def effective(unit):
    text=subprocess.check_output(['systemctl','cat',unit],text=True)
    command=''
    for line in text.splitlines():
        if line.startswith('ExecStart='):command=line[10:]
    if not command:raise ValueError('No command for '+unit)
    return text,command


def write(unit,body):
    path=SYSTEM/(unit+'.d')/'zzzzz-constellation-routing.conf'
    path.parent.mkdir(exist_ok=True,parents=True);path.write_text(body)


def main():
    enabled=subprocess.check_output(['systemctl','list-unit-files','optima*.timer','--no-legend','--no-pager'],text=True)
    if any(line.split()[1] in ('enabled','enabled-runtime') for line in enabled.splitlines()):
        raise RuntimeError('Pause legacy timers before applying migration')
    routes=json.loads((ROOT/'config/constellation-legacy-routes.json').read_text())['routes']
    saved=ROOT/'constellation/migration/controller-units-before';saved.mkdir(parents=True,exist_ok=True)
    changed=[]
    for row in routes:
        if row['route_kind']=='migration_probe':continue
        unit=row['original_unit']
        text,command=effective(unit)
        backup=saved/(unit+'.txt')
        if not backup.exists():backup.write_text(text)
        if row['route_kind']=='historical_only':
            new=shlex.join([str(ROOT/'.venv-athena/bin/python'),'-B','-m','constellation.legacy_dispatch','--unit',row['unit']])
        else:
            # Retain the existing S3 runtime and lock/memory guards. Only replace
            # the final payload's lane selector.
            parts=shlex.split(command)
            script=row['argv'][0]
            index=next(i for i,p in enumerate(parts) if Path(p).name==script)
            parts=parts[:index+1]+row['controller_daily_arguments']
            new=shlex.join(parts)
        write(unit,'[Service]\nExecStart=\nExecStart='+new+'\nSuccessExitStatus=2\nEnvironment=CONSTELLATION_SHARED_HTTP_LIMITS=1\nEnvironment=CONSTELLATION_ROLE=controller\n')
        changed.append({'unit':unit,'route':row['route_kind'],'exec_start':new})
    # All remaining original clients use the shared pacing hook when resumed.
    # This changes neither their payload nor their enabled state.
    for line in subprocess.check_output(['systemctl','list-unit-files','optima*.service','--no-legend','--no-pager'],text=True).splitlines():
        unit=line.split()[0]
        if any(r['unit']==unit for r in changed):continue
        directory=SYSTEM/(unit+'.d');directory.mkdir(parents=True,exist_ok=True)
        (directory/'zzzz-constellation-shared-http.conf').write_text('[Service]\nEnvironment=CONSTELLATION_SHARED_HTTP_LIMITS=1\nEnvironment=CONSTELLATION_ROLE=controller\n')
    (SYSTEM/'optima-historical-dispatch.service').write_text('[Unit]\nDescription=Dispatch split historical lanes to c7i\nAfter=network-online.target\n[Service]\nType=oneshot\nUser=ec2-user\nWorkingDirectory='+str(ROOT)+'\nExecStart='+str(ROOT/'.venv-athena/bin/python')+' -B -m constellation.legacy_dispatch --mixed-only\nSuccessExitStatus=2\nEnvironment=PYTHONDONTWRITEBYTECODE=1\n')
    (SYSTEM/'optima-historical-dispatch.timer').write_text('[Unit]\nDescription=Controller schedule for split historical lanes\n[Timer]\nOnCalendar=*-*-* *:12:00 UTC\nPersistent=true\nUnit=optima-historical-dispatch.service\n[Install]\nWantedBy=timers.target\n')
    subprocess.run(['systemctl','daemon-reload'],check=True)
    report={'historical_only_dispatchers':sum(r['route']=='historical_only' for r in changed),
        'mixed_daily_only_units':sum(r['route']=='split_historical' for r in changed),
        'timers_enabled':False,'changed_units':changed}
    (ROOT/'constellation/migration/controller-routing.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='changed_units'}))


if __name__=='__main__':main()
