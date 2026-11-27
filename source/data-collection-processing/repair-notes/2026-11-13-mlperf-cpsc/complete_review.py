import json,re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

P=Path(__file__).parent;root=P.parents[1];counts=json.loads((P/'counts.json').read_text());assert counts['state']=='SUCCEEDED'
rows={r['Data'][0]['VarCharValue']:[c.get('VarCharValue')for c in r['Data']]for r in counts['rows'][1:]}
assert set(rows)=={'mlperf_results','cpsc_recalls'}
for source,r in rows.items():assert int(r[1])>0 and r[1]==r[3]
validation=json.loads((P/'failed-batch-validation.json').read_text());assert len(validation)==13 and all(r['status']=='verified'for r in validation)
assert sum(r['verified_rows']for r in validation)==3028
controls=json.loads((P/'final-controls.json').read_text());assert all(r['state']=='enabled'and r['consecutive_raw_failures']==0 for r in controls['reviewed_sources'])
fresh=json.loads((P/'fresh-cpsc-capture.json').read_text());assert fresh['remaining_jobs']==0 and fresh['outcomes'][0]['status']=='complete'and fresh['outcomes'][0]['records']==7
for name in ('sample-mlperf_results','sample-cpsc_recalls','mlperf-kinds'):
 r=json.loads((P/(name+'.json')).read_text());assert r['state']=='SUCCEEDED'and len(r['rows'])>1
assert 'Ran 65 tests'in(P/'tests.log').read_text()and 'OK'in(P/'tests.log').read_text()
workers={}
for host in ('t3','m7'):
 path=sorted((root/'constellation/migration').glob('worker-check-20261113*-'+host+'.json'))[-1];d=json.loads(path.read_text())
 assert not [u for u,v in d['units'].items()if u.endswith('.timer')and v.get('UnitFileState')=='enabled'and v['ActiveState']!='active']
 assert not [f for f in d['failed']if 'ec2-code-backup.service'not in f]
 workers[host]={'snapshot':str(path),'checked_at_epoch':d['checked_at_epoch'],'failed':d['failed'],'enabled_timers':sum(u.endswith('.timer')and v.get('UnitFileState')=='enabled'for u,v in d['units'].items())}
 if host=='m7':
  n=sum(u.startswith(('constellation-backfill@','constellation-legacy-worker@','constellation-public-worker@'))and v['ActiveState']=='active'for u,v in d['units'].items());assert n==15
  workers[host]['historical_executors']=n;workers[host]['recent_kernel_oom']=d['recent_kernel_oom']
  for u in ('optima-metadata-worker.timer','optima-metadata-worker-extra.timer'):assert d['units'][u]['ActiveState']=='active'
stamp=datetime.now(ZoneInfo('Europe/Madrid')).isoformat()
proof={'reviewed_at':stamp,'entries':[46,47],'review_status':'reviewed_scoped_pipeline','scope':'configured original raw records, metadata validation and verified SQL publication; not complete historical collection or a rights/entity-resolution review',
       'source_controls':controls['reviewed_sources'],'remaining_reviewed_source_jobs':controls['remaining_source_jobs'],
       'raw_validation':{'cases':13,'rows':3028,'passed':True},'athena_query_id':counts['query_id'],'sql_counts':rows,'tests_passed':65,'worker_health':workers,
       'all_source_controls':controls['all_source_controls'],'daily_collection_enabled':controls['daily_enabled'],'historical_control':controls['historical_control'],
       'other_repairs':{'eodhd':'added only the required plan-manifest S3 prefix; existing effective grants retained; successful restart','patents_daily':'retried after conditional checkpoint contention; successful restart'},
       'cpsc_fresh_capture_records':7,'github_backup':'Previously deferred; not retried in this task'}
(P/'review-complete.json').write_text(json.dumps(proof,indent=2)+'\n')

schedule=root/'RAW_DATA_VERIFICATION_SCHEDULE.md';text=schedule.read_text()
names={'mlperf_results':(46,'MLPerf benchmark results'),'cpsc_recalls':(47,'CPSC recalls')}
limits={'mlperf_results':'Published summary results, original supporting files and Git-tree inventories have distinct record kinds. Two older batches remain uncommitted and excluded because commit evidence is missing; current processing continues. This does not certify all benchmark artifacts, comparisons or historical availability.',
        'cpsc_recalls':'Entire official recall records, including nested products, hazards and remedies, match original API responses. The overnight network backoff was cleared after normal transport recovery; today’s capture completed with 7 records. Image URLs are retained; image downloads, all incidents and historical vintages are outside this review.'}
for source,(number,name)in names.items():
 match=re.search(r'- \[[ xX]\] \*\*'+str(number)+r'\. .*?(?=\n- \[|\n###|\Z)',text,re.S);assert match
 r=rows[source];entry=f'- [x] **{number}. {name}** (`{source}`) — reviewed 13 November 2026, scoped pipeline verification  \n'
 entry+=f'  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source={source}/`; checksummed originals linked in each record.  \n'
 entry+=f'  Source enabled under contract 2.0.3. SQL verified **{r[1]} row occurrences / {r[2]} linked raw batches**, all {r[3]} raw-complete for the declared record kind. Counts are observations, not unique recalls/results or completed history.  \n'
 entry+='  '+limits[source]+'  \n'
 entry+=f"  Athena SQL: `SELECT source_key, count(*) AS observations, count(DISTINCT raw_s3_uri) AS linked_raw_objects, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(ingested_at) AS first_ingested_at, max(ingested_at) AS latest_ingested_at FROM optima_metadata_engine.source_observations WHERE source_key = '{source}' GROUP BY source_key;`  \n"
 entry+='  All 3,028 saved validation rows tested across both sources passed; 65 tests passed. Capture/metadata/publication and all 15 historical executors checked, with enabled timers active. [Review evidence](repair-notes/2026-11-13-mlperf-cpsc/review-complete.json) · [SQL examples](repair-notes/2026-11-13-mlperf-cpsc/review-queries.sql).\n'
 text=text[:match.start()]+entry+text[match.end():]
schedule.write_text(text)

status=Path('/home/ec2-user/data-source-status-2026-10-26.md');text=status.read_text();title='## November 13 — MLPerf and CPSC raw-data reviews completed'
intro=title+'\n\nEntries **46 (`mlperf_results`) and 47 (`cpsc_recalls`) are reviewed for their current raw-validation/metadata/SQL pipelines**. Corrected MLPerf original-host validation, exact result/file/tree matching, legacy CSV identities and CPSC original recall-row validation. Both sources are enabled under immutable contract 2.0.3; 70 old queued/failing jobs were superseded by new contract jobs with original evidence retained. **All 3,028 saved validation rows tested passed; 65 focused tests passed.**\n\n'
intro+=f"Verified Athena snapshot: **{rows['mlperf_results'][1]} MLPerf row occurrences and {rows['cpsc_recalls'][1]} CPSC row occurrences**, all raw-complete for their declared record kinds. MLPerf inventories and supporting files remain distinct from benchmark results. CPSC captured seven records today after the overnight network backoff recovered. Two old MLPerf batches remain excluded for missing commit evidence; full archive completion, historic availability, image downloads, rights and legal-entity matching are not certified.\n\n"
intro+='All 15 historical executors, metadata lanes and enabled collection timers were checked. Repaired EODHD plan-manifest IAM access and successfully retried patent daily checkpoint contention. Other source validation holds and deliberate pauses remain; the previously deferred GitHub backup was not retried. No IAM edit or manual restart is required from you. [Review evidence](data-collection-processing/repair-notes/2026-11-13-mlperf-cpsc/review-complete.json) · [working SQL examples](data-collection-processing/repair-notes/2026-11-13-mlperf-cpsc/review-queries.sql).\n\n'
if title not in text:text=text[:text.index('\n')+1]+'\n'+intro+text[text.index('\n')+1:].lstrip('\n')
for source,(number,name)in names.items():
 pattern=r'### q'+str(number).zfill(3)+r'\n.*?(?=\n### q|\Z)';match=re.search(pattern,text,re.S);assert match
 note='Published benchmark results; file inventories and supporting logs are separate kinds.'if source=='mlperf_results'else'Full original recall fields and evidence; image URLs do not imply downloaded images.'
 sql="SELECT source_key, record_kind, source_record_id, ingested_at,\n       raw_completeness_status,\n       json_extract(labelled_json, '$.payload.data') AS provider_data,\n       json_extract(labelled_json, '$.raw_artifacts') AS original_evidence\nFROM optima_metadata_engine.source_observations\nWHERE source_key = '"+source+"'\n"+("  AND record_kind = 'benchmark_result'\n"if source=='mlperf_results'else'')+'LIMIT 25;'
 block=f'### q{number:03d}\n\n**{number:03d}. {name} — reviewed 13 November 2026**\n\n{note} Workgroup: `optima-collected-data`, us-east-1, AwsDataCatalog, result reuse off.\n\n```sql\n{sql}\n```\n'
 text=text[:match.start()]+block+text[match.end():]
status.write_text(text)
print('Marked entries 46 and 47 reviewed; updated SQL examples and retained explicit coverage gaps.',stamp)
