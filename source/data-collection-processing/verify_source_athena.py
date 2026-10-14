#!/usr/bin/env python3
"""Rerun count queries on bounded currently published partitions; never mutate catalog."""
import json,re,time
from datetime import datetime,timezone
from pathlib import Path
import boto3
from sec_athena_pilot import run_query
ROOT=Path(__file__).resolve().parent

def main():
 athena=boto3.client('athena',region_name='us-east-1');glue=boto3.client('glue',region_name='us-east-1');chosen={};results=[]
 for p in ROOT.glob('*build*/**/window-verification.json'):
  v=json.loads(p.read_text());rp=p.parent/'release.json'
  if v.get('status')!='verified' or not rp.exists():continue
  r=json.loads(rp.read_text())
  for item in r.get('inputs',[]):
   m=re.search('source=([^/]+)/dataset=([^/]+)/',item.get('key',''))
   if m:
    key='/'.join(m.groups());score=(item.get('records',0)>0,v.get('checked_at',''))
    if key not in chosen or score>chosen[key][0]:chosen[key]=(score,p,v,r)
 done={}
 for source,(_,p,v,r) in sorted(chosen.items()):
  identity=(r['config']['database'],v['window_id'],v['release_id'])
  if identity in done:results.append({'source_dataset':source,**done[identity]});continue
  try:
   c=r['config'];wc=athena.get_work_group(WorkGroup=c['workgroup'])['WorkGroup']['Configuration']
   if wc.get('BytesScannedCutoffPerQuery')!=104857600 or not wc.get('EnforceWorkGroupConfiguration'):raise ValueError('query_budget_contract_mismatch')
   for name in r['files']:
    part=glue.get_partition(DatabaseName=c['database'],TableName=name+'_windows',PartitionValues=[v['window_id']])['Partition']
    if part.get('Parameters',{}).get('release_id')!=r['release_id']:raise ValueError('partition_advanced_since_receipt')
   sql=' UNION ALL '.join(f"SELECT '{name}' AS table_name,count(*) AS records FROM {c['database']}.{name}_windows WHERE window_id='{v['window_id']}'" for name in sorted(r['files']))+' ORDER BY table_name'
   q=run_query(athena,r,sql);expected=[[name,str(r['files'][name]['rows'])] for name in sorted(r['files'])]
   result={'status':'verified' if q['rows']==expected else 'count_mismatch','checked_at':datetime.now(timezone.utc).isoformat(),'query':q,'expected':expected,'release_id':r['release_id'],'window_id':v['window_id'],'database':c['database']}
  except Exception as exc:result={'status':'unverified','reason':str(exc) if isinstance(exc,ValueError) else type(exc).__name__,'checked_at':datetime.now(timezone.utc).isoformat()}
  done[identity]=result;results.append({'source_dataset':source,**result})
  print(json.dumps({'source_dataset':source,'status':result['status']}),flush=True)
 report={'checked_at':datetime.now(timezone.utc).isoformat(),'method':'Fresh bounded table-count queries for one nonempty-preferred partition per source/dataset represented by local verified window receipts. Source coverage and historical availability are separate.','results':results,'unrepresented_sources':'Sources without a verified window receipt, including separate patent pilot tables, require separate query verification.'}
 (ROOT/'reports/source-end-to-end-athena.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
