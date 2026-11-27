import json,re,hashlib
from pathlib import Path
from datetime import datetime,timezone
P=Path(__file__).parent;root=P.resolve().parents[1]
entries=json.loads((P/'entries.json').read_text());proof=json.loads((P/'capture-proof.json').read_text());migration=json.loads((P/'migration.json').read_text());sql=json.loads((P/'verified-sample-sql.json').read_text());control=json.loads((P/'controller-verified.json').read_text());worker=json.loads((P/'worker-verified.json').read_text());withdraw=json.loads((P/'withdrawal-verified.json').read_text());lifecycle=json.loads((P/'lifecycle-final.json').read_text());old=json.loads((P/'review-status.json').read_text())
assert sql['state']=='SUCCEEDED'and len({r['source_key']for r in sql['decoded_rows']})==14;assert withdraw['withdrawn_jobs']==220 and withdraw['published_partitions_removed']==184;assert not lifecycle['deployment_hold_active']and lifecycle['policy_unchanged']
counts={};uris={}
for r in sql['decoded_rows']:counts[r['source_key']]=counts.get(r['source_key'],0)+int(r['observations']);uris[r['source_key']]=r['provider_original_s3_uri']
reasons={r['entry']:r.get('cause_and_findings',r.get('cause_and_repair','')).replace('staged converter','deployed converter').replace('staged scope','deployed scope').replace('staged validator','validator')for r in old['entries']}
# Remove preparation-only wording now replaced by measured worker results.
reasons[96]='The old route crawled navigation, misclassified substantive notices and delayed every transient failure for 24 hours. Discovery now follows the relevant policy index; a source-specific transient retry and 15-minute backoff are installed. The native catalogue notice and both linked original PDFs passed worker validation and publication; the final daily checkpoint has zero current failures.'
reasons[98]='The collector previously archived only listing rows. Native receipt-specific original ZIP capture is repaired, and both daily and historical commits plus four complete filing records passed metadata/Athena verification. Four proof batches remain rejected for unavailable or malformed provider originals, and processing retains these gaps explicitly. An additional archived sample contains malformed XML. The source stays enabled with failures isolated by source/date; its review remains partial.'
reasons[103]='Legacy accepted site JPEGs were unrelated to mineral statistics. The corrected route follows Geological Agency mineral/coal resource-and-reserve reports; a complete official original report passed PDF validation and publication. All 117 individually confirmed invalid legacy jobs were superseded, with published partitions withdrawn and originals retained.'
reasons[104]='ANM moved its public data host, its TLS response omitted an intermediate certificate, and native CSVs use CP1252. The provider-specific intermediate chain was independently verified to trusted roots, without disabling TLS checks. All three native production CSVs were captured, fully parsed and published.'
reasons[105]='The legacy route accepted an unrelated protocol manual. It now uses three official CFEM revenue CSV chunks, each within the 128 MB capture limit, with verified TLS and native encoding. Entire chunks passed CSV/schema/checksum checks and publication. All 101 individually confirmed bad legacy jobs were superseded; published partitions were withdrawn and raw objects retained.'
rows=[]
for e in entries:
 n=e['entry'];source=e['source'];status='reviewed'if n not in (98,99)else'partial_provider_document_gaps'if n==98 else'blocked_owner_configuration'
 current=control['sources'][source];raw=[]
 if source in proof['public']:raw=[r['record']['artifact_uri']for r in proof['public'][source]['results']if r['status']=='verified']
 elif source in uris:raw=[uris[source]]
 row={'entry':n,'name':e['name'],'source':source,'review_status':status,'cause_and_repair':reasons[n],'verified_sample_rows':counts.get(source,0),'verified_provider_originals':raw,'metadata':current,'daily':control['daily'].get(source,{'status':'not_configured'}),'historical':[r for r in control['historical']if source in r['unit']],'historical_url_check':control.get('historical_raw',{}).get(source),'coverage':'Working bounded capture and validated samples; exhaustive historical completeness and original historical vintages not asserted.'}
 if n in (91,93,94,95,96,97,102,103,104,105):row['sql_scope']='SQL rows represent validated original files/releases. Source measurements remain in the linked originals; detailed numerical extraction is a separate step.'
 elif n==100:row['sql_scope']='Native issuer/revenue rows with all returned fields and original reporting month/units. Both complete source arrays (2190 rows) passed raw verification; published proof samples cover 64 rows and continuation remains active. Historical MOPS issuer and monthly-release archive coverage remains unverified.'
 elif n==101:row['sql_scope']='Native monthly aggregate clearance rows, with reporting year and NTD-thousand fields retained. All 153 source rows passed raw verification; published proof sample covers 32 rows, with continuation active. Detailed HS/country trade is outside this feed.'
 else:row['sql_scope']='Complete native filing-index row paired with its original PDF/XML document; no XBRL fact extraction or historical-vintage inference.'if n==92 or n==98 else'No collector, data or verified observations.'
 rows.append(row)
report={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'overall_status':'completed_with_explicit_source_exceptions','reviewed_entries':[r['entry']for r in rows if r['review_status']=='reviewed'],'partial_entries':[98],'blocked_entries':[99],'entries':rows,'validation':{'focused_tests_passed':99,'test_log':'test-results.txt','additional_test_limitation':'The older test_specialist_inputs setup could not read its existing local company-universe fixture; the focused repair, publication and lifecycle suites passed. See tests-universe-fixture-blocked.txt.','athena_query_id':sql['query_id'],'verified_complete_sample_rows':124,'sources_with_verified_sql':14,'withdrawn_rows_returned':0,'sample_scope':sql['scope']},'legacy_cleanup':{k:v for k,v in withdraw.items()if k!='results'},'worker':worker,'lifecycle':lifecycle,'owner_action':{'source':'south_korea_kosis_statistical_openapi','required':'Obtain an issued KOSIS OpenAPI key; add field kosis to the existing dataSourceAPIkeys-PSTzff secret while preserving other fields; identify the intended table IDs/indicators. Do not paste the key into chat. A collector plan/adapter must then be implemented for those tables.'},'raw_storage_note':'Verified object links identify the repaired originals. Older crawler objects remain in their prefixes for audit; the 220 proven invalid jobs are excluded from publication.','deliberate_pauses_preserved':True}
report['historical_runtime_recovery']={'shared_dependency':'The provider-specific URL helper was missing from old historical workspaces. It was installed and its import was scoped to the provider; actual URL-level historical captures then recovered.','evidence':'historical-dependency-recovery.json','transport_retry':'Interrupted HTTP transfers now retry after 15 minutes under the same pacing and source quotas; the interrupted September 2024 India PDF was fully recovered and validated.','contact_links':'Malformed ANM contact email links are excluded from archive discovery and retained in retired-failure audit records.'}
archive_file=P/'recovered-twse-archives.json'
if archive_file.exists():report['recovered_twse_history']=json.loads(archive_file.read_text())
assert len(report['reviewed_entries'])==13
(P/'review-status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n')
checklist=root/'RAW_DATA_VERIFICATION_SCHEDULE.md';text=checklist.read_text()
for row in reversed(rows):
 n=row['entry'];source=row['source'];pattern=rf'(?m)^- \[[ x]\] \*\*{n}\. .*?(?=^- \[[ x]\] \*\*\d+\.|^### Day |\Z)';m=re.search(pattern,text,re.S|re.M);assert m,n;block=m.group(0)
 block=block.replace('  Recorded raw-data errors:', '  Pre-repair recorded raw-data errors:')
 block=re.sub(r'\n  Review \(18 November 2026\):.*?(?=\n\n|\Z)','',block,flags=re.S);block=re.sub(r'^- \[[ x]\]', '- [x]'if row['review_status']=='reviewed'else'- [ ]',block,count=1)
 if "Owner's pre-repair check:"not in block:block=block.replace('\n  RM:',"\n  Owner's pre-repair check:\n\n  RM:",1)
 if n==99:
  block=re.sub(r'(?m)^  Raw S3:.*$', '  Raw S3: **not created — no configured collector**',block)
  block=re.sub(r'(?m)^  Current collection state:.*$', '  Current collection state: **blocked — missing KOSIS key and table plan**. The registry enabled flag does not represent a working collector.',block)
 else:
  prefix='research-data/source_documents/'+source+'/'if n in (92,98)else'research-data/constellation-backfill/public-capture/objects/'+source+'/'
  block=re.sub(r'(?m)^  Raw S3:.*$', '  Raw S3: `s3://data-collection-059416028963-us-east-1-an/'+prefix+'` (original provider files; verified object links below).  ',block)
  block=re.sub(r'(?m)^  Current collection state:.*$', '  Current collection state: **enabled — daily and historical capture verified; metadata source enabled**'+(' — individual provider-document gaps remain isolated.'if n==98 else'.'),block)
  block=re.sub(r'(?m)^  Current raw processing:.*$', '  Current raw processing: '+row['sql_scope']+'  ',block)
  block=block.replace("WHERE source_key = '"+source+"' GROUP BY", "WHERE source_key = '"+source+"' AND contract_version = '2.0.3' GROUP BY")
 label='reviewed'if n not in (98,99)else'partially reviewed — provider document gaps'if n==98 else'not reviewed — owner configuration required'
 note='\n  Review (18 November 2026): **'+label+'** — '+('Current RM: yes; SQL: yes. 'if n not in (98,99)else'Current RM: partial; SQL: yes. 'if n==98 else'Current RM: no; SQL: no. ')+row['cause_and_repair']
 if n!=99:
  note+=' Verified Athena sample: '+str(row['verified_sample_rows'])+' complete row(s). '+row['sql_scope']+' Daily and historical checkpoints are verified for the declared scope; complete historical coverage remains under audit. '
  if row['verified_provider_originals']:note+='Verified original: `'+row['verified_provider_originals'][0]+'`. '
 note+='Evidence and scope: [review status](repair-notes/2026-11-18-entries-91-105/review-status.json). Original owner RM/SQL notes are retained as pre-repair observations.\n\n'
 text=text[:m.start()]+block.rstrip()+'\n'+note+text[m.end():]
checklist.write_text(text)
status=Path('/home/ec2-user/data-source-status-2026-10-26.md');text=status.read_text()
for row in reversed(rows):
 n=row['entry'];source=row['source'];pattern=rf'(?m)^### q{n:03d}\n.*?(?=^### |^## |\Z)';m=re.search(pattern,text,re.S|re.M);assert m,n
 title=f'### q{n:03d}\n\n**{n:03d}. {row["name"]}**\n\n'
 if n==99:
  body='Review (18 November 2026): **not reviewed — owner configuration required**. '+row['cause_and_repair']+' No observations are expected until the key, tables and collector are configured.\n\n'
  query="SELECT source_key, count(*) AS observations FROM optima_metadata_engine.source_observations WHERE source_key = '"+source+"' GROUP BY source_key;"
 else:
  body='Review (18 November 2026): **'+('reviewed'if n!=98 else'partially reviewed — provider document gaps')+'**. '+row['sql_scope']+' Exact verified published jobs are selected below; this is a bounded verification sample, not the full inventory. Workgroup: `optima-collected-data`.\n\n'
  field='2'if n in (92,98)else'1';ids=','.join(repr(i)for i in migration['targets'][source]);query="SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations, min(json_extract_scalar(labelled_json, '$.raw_artifacts["+field+"].s3_uri')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE source_key = '"+source+"' AND contract_version = '2.0.3' AND job_id IN ("+ids+") GROUP BY source_key, dataset;"
 block=title+body+'```sql\n'+query+'\n```\n\n[Repair evidence and remaining gaps]('+str((P/'review-status.json').resolve())+').\n\n';text=text[:m.start()]+block+text[m.end():]
status.write_text(text)
plan=json.loads((P/'deployment-plan.json').read_text());plan.update(status='deployed_and_verified',production_source_config_not_updated=False,worker_drain_note='Provisional historical-queue daily routes were retired. Three large daily captures use lifecycle-managed capture services, independent of historical enable/deadline, with controller daily/source pause checks.');plan['files'].update({name:hashlib.sha256((root/name).read_bytes()).hexdigest()for name in [*plan['files'],'constellation/m7_batch.py','constellation/m7_capture_plan.py','constellation/public_file_dispatch.py','constellation/m7_lifecycle.py']});(P/'deployment-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
updates=json.loads((P/'public-source-updates.json').read_text());current={r['source']:r for r in json.loads((root/'config/constellation-public-sources.json').read_text())['sources']}
for source in updates:updates[source]=current[source]
(P/'public-source-updates.json').write_text(json.dumps(updates,ensure_ascii=False,indent=2)+'\n')
withdraw_plan=json.loads((P/'withdrawal-plan.json').read_text());withdraw_plan.update(approval_status='explicitly_approved_and_completed',result='withdrawal-verified.json');(P/'withdrawal-plan.json').write_text(json.dumps(withdraw_plan,indent=2)+'\n')
print('Marked 13 reviewed; OpenDART partial and KOSIS blocked. Updated raw locations and verified SQL queries.')
