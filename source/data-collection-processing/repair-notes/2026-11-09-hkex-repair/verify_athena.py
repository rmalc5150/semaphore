import json,time,boto3
from pathlib import Path
p=Path(__file__).parent;a=boto3.client('athena',region_name='us-east-1')
ids=[j['job_id']for j in json.loads((p/'before-resume.json').read_text())['jobs']];scope="source_key='hkex_news' AND job_id IN ("+','.join("'"+i+"'"for i in ids)+')'
queries={
 'counts':"SELECT source_key,count(*) observations,count(DISTINCT source_record_id) distinct_filing_ids,count(DISTINCT raw_s3_uri) linked_raw_objects,count_if(raw_completeness_status='complete') complete_raw_observations,min(ingested_at) first_ingested_at,max(ingested_at) latest_ingested_at FROM optima_metadata_engine.source_observations WHERE "+scope+' GROUP BY source_key',
 'originals':"SELECT source_record_id,raw_completeness_status,raw_s3_uri,labelled_json FROM optima_metadata_engine.source_observations WHERE "+scope+" AND source_record_id IN ('12343954','12343952','12343951','12343918') LIMIT 8",
 'english_notices':"SELECT count(*) notice_rows FROM optima_metadata_engine.source_observations WHERE "+scope+" AND source_record_id IN ('12343955','12343953','12343919')"}
out={}
for name,sql in queries.items():
 q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];r={'sql':sql,'query_id':q}
 for _ in range(60):
  status=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=status['Status']['State']
  if state in ('SUCCEEDED','FAILED','CANCELLED'):
   r.update(state=state,bytes_scanned=status['Statistics'].get('DataScannedInBytes'),reason=status['Status'].get('StateChangeReason'))
   if state=='SUCCEEDED':r['rows']=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows']
   break
  time.sleep(1)
 else:a.stop_query_execution(QueryExecutionId=q);r['state']='CANCELLED_BY_TIMEOUT'
 out[name]=r;(p/'athena-verification.json').write_text(json.dumps(out,indent=2));print(name,r['state'],r['query_id'],r.get('rows',[])if name!='originals'else str(len(r.get('rows',[])))+' sample result rows',flush=True)
 if r['state']!='SUCCEEDED':raise SystemExit(1)
# Inspect the returned payload rather than relying solely on counts.
rows=out['originals']['rows'];columns=[v['VarCharValue']for v in rows[0]['Data']];samples=[]
for row in rows[1:]:
 d={k:v.get('VarCharValue')for k,v in zip(columns,row['Data'])};label=json.loads(d['labelled_json']);payload=label['payload'];assert payload['document_language']=='zh-Hant';assert str(payload['data']['NEWS_ID'])==d['source_record_id'];assert payload['language_notice_context']['notice_record_id']!=d['source_record_id'];assert any(x['artifact_kind']=='primary_document'and x['source_url'].endswith('_c.pdf')for x in label['raw_artifacts']);samples.append({'source_record_id':d['source_record_id'],'document_language':payload['document_language'],'notice_record_id':payload['language_notice_context']['notice_record_id'],'artifacts':label['raw_artifacts']})
assert samples
assert out['english_notices']['rows'][1]['Data'][0]['VarCharValue']=='0'
(p/'payload-inspection.json').write_text(json.dumps({'status':'passed','samples':samples},indent=2));print('Chinese original identities, payload language and PDF evidence verified; English notices excluded.')
