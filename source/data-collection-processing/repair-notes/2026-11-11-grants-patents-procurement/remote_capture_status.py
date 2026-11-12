import subprocess,json
for unit in ('optima-grants-review-probes-v3','optima-grants-reviewed-capture','optima-metadata-worker'):
 print('UNIT',unit,subprocess.run(['systemctl','show',unit,'-p','ActiveState','-p','Result','-p','ExecMainStatus'],capture_output=True,text=True).stdout)
 print(subprocess.run(['journalctl','-u',unit,'--no-pager','-n','8'],capture_output=True,text=True).stdout)
