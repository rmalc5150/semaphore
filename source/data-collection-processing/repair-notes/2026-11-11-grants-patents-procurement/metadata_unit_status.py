import subprocess
for unit in ('optima-metadata-worker.service','optima-metadata-worker.timer'):
 print(subprocess.run(['systemctl','show',unit,'-p','ActiveState','-p','ExecMainPID','-p','ExecMainStartTimestamp','-p','Result'],capture_output=True,text=True).stdout)
print(subprocess.run(['journalctl','-u','optima-metadata-worker.service','--no-pager','-n','3'],capture_output=True,text=True).stdout)
