import json,boto3
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3',region_name='us-east-1');bucket='data-collection-059416028963-us-east-1-an';health=json.load(open(p/'monitor-health-latest.json'));out={}
for key in ('research-data/monitoring/state/latest.json',*['research-data/'+k for unit,v in health['jobs'].items()if any(x in unit for x in ('market-collection','news-collection','patents-daily','patents-prosecution.service'))for k in v.get('evidence_keys',[])]):
 try:d=json.loads(s.get_object(Bucket=bucket,Key=key)['Body'].read());out[key]=d
 except Exception as e:print(key,type(e).__name__)
(p/'lower-alert-evidence.json').write_text(json.dumps(out,indent=2,default=str))
for key,d in out.items():
 if 'state/latest'in key:
  for a in d.get('active',{}).values():
   if any(x in a.get('unit','')for x in ('market','news','patent')):print('ACTIVE',a)
 elif'/news/'in key:print('NEWS',key,json.dumps(d)[:1800])
 elif'/market/'in key:
  print('MARKET',key,list(d),len(d.get('symbols',{})))
  for symbol,state in list(d.get('symbols',{}).items())[:4]:print(symbol,json.dumps(state)[:600])
