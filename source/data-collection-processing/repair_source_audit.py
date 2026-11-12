"""Verify repaired batch membership in published Athena manifests."""
import json
from pathlib import Path
import boto3
from collection_storage import StorageSettings
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'repair-notes/2026-10-21-athena-source-checks'
TARGETS={
'MHRA':('uk_mhra','research_records','2a746294-e312-4092-91ba-486a784e6ec6'),
'CTIS':('ema_ctis','research_records','f5b8c64d-66f0-4994-9d17-f28f2b6d551d'),
'NMPA':('nmpa_trials','registry_inventory','2245d9be-0379-44be-9d62-58c4cbcff796'),
'EDINET':('edinet_filings','specialist_inputs','be813688-99ab-4fb0-ad7b-c484e16de0e3'),
'TED':('ted_notices','specialist_inputs','80a4c8be-8750-4a45-9cf4-e74e9b22658e')}

def main():
 settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store()
 glue=boto3.client('glue',region_name='us-east-1');s3=store.client;rows=[]
 for name,(source,dataset,run) in TARGETS.items():
  key=f'manifests/collection_runs/source={source}/dataset={dataset}/run_{run}/final.json'
  obj=store.get(key)
  if not obj:
   print(json.dumps({'source':name,'manifest_missing':key}),flush=True);continue
  m=json.loads(obj.body)
  batches=[b for p in m['pages'] for b in p['batches']]
  part=glue.get_partition(DatabaseName='optima_collected_data',TableName='committed_records',PartitionValues=[source,dataset])['Partition']
  location=part['StorageDescriptor']['Location'];bucket,prefix=location[5:].split('/',1)
  listing=s3.list_objects_v2(Bucket=bucket,Prefix=prefix)
  published=set()
  for o in listing.get('Contents',[]):
   published.update(s3.get_object(Bucket=bucket,Key=o['Key'])['Body'].read().decode().splitlines())
  missing=[b['key'] for b in batches if 's3://'+settings.s3_bucket+'/'+settings.s3_prefix+'/'+b['key'] not in published]
  row={'name':name,'source':source,'dataset':dataset,'manifest':key,'capture_status':m['status'],'reason':m.get('reason_code'),'record_count':m['record_count'],'batch_count':len(batches),'missing_published_batches':missing,'last_batches':batches[-3:],'table_location':location,'task_id':m['task_id']}
  rows.append(row);print(json.dumps({k:v for k,v in row.items() if k not in {'last_batches','table_location'}}),flush=True)
 (OUT/'batch-membership.json').write_text(json.dumps(rows,indent=2)+'\n')
if __name__=='__main__':main()
