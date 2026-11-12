import json,boto3,time
from pathlib import Path
from metadata_engine.runtime_db import Database
from collection_storage import StorageSettings
from window_publication import list_keys
from metadata_engine.fda_authenticated import SOURCES
p=Path(__file__).parent;cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);out={}
with db.tx()as c:
 c.execute('SELECT * FROM engine_sources WHERE source_key IN %s',(tuple(SOURCES),));out['sources']=c.fetchall();c.execute('SELECT source_key,state,count(*) n FROM engine_jobs WHERE source_key IN %s GROUP BY source_key,state',(tuple(SOURCES),));out['jobs']=c.fetchall()
settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store();out['receipts']=[json.loads(store.get(key).body)for key in list_keys(store,settings,'constellation-backfill/fda-review/receipts/')];out['windows']=[json.loads(store.get(key).body)for key in list_keys(store,settings,'constellation-backfill/specialist-publication-queue/fda-review/')]
(p/'live-status.json').write_text(json.dumps(out,indent=2,default=str));print('SOURCES',out['sources']);print('JOBS',out['jobs']);print('CAPTURES',[(r['job']['source'],r['status'],r.get('records'),r.get('reason'))for r in out['receipts']]);print('WINDOWS',len(out['windows']))
s=boto3.client('ssm',region_name='us-east-1');cmd="systemctl show optima-fda-reviewed-capture.service optima-metadata-worker.service -p Result -p ExecMainStatus -p ActiveState; journalctl -u optima-fda-review-probes-v3.service -o cat -n 7 --no-pager; systemctl list-timers optima-fda-reviewed-capture.timer --no-pager; systemctl list-units 'constellation-backfill@*.service' 'constellation-legacy-worker@*.service' 'constellation-public-worker@*.service' --no-pager"
r=s.send_command(InstanceIds=['i-06241bd1c4e91c2fc'],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=60);ref={'command_id':r['Command']['CommandId'],'instance':'i-06241bd1c4e91c2fc'};(p/'health-command.json').write_text(json.dumps(ref))
for _ in range(40):
 try:o=s.get_command_invocation(CommandId=ref['command_id'],InstanceId=ref['instance'])
 except s.exceptions.InvocationDoesNotExist:time.sleep(1);continue
 if o['Status']not in ('Pending','InProgress','Delayed'):break
 time.sleep(1)
(p/'health-result.json').write_text(json.dumps(o,indent=2,default=str));print(o['StandardOutputContent'][-6500:],o['StandardErrorContent'])
