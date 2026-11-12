import base64,json,boto3
from pathlib import Path
p=Path(__file__).parent;c=json.load(open('config/constellation-infrastructure.json'));job=json.load(open(p/'historical-seeds.json'))[0]['job']
script='''import json
from collection_storage import StorageSettings
from research_contract import ROOT,load_json
from specialist_inputs import collect
from epmc_fulltext_capture import deadline,queue_window,report
job=JOB;settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store()
with deadline(75):result=collect(job,store,settings,load_json(ROOT/'config/drugsfda-inventory-universe.json'),load_json(ROOT/'config/sectors.v1.json'),1)
queue_window(store,job,result);report(store,'historical_probe',{'job':job,**result})
assert result['status']=='complete'
'''.replace('JOB',repr(job));enc=base64.b64encode(script.encode()).decode();cmd="systemd-run --unit=optima-epmc-fulltext-historical-probe --wait --pipe --property=User=ec2-user --property=WorkingDirectory=/opt/constellation/source --property=Slice=constellation-workers.slice --property=MemoryMax=402653184 --property=CPUQuota=20% --property=RuntimeMaxSec=120 --setenv=CONSTELLATION_ROLE=worker --setenv=CONSTELLATION_SHARED_HTTP_LIMITS=1 /opt/constellation/legacy-venv/bin/python -c \"import base64;exec(base64.b64decode('"+enc+"'))\"";r=boto3.client('ssm',region_name=c['region']).send_command(InstanceIds=[c['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=180);(p/'historical-probe-command.json').write_text(json.dumps({'command_id':r['Command']['CommandId'],'instance':c['worker_instance_id']},indent=2));print(r['Command']['CommandId'])
