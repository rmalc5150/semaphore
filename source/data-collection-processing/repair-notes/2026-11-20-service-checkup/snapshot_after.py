import boto3,json,time
from pathlib import Path
from monitoring_overview import overview
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an'
for label,key in [('health','health/latest.json'),('alerts','state/latest.json')]:
 d=json.loads(s.get_object(Bucket=b,Key='research-data/monitoring/'+key)['Body'].read());(p/(label+'-after.json')).write_text(json.dumps(d,indent=2))
 if label=='health':
  h=d;print('HEALTH',d['checked_at'],'errors',sum('inspection_error'in j for j in d['jobs'].values()),'verified_prior_invocations',sum('successful_execution_at'in j for j in d['jobs'].values()))
 else:
  title,body=overview(d['active'],time.time(),d['checked_at'],h);(p/'overview-preview.txt').write_text(title+'\n'+body);print(title)
  for a in d['active'].values():print(a['unit'],a['code'])
