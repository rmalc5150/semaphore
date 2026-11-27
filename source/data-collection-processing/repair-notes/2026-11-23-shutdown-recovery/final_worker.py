import subprocess,json
for u in ['optima-canada-noc-daily.service','optima-m7-capture-assignments-reviewed-historical.service','optima-metadata-worker.service','optima-metadata-streaming.timer']:
 print(u,subprocess.run(['systemctl','show',u,'-p','ActiveState','-p','Result','-p','ExecMainStatus'],capture_output=True,text=True).stdout.replace('\n',' '))
 if u=='optima-canada-noc-daily.service':print(subprocess.run(['journalctl','-u',u,'-n','5','-o','cat','--no-pager'],capture_output=True,text=True).stdout[-2800:])
print('FAILED',subprocess.run(['systemctl','--failed','--no-pager'],capture_output=True,text=True).stdout)
