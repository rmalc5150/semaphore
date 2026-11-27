import os,json,subprocess,fcntl
from pathlib import Path
root=Path('/opt/constellation/auxiliary-publication/source');inode=Path('/opt/constellation/auxiliary-publication/publish.lock').stat().st_ino
owner=None
for line in Path('/proc/locks').read_text().splitlines():
 f=line.split()
 if '->'not in f and len(f)>5 and f[5].endswith(':'+str(inode)):owner=int(f[4])
if not owner:print(json.dumps({'status':'no_lock_owner'}));raise SystemExit(0)
cmd=Path('/proc/'+str(owner)+'/cmdline').read_bytes().split(b'\0')
if b'specialist_publication.py'not in cmd:print(json.dumps({'status':'lock_already_advanced','owner':owner}));raise SystemExit(0)
cg=Path('/proc/'+str(owner)+'/cgroup').read_text();unit=next((part for part in cg.strip().split('/')if part.startswith('optima-m7-aux-')and part.endswith('.service')),None)
if not unit:raise RuntimeError('Unexpected publisher cgroup; no service changed')
with(root/'.specialist-publication.lock').open('a')as lock:
 try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:print(json.dumps({'status':'publication_stage_active_no_interruption','unit':unit}));raise SystemExit(0)
 # Holding preparation's own lock proves no Glue publication can begin while
 # stopping the old inventory-only scan. Each queued record is already atomic.
 before=subprocess.run(['systemctl','show',unit,'-p','ActiveState','-p','ExecMainPID'],capture_output=True,text=True).stdout
 subprocess.run(['systemctl','stop',unit],check=True,timeout=45)
print(json.dumps({'status':'bounded_bridge_installed','restarted_unit':unit,'previous_state':before}))
subprocess.run(['systemctl','start','--no-block',unit],check=True)
