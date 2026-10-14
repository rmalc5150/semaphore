import json,boto3
from pathlib import Path
from collection_storage import StorageSettings
from source_observation_athena import SCHEMAS
from window_publication import ensure_catalog,descriptor
from botocore.exceptions import ClientError
s=StorageSettings.load(Path('config/collection-storage.s3.json'))
g=boto3.client('glue',region_name=s.region);a=boto3.client('athena',region_name=s.region)
reports=[]
for owner,db,wg,curated,results in [('specialists','optima_specialist_inputs','optima-specialist-inputs','curated/specialists/releases','athena-results/specialists'),('social','optima_social_research','optima-social-research','curated/social/observations/releases','athena-results/social')]:
 c={'owner':owner,'database':db,'workgroup':wg,'region':s.region,'curated_prefix':curated,'query_results_prefix':results,'dataset':'specialist_inputs' if owner=='specialists' else 'social_records','allowed_sources':['placeholder']}
 r={'config':c,'bucket':s.s3_bucket,'s3_prefix':s.s3_prefix}
 ensure_catalog(g,a,r,owner)
 for name,columns in SCHEMAS.items():
  table=name+'_windows';location=f's3://{s.s3_bucket}/{s.s3_prefix}/curated/{owner}/empty/{table}/'
  definition={'Name':table,'TableType':'EXTERNAL_TABLE','Parameters':{'classification':'parquet','optima_owner':owner},'PartitionKeys':[{'Name':'window_id','Type':'string'}],'StorageDescriptor':descriptor({'columns':columns,'location':location})}
  try:g.get_table(DatabaseName=db,Name=table)
  except ClientError as e:
   if e.response['Error']['Code']!='EntityNotFoundException':raise
   g.create_table(DatabaseName=db,TableInput=definition)
 reports.append({'database':db,'workgroup':wg,'tables':list(SCHEMAS),'data_state':'partition publication required; catalog presence does not certify data'})
 print(db,'ready',flush=True)
Path('reports/source-schedule-2026-10-09/catalog-provisioning.json').write_text(json.dumps(reports,indent=2)+'\n')
