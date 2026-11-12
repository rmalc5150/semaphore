import base64,json,boto3
from pathlib import Path
p=Path(__file__).parent;c=json.load(open('config/constellation-infrastructure.json'))
script='''import json
from datetime import date,timedelta
from collection_storage import StorageSettings,write_json,now
from research_contract import ROOT,load_json,digest
from conference_collection import collect
from crossref_resumed_capture import deadline,PREFIX
settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store()
with deadline(110):result=collect(store,settings,load_json(ROOT/'config/crossref-resumed-universe.json'),load_json(ROOT/'config/sectors.v1.json'),date(2016,1,3),date(2016,1,4),'historical',max_pages=4,resume_recent_cursor=True)
if result['status']=='complete':
 manifest=json.loads(store.get(result['manifest']).body);identity=digest(manifest['task']);key=PREFIX+'/publication-queue/'+identity+'.json'
 if store.get(key)is None:write_json(store,key,{'window_id':identity,'manifests':[result['manifest']],'queued_at':now()})
 result['window_id']=identity
entry={'source':'crossref_proceedings','mode':'historical_probe','at':now(),**result};write_json(store,PREFIX+'/receipts/'+now()[:10]+'/'+digest(entry)+'.json',entry);print(json.dumps(entry),flush=True)
assert result['status']=='complete'
''';enc=base64.b64encode(script.encode()).decode();cmd="systemd-run --unit=optima-crossref-historical-probe --wait --pipe --property=User=ec2-user --property=WorkingDirectory=/opt/constellation/source --property=Slice=constellation-workers.slice --property=MemoryMax=402653184 --property=CPUQuota=20% --property=RuntimeMaxSec=150 --setenv=CONSTELLATION_ROLE=worker --setenv=CONSTELLATION_SHARED_HTTP_LIMITS=1 /opt/constellation/legacy-venv/bin/python -c \"import base64;exec(base64.b64decode('"+enc+"'))\"";r=boto3.client('ssm',region_name=c['region']).send_command(InstanceIds=[c['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[cmd]},TimeoutSeconds=180);(p/'historical-probe-command.json').write_text(json.dumps({'command_id':r['Command']['CommandId'],'instance':c['worker_instance_id']},indent=2));print(r['Command']['CommandId'])
