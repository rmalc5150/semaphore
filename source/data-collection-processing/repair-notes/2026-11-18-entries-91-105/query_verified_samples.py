from ops import *
import time
s3=session.client('s3');migration=json.loads(s3.get_object(Bucket=B,Key=BASE+'migration.json')['Body'].read());replay=json.loads(s3.get_object(Bucket=B,Key=BASE+'replay-publication.json')['Body'].read());assert replay.get('finished_at')and not replay['errors'];withdrawal=json.loads(s3.get_object(Bucket=B,Key=BASE+'withdrawal-verified.json')['Body'].read());new=[j for jobs in migration['targets'].values()for j in jobs];old=[v['job_id']for v in withdrawal['results']];assert len(new)==31 and len(old)==220
values=','.join(repr(j)for j in new+old);retired=','.join(repr(j)for j in old)
sql="SELECT source_key,dataset,contract_version,count(*) observations,count_if(raw_completeness_status='complete') complete_raw_observations,min(CASE WHEN source_key IN ('cninfo_mainland_china_company_disclosures','south_korea_fss_opendart') THEN json_extract_scalar(labelled_json,'$.raw_artifacts[2].s3_uri') ELSE json_extract_scalar(labelled_json,'$.raw_artifacts[1].s3_uri') END) provider_original_s3_uri,count_if(job_id IN ("+retired+")) withdrawn_legacy_rows FROM optima_metadata_engine.source_observations WHERE job_id IN ("+values+") GROUP BY source_key,dataset,contract_version ORDER BY source_key,dataset"
a=session.client('athena');q=a.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId'];print('Query:',q,flush=True);started=time.monotonic()
while True:
 e=a.get_query_execution(QueryExecutionId=q)['QueryExecution'];state=e['Status']['State']
 if state in ('SUCCEEDED','FAILED','CANCELLED'):break
 if time.monotonic()-started>120:a.stop_query_execution(QueryExecutionId=q);raise TimeoutError('Bounded verification exceeded 120s: '+q)
 time.sleep(1)
out={'query_id':q,'sql':sql,'state':state,'statistics':e['Statistics'],'scope':'Exact 31 verified replacement jobs plus all 220 withdrawn legacy job partitions; sample counts are not full source or historical coverage.'}
assert state=='SUCCEEDED',e['Status'];rows=a.get_query_results(QueryExecutionId=q)['ResultSet']['Rows'];out['rows']=rows
out['decoded_rows']=[dict(zip([d['VarCharValue']for d in rows[0]['Data']],[d.get('VarCharValue')for d in r['Data']]))for r in rows[1:]]
assert len({r['source_key']for r in out['decoded_rows']})==14
assert all(r['contract_version']=='2.0.3'and r['observations']==r['complete_raw_observations']and r['withdrawn_legacy_rows']=='0'for r in out['decoded_rows'])
assert sum(int(r['observations'])for r in out['decoded_rows'])==124
(P/'verified-sample-sql.json').write_text(json.dumps(out,indent=2)+'\n');(P/'verified-sample-job-ids.json').write_text(json.dumps(migration['targets'],indent=2)+'\n');s3.put_object(Bucket=B,Key=BASE+'verified-sample-sql.json',Body=(P/'verified-sample-sql.json').read_bytes(),ServerSideEncryption='AES256');print('Verified 124 complete rows across 14 sources; zero withdrawn legacy rows returned.',flush=True)
