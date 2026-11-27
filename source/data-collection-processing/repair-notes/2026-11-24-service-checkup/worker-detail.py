import subprocess
print(subprocess.run(['systemctl','list-units','--all','--no-pager','*metadata*'],capture_output=True,text=True).stdout)
print(subprocess.run(['journalctl','-u','optima-canada-noc-daily.service','-n','6','--no-pager'],capture_output=True,text=True).stdout)
