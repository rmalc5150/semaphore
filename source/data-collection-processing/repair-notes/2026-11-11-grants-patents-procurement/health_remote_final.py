import subprocess,json,hashlib
from pathlib import Path
for unit in ('optima-grants-reviewed-capture','optima-nih-reviewed-historical','optima-reviewed-metadata-continuation','optima-metadata-worker'):
 out={'unit':unit}
 for suffix in ('.service','.timer'):
  out[suffix]=subprocess.run(['systemctl','show',unit+suffix,'-p','ActiveState','-p','Result','-p','ExecMainStatus','-p','UnitFileState'],capture_output=True,text=True).stdout.strip()
 print(json.dumps(out),flush=True)
root=Path('/opt/constellation/metadata-engine-runtime');p=root/'metadata_engine/patent_sources.py';print(json.dumps({'patent_validator_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'approved_exclusions_installed':'def reviewed_exclusion' in p.read_text(),'continuation_installed':(root/'metadata_engine/reviewed_continuation.py').exists()}))
print(subprocess.run(['journalctl','-u','optima-nih-reviewed-historical','-u','optima-reviewed-metadata-continuation','--no-pager','-n','6'],capture_output=True,text=True).stdout)
