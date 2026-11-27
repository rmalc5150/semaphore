import subprocess,json
units=['optima-m7-committed-athena.service','optima-m7-specialist-publication.service','optima-m7-capture-patents-prosecution.service','optima-m7-patents-prosecution-publication.service']
print(subprocess.run(['systemctl','--failed','--no-pager'],capture_output=True,text=True).stdout)
print(subprocess.run(['systemctl','list-units','--type=service','--state=running','--no-pager'],capture_output=True,text=True).stdout)
for unit in units:
 print(subprocess.run(['systemctl','show',unit,'-p','Id','-p','ActiveState','-p','ExecMainStartTimestamp','-p','Result','-p','ExecMainStatus'],capture_output=True,text=True).stdout)
