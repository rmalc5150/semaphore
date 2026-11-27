import json,re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

P=Path(__file__).parent;root=P.parents[1]
counts=json.loads((P/'counts.json').read_text());assert counts['state']=='SUCCEEDED'
rows={r['Data'][0]['VarCharValue']:[c.get('VarCharValue')for c in r['Data']]for r in counts['rows'][1:]}
assert set(rows)=={'federal_register','federal_register_documents'}
for r in rows.values():assert int(r[1])>0 and r[1]==r[3]
validation=json.loads((P/'failed-batch-validation.json').read_text());passed=[r for r in validation if r['status']=='verified'];gaps=[r for r in validation if r['status']!='verified']
assert len(validation)==100 and len(passed)==99 and len(gaps)==1
large=json.loads((P/'large-notice-verified.json').read_text());assert large['official_pdf']['bytes']==120719355 and large['raw_completeness_status']=='complete'
large_sql=json.loads((P/'large-notice-sql.json').read_text());assert large_sql['state']=='SUCCEEDED'and len(large_sql['rows'])==2
resolved=json.loads((P/'incomplete-notice-resolved.json').read_text());assert resolved['superseded_jobs']==1 and resolved['old_raw_preserved']
controls=json.loads((P/'final-controls.json').read_text());assert all(s['state']=='enabled'and s['consecutive_raw_failures']==0 for s in controls['sources']);assert not controls['remaining_source_failures']
assert 'Ran 83 tests'in(P/'tests.log').read_text()and 'OK'in(P/'tests.log').read_text()
workers={}
for host in ('t3','m7'):
 f=sorted((root/'constellation/migration').glob('worker-check-20261113*-'+host+'.json'))[-1];d=json.loads(f.read_text())
 assert not [u for u,v in d['units'].items()if u.endswith('.timer')and v.get('UnitFileState')=='enabled'and v['ActiveState']!='active']
 assert not [x for x in d['failed']if 'ec2-code-backup.service'not in x]
 entry={'snapshot':str(f),'checked_at_epoch':d['checked_at_epoch'],'failed':d['failed'],'enabled_timers':sum(u.endswith('.timer')and v.get('UnitFileState')=='enabled'for u,v in d['units'].items())}
 if host=='m7':
  entry['historical_executors']=sum(u.startswith(('constellation-backfill@','constellation-legacy-worker@','constellation-public-worker@'))and v['ActiveState']=='active'for u,v in d['units'].items());assert entry['historical_executors']==15
  entry['recent_kernel_oom']=d['recent_kernel_oom'];entry['pool']=d['pool']
  for timer in ('optima-metadata-worker.timer','optima-metadata-worker-extra.timer','optima-metadata-streaming.timer'):assert d['units'][timer]['ActiveState']=='active'
 workers[host]=entry
stamp=datetime.now(ZoneInfo('Europe/Madrid')).isoformat();monitor=json.loads((P/'monitoring-final.json').read_text())
proof={'reviewed_at':stamp,'catalog_entry':48,'review_status':'reviewed_scoped_pipeline',
       'scope':'configured semiconductor, battery, robotics and clinical-trial searches and their full-notice companion records; not every Federal Register notice or completed historical coverage',
       'source_controls':controls['sources'],'sql_counts':rows,'athena_count_query_id':counts['query_id'],
       'saved_validation':{'inputs_checked':100,'passed_inputs':99,'verified_rows':sum(r['verified_rows']for r in passed),'incomplete_input_replaced':resolved},
       'large_notice':large,'large_notice_athena_query_id':large_sql['query_id'],'tests_passed':83,
       'worker_health':workers,'collection_controls':controls,'monitoring':monitor,
       'limits':['Listing observations are metadata, distinct from full notices.','Large full extractions remain linked in S3 rather than truncated into SQL rows.','Policy stages and dates reflect the original notice; later legal amendments and product applicability remain unreviewed.','Other source validation holds and owner pauses remain.','Previously deferred GitHub backup not retried.'],
       'upstream_documentation':['https://www.federalregister.gov/developers/documentation/api/v1','https://www.federalregister.gov/reader-aids/developer-resources/rest-api']}
(P/'review-complete.json').write_text(json.dumps(proof,indent=2)+'\n')

schedule=root/'RAW_DATA_VERIFICATION_SCHEDULE.md';text=schedule.read_text();m=re.search(r'- \[[ xX]\] \*\*48\. .*?(?=\n- \[|\n###|\Z)',text,re.S);assert m
entry='- [x] **48. Federal Register** (`federal_register`, companion `federal_register_documents`) — reviewed 13 November 2026, scoped pipeline verification  \n'
entry+='  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source=federal_register/` and `raw/source=federal_register_documents/`; original API, XML/HTML and PDF links retained.  \n'
entry+=f"  Both streams enabled under contract 2.0.3. Verified SQL snapshot: **{rows['federal_register'][1]} listing observations / {rows['federal_register_documents'][1]} full-notice observations**, all raw-complete for their distinct record kinds. Counts are row occurrences, not unique notices or historical completion.  \n"
entry+='  Checked 100 saved inputs: 99 inputs / 446 rows passed; the one incomplete 2026-22743 capture was superseded by a newly committed, metadata-verified replacement with its 120,719,355-byte official PDF and 4,375,819-character extraction. Old raw evidence is preserved. Missing PDFs now stay queued for retry.  \n'
entry+='  Scope: configured semiconductor, battery, robotics and clinical-trial searches. Full notice validation checks exact API identities, reparsed XML/HTML content and streamed official-PDF checksums. Large extractions are linked in S3. Current-law status, product applicability, exhaustive coverage and historical availability are not certified.  \n'
entry+="  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations FROM optima_metadata_engine.source_observations WHERE source_key IN ('federal_register','federal_register_documents') GROUP BY source_key;`  \n"
entry+='  **83 tests passed.** Capture/metadata/publication and all 15 historical executors checked; enabled timers active. No new IAM, key or manual restart action for you. [Review evidence](repair-notes/2026-11-13-federal-register/review-complete.json) · [SQL examples](repair-notes/2026-11-13-federal-register/review-queries.sql).\n'
text=text[:m.start()]+entry+text[m.end():];schedule.write_text(text)

status=Path('/home/ec2-user/data-source-status-2026-10-26.md');text=status.read_text();heading='## November 13 — Federal Register raw-data review completed'
intro=heading+'\n\n**Entry 48 is reviewed for the configured raw-validation, metadata and SQL pipelines.** Both `federal_register` listings and `federal_register_documents` full notices are enabled under corrected contract 2.0.3. Fixed the generic raw-validation false stops and missing companion-document contract. Full notices require matching API metadata, original XML/HTML and official PDF; listings remain distinctly labelled metadata.\n\n'
intro+=f"Verified Athena snapshot: **{rows['federal_register'][1]} listing observations and {rows['federal_register_documents'][1]} full-notice observations**, all raw-complete for their declared kinds. Checked 100 saved inputs: 99 inputs / 446 rows passed and one incomplete large notice was recaptured and verified. Notice 2026-22743 now links its full 120,719,355-byte PDF and 4,375,819-character extraction. Preserved the old partial raw capture and resolved its replacement lineage. Future PDF failures remain retries. **83 focused tests passed.**\n\n"
intro+='All 15 historical executors, metadata lanes, streaming lane and enabled collection schedules were checked. A timed-out bounded patent continuation was successfully retried. Other source validation holds, intentional pauses and the deferred GitHub backup remain. This review covers the configured four search topics and companion notices; full archive completion, current-law status and product applicability are not certified. No new IAM edit, key or manual restart is required from you. [Review evidence](data-collection-processing/repair-notes/2026-11-13-federal-register/review-complete.json) · [working SQL](data-collection-processing/repair-notes/2026-11-13-federal-register/review-queries.sql).\n\n'
if heading not in text:text=text[:text.index('\n')+1]+'\n'+intro+text[text.index('\n')+1:].lstrip('\n')
m=re.search(r'### q048\n.*?(?=\n### q|\Z)',text,re.S);assert m
block='''### q048

**048. Federal Register — reviewed 13 November 2026**

Workgroup: `optima-collected-data`, us-east-1, AwsDataCatalog, result reuse off. Listings and full notices have separate source keys and record kinds. Full notice text/provisions are in `payload.data.enrichment`; oversized complete extractions are linked through `full_extraction_source`.

```sql
SELECT source_key, record_kind, source_record_id, ingested_at,
       raw_completeness_status,
       json_extract(labelled_json, '$.payload.data') AS provider_data,
       json_extract(labelled_json, '$.raw_artifacts') AS original_evidence
FROM optima_metadata_engine.source_observations
WHERE source_key IN ('federal_register','federal_register_documents')
LIMIT 25;
```
'''
text=text[:m.start()]+block+text[m.end():]
table=re.search(r'^\| 048 \|.*$',text,re.M)
if table:
 columns=table.group().split('|');columns[3]=' Reviewed 13 November 2026; daily/historical capture and m7 document/metadata schedules checked; both streams enabled '
 columns[5]=' YES — verified listings and full notices — [SQL](#q048) '
 columns[6]=' Continue existing queues; scoped raw/SQL review complete; current-law/application interpretation remains separate. '
 text=text[:table.start()]+'|'.join(columns)+text[table.end():]
status.write_text(text)
print('Federal Register entry 48 marked reviewed.',stamp)
