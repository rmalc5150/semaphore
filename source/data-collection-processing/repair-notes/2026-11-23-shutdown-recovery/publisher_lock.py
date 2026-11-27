import os,json,subprocess
from pathlib import Path
for line in Path('/proc/locks').read_text().splitlines():
 parts=line.split()
 if 'FLOCK'not in parts or '->'in parts:continue
 try:
  pid=parts[4];cmd=Path('/proc/'+pid+'/cmdline').read_bytes().replace(b'\0',b' ').decode()
  if 'publication'in cmd and 'base64'not in cmd:print('LOCK_HOLDER',pid,cmd[:350])
 except (FileNotFoundError,IndexError):pass
for u in ['optima-canada-noc-daily.service','optima-m7-research-publication.service','optima-m7-aux-specialist-publication.service','optima-m7-aux-metadata-publication.service']:
 print(u,subprocess.run(['systemctl','show',u,'-p','ActiveState','-p','Result','-p','ExecMainStartTimestamp','-p','MainPID'],capture_output=True,text=True).stdout.replace('\n',' '))
 print(subprocess.run(['journalctl','-u',u,'-n','2','-o','cat','--no-pager'],capture_output=True,text=True).stdout[-700:])
