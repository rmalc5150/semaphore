import json,subprocess
from pathlib import Path
p=Path(__file__).parent
unit='''[Unit]
Description=Bounded independent Crossref Athena publication
After=network-online.target
[Service]
Type=oneshot
User=ec2-user
WorkingDirectory=/home/ec2-user/data-collection-processing
ExecStart=/home/ec2-user/data-collection-processing/.venv-athena/bin/python -B crossref_resumed_publication.py
Slice=optima-data.slice
MemoryMax=402653184
CPUQuota=20%
TimeoutStartSec=300
SuccessExitStatus=2
'''
timer='''[Unit]
Description=Continue Crossref Athena publication independently
[Timer]
OnBootSec=120
OnUnitInactiveSec=120
Persistent=true
Unit=optima-crossref-publication-resumed.service
[Install]
WantedBy=timers.target
'''
for name,body in [('optima-crossref-publication-resumed.service',unit),('optima-crossref-publication-resumed.timer',timer)]:
 target=p/name;target.write_text(body);subprocess.run(['sudo','install','-m','0644',str(target),'/etc/systemd/system/'+name],check=True)
subprocess.run(['sudo','systemctl','daemon-reload'],check=True)
subprocess.run(['sudo','systemctl','enable','--now','optima-crossref-publication-resumed.timer'],check=True)
subprocess.run(['sudo','systemctl','start','--no-block','optima-crossref-publication-resumed.service'],check=True)
print('Independent bounded publisher enabled.')
