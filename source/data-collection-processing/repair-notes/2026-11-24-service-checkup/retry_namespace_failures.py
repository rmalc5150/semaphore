import json,subprocess
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from source_pauses import unit_pause
cfg=json.loads(Path('config/collection-monitoring.json').read_text());rows=[]
for line in subprocess.check_output(['systemctl','list-units','--failed','--no-legend','--plain','--no-pager'],text=True).splitlines():
 unit=line.split()[0]
 if not unit.endswith('.service'):continue
 status=subprocess.check_output(['systemctl','show',unit,'-p','ExecMainStatus','--value'],text=True).strip()
 paused=unit_pause(unit)or cfg.get('jobs',{}).get(unit,{}).get('maintenance_pause_reason')
 if status=='226'and not paused:
  r=subprocess.run(['systemctl','start','--no-block',unit],capture_output=True,text=True);rows.append({'unit':unit,'requested':r.returncode==0})
Path('repair-notes/2026-11-24-service-checkup/namespace-retries.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
