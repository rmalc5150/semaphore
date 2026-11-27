"""Reconcile verified operational evidence into entries 51 and 52."""
import json,re
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

P=Path(__file__).parent;root=P.parents[1]
def read(name):return json.loads((P/name).read_text())
counts=read('counts-final.json');assert counts['state']=='SUCCEEDED'
rows={r['Data'][0]['VarCharValue']:[c.get('VarCharValue')for c in r['Data']]for r in counts['rows'][1:]}
assert set(rows)=={'un_comtrade','doe_storage_program','doe_storage_documents','doe_storage_benchmarks','doe_storage_funding'}
assert all(int(r[1])>0 and r[1]==r[3]for r in rows.values())
for name in ('preview-comtrade.json','preview-doe.json','public-report-sql.json'):
 d=read(name);assert d['state']=='SUCCEEDED' and len(d['rows'])>1
validation=read('failed-batch-validation.json');assert len(validation)==53 and all(r['status']=='verified'for r in validation)
historical=read('historical-validation.json');assert sum(r['status']=='verified'for r in historical)==4
controls=read('final-controls.json');assert all(s['state']=='enabled'and s['consecutive_raw_failures']==0 for s in controls['sources'])
assert len(controls['former_failed_batches'])==20 and all(r['state']=='accepted'and r['publication_status']=='published'for r in controls['former_failed_batches'])
assert all(r['state']=='uncommitted'for r in controls['remaining_source_failures'])
assert 'Ran 61 tests'in(P/'tests.log').read_text()and 'OK'in(P/'tests.log').read_text()
workers={}
for host in ('t3','m7'):
 d=read('worker-check-'+host+'.json');units=d['units']
 assert not d['failed']
 assert not[u for u,v in units.items()if u.endswith('.timer')and v.get('UnitFileState')=='enabled'and v['ActiveState']!='active']
 workers[host]={'snapshot':'worker-check-'+host+'.json','checked_at_epoch':d['checked_at_epoch'],
  'enabled_active_timers':sum(u.endswith('.timer')and v.get('UnitFileState')=='enabled'for u,v in units.items()),'failed_units':d['failed']}
 if host=='m7':
  workers[host]['historical_executors']=sum(u.startswith(('constellation-backfill@','constellation-legacy-worker@','constellation-public-worker@'))and v['ActiveState']=='active'for u,v in units.items())
  assert workers[host]['historical_executors']==15
  for timer in ('optima-metadata-worker.timer','optima-metadata-worker-extra.timer','optima-metadata-streaming.timer'):
   assert units[timer]['ActiveState']=='active'
database=read('database-audit.json');audit_counts=Counter()
for k,v in database['counts'].items():lane,source,state=k.split('|');audit_counts[lane+' '+state]+=v
migration=read('migration.json');scope=read('public-scope-reconciliation.json');inventory=read('public-receipt-inventory.json')
publisher=read('recurring-publisher-verified.json');assert 'Finished optima-m7-aux-reviewed-metadata-publication.service'in publisher['journal']
assert 'reviewed-metadata.lock'in publisher['properties']
frontiers=read('capture-frontiers.json');daily=read('daily-frontier-verified.json');assert daily['captured_urls']>=1 and daily['failed_urls']==0
assert frontiers['historical'].get('done',0)>=1 and not frontiers['historical'].get('failures')
stamp=datetime.now(timezone.utc).isoformat();doe_total=sum(int(r[1])for s,r in rows.items()if s!='un_comtrade')
proof={'reviewed_at_utc':stamp,'catalog_entries':[51,52],'status':'reviewed_scoped_raw_metadata_athena_pipeline',
 'source_controls':controls['sources'],'sql_snapshot':rows,'athena_summary_query_id':counts['query_id'],
 'causes':['Generic validation rejected Comtrade native rows and DOE HTML/extractions.','DOE document/technical/funding companion streams lacked source contracts.','Public DOE receipts lacked a source-specific document adapter; archive discovery followed unrelated DOE navigation.','Bounded metadata publication contended with larger auxiliary publishers.'],
 'repairs':['Exact official Comtrade row, identity, dimensions, year, count and cap validation.','DOE original checksums, reparse, documented composite identities and exact saved extraction/fact/table matching.','Validated public storage documents feed metadata; discovery and unrelated administrative/history receipts excluded with originals retained.','Storage main-content discovery and new retained daily/historical frontiers.','Independent lock for the bounded recurring metadata publisher on m7; verified successful pass.'],
 'requeued_old_jobs':len(migration),'distinct_replacement_jobs':len({r['new_job_id']for r in migration}),
 'all_20_previously_failed_batches_accepted_and_published':True,
 'saved_validation':{'selected_inputs_verified':53,'additional_historical_inputs_verified':4,'historical_discovery_receipts_excluded':2,'public_storage_pdf_verified_in_athena':read('public-report-sql.json')['query_id']},
 'scope_exclusions':{'discovery_jobs':sum(r['action']=='discovery_excluded'for r in inventory),'unrelated_public_document_jobs':len(scope['excluded_jobs']),'raw_deleted':False},
 'remaining_target_source_exclusions':controls['remaining_source_failures'],'workers':workers,'tests_passed':61,
 'database_diagnostic':{'started_at':database['started_at'],'finished_at':database['finished_at'],'sources_audited':database['sources_audited'],
  'job_rows_counted':database['job_rows_counted'],'query_metrics':database['query_metrics'],'job_counts':dict(audit_counts),
  'source_controls':dict(Counter(r['state']for r in database['source_controls'])),'report':'database-audit.json',
  'remaining_historical_failure_details':'historical-failure-samples.json','consistency':database['consistency']},
 'scope_limits':['Counts are observation occurrences, not unique trade flows or documents, nor completed history.','Comtrade scope is configured annual reporters/commodities/import-export world totals; not all countries, partners or historical vintages.','DOE original pages/documents and saved technical/funding statements stay distinct; extraction limits and unverified measurements/award/payment claims remain explicit.','Tracking-based DOE enrichment remains retired; its old saved outputs are replayed without restoring the abandoned database.','Other 51 raw-stopped sources, 21 blocked and 34 retryable historical records remain in the diagnostic; no blanket retry or false coverage clearance.'],
 'owner_action_required_for_entries_51_52':False}
(P/'review-complete.json').write_text(json.dumps(proof,indent=2)+'\n')

schedule=root/'RAW_DATA_VERIFICATION_SCHEDULE.md';text=schedule.read_text()
entries={51:f'''- [x] **51. UN Comtrade** (`un_comtrade`) — reviewed 13 November 2026, scoped raw/metadata/Athena pipeline  
  Source enabled under contract 2.0.3. Replaced generic false raw failures with exact official response/row, identity, query-dimension, year and truncation checks. Provider quantities, units, nulls and estimation flags are retained.  
  Verified SQL snapshot: **{rows['un_comtrade'][1]} observations / {rows['un_comtrade'][2]} linked raw batches**, all raw-complete; latest captured input **{rows['un_comtrade'][5]}**. Two older 2021 inputs also passed original-byte and collection-commit checks. Counts are occurrences, not unique trade flows.  
  Scope: configured five reporters, four battery/mineral HS6 commodities, annual imports/exports and world partner totals. Historical route has checkpointed successes and reports its configured target drained; exhaustive coverage and historical vintages are not certified. Daily capture and all enabled schedules checked. No new key/IAM action required.  
  [Working SQL](repair-notes/2026-11-13-comtrade-doe/review-queries.sql) · [Review evidence](repair-notes/2026-11-13-comtrade-doe/review-complete.json).
''',52:f'''- [x] **52. Department of Energy storage program** (`doe_storage_program` and document/technical/funding companions) — reviewed 13 November 2026, scoped raw/metadata/Athena pipeline  
  All four streams enabled under contract 2.0.3. Verified SQL snapshot: **{doe_total} observations**: {rows['doe_storage_program'][1]} program/original-document, {rows['doe_storage_documents'][1]} document-summary, {rows['doe_storage_benchmarks'][1]} technical-evidence and {rows['doe_storage_funding'][1]} funding-evidence rows, all raw-complete for their declared kinds. These are occurrences, not unique documents or certified results.  
  Originals, deterministic reparsing, saved extraction/fact/table mapping and URL/semantic identities are checked. Two older PDFs also passed commit/original checks. The archived long-duration storage report is visible in Athena with its full original PDF and 117,216 extracted characters. Extraction limits remain explicit.  
  Public discovery now follows storage main content and linked official reports, with new retained daily/historical frontiers. Excluded 55 discovery receipts and 25 unrelated DOE history/administrative receipts; originals retained. One old input lacking committed-history evidence remains excluded. Tracking-based enrichment stays retired.  
  Current daily and historical capture, metadata lanes and all enabled schedules checked. The bounded recurring publisher uses an independent lock on m7 and completed successfully. Full archive coverage, normalized performance, recipient allocation and actual payments are not certified.  
  [Working SQL](repair-notes/2026-11-13-comtrade-doe/review-queries.sql) · [Review evidence](repair-notes/2026-11-13-comtrade-doe/review-complete.json).
'''}
for number,entry in entries.items():
 pattern=rf'- \[ \] \*\*{number}\. .*?(?=\n- \[|\Z)';match=re.search(pattern,text,re.S);assert match
 text=text[:match.start()]+entry+text[match.end():]
schedule.write_text(text)

status=Path('/home/ec2-user/data-source-status-2026-10-26.md');text=status.read_text()
intro=f'''\n## November 13 — UN Comtrade and DOE storage reviews completed

**Entries 51 and 52 are reviewed for their scoped raw-validation, metadata and Athena pipelines.** Fixed false generic raw stops, missing DOE companion contracts, the public-document receipt adapter and metadata publication contention. All five source streams are enabled; all 20 formerly failing batches are accepted and published. Replaced 831 old queue entries with 754 distinct contract jobs. **61 tests passed**, plus 53 saved-input validations, four older historical-input checks and an Athena readback of the archived storage report.

Verified SQL snapshot: **{rows['un_comtrade'][1]} Comtrade observations and {doe_total} DOE observations** across program/documents/technical/funding streams, all raw-complete for their declared kinds. Latest Comtrade and program inputs are from November 13; saved DOE companion inputs extend through November 11. Counts are occurrences, not unique flows/documents or complete history. Storage-only discovery now has working daily and historical frontiers; old unrelated files are retained but excluded. The retired tracking-based enrichment stays retired. One old uncommitted DOE input remains excluded.

**All 75 enabled timers and 15 historical executors checked healthy; metadata/streaming lanes active.** The full indexed diagnostic completed: 448,882 job records, 161 metadata sources and 123 historical routes, 494 queries, maximum query time 0.8665 seconds, no query retries. It still records **51 other raw-stopped sources, 21 blocked historical attempts and 34 retryable historical attempts**; these are not cleared by this review. Intentional pauses remain. No new IAM, key or manual restart is needed for entries 51/52. [Working SQL](data-collection-processing/repair-notes/2026-11-13-comtrade-doe/review-queries.sql) · [Review and remaining holds](data-collection-processing/repair-notes/2026-11-13-comtrade-doe/review-complete.json).

'''
pos=text.index('\n')+1;text=text[:pos]+intro+text[pos:]
for number,title,where,note in (
 ('051','UN Comtrade',"source_key = 'un_comtrade'",'Entire provider rows retain original units, nulls and estimation flags; the configured annual trade scope is not all trade.'),
 ('052','Department of Energy storage program',"source_key IN ('doe_storage_program','doe_storage_documents','doe_storage_benchmarks','doe_storage_funding')",'Program pages, originals, technical statements and funding statements have separate record kinds. Full saved extractions are linked; statements are not certified measurements or payments.')):
 block=f'''### q{number}

**{number}. {title} — reviewed 13 November 2026**

Workgroup: `optima-collected-data`, us-east-1, AwsDataCatalog, result reuse off. {note}

```sql
SELECT source_key, record_kind, source_record_id, ingested_at,
       raw_completeness_status,
       json_extract(labelled_json, '$.payload.data') AS provider_data,
       json_extract(labelled_json, '$.payload.extraction_reference') AS saved_extraction,
       json_extract(labelled_json, '$.raw_artifacts') AS original_evidence
FROM optima_metadata_engine.source_observations
WHERE {where}
LIMIT 25;
```

[Verified summary and detail queries](data-collection-processing/repair-notes/2026-11-13-comtrade-doe/review-queries.sql).
'''
 match=re.search(rf'### q{number}\n.*?(?=\n### q|\Z)',text,re.S);assert match
 text=text[:match.start()]+block+text[match.end():]
 table=re.search(rf'^\| {number} \|.*$',text,re.M);assert table
 columns=table.group().split('|');columns[3]=' Reviewed 13 November 2026; current daily/historical capture and metadata/publication checked '
 columns[5]=f' REVIEWED — verified metadata-engine observations — [SQL](#q{number}) '
 columns[6]=' No owner action for the scoped repair; remaining backlog/coverage limits in review evidence '
 text=text[:table.start()]+'|'.join(columns)+text[table.end():]
status.write_text(text)
print('Entries 51 and 52 marked reviewed:',stamp,'SQL counts',rows['un_comtrade'][1],doe_total)
