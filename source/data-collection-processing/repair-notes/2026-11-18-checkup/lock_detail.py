import subprocess
for unit in ['optima-m7-aux-research-publication.service','optima-m7-aux-specialist-publication.service','optima-m7-aux-cms-catalog-publication.service','optima-m7-aux-fda-reviewed-publication.service']:
 print(unit,subprocess.run(['systemctl','show',unit,'-p','ActiveState','-p','MainPID','-p','ExecMainStartTimestamp','-p','MemoryCurrent'],capture_output=True,text=True).stdout.replace('\n',' '))
 print(subprocess.run(['journalctl','-u',unit,'-n','3','--no-pager','-o','cat'],capture_output=True,text=True).stdout[-1800:])
print(subprocess.run(['ps','-eo','pid,etime,rss,args'],capture_output=True,text=True).stdout[-12000:])
