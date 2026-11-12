import subprocess
from pathlib import Path
p=Path(__file__).parent
units={
'optima-grants-reviewed-publication.service':'''[Unit]
Description=Publish bounded reviewed grants/procurement source windows to Athena
After=network-online.target
[Service]
Type=oneshot
User=ec2-user
WorkingDirectory=/home/ec2-user/data-collection-processing
ExecStart=/home/ec2-user/data-collection-processing/.venv-athena/bin/python -B grants_review_publication.py
Slice=optima-financial.slice
MemoryMax=268435456
MemorySwapMax=0
CPUQuota=20%
TimeoutStartSec=300
'''}
for base,seconds in [('optima-grants-reviewed-publication',120)]:units[base+'.timer']='[Unit]\nDescription=Continue '+base+'\n[Timer]\nOnBootSec=120\nOnUnitInactiveSec='+str(seconds)+'\nPersistent=true\nUnit='+base+'.service\n[Install]\nWantedBy=timers.target\n'
for name,body in units.items():
 file=p/name;file.write_text(body);subprocess.run(['sudo','install','-m','0644',str(file),'/etc/systemd/system/'+name],check=True)
subprocess.run(['sudo','systemctl','daemon-reload'],check=True)
for base in ('optima-grants-reviewed-publication',):
 subprocess.run(['sudo','systemctl','enable','--now',base+'.timer'],check=True);subprocess.run(['sudo','systemctl','start','--no-block',base+'.service'],check=True)
