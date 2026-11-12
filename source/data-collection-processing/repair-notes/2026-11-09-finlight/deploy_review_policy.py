import json,base64,boto3
from pathlib import Path
p=Path(__file__).parent;cfg=json.load(open('config/constellation-infrastructure.json'))
script='''import json,hashlib
from pathlib import Path
p=Path('/opt/constellation/metadata-engine-runtime/config/metadata-engine.json');before=p.read_bytes();text=before.decode();text=text[:-2] if text.endswith(chr(92)+'n') else text;d=json.loads(text)
assert 'finlight' in d['contracts']
backup=Path('/opt/constellation/tmp/finlight-review-20261109-config.json')
if not backup.exists():backup.write_bytes(before)
d.setdefault('verified_source_failure_handling',{})['finlight']='queue_by_source_date'
tmp=p.with_suffix('.review.tmp');tmp.write_text(json.dumps(d,indent=2));json.loads(tmp.read_text());tmp.replace(p)
print(json.dumps({'source':'finlight','failure_handling':d['verified_source_failure_handling']['finlight'],'config_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
'''
encoded=base64.b64encode(script.encode()).decode();command="/opt/constellation/legacy-venv/bin/python -c \"import base64;exec(base64.b64decode('"+encoded+"'))\""
r=boto3.client('ssm',region_name=cfg['region']).send_command(InstanceIds=[cfg['worker_instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[command]},TimeoutSeconds=60)
(p/'review-policy-command.json').write_text(json.dumps({'command_id':r['Command']['CommandId'],'instance':cfg['worker_instance_id']},indent=2));print(r['Command']['CommandId'])
