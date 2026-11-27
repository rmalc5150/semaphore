import subprocess,json
for cmd in (['df','-h','/opt/constellation/tmp'],['systemctl','show','optima-metadata-worker.service','-p','ActiveState','-p','Result'],['journalctl','-u','optima-m7-capture-patents-daily.service','--no-pager','-n','28'],['journalctl','-u','optima-m7-capture-patents-prosecution.service','--no-pager','-n','8']):print(subprocess.run(cmd,capture_output=True,text=True).stdout)
