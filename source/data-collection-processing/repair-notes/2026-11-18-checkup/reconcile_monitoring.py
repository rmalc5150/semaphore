import boto3,json,hashlib
from pathlib import Path
from datetime import date,datetime,timezone
from concurrent.futures import ThreadPoolExecutor
from constellation.gaps import current_core_window
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an';key='research-data/monitoring/health/constellation-gaps.json';response=s.get_object(Bucket=b,Key=key);body=response['Body'].read();report=json.loads(body);etag=response['ETag'];stream='935af362e43726fe97e95f4c6848b591ce8083c6cdf1ec5843bef67f9ae9d53f';scope='fda|'+stream+'|configured_legacy_scope'
def read(k):return json.loads(s.get_object(Bucket=b,Key='research-data/'+k)['Body'].read())
def check(day):
 d=date.fromisoformat(day);end=date(d.year+(d.month==12),d.month%12+1,1);window={'scope':scope,'start':day+'T00:00:00','end':str(end)+'T00:00:00','status':'failed'};outcome=read('operations/streams/'+stream+'/historical/fda/'+day+'_'+str(end)+'.json');manifest=read(outcome['manifest']);head=read('checkpoints/'+manifest['task_id']+'/head.json');replacement=current_core_window(window,outcome,manifest,head);assert replacement['status']=='complete',day;return {'start':day,'end':str(end),'manifest':outcome['manifest'],'task_id':manifest['task_id']}
dates=json.load(open(p/'fda-replay-dates.json'))
with ThreadPoolExecutor(max_workers=4) as pool:proof=list(pool.map(check,dates))
covered={(r['start'],r['end'])for r in proof};remaining=[];removed=[];backlog=[]
for gap in report['gaps']:
 if gap['scope']==scope:
  d=date.fromisoformat(gap['start'][:10]);end=date.fromisoformat(gap['end'][:10]);assert d.day==end.day==1
  while d<end:
   following=date(d.year+(d.month==12),d.month%12+1,1);assert (str(d),str(following))in covered;d=following
  removed.append(gap);continue
 if gap['scope'].startswith('copernicus_era5_era5_land|') and set(gap['reasons'])=={'copernicus_queue_wait'}:
  backlog.append(gap);continue
 remaining.append(gap)
report['gaps']=remaining;report['flagged_gaps']=sum(g['flag_for_checkup']for g in remaining);report['record_only_gaps']=sum(not g['flag_for_checkup']for g in remaining);report['capacity_backlog_intervals']=backlog;report['reconciled_at']=datetime.now(timezone.utc).isoformat();report['reconciliation_note']='FDA intervals removed only after exact complete checkpoint proof; Copernicus admission waits retained separately as backlog. Other observations retain their original checked_at.'
base='research-data/constellation-backfill/repairs/2026-11-18';backup=base+'/monitoring-before-'+hashlib.sha256(body).hexdigest()+'.json';s.put_object(Bucket=b,Key=backup,Body=body,ServerSideEncryption='AES256');audit={'at':report['reconciled_at'],'backup_key':backup,'fda_windows':proof,'removed_fda_gap_intervals':len(removed),'capacity_backlog_intervals':len(backlog),'remaining_flagged_gaps':report['flagged_gaps']};s.put_object(Bucket=b,Key=base+'/monitoring-reconciliation.json',Body=json.dumps(audit).encode(),ServerSideEncryption='AES256');s.put_object(Bucket=b,Key=key,Body=json.dumps(report).encode(),ServerSideEncryption='AES256',IfMatch=etag);(p/'monitoring-reconciliation.json').write_text(json.dumps(audit,indent=2));print({k:v for k,v in audit.items()if k!='fda_windows'})
