"""Update only entries 76–90; retain owner notes and earlier review history."""
import json,re,hashlib
from pathlib import Path
from datetime import datetime,timezone
P=Path(__file__).parent;root=P.parents[1];entries=json.loads((P/'entries.json').read_text());sqlproof=json.loads((P/'verified-sample-sql.json').read_text());assert sqlproof['state']=='SUCCEEDED';header=[v['VarCharValue']for v in sqlproof['rows'][0]['Data']];rows=[dict(zip(header,[v.get('VarCharValue')for v in r['Data']]))for r in sqlproof['rows'][1:]];counts={r['source_key']:r for r in rows};ids=json.loads((P/'verified-sample-job-ids.json').read_text());before=json.loads((P/'before.json').read_text());after=json.loads((P/'after.json').read_text());bucket='data-collection-059416028963-us-east-1-an';base='s3://'+bucket+'/research-data/';reviewed={76,77,78,80,81,82,83,84,85,86,87,89,90}
notes={
76:'Native NASA measurements were checked against the saved complete provider response, including parameter values and units. Daily capture and the configured historical scopes are healthy; the eight reference locations are a bounded geographic scope.',
77:'The missing folder was a locator error. Daily GeoJSON originals live under public-capture/objects/usgs_earthquakes; historical originals are linked from native job manifests. All 3,951 registered historical query partitions succeeded and the seven current daily windows completed; this does not certify every possible earthquake query or original vintage.',
78:'Added official UCDP GED ZIP and candidate CSV acquisition, checksums, whole-archive CRC/structure checks, metadata validation and publication. Daily and historical public-file routes completed their present frontiers. Public downloads work without the separately authenticated UCDP API.',
79:'Citation and abstract processing is repaired and published under contract 2.0.3; all 400 records from the four former failed batches matched saved Atom originals. These are metadata/abstracts, not full papers. Full-text acquisition remains outstanding, so this entry is not fully reviewed. An older daily snapshot stopped on duplicate provider IDs; its replacement query completed with 1,647 records, all were validated against native Atom originals, and only the exact incomplete metadata input was superseded. Original bytes remain retained; replacement metadata processing is queued.',
80:'Replaced catalogue-only input with native, full-field prescribing rows. Daily collection prefers the current SNOMED catalogue, whose latest probed release is August 2026; the retired catalogue remains available for older months. Verified 1,000 January-2016 rows and 1,000 August-2026 rows. Pagination continues; neither month nor the full history is claimed complete.',
81:'Reviewed as an access layer: successful CDA-AMC retrieval and strict base64-PDF recovery verified the gateway. Standalone raw folders and source_observations rows are not applicable; dependent sources own their original artifacts and observations.',
82:'Located and verified the complete saved WSTS billings PDF and restored scoped native-file publication. The old August URL now returns 404, while its archived original remains intact; current daily and historical index discovery completed without download failures.',
83:'Moved discovery to the working official SEAJ index and followed only its worldwide SEMS rows, excluding Japan-only and FPD rows. The joint SEMI/SEAJ worldwide PDFs and back-number PDF are captured; daily and historical crawls are healthy. Paid detailed WWSEMS products are excluded.',
84:'Rejected images and discovery pages as reports; verified the complete public 2025 World Robotics executive-summary PDF and published its native-file metadata. Daily and historical discovery continue. This does not assert a paid full database or that the 2025 summary is a 2026 release.',
85:'Verified the actual Snapshot of Global PV Markets 2026 PDF, excluded unrelated technical files, and replaced the broken trends index with the working publications index. Daily and historical capture are healthy; additional public reports continue through the queue.',
86:'Restricted discovery to benefit-assessment cases and original dossier/assessment PDFs. Verified an original IQWiG/G-BA benefit-assessment PDF and its published metadata. Daily and historical discovery continue; no clinical or reimbursement interpretation is inferred.',
87:'Fixed HAS relative links, native CP1252/dollar-quoted CSV validation, and its headerless CT-to-opinion URL export. SMR/ASMR originals and a final committee-opinion PDF are verified and published. All daily download errors recovered. Discovered 10,490 opinion links and restored about 5,000 within the existing frontier cap; historical processing is active and full coverage remains open.',
88:'Deliberate owner pause preserved. NICE capture and AI processing were not resumed and no fresh provider request was made. The existing licensed API, cybersecurity review and owner authorization requirements remain; no completed review is claimed.',
89:'Fixed gateway base64 PDFs that had been mislabelled HTML, preserving the original gateway wrapper separately. Verified and published a final CDA-AMC reimbursement recommendation PDF as well as the separately labelled patient/clinician input. Daily and historical public-file crawls completed their current frontiers; exhaustive review history and clinical interpretation are not asserted.',
90:'Corrected the provider download host, catalogue/document classification and fresh public download-link resolution. Verified the complete 2025 Open Medic ZIP, checksum and every member CRC. Daily and historical capture are active. SQL rows represent validated original annual dataset files; individual medicine/cost-row extraction is a separate downstream step.'}

def sql(entry):
 n=entry['entry'];source=entry['source']
 if n==81:return '-- Decodo is a retrieval access layer; standalone source rows are not applicable.'
 contract='2.0.2'if n in (76,77)else'2.0.3';where="source_key = '"+source+"'"
 if n!=88:where+=" AND contract_version = '"+contract+"' AND job_id IN ("+', '.join(repr(x)for x in ids[source])+")"
 return 'SELECT source_key, dataset, count(*) AS observations, count_if(raw_completeness_status = \'complete\') AS complete_raw_observations, min(json_extract_scalar(labelled_json, \'$.raw_artifacts[1].s3_uri\')) AS provider_original_s3_uri FROM optima_metadata_engine.source_observations WHERE '+where+' GROUP BY source_key, dataset;'
locators={}
for entry in entries:
 n=entry['entry'];source=entry['source'];loc={'source':source,'entry':n,'sql_scope':'At most five published jobs; representative verification, not a complete inventory.'}
 if source in counts:loc.update(provider_original_example=counts[source]['provider_original_s3_uri'],published_job_ids=ids[source])
 if n in (77,79):
  sample=before[source]['samples'][0];loc.update(historical_manifest='s3://'+bucket+'/'+sample['input_key'],historical_original=sample['record']['pages'][0]['raw']['uri'],daily_original_prefix=base+'constellation-backfill/public-capture/objects/'+source+'/')
 elif n in (76,80):loc['original_prefix']=base+'source_documents/'+source+'/';loc['committed_row_prefix']=base+'raw/source='+source+'/'
 elif n==81:loc['scope']='Access layer; use dependent-source originals.'
 elif n==88:loc['scope']='Owner paused; no new acquisition.'
 else:loc['original_prefix']=base+'constellation-backfill/public-capture/objects/'+source+'/'
 locators[source]=loc
(P/'raw-locators.json').write_text(json.dumps(locators,indent=2)+'\n')

def original_location(entry):
 n=entry['entry'];source=entry['source'];loc=locators[source]
 if n in (77,79):return '`'+loc['daily_original_prefix']+'` (daily); historical example: `'+loc['historical_original']+'`.'
 if n in (76,80):return '`'+loc['original_prefix']+'` (provider originals); `'+loc['committed_row_prefix']+'` (committed row batches).'
 if n==81:return 'Not applicable — retrieval access layer; originals belong to dependent sources.'
 if n==88:return 'Owner paused; retained evidence only. No new raw material acquired.'
 return '`'+loc['original_prefix']+'`'

def checked_write(path,old,new):
 if new==old:return
 backup=P/'documentation-before'/path.name;backup.parent.mkdir(exist_ok=True)
 if not backup.exists():backup.write_text(old)
 assert path.read_text()==old,'Concurrent documentation edit: '+str(path)
 tmp=path.with_suffix(path.suffix+'.review.tmp');tmp.write_text(new);tmp.replace(path)

path=root/'RAW_DATA_VERIFICATION_SCHEDULE.md';old=path.read_text();text=old
for entry in entries:
 n=entry['entry'];source=entry['source'];pattern=rf'(?ms)^- \[[ x]\] \*\*{n}\. .*?(?=^- \[[ x]\] \*\*\d+\. |\Z)';match=re.search(pattern,text);assert match,(path,n);block=match[0];block=re.sub(r'^- \[[ x]\]', '- [x]'if n in reviewed else'- [ ]',block,count=1)
 block=re.sub(r'(?m)^  Raw S3:.*$',lambda m:'  Raw S3: '+original_location(entry),block)
 state=('**owner_paused** — deliberate pause preserved'if n==88 else'**access_layer** — verified through dependent-source retrieval; no standalone queue'if n==81 else'**enabled** — daily/historical capture and metadata queues checked on 16 November 2026')
 block=re.sub(r'(?m)^  Current collection state:.*$',lambda m:'  Current collection state: '+state+'  ',block)
 block=re.sub(r'(?m)^  Current raw processing:.*$',lambda m:'  Current raw processing: '+notes[n]+'  ',block)
 block=re.sub(r'(?m)^  Athena SQL(?: \(bounded published sample, not a source total\))?:.*$',lambda m:'  Athena SQL (bounded published sample, not a source total): `'+sql(entry)+'`',block)
 block=re.sub(r'(?m)^  Review \(16 November 2026\):.*\n?', '',block)
 status='**reviewed**'if n in reviewed else'**partial — not fully reviewed**'if n==79 else'**not reviewed — intentionally paused**'
 observed='N/A (access layer)'if n==81 else'not run (owner paused)'if n==88 else counts[source]['observations']+' complete published sample rows'
 block=block.rstrip()+'\n\n  Review (16 November 2026): '+status+' — '+observed+'. '+notes[n]+' Evidence: [review report](repair-notes/2026-11-16-entries-76-90/review-report.md). Original owner RM/SQL notes above are retained as the pre-repair observations.\n\n'
 text=text[:match.start()]+block+text[match.end():]
checked_write(path,old,text)

path=Path('/home/ec2-user/data-source-status-2026-10-26.md');old=path.read_text();text=old
for entry in entries:
 n=entry['entry'];source=entry['source'];number=f'{n:03d}';pattern=rf'(?m)^\| {number} \|.*$';assert len(re.findall(pattern,text))==1,n
 state='Reviewed access layer; used by dependent daily/historical capture'if n==81 else'PAUSED — owner licensing/security hold preserved'if n==88 else'Daily and historical enabled; metadata queue enabled'
 visibility='N/A — access layer; no standalone dataset'if n==81 else'Not queried during the pause'if n==88 else'YES — '+counts[source]['observations']+' complete rows in bounded published sample'
 status='Reviewed 16 Nov 2026'if n in reviewed else'Partial; full text outstanding'if n==79 else'Owner pause; not reviewed'
 line='| '+number+' | '+entry['name']+' (`'+source+'`) | '+state+' | '+notes[n]+' | '+visibility+' — [SQL](#q'+number+') | '+status+'; [evidence](data-collection-processing/repair-notes/2026-11-16-entries-76-90/review-report.md). |'
 text=re.sub(pattern,lambda m:line,text)
 scope='Access-layer verification; no standalone query.'if n==81 else'Intentionally paused. Retained-data query shown only; no query was run during this review.'if n==88 else'Verified published sample, up to five jobs; these counts are not the full source inventory. Workgroup: `optima-collected-data`. Public-file sources count validated original files, while NASA/USGS/NHSBSA/arXiv count source rows. Native originals are linked separately from collected envelopes.'
 section='### q'+number+'\n\n**'+number+'. '+entry['name']+'**\n\n'+scope+'\n\n```sql\n'+sql(entry)+'\n```\n\n'
 pattern=rf'(?ms)^### q{number}\n.*?(?=^### q\d+\n|\Z)'
 if re.search(pattern,text):text=re.sub(pattern,lambda m:section,text,count=1)
 else:
  later=re.search(r'(?m)^### q'+f'{n+1:03d}'+r'\n',text);assert later,n;text=text[:later.start()]+section+text[later.start():]
checked_write(path,old,text)

report=['Entries 76–90 were checked on 16 November 2026. Thirteen entries are marked reviewed for the explicit scope below. arXiv remains partial because full papers are not captured; NICE remains deliberately paused.\n',
'The most consequential operational fault was an expired historical controller deadline despite its enable flag being true. Its previous state was saved, its run window was renewed for seven days (to '+datetime.fromtimestamp(after['historical_control']['stop_after_epoch'],timezone.utc).isoformat()+'), and historical dispatch resumed. Existing source pauses were preserved. Heavy validation, metadata processing and publication run on m7; bounded public daily capture remains on t3.\n',
'| Entry | Result | Published SQL verification sample | Finding / remaining scope |','|---|---|---:|---|']
for entry in entries:
 n=entry['entry'];source=entry['source'];result='Reviewed'if n in reviewed else'Partial'if n==79 else'Owner paused';c='N/A'if n in(81,88)else counts[source]['observations'];report.append('| '+str(n)+' '+entry['name']+' | '+result+' | '+c+' | '+notes[n]+' |')
report +=['\nThe SQL verification succeeded with result reuse disabled: query `'+sqlproof['query_id']+'`. It explicitly selects up to five published job partitions per source. Every returned sample row has complete evidence for its declared scope. Public-document counts are file observations, not extracted numeric measurements. Full history, paid datasets, original historical vintages and clinical interpretation are not certified. Legacy 2.0.2 public-report rows are retained for audit and excluded from the repaired-source 2.0.3 verification.\n',
'The initial aggregate across all published partitions exceeded the local 100-second limit and was cancelled. Its queue delay was only 92 ms, so queueing was not the cause. The partition-pruned verification completed. The first detailed RDS audit also hit its 10-second statement limit because its grouped fields required row reads; the completed audit uses covering-index counts and small direct job lookups. These bounded checks avoid claiming that a timeout is an empty dataset.\n',
'All nine repaired public-file sources had zero current daily download failures in the final audit. Remaining frontiers are genuine queued discovery work, including the bounded HAS opinion frontier. Daily source attempt limits are preserved. NHSBSA monthly pagination and arXiv metadata continuations are still running; a completed review does not mean every historical job has drained. The old arXiv duplicate-ID snapshot was retired only after its replacement query committed and all 1,647 records passed original-evidence validation. Its partial bytes and failure state remain retained; replacement metadata continues through the normal queue.\n',
'The final service inventory found no failed optima/constellation units and no inactive enabled timers on either instance. Fifteen historical executors were active on m7. No recent kernel OOM appeared in the 30-minute check. This service check does not certify unreviewed catalogue entries outside 76–90. The detailed inventories and intentional source pauses are in `worker-check-t3.json` and `worker-check-m7.json`.\n',
'Validation: 93 focused tests passed; native artifacts were checked against originals and readback checksums, with PDF structure, CSV row structure and ZIP-member CRC checks where relevant. The four former arXiv failure inputs were checked record-by-record (400 Atom entries); two NHSBSA proof pages contained 1,000 verified native rows each.\n',
'Owner action: none is needed today to keep the repaired routes running. NICE remains subject to its existing licensed API/security approval process. arXiv full-text acquisition needs a separately configured, rights-appropriate bulk/full-text route before entry 79 can be fully reviewed. No new IAM or provider-key change was needed for the repaired public-file routes.\n',
'Useful evidence: [native capture proof](capture-proof.json), [original S3 locators](raw-locators.json), [successful SQL](verified-sample-sql.json), [current source audit](after.json), [source plans and scheduler evidence](source-lanes.json), [queue migration](migration.json), [final opinions](final-opinions.json), [daily recovery](daily-cleanup.json), [HAS frontier repair](has-frontier-repair.json), [test results](test-results.txt).\n',
'Official scope references: [UCDP downloads](https://ucdp.uu.se/downloads/), [current NHSBSA SNOMED dataset](https://opendata.nhsbsa.net/dataset/english-prescribing-dataset-epd-with-snomed-code), [SEAJ worldwide statistics index](https://www.seaj.or.jp/english/statistics/index.html), [HAS native assessment exports](https://www.data.gouv.fr/datasets/evaluation-des-medicaments), [CDA-AMC final recommendation original](https://www.cda-amc.ca/sites/default/files/DRR/2024/SR0793_Uplizna-Final_Rec.pdf), [IEA-PVPS 2026 Snapshot](https://iea-pvps.org/wp-content/uploads/2026/04/Snapshot-of-Global-PV-Markets-2026.pdf).\n']
(P/'review-report.md').write_text('\n'.join(report));(P/'verification.sql').write_text('\n\n'.join('-- '+str(e['entry'])+' '+e['source']+'\n'+sql(e)for e in entries)+'\n');print('Updated 15 entries; marked 13 reviewed; arXiv partial and NICE paused; saved report and SQL.')
