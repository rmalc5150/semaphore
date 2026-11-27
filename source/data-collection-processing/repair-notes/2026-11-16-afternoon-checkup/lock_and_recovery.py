import os,subprocess,json
from pathlib import Path
path=Path('/opt/constellation/auxiliary-publication/publish.lock');ino=str(path.stat().st_ino)
for line in Path('/proc/locks').read_text().splitlines():
 if ':'+ino+' ' not in line:continue
 print('PUB_LOCK',line)
 parts=line.split();pid=parts[4] if parts[1]!='->'else parts[5]
 if pid.isdigit():
  p=Path('/proc')/pid
  try:print('HOLDER',pid,(p/'comm').read_text().strip(),(p/'cgroup').read_text().strip())
  except Exception:pass
for unit in ['optima-m7-capture-assignments-reviewed-historical.service','optima-m7-aux-cms-catalog-publication.service','optima-m7-aux-fda-reviewed-publication.service','optima-m7-capture-nist-robotics-daily.service','optima-m7-aux-patents-prosecution-publication.service']:
 lines=subprocess.run(['journalctl','-u',unit,'--since','2026-11-16 00:00:00','--no-pager','-o','cat'],capture_output=True,text=True).stdout.splitlines();interesting=[line for line in lines if any(s in line for s in ['signal','status=','Stopping ','Stopped ','Killed','oom'])];print('SIGNALS',unit,interesting[-6:])
print('FDA_CONTINUATION',subprocess.run(['systemctl','show','optima-fda-gap-repair-20261116.service','-p','ActiveState','-p','Result','-p','MemoryCurrent'],capture_output=True,text=True).stdout.replace('\n',' '));p=Path('/opt/constellation/tmp/checkup1116-afternoon/fda-continuation.log');lines=p.read_text().splitlines()if p.exists()else[];print('FDA_PROGRESS',len(lines),lines[-2:])
