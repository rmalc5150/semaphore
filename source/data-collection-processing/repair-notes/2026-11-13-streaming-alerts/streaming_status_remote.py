import subprocess
print(subprocess.run(['systemctl','show','optima-metadata-streaming.service','-p','ActiveState','-p','Result','-p','MemoryPeak','-p','ExecMainStatus'],capture_output=True,text=True).stdout)
print(subprocess.run(['journalctl','-u','optima-metadata-streaming.service','--no-pager','-n','12'],capture_output=True,text=True).stdout[-9000:])
