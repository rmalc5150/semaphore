import subprocess
u='optima-m7-aux-cms-coverage-publication.service'
print(subprocess.run(['systemctl','show',u,'-p','ActiveState','-p','ExecStart','-p','MemoryCurrent','-p','CPUUsageNSec','-p','ActiveEnterTimestamp','-p','InactiveExitTimestamp'],capture_output=True,text=True).stdout)
print(subprocess.run(['journalctl','-u',u,'-n','5','--no-pager','-o','cat'],capture_output=True,text=True).stdout[-3500:])
print(subprocess.run(['ps','-eo','pid,ppid,etime,pcpu,rss,wchan:25,args'],capture_output=True,text=True).stdout[-14000:])
