import subprocess
for unit in ('optima-grants-reviewed-capture','optima-metadata-worker','optima-reviewed-metadata-ted-notices'):
 print('UNIT',unit);print(subprocess.run(['journalctl','-u',unit,'--no-pager','-n','15'],capture_output=True,text=True).stdout[-6500:])
