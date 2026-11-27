import json,time
from pathlib import Path
import boto3
P=Path(__file__).parent;a=boto3.client('athena',region_name='us-east-1')
sources=('usgs_minerals','eia_battery_generators','caiso_prices','bls_wages','ror_institutions','eia_retail_prices')
queries={'committed-counts':"SELECT source,dataset,count(*) observations,count(DISTINCT record_id) record_identities,min(ingested_at) first_ingested_at,max(ingested_at) latest_ingested_at FROM optima_collected_data.observations WHERE source IN ('usgs_minerals','eia_battery_generators','caiso_prices','bls_wages','ror_institutions','eia_retail_prices') GROUP BY source,dataset",
 'metadata-counts':"SELECT source_key,count(*) observations,count_if(raw_completeness_status='complete') complete_raw_observations FROM optima_metadata_engine.source_observations WHERE source_key IN ('usgs_minerals','eia_battery_generators','caiso_prices','bls_wages','ror_institutions','eia_retail_prices') GROUP BY source_key"}
for source in sources:
 queries['sample-'+source]="SELECT source,dataset,record_id,provider_id,ingested_at,source_url,event_at_json,payload_json FROM optima_collected_data.observations WHERE source='"+source+"' LIMIT 3"

results={}
for name,sql in queries.items():
 q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];results[name]={'query_id':q,'sql':sql};print(name,q,flush=True)
deadline=time.monotonic()+100
while time.monotonic()<deadline and any('state'not in r for r in results.values()):
 for name,r in results.items():
  if 'state'in r:continue
  e=a.get_query_execution(QueryExecutionId=r['query_id'])['QueryExecution'];state=e['Status']['State']
  if state in ('SUCCEEDED','FAILED','CANCELLED'):
   r.update(state=state,reason=e['Status'].get('StateChangeReason'),bytes_scanned=e['Statistics'].get('DataScannedInBytes'))
   if state=='SUCCEEDED':r['rows']=a.get_query_results(QueryExecutionId=r['query_id'])['ResultSet']['Rows']
 time.sleep(1)
for name,r in results.items():
 if 'state'not in r:a.stop_query_execution(QueryExecutionId=r['query_id']);r['state']='TIMEOUT'
 (P/(name+'.json')).write_text(json.dumps(r,indent=2)+'\n');print(name,r['state'],[[v.get('VarCharValue')for v in x['Data']]for x in r.get('rows',[])[:8] if name.endswith('counts')],flush=True)
