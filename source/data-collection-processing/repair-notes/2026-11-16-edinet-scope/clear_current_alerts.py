"""Apply the explicit owner scope decision to the cached gap view; preserve its audit."""
import json,copy,hashlib,boto3
from datetime import datetime,timezone
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3',region_name='us-east-1');bucket='data-collection-059416028963-us-east-1-an';key='research-data/monitoring/health/constellation-gaps.json';base='research-data/constellation-backfill/repairs/2026-11-16-edinet-scope'
a=datetime(2016,1,1,tzinfo=timezone.utc);b=datetime(2017,1,1,tzinfo=timezone.utc)
def instant(v):
 d=datetime.fromisoformat(v.replace('Z','+00:00'));return d.replace(tzinfo=timezone.utc)if d.tzinfo is None else d

def pieces(g):
 start,end=instant(g['start']),instant(g['end'])
 if not g['scope'].startswith('edinet_filings|')or end<=a or start>=b:return [g],False
 result=[]
 for left,right in ((start,min(end,a)),(max(start,b),end)):
  if right>left:
   seconds=(right-left).total_seconds();result.append({**g,'start':left.isoformat(),'end':right.isoformat(),'duration_days':seconds/86400,'flag_for_checkup':seconds>threshold*86400})
 return result,True
threshold=5
fixture={'scope':'edinet_filings|fixture','start':'2016-12-01','end':'2017-02-01'}
assert pieces(fixture)[0][0]['start'].startswith('2017-01-01')
assert pieces({**fixture,'scope':'other|fixture'})[1]is False
assert pieces({**fixture,'start':'2017-01-01'})[1]is False
for attempt in range(3):
 r=s.get_object(Bucket=bucket,Key=key);raw=r['Body'].read();doc=json.loads(raw);threshold=doc.get('threshold_days',5);retained=[];affected=[]
 for gap in doc.get('gaps',[]):
  new,changed=pieces(gap);retained.extend(new)
  if changed:affected.append(gap)
 if affected:
  sha=hashlib.sha256(raw).hexdigest();backup=base+'/prior-gap-reports/'+sha+'.json'
  try:s.put_object(Bucket=bucket,Key=backup,Body=raw,ServerSideEncryption='AES256',IfNoneMatch='*')
  except s.exceptions.ClientError as e:
   if e.response['Error']['Code']!='PreconditionFailed':raise
  doc.update(gaps=retained,flagged_gaps=sum(g.get('flag_for_checkup',False)for g in retained),record_only_gaps=sum(not g.get('flag_for_checkup',False)for g in retained))
  doc['owner_scope_exclusions']=[{'source':'edinet_filings','period_start':'2016-01-01','period_end_exclusive':'2017-01-01','reason':'historical_period_not_required_by_owner','evidence_uri':'s3://'+bucket+'/'+base+'/owner-decision.json','applied_at':datetime.now(timezone.utc).isoformat(),'affected_gaps':len(affected),'prior_report_uri':'s3://'+bucket+'/'+backup}]
  try:s.put_object(Bucket=bucket,Key=key,Body=json.dumps(doc).encode(),ServerSideEncryption='AES256',ContentType='application/json',IfMatch=r['ETag'])
  except s.exceptions.ClientError as e:
   if e.response['Error']['Code']in('PreconditionFailed','ConditionalRequestConflict')and attempt<2:continue
   raise
 final=json.loads(s.get_object(Bucket=bucket,Key=key)['Body'].read())
 remaining=[g for g in final.get('gaps',[])if g['scope'].startswith('edinet_filings|')and instant(g['start'])<b and instant(g['end'])>a]
 assert not remaining,'Concurrent report still contains excluded 2016 period'
 evidence={'checked_at':datetime.now(timezone.utc).isoformat(),'cached_2016_edinet_gaps_remaining':len(remaining),'affected_gap_intervals':len(affected),'other_gaps_retained':len(final.get('gaps',[])),'owner_decision_uri':'s3://'+bucket+'/'+base+'/owner-decision.json'}
 (p/'verification.json').write_text(json.dumps(evidence,indent=2));s.put_object(Bucket=bucket,Key=base+'/verification.json',Body=json.dumps(evidence).encode(),ServerSideEncryption='AES256');print(json.dumps(evidence));break
