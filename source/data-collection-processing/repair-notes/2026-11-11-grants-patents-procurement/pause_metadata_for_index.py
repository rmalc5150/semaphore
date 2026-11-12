import json,subprocess
from pathlib import Path
units=['optima-metadata-worker.timer','optima-reviewed-metadata-continuation.timer'];prior={u:subprocess.run(['systemctl','is-active',u],capture_output=True,text=True).stdout.strip()for u in units};p=Path('/opt/constellation/tmp/grants-metadata-index-pause.json');p.write_text(json.dumps(prior));subprocess.run(['systemctl','stop',*units],check=True)
active=subprocess.run(['systemctl','list-units','--type=service','--state=running,activating','--plain','--no-legend','optima-reviewed-metadata-*'],capture_output=True,text=True).stdout
services=['optima-metadata-worker.service','optima-reviewed-metadata-continuation.service']+[line.split()[0]for line in active.splitlines()if line.split()[0].startswith('optima-reviewed-metadata-')]
subprocess.run(['systemctl','stop',*services],check=False);print(json.dumps({'paused_timers':prior,'stopped_metadata_steps':services}))
