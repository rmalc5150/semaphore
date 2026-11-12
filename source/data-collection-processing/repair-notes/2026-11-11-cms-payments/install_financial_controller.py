import json,hashlib,sqlite3,subprocess
from pathlib import Path
from collection_storage import StorageSettings
p=Path(__file__).parent;store=StorageSettings.load('config/collection-storage.s3.json').store();ref=json.loads(store.get('constellation-backfill/cms-payments/registry/latest.json').body);raw=store.get(ref['key']).body;assert hashlib.sha256(raw).hexdigest()==ref['sha256']
state=Path('state/cms-financial/registry.sqlite3');state.parent.mkdir(parents=True,exist_ok=True)
if not state.exists():
 temp=state.with_suffix('.restore.tmp');temp.write_bytes(raw)
 with sqlite3.connect(temp)as db:assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok';print('Controller restored',db.execute('SELECT status,count(*) FROM editions GROUP BY status').fetchall())
 temp.replace(state)
config=json.load(open('config/cms-financial-resumed.json'));config.update(state_file=str(state.resolve()),status_file=str((p/'financial-status-latest.json').resolve()));Path('config/cms-financial-controller.json').write_text(json.dumps(config,indent=2)+'\n')
unit='''[Unit]
Description=Bounded CMS financial files refresh and Athena verification
After=network-online.target
[Service]
Type=oneshot
User=ec2-user
WorkingDirectory=/home/ec2-user/data-collection-processing
ExecStart=/home/ec2-user/data-collection-processing/.venv-athena/bin/python -B cms_payments_resumed.py --mode financial --config config/cms-financial-controller.json
Slice=optima-financial.slice
MemoryMax=402653184
MemorySwapMax=0
CPUQuota=20%
TimeoutStartSec=360
'''
timer='''[Unit]
Description=Continue CMS financial file collection with daily release discovery
[Timer]
OnBootSec=120
OnUnitInactiveSec=300
Persistent=true
Unit=optima-cms-financial-resumed.service
[Install]
WantedBy=timers.target
'''
slice_unit='[Unit]\nDescription=Bounded CMS financial and catalog publication budget\n[Slice]\nMemoryHigh=335544320\nMemoryMax=402653184\nMemorySwapMax=0\nCPUQuota=30%\n'
for name,body in [('optima-financial.slice',slice_unit),('optima-cms-financial-resumed.service',unit),('optima-cms-financial-resumed.timer',timer)]:
 file=p/name;file.write_text(body);subprocess.run(['sudo','install','-m','0644',str(file),'/etc/systemd/system/'+name],check=True)
subprocess.run(['sudo','systemctl','daemon-reload'],check=True);subprocess.run(['sudo','systemctl','enable','--now','optima-cms-financial-resumed.timer'],check=True);subprocess.run(['sudo','systemctl','start','--no-block','optima-cms-financial-resumed.service'],check=True)
