import subprocess
from pathlib import Path
p=Path(__file__).parent
for mode in ('google','odp','odp-historical'):
 base='optima-patents-reviewed-'+mode
 unit='[Unit]\nDescription=Bounded patent '+mode+' capture using existing controller access\nAfter=network-online.target\n[Service]\nType=oneshot\nUser=ec2-user\nWorkingDirectory=/home/ec2-user/data-collection-processing\nExecStart=/home/ec2-user/data-collection-processing/.venv-athena/bin/python -B patent_review_continuation.py --lane '+mode+'\nSlice=optima-financial.slice\nMemoryMax=268435456\nMemorySwapMax=0\nCPUQuota=15%\nTimeoutStartSec=190\n'
 timer='[Unit]\nDescription=Continue '+base+'\n[Timer]\nOnBootSec=120\nOnUnitInactiveSec=900\nPersistent=true\nUnit='+base+'.service\n[Install]\nWantedBy=timers.target\n'
 for suffix,body in (('.service',unit),('.timer',timer)):
  file=p/(base+suffix);file.write_text(body);subprocess.run(['sudo','install','-m','0644',str(file),'/etc/systemd/system/'+file.name],check=True)
subprocess.run(['sudo','systemctl','daemon-reload'],check=True)
for mode in ('google','odp','odp-historical'):
 base='optima-patents-reviewed-'+mode
 subprocess.run(['sudo','systemctl','enable','--now',base+'.timer'],check=True);subprocess.run(['sudo','systemctl','start','--no-block',base+'.service'],check=True)
