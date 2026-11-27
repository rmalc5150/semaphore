import subprocess,json
for line in subprocess.run(['systemctl','list-unit-files','--no-pager'],capture_output=True,text=True).stdout.splitlines():
 if 'news-collection' in line or ('fda' in line and ('code' in line or 'reference' in line)):
  print(line)
  if line.startswith('optima-') and line.split()[0].endswith('.service') and 'news' in line:print(subprocess.run(['systemctl','start','--no-block',line.split()[0]],capture_output=True,text=True).returncode)
