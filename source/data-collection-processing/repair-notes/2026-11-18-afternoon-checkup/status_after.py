import json,boto3
from pathlib import Path
from datetime import datetime,timezone
from monitoring_overview import overview
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an'
for name,key in [('health','health/latest.json'),('alerts','watchdog-state.json')]:
 try:d=json.loads(s.get_object(Bucket=b,Key='research-data/monitoring/'+key)['Body'].read())
 except s.exceptions.NoSuchKey:print('MISSING',key);continue
 (p/(name+'-after.json')).write_text(json.dumps(d,indent=2))
 if name=='health':
  print('health',d['checked_at'],'inspection_errors',sum('inspection_error'in j for j in d['jobs'].values()),'scheduled_wait',sum(j.get('activity')=='scheduled_wait'for j in d['jobs'].values()))
  waits=[j['scheduled_batch_wait']for j in d['jobs'].values()if j.get('scheduled_batch_wait')]
  if waits:
   for k in ['stopped_at_epoch','earliest_wake_at_epoch','wake_deadline_epoch']:print(k,datetime.fromtimestamp(waits[0][k],timezone.utc).isoformat())
