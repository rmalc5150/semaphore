"""Install bounded daily public collectors on t3; existing units remain enabled."""
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[2]
SYSTEM=Path('/etc/systemd/system')

def install(name,description,command,interval,memory='512M',extra=''):
    service='[Unit]\nDescription='+description+'\nAfter=network-online.target\n[Service]\nType=oneshot\nUser=ec2-user\nWorkingDirectory='+str(ROOT)+'\nExecStart='+command+'\nSlice=constellation-daily.slice\nEnvironment=PYTHONDONTWRITEBYTECODE=1\nEnvironment=CONSTELLATION_ROLE=controller\nEnvironment=CONSTELLATION_SHARED_HTTP_LIMITS=1\nMemoryMax='+memory+'\nMemorySwapMax=0\nCPUQuota=50%\nNice=15\nTimeoutStartSec=45min\nTimeoutStopSec=180\nKillSignal=SIGINT\n'+extra
    (SYSTEM/(name+'.service')).write_text(service)
    (SYSTEM/(name+'.timer')).write_text('[Unit]\nDescription='+description+'\n[Timer]\nOnBootSec=2min\nOnUnitInactiveSec='+interval+'\nPersistent=true\nUnit='+name+'.service\n[Install]\nWantedBy=timers.target\n')

def main():
    interpreter=str(ROOT/'.venv-athena/bin/python')
    install('constellation-public-daily','Daily public archive and document capture on t3',interpreter+' -B -m constellation.public_daily --sources 6 --limit 2','30s')
    install('constellation-public-raw-daily','Daily USGS NSF and arXiv capture on t3',interpreter+' -B -m constellation.daily_raw','2min')
    command=interpreter+' -B -m constellation.public_api_daily'
    definitions=json.loads((ROOT/'constellation/expansion/new-adapters.json').read_text())
    public=[d for d in definitions if d.get('daily_enabled',True)]
    install('constellation-public-api-daily','Independent public API daily captures on t3',command,'30s','768M')
    (SYSTEM/'constellation-daily.slice').write_text('[Unit]\nDescription=Bounded new public daily capture on t3\n[Slice]\nCPUQuota=100%\nMemoryHigh=768M\nMemoryMax=1G\nMemorySwapMax=0\n')
    # Register the same source definitions for ordinary daily publication.
    path=ROOT/'config/specialist-inputs.json';plan=json.loads(path.read_text());historical=json.loads((ROOT/'config/constellation-specialist-historical.json').read_text())
    names={d['source'] for d in public};plan['sources']=[s for s in plan['sources'] if s['source'] not in names]+[{**s,'execution_lane':'independent_public_daily'} for s in historical['sources'] if s['source'] in names]
    path.write_text(json.dumps(plan,indent=2)+'\n')
    subprocess.run(['systemctl','daemon-reload'],check=True)
    units=['constellation-public-daily.timer','constellation-public-raw-daily.timer','constellation-public-api-daily.timer']
    subprocess.run(['systemctl','enable','--now',*units],check=True)
    # --no-block permits normal systemd scheduling and keeps the controller responsive.
    subprocess.run(['systemctl','start','--no-block',*[u.replace('.timer','.service') for u in units]],check=True)
    print(json.dumps({'enabled_daily_timers':units,'native_public_api_sources':[d['source'] for d in public]}))

if __name__=='__main__':main()
