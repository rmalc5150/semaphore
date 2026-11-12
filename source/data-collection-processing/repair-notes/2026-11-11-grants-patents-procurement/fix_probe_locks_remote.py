import os,pwd,re,subprocess,json
from pathlib import Path
user=pwd.getpwnam('ec2-user');fixed=[]
for file in Path('/opt/constellation/tmp').glob('grants-scope-*.lock'):
 if re.fullmatch(r'grants-scope-[a-f0-9]{64}\.lock',file.name)and file.is_file()and not file.is_symlink()and file.stat().st_uid==0:
  os.chown(file,user.pw_uid,user.pw_gid);os.chmod(file,0o644);fixed.append(file.name)
print(json.dumps({'lock_ownership_fixed':fixed}))
subprocess.run(['systemctl','reset-failed','optima-grants-reviewed-capture.service'],check=False);subprocess.run(['systemctl','start','--no-block','optima-grants-reviewed-capture.service'],check=True)
