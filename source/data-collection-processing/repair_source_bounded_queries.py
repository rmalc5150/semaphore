import json,hashlib
from pathlib import Path
import boto3
from committed_data_athena import query
P=Path('repair-notes/2026-10-21-athena-source-checks')
a=boto3.client('athena',region_name='us-east-1');groups=json.loads((P/'existing-verification-groups.json').read_text());audit=[]
for source in ('edinet_filings','ted_notices'):
 gs=[g for g in groups if g['source']==source];paths=["'s3://data-collection-059416028963-us-east-1-an/research-data/"+k+"'" for g in gs for k in g['matched']]
 where="source='"+source+"' AND dataset='specialist_inputs' AND batch_group IN ("+','.join("'"+g['batch_group']+"'" for g in gs)+')'
 target=where+' AND "$path" IN ('+','.join(paths)+')'
 count=query(a,'SELECT count(*) FROM optima_collected_data.batch_verification_records WHERE '+target)
 expected=2 if source=='edinet_filings' else 126
 assert count['rows']==[[str(expected)]],count
 sample=query(a,'SELECT record_json FROM optima_collected_data.batch_verification_records WHERE '+target+' LIMIT 8')
 name='edinet' if source=='edinet_filings' else 'ted';(P/(name+'-repaired-sample.json')).write_text(json.dumps(sample,indent=2))
 audit.append({'source':source,'count':count,'sample_query_id':sample['query_id'],'verification_scope':target});print(json.dumps(audit[-1]),flush=True)
 if source=='ted_notices':
  r=query(a,'SELECT record_json FROM optima_collected_data.batch_verification_records WHERE '+where+" AND (json_extract_scalar(record_json,'$.payload.data.parent_notice_id')='709615-2026' OR json_extract_scalar(record_json,'$.source_record_id')='709615-2026')")
  records=[json.loads(row[0]) for row in r['rows']];chunks=[x['payload']['data'] for x in records if x['payload']['data'].get('record_type')=='notice_content_chunk'];chunks.sort(key=lambda x:x['chunk_index']);assert [c['chunk_index'] for c in chunks]==list(range(chunks[0]['chunk_count']))
  body=''.join(c['content_text'] for c in chunks).encode();assert hashlib.sha256(body).hexdigest()==chunks[0]['content_sha256'];obj=json.loads(body)
  proof={'query_id':r['query_id'],'bytes_scanned':r['bytes_scanned'],'notice_id':'709615-2026','chunk_count':len(chunks),'sha256_verified':True,'reconstructed_bytes':len(body),'reconstructed_keys':list(obj)}
  (P/'ted-reassembly-check.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof),flush=True)
  (P/'ted-reassembled-notice.json').write_text(json.dumps(obj,ensure_ascii=False))
  sample=query(a,"SELECT * FROM optima_collected_data.observations WHERE source='ted_notices' AND dataset='specialist_inputs' LIMIT 5")
  (P/'ted-view-sample.json').write_text(json.dumps(sample,indent=2))
(P/'bounded-query-audit.json').write_text(json.dumps(audit,indent=2))
