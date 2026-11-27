import os,json,subprocess
from pathlib import Path
p=Path('/opt/constellation/auxiliary-publication/publish.lock');inode=p.stat().st_ino
for line in Path('/proc/locks').read_text().splitlines():
 fields=line.split()
 if '->'in fields:continue
 if len(fields)>5 and fields[5].endswith(':'+str(inode)):
  pid=int(fields[4]);cmd=Path('/proc/'+str(pid)+'/cmdline').read_bytes().split(b'\0');print('LOCK_OWNER',pid,[x.decode(errors='replace')for x in cmd[:5]])
print(subprocess.run(['systemctl','show','optima-m7-aux-collection-daily.service','-p','ActiveState','-p','Result'],capture_output=True,text=True).stdout)
print(subprocess.run(['journalctl','-u','optima-m7-aux-collection-daily.service','-n','4','--no-pager'],capture_output=True,text=True).stdout[-1700:])
