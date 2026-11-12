import boto3,json,time
from pathlib import Path
from metadata_engine.runtime_db import Database
from collection_storage import StorageSettings
p=Path(__file__).parent;db=Database(json.load(open('config/metadata-engine.json')));out={}
with db.tx()as c:
 c.execute("SELECT * FROM engine_sources WHERE source_key='cms_payments_catalog'");out['source']=c.fetchall()
 c.execute("SELECT state,count(*) n FROM engine_jobs WHERE source_key='cms_payments_catalog' GROUP BY state");out['jobs']=c.fetchall()
settings=StorageSettings.load('config/collection-storage.s3.json');store=settings.store()
for name,key in {'catalog':'constellation-backfill/cms-payments/catalog-state.json','verification':'constellation-backfill/cms-payments/verification/latest.json','registry_backup':'constellation-backfill/cms-payments/registry/latest.json'}.items():
 o=store.get(key);out[name]=json.loads(o.body)if o else None
(p/'live-status.json').write_text(json.dumps(out,indent=2,default=str));print(json.dumps(out,default=str),flush=True)
s=boto3.client('ssm',region_name='us-east-1');cmd="systemctl show optima-cms-payments-resumed.service optima-metadata-worker.service -p ActiveState -p Result -p ExecMainStatus; systemctl list-timers optima-cms-payments-resumed.timer --no-pager; journalctl -u optima-cms-payments-resumed.service -n 12 --no-pager; systemctl list-units 'constellation-backfill@*.service' 'constellation-legacy-worker@*.service' 'constellation-public-worker@*.service' --no-pager"
r=s.send_command(InstanceIds=['i-06241bd1c4e91c2fc'],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=60);ref={'command_id':r['Command']['CommandId'],'instance':'i-06241bd1c4e91c2fc'};(p/'health-command.json').write_text(json.dumps(ref))
for _ in range(45):
 try:o=s.get_command_invocation(CommandId=ref['command_id'],InstanceId=ref['instance'])
 except s.exceptions.InvocationDoesNotExist:time.sleep(1);continue
 if o['Status']not in ('Pending','InProgress','Delayed'):break
 time.sleep(1)
(p/'health-result.json').write_text(json.dumps(o,indent=2,default=str));print(o['Status'],o['StandardOutputContent'],o['StandardErrorContent'])
