import json,base64,time,boto3
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('ssm',region_name='us-east-1')
code='''import json
from cms_coverage_capture import BASE,VERSION,report,save_state,queue_window
from collection_storage import StorageSettings
from research_contract import ROOT,load_json
from specialist_inputs import collect
from window_publication import list_keys
settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store();universe=load_json(ROOT/'config/drugsfda-inventory-universe.json');taxonomy=load_json(ROOT/'config/sectors.v1.json');fixed=0
for key in list_keys(store,settings,BASE+'outcomes/'):
 value=json.loads(store.get(key).body)
 if value.get('reason')!="ModuleNotFoundError: No module named 'metadata_engine.runtime_db'":continue
 job=value['job'];result=collect(job,store,settings,universe,taxonomy,1);queue_window(store,job,result)
 entry=report(store,'repaired_metadata_handoff',{'job':job,**result,'capture_version':VERSION,'retry_after':0});save_state(store,key,entry);assert result['status']=='complete';fixed+=1
print(json.dumps({'repaired_handoffs':fixed}),flush=True)
'''
enc=base64.b64encode(code.encode()).decode();cmd="cd /opt/constellation/source\nflock -w 90 /opt/constellation/tmp/cms-coverage-capture.lock /opt/constellation/legacy-venv/bin/python -B -c \"import base64;exec(base64.b64decode('"+enc+"'))\""
r=s.send_command(InstanceIds=['i-06241bd1c4e91c2fc'],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=210);ref={'command_id':r['Command']['CommandId'],'instance':'i-06241bd1c4e91c2fc'};(p/'handoff-repair-command.json').write_text(json.dumps(ref))
for _ in range(100):
 try:o=s.get_command_invocation(CommandId=ref['command_id'],InstanceId=ref['instance'])
 except s.exceptions.InvocationDoesNotExist:time.sleep(1);continue
 if o['Status']not in ('Pending','InProgress','Delayed'):break
 time.sleep(1)
(p/'handoff-repair-result.json').write_text(json.dumps(o,indent=2,default=str));print(o['Status'],o['StandardOutputContent'],o['StandardErrorContent']);assert o['Status']=='Success'
