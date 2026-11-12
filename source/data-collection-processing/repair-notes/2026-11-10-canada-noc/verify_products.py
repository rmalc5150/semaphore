import json,time,boto3
from pathlib import Path
p=Path(__file__).parent;product=json.load(open(p/'products-progress.json'));notice=json.load(open(p/'fresh-capture.json'));a=boto3.client('athena',region_name='us-east-1');out={}
def query(name,sql):
 q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];r={'query_id':q,'sql':sql}
 for _ in range(60):
  e=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=e['Status']['State']
  if state in ('SUCCEEDED','FAILED','CANCELLED'):
   r.update(state=state,reason=e['Status'].get('StateChangeReason'))
   if state=='SUCCEEDED':r['rows']=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
   break
  time.sleep(1)
 out[name]=r;print(name,json.dumps(r),flush=True);assert r.get('state')=='SUCCEEDED',r
query('metadata_product_sample',"SELECT source_record_id,ingested_at,raw_completeness_status,json_extract_scalar(labelled_json,'$.payload.data.noc_number') noc_number,json_extract_scalar(labelled_json,'$.payload.data.noc_br_brandname') brand_name,json_extract_scalar(labelled_json,'$.payload.data.noc_br_din') din FROM optima_metadata_engine.source_observations WHERE source_key='canada_noc' AND source_record_id LIKE 'product:%' ORDER BY ingested_at DESC LIMIT 3")
if product['status']=='complete':
 wid=product['window_id'];nid=notice['window_id']
 query('counts',f"SELECT count(*) observations,count(DISTINCT provider_id) distinct_product_records,count(DISTINCT nullif(json_extract_scalar(payload_json,'$.data.noc_br_din'),'')) distinct_supplied_nonempty_din_values FROM optima_specialist_inputs.source_observations_windows WHERE source='canada_noc' AND window_id='{wid}'")
 row=out['counts']['rows'][1]['Data'];assert int(row[0]['VarCharValue'])==int(row[1]['VarCharValue'])==product['distinct_provider_rows']
 query('product_sample',f"SELECT provider_id,json_extract_scalar(payload_json,'$.data.noc_number') noc_number,json_extract_scalar(payload_json,'$.data.noc_br_brandname') brand_name,json_extract_scalar(payload_json,'$.data.noc_br_din') din,length(payload_json) payload_characters FROM optima_specialist_inputs.source_observations_windows WHERE source='canada_noc' AND window_id='{wid}' ORDER BY rand() LIMIT 3")
 query('notice_links',f"WITH notices AS (SELECT provider_id FROM optima_specialist_inputs.source_observations_windows WHERE source='canada_noc' AND window_id='{nid}'),products AS (SELECT provider_id,json_extract_scalar(payload_json,'$.data.noc_number') noc_number FROM optima_specialist_inputs.source_observations_windows WHERE source='canada_noc' AND window_id='{wid}') SELECT count(*) product_records,count_if(n.provider_id IS NULL) missing_notice_links FROM products p LEFT JOIN notices n ON n.provider_id=p.noc_number")
(p/'products-athena-verification.json').write_text(json.dumps(out,indent=2))
