import json,subprocess
from pathlib import Path
p=Path('/opt/constellation/tmp/grants-metadata-index-pause.json');prior=json.loads(p.read_text())if p.exists()else{}
for unit,state in prior.items():
 if state=='active':subprocess.run(['systemctl','start',unit],check=True)
for unit in ('optima-metadata-worker.service','optima-reviewed-metadata-continuation.service'):subprocess.run(['systemctl','reset-failed',unit],check=False);subprocess.run(['systemctl','start','--no-block',unit],check=True)
print(json.dumps({'restored_timers':prior}))
