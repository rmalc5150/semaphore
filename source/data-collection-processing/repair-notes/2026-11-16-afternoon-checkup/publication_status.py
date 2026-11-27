import subprocess,json
print(subprocess.run(['lslocks','--output','PID,COMMAND,PATH'],capture_output=True,text=True).stdout[-4500:])
for unit in ['optima-m7-aux-research-publication.service','optima-m7-aux-fda-reviewed-publication.service','optima-m7-aux-specialist-publication.service']:
 print(unit,subprocess.run(['systemctl','show',unit,'-p','ActiveState','-p','ActiveEnterTimestamp','-p','MemoryCurrent'],capture_output=True,text=True).stdout.replace('\n',' '))
 print(subprocess.run(['journalctl','-u',unit,'-n','2','-o','cat','--no-pager'],capture_output=True,text=True).stdout[-1600:])
print('RUNNING',subprocess.run(['systemctl','list-units','--state=running','--no-pager','--plain'],capture_output=True,text=True).stdout[-7500:])
