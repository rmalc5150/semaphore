import json,re,hashlib,shutil
from pathlib import Path
from datetime import datetime,timezone
P=Path(__file__).parent;root=P.resolve().parents[1]
entries=json.loads((P/'entries.json').read_text());before=json.loads((P/'before.json').read_text());staged=json.loads((P/'staged-originals.json').read_text());formats=json.loads((P/'small-format-checks.json').read_text())
reasons={
91:'The collector followed NDB discovery pages without selecting native workbooks. A complete official XLSX is now archived; ZIP member CRCs, four worksheets and worksheet XML passed the bounded sample check.',
92:'The homepage is a JavaScript discovery page; the announcement endpoint requires POST. The new collector pairs complete native index rows with original PDFs. One seven-page PDF and its native index row passed sample validation.',
93:'The original statistical HTML releases were misclassified as discovery pages. The repair preserves substantive releases and all same-directory figures. An October 2026 release and nine original figures are archived.',
94:'The old route followed navigation and unrelated binary assets. The staged scope selects original MIIT electronics/battery statistical releases. A native January–August 2026 release is archived.',
95:'Genuine short statistical releases were treated as discovery-only pages. The staged validator accepts the complete official release and requires its original table figure. Both are archived; the PNG passed CRC/structure checks.',
96:'The old discovery route did not acquire substantive NHSA notices and attachments. A native 2026 catalogue notice is archived, and its official linked PDFs are identified. The notice alone does not prove the linked medicine catalogues were captured.',
97:'The former route archived a navigation-heavy export-control page rather than a formal notice. The staged parser rejects generic site titles and uses a substantive official MOFCOM notice. One complete notice is archived.',
98:'The collector saved OpenDART index rows without original filing documents. The replacement now downloads the receipt-specific original ZIP. The tested ZIP is intact, but its provider XML is malformed at line 753 and correctly fails strict document validation. Preserve the original and test additional filings; do not repair provider bytes silently.',
99:'The enabled registry flag was misleading: there is no collector plan, historical route, metadata job inventory or configured KOSIS credential. Owner action: obtain an issued KOSIS OpenAPI key, add it as field kosis to the existing dataSourceAPIkeys-PSTzff secret without replacing other fields, and identify the intended tables/indicators. Do not paste the key into chat.',
100:'The native issuer/revenue JSON arrays were wrongly treated as filings that required a primary PDF. Two complete native TWSE arrays are archived. The staged converter retains every original row, company identifier, ROC reporting month and native units. These are current snapshots, not a full MOPS historical filing archive.',
101:'The route crawled the interactive customs website instead of the official public CSV. The complete monthly aggregate clearance CSV is archived. The staged converter preserves native year/month and NTD-thousand fields; this is not detailed HS/country trade.',
102:'The old homepage crawl did not follow monthly mineral-production report files. The June 2026 original PDF is archived. A bounded archive plan is prepared; older year index URLs and monthly completeness still need worker checks.',
103:'Sampled accepted legacy rows point to site JPEGs rather than mineral statistics. New scope rejects images and follows the Geological Agency resource-and-reserve reports. Current report links are identified; the original report download and metadata proof still require the worker. Existing accepted rows have not been mass deleted or retracted.',
104:'The ANM data host moved, its TLS response omits an intermediate certificate, and its CSV files use CP1252. The exact provider-specific CA bundle was independently verified to trusted roots with hostname/server-purpose checks; TLS verification stays enabled. Three complete native production CSVs are archived. Full worker parsing and publication remain pending.',
105:'The old route accepted an unrelated protocol-manual PDF. The new plan uses official CFEM revenue CSV chunks at the moved data host, with verified TLS and CP1252 support. Each chunk is about 67–100 MB; full capture/validation is deferred to m7. The 325 MB combined file is excluded from the 128 MB capture lane.'}
source_by_number={}
for source,data in before.items():
 if not isinstance(data,dict)or 'source'not in data:continue
 n=json.loads(data['source']['catalog_entries'])[0];source_by_number[n]=source
rows=[]
for n in range(91,106):
 source=source_by_number[n];raw=[r['record']['artifact_uri']for r in staged.get(source,[])]
 if n in (92,98):
  probe=json.loads((P/('cninfo-original-probe.json'if n==92 else'dart-original-probe.json')).read_text());raw=['s3://data-collection-059416028963-us-east-1-an/research-data/'+probe['artifact']['key']]
 rows.append({'entry':n,'source':source,'review_status':'unreviewed_owner_configuration_required'if n==99 else'unreviewed_worker_deployment_and_end_to_end_proof_pending','cause_and_findings':reasons[n],'provider_original_s3_uris':raw,'metadata_control_at_audit':before[source]['source'],'sample_format_check':formats.get(source),'daily_historical_status':'No configured lanes'if n==99 else'Existing configured lanes inventoried; corrected routes and runtime deployment have not been activated. Fresh successful daily and historical invocations remain to be proven.'})
manifest={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'overall_status':'prepared_not_completed','reviewed_entries':[],'worker_wake_approval':'pending; do not override the configured sleeping interval','next_earliest_normal_wake_utc':'2026-11-19T02:50:57Z','normal_wake_condition':'after 14 off-hours and at least 26000 queued metadata jobs; otherwise max-off-hours 24','worker_policy_file':str(root/'config/m7-batch-policy.json'),'worker_instance_id':'i-06241bd1c4e91c2fc','worker_actual_type':'c7i.2xlarge','changes_state':'Repository repair code and plans prepared; worker runtimes, source JSON contracts, RDS controls and production publication unchanged. Staged receipts are outside metadata intake.','entries':rows,'validation':{'focused_tests':str(P/'test-results.txt'),'additional_test_limitation':'test_specialist_inputs setUpClass cannot read config/company-universe.v0.5.json under current filesystem ownership; its setup error is preserved separately in tests-universe-fixture-blocked.txt','format_checks':str(P/'small-format-checks.json'),'production_athena_checks':'not yet run for corrected contracts; no source marked reviewed'},'deployment_order':['Obtain explicit approval to wake during the scheduled off interval, or allow the normal bounded batch policy to wake it.','Protect deployment with a bounded lifecycle hold and the batch pause fence; stage and hash-check worker files before resuming payloads.','Install source-scoped capture/metadata code and public certificate into metadata, auxiliary, generic worker roots and affected historical workspaces; preserve all deliberate pauses.','Prepare CNINFO native daily/historical workspaces and dispatchers; preserve per-workspace execution lanes. Install worker daily routes for NDB, Indonesia reports and CFEM, including dispatcher timers and daily drain handling, before excluding them from controller capture.','Validate the real staged files and native rows on m7; capture NHSA attachments, current Indonesia report, CFEM chunks and additional valid DART originals.','Only after raw proof, update scoped 2.0.3 contracts and source controls, back up/supersede obsolete unprocessed discovery-only jobs, and register replacement receipts/batches. Do not blindly retry all legacy inputs.','Run bounded source-fenced metadata processing and publication, then query exact published sample job partitions in Athena.','Verify fresh daily/historical invocation results, preserve explicit coverage limits, and mark only proven entries reviewed.','Remove deployment hold and restore the same batch/lifecycle controller; do not change the cost-saving policy.']}
(P/'review-status.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,default=str)+'\n')
docs=[root/'RAW_DATA_VERIFICATION_SCHEDULE.md',Path('/home/ec2-user/data-source-status-2026-10-26.md')]
backup=P/'documentation-before';backup.mkdir(exist_ok=True)
for path in docs:
 saved=backup/path.name
 if not saved.exists():shutil.copy2(path,saved)
 text=path.read_text()
 if path.name=='RAW_DATA_VERIFICATION_SCHEDULE.md':
  for r in reversed(rows):
   n=r['entry'];pattern=rf'(?m)^- \[[ x]\] \*\*{n}\. .*?(?=^- \[[ x]\] \*\*\d+\.|^### Day |\Z)';match=re.search(pattern,text,re.S|re.M);assert match,n
   block=match.group(0);block=re.sub(r'\n  Review \(18 November 2026\):.*?(?=\n\n|\Z)','',block,flags=re.S)
   note='\n  Review (18 November 2026): **not reviewed — '+('owner configuration required'if n==99 else'worker validation pending')+'**. '+r['cause_and_findings']+' '
   if n!=99:note+='Corrected daily/historical capture, metadata labelling and Athena publication have not yet been verified; m7 is in its deliberately scheduled off interval and a wake exception is awaiting approval. '
   if r['provider_original_s3_uris']:note+='Actual staged provider originals: '+', '.join('`'+u+'`'for u in r['provider_original_s3_uris'])+'. '
   note+='Evidence and remaining work: [review status](repair-notes/2026-11-18-entries-91-105/review-status.json). Owner RM/SQL notes above are retained.\n\n'
   text=text[:match.start()]+block.rstrip()+'\n'+note+text[match.end():]
 else:
  for r in rows:
   n=r['entry'];heading=f'### q{n:03d}\n'
   if heading not in text:
    assert n==99
    nextheading='### q100\n';new=heading+'\n**099. South Korea KOSIS statistical OpenAPI**\n\nNo configured collector or verified observations. The API credential and table scopes are missing.\n\n';text=text.replace(nextheading,new+nextheading,1)
   start=text.index(heading)+len(heading);note='\nReview (18 November 2026): **not reviewed**. '+r['cause_and_findings']+' Corrected production Athena results are not yet verified. [Detailed status]('+str((P/'review-status.json').resolve())+').\n'
   text=text[:start]+note+text[start:]
 path.write_text(text)
files=['regional_source_review.py','provider_tls.py','config/anm-intermediate.pem','filing_originals_capture.py','public_source_scope.py','public_source_capture.py','additional_source_apis.py','specialist_inputs.py','metadata_engine/regional_public.py','metadata_engine/regional_filings.py','metadata_engine/evidence.py','metadata_engine/worker.py','metadata_engine/controller.py','metadata_engine/source_policies.py','metadata_engine/labelling.py','reviewed_metadata_publication.py','constellation/public_daily.py']
packet={'status':'prepared_only_do_not_activate_without_worker_proof','files':{f:hashlib.sha256((root/f).read_bytes()).hexdigest()for f in files},'plans':['public-source-updates.json','native-source-updates.json','worker-daily-route-additions.json','policies.json'],'production_source_config_not_updated':True,'worker_drain_note':'New worker daily route dispatchers must continue daily even when yesterday’s crawl drained; do not use the historical permanent-drain shortcut for these units. All prepared new daily routes remain execution_enabled=false.'}
(P/'deployment-plan.json').write_text(json.dumps(packet,indent=2)+'\n')
print('Annotated 15 entries; none marked reviewed. Prepared deployment and evidence manifests.')
