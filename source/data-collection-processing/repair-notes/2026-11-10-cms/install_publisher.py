import json,subprocess
from pathlib import Path
p=Path(__file__).parent
unit='''[Unit]
Description=Bounded independent CMS coverage Athena publication
After=network-online.target
[Service]
Type=oneshot
User=ec2-user
WorkingDirectory=/home/ec2-user/data-collection-processing
ExecStart=/home/ec2-user/data-collection-processing/.venv-athena/bin/python -B cms_coverage_publication.py
Slice=optima-data.slice
MemoryMax=402653184
CPUQuota=20%
TimeoutStartSec=300
SuccessExitStatus=2
'''
timer='''[Unit]
Description=Continue CMS coverage Athena publication independently
[Timer]
OnBootSec=120
OnUnitInactiveSec=120
Persistent=true
Unit=optima-cms-coverage-publication.service
[Install]
WantedBy=timers.target
'''
for name,body in [('optima-cms-coverage-publication.service',unit),('optima-cms-coverage-publication.timer',timer)]:
 target=p/name;target.write_text(body);subprocess.run(['sudo','install','-m','0644',str(target),'/etc/systemd/system/'+name],check=True)
subprocess.run(['sudo','systemctl','daemon-reload'],check=True)
subprocess.run(['sudo','systemctl','enable','--now','optima-cms-coverage-publication.timer'],check=True)
subprocess.run(['sudo','systemctl','start','--no-block','optima-cms-coverage-publication.service'],check=True)
print('Independent bounded publisher enabled.')
