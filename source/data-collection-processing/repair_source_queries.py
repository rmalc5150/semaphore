"""Query representative repaired records without unbounded random scans."""
import json
from pathlib import Path
import boto3
from committed_data_athena import query
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'repair-notes/2026-10-21-athena-source-checks'
def main():
 a=boto3.client('athena',region_name='us-east-1');rows=json.loads((OUT/'batch-membership.json').read_text());audit=[];sqls=[]
 for r in rows:
  scope="source='"+r['source']+"' AND dataset='"+r['dataset']+"'"
  sql='SELECT * FROM optima_collected_data.observations WHERE '+scope+' LIMIT 5'
  sample=query(a,sql);(OUT/(r['name'].lower()+'-view-sample.json')).write_text(json.dumps(sample,indent=2)+'\n')
  sqls.append('## '+r['name']+'\n\n```sql\n'+sql+';\n```\n')
  targeted=None
  if r['last_batches']:
   paths=["'s3://data-collection-059416028963-us-east-1-an/research-data/"+b['key']+"'" for b in r['last_batches']]
   where=scope+' AND "$path" IN ('+','.join(paths)+')'
   count=query(a,'SELECT count(*) FROM optima_collected_data.committed_records WHERE '+where)
   expected=sum(b['records'] for b in r['last_batches']);assert count['rows']==[[str(expected)]],(r['name'],count,expected)
   targeted=query(a,'SELECT record_json FROM optima_collected_data.committed_records WHERE '+where+' LIMIT 8')
   (OUT/(r['name'].lower()+'-repaired-sample.json')).write_text(json.dumps(targeted,indent=2)+'\n')
  records=[json.loads(row[-1]) for row in sample['rows']]
  inspected=[]
  for record in records:
   payload=record.get('payload',{});data=payload.get('data',payload)
   inspected.append({'record_type':payload.get('record_type'),'provider_id':record.get('source_record_id'),'company_ids':record.get('company_ids'), 'event_at':record.get('event_at'),'payload_keys':list(payload),'data_keys':list(data) if isinstance(data,dict) else type(data).__name__})
  entry={'source':r['name'],'view_query_id':sample['query_id'],'sample_count':len(records),'targeted_count_query':count if targeted else None,'targeted_sample_query_id':targeted['query_id'] if targeted else None,'inspected':inspected}
  audit.append(entry);(OUT/'query-audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(entry),flush=True)
 (OUT/'query-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 (OUT/'SQL-checks.md').write_text('# Repaired-source payload checks\n\nUse workgroup `optima-collected-data`. These bounded samples are not random or completeness checks.\n\n'+'\n'.join(sqls))
if __name__=='__main__':main()
