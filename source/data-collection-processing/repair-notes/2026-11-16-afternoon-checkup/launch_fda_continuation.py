import json,boto3,base64
from pathlib import Path
p=Path(__file__).parent;script=(p/'replay_core.py').read_text();dates=json.load(open(p/'fda-replay-dates.json'))
script=script.replace('for month in [2,3,4]:\n start=date(2016,month,1);end=date(2016,month+1,1)',"for day in "+repr(dates)+":\n start=date.fromisoformat(day);end=date(start.year+(start.month==12),start.month%12+1,1)")
script=script.replace("write_json(store,'constellation-backfill/repairs/2026-11-16-afternoon/core-fda-'+str(start)+'.json',r)", "latest='constellation-backfill/repairs/2026-11-16-afternoon/core-fda-'+str(start)+'.json'; previous=store.get(latest); write_json(store,'constellation-backfill/repairs/2026-11-16-afternoon/attempts/'+__import__('uuid').uuid4().hex+'.json',r); write_json(store,latest,r,previous.token if previous else None)")
s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an';key='research-data/constellation-backfill/repairs/2026-11-16-afternoon/fda-continuation.py';s.put_object(Bucket=b,Key=key,Body=script.encode(),ServerSideEncryption='AES256')
remote='''import boto3,subprocess,json
from pathlib import Path
p=Path('/opt/constellation/tmp/checkup1116-afternoon');p.mkdir(exist_ok=True,parents=True);f=p/'fda-continuation.py';f.write_bytes(boto3.client('s3').get_object(Bucket=BUCKET,Key=KEY)['Body'].read())
subprocess.run(['systemctl','stop','optima-fda-gap-repair-20261116.service'],check=True); r=subprocess.run(['systemd-run','--unit=optima-fda-gap-repair-20261116b','--property=Slice=constellation-workers.slice','--property=MemoryMax=900M','--property=CPUQuota=25%','--property=RuntimeMaxSec=3600','--property=StandardOutput=append:'+str(p/'fda-continuation.log'),'--property=StandardError=append:'+str(p/'fda-continuation.log'),'--setenv=AWS_CONFIG_FILE=/dev/null','--setenv=AWS_SHARED_CREDENTIALS_FILE=/dev/null','--setenv=AWS_DEFAULT_REGION=us-east-1','/opt/constellation/legacy-venv/bin/python',str(f)],capture_output=True,text=True);print(json.dumps({'exit':r.returncode,'detail':r.stderr}));assert r.returncode==0
'''.replace('BUCKET',repr(b)).replace('KEY',repr(key));(p/'start_fda_continuation.py').write_text(remote)
