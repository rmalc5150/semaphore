import json,re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
p=Path(__file__).parent;counts=json.loads((p/'counts.json').read_text());rows={r['Data'][0]['VarCharValue']:[d.get('VarCharValue')for d in r['Data']]for r in counts['rows'][1:]};names={'nih_reporter':(38,'NIH RePORTER grants'),'google_patents_bigquery':(39,'Google Patents BigQuery'),'uspto_odp':(40,'USPTO Open Data Portal'),'uspto_assignment_histories':(41,'USPTO assignment histories'),'ted_notices':(42,'Tenders Electronic Daily procurement notices'),'usa_spending':(43,'USAspending federal awards'),'nist_robotics_methods':(45,'NIST robotics methods')}
scopes={
'nih_reporter':'Complete returned NIH project-application records: grant IDs, project numbers, title/abstract, amount, organisation and investigators. Configured topics/organisation candidates; grant proposals and historical API vintages remain separate. One October 9 batch lacks its commit checkpoint and remains uncommitted, with raw files retained.',
'google_patents_bigquery':'Verified bibliographic exports, original completed BigQuery result pages, provider identifiers and typed schema. Patent claims/specification/full text remain uncollected by this route; this review covers the bibliographic pipeline only.',
'uspto_odp':'Verified application bibliography, normalized assignment ledgers, office-action text with original PDFs, and petition-decision PDFs, separately by dataset. Candidate entity links and current legal title remain unverified. Approved application/document exclusions are retained and excluded from full-document observations.',
'uspto_assignment_histories':'Recorded assignment events and the complete returned chain for the eight configured applications. Recorded deed images, all USPTO assignments and legal/current ownership are separate coverage requirements.',
 'ted_notices':'Original notice XML, complete parsed XML trees and provider search metadata for configured CPV scopes. Oversized notices retain ordered content chunks; chunks are not additional notices or awards. The fresh verified notice is 768246-2026. XML retrieval gaps remain separately retryable.',
'usa_spending':'Complete returned selected award-summary fields for named-universe contract candidates. Grant/loan programmes, all recipients, full transactions and full award dossiers are outside this configured route.',
'nist_robotics_methods':'Original NIST robotics pages and a fresh 19-page grasp-performance study PDF with 6,713 extracted text characters. Discovery/project/method/PDF kinds remain explicit. Companion documents use nist_robotics_documents. Graphics, measurements not present in extracted text and historical website vintages are not inferred.'}
md='# NIH, NIST, federal awards, TED and patents — review, 11 November 2026\n\n'
md+='The source queries now return actual Athena records. Generic raw validators had rejected valid original API responses; metadata jobs then stopped before publication. Added source-specific identity/content validation and replayed the saved batches under contract 2.0.3.\n\n'
md+='This is verification of the stated source/dataset pipelines and representative payloads. Historical completion, exhaustive issuer/universe coverage, entity resolution and readiness of every specialist feature remain separate checks.\n\n'
md+='## Verified Athena snapshot\n\n| Source | Observations | Linked collection batches | Raw-complete rows |\n|---|---:|---:|---:|\n'
for key in list(names)+['nist_robotics_documents']:
 v=rows[key];md+=f'| `{key}` | {v[1]} | {v[2]} | {v[3]} |\n'
md+='\nCounts are row occurrences over captures, snapshots and content chunks, not unique grants, patents or awards. `raw_s3_uri` names the committed collection envelope; original API/XML/PDF references and checksums are in `labelled_json.raw_artifacts`. The query ID and full response are in [counts.json](counts.json).\n\n'
md+='## What was checked\n\n'
for key,(_,name)in names.items():md+=f'- **{name}:** {scopes[key]}\n'
md+='\nInspected actual provider payloads, not only status rows or counts. Evidence: `sample-<source>.json`, `fresh.json`, `nist-method-pdf.json`, `odp-datasets.json`, the replay receipts and deployment manifests in this folder.\n\n'
md+='## Ongoing processing\n\nDaily specialist capture: `optima-grants-reviewed-capture.timer` (five-minute continuation). NIH historical capture: `optima-nih-reviewed-historical.timer` (ten-minute continuation). TED/USAspending retain their independently scheduled historical routes. Assignments use the existing authorised controller role with separate daily/historical timers.\n\nGoogle historical and USPTO daily/historical continuation use `optima-patents-reviewed-{google,odp,odp-historical}.timer` (15 minutes). Existing Google per-query and daily billing ceilings remain unchanged. Google is currently collecting historical bibliography; a complete, current global patent-text feed is not verified. NIST retrieves current original documents; older publication dates are not reconstructed historical website snapshots.\n\nMetadata has separate per-source leases, a maximum of two additional workers and bounded batches. `optima-reviewed-metadata-continuation.timer` and `optima-reviewed-metadata-publication.timer` keep these queues moving alongside the general engine. Individual failures retain reports and retry independently. Native specialist publication uses `optima-grants-reviewed-publication.timer`.\n\nA sustained background check exposed slow queue SELECTs and incorrect probe lock ownership. Added online covering indexes, candidate-ID selection, primary-key fetches, ten-second query/lock limits and preservation of the original error if rollback fails. See `database-queue-repair-proposal.md`, `queue-indexes-after.json` and operational verification receipts.\n\n## Your checks\n\nNo new API key, account or permission purchase is required for these configured routes. Open Athena in `us-east-1`, workgroup `optima-collected-data`, and run the source count checks in the main review schedule. Use the bounded examples below to inspect the complete saved metadata columns and original payload.\n\n'
for key,(_,name)in names.items():
 # Bound a random sample to a verified partition to retain the workgroup scan limit.
 jobs=[]
 for filename in ('fresh-replay-jobs.json','dataset-replay-jobs.json'):
  if (p/filename).exists():jobs+=json.loads((p/filename).read_text()).get(key,[])
 if not jobs and (p/key/'migration.json').exists():jobs=json.loads((p/key/'migration.json').read_text())['repair_job_ids']
 
 if key=='nist_robotics_methods':jobs.insert(0,'a665c068b995b4ac142725aa181f6cb93c392185d3154a8c1ccd9d32880ea808')
 jobs=list(dict.fromkeys(jobs))[:4];md+=f'### {name}\n\n```sql\nSELECT *\nFROM optima_metadata_engine.source_observations\nWHERE source_key = \'{key}\'\n'
 if jobs:md+='  AND job_id IN ('+', '.join("'"+j+"'"for j in jobs)+')\n'
 md+='ORDER BY rand()\nLIMIT 20;\n```\n\n'
md+='Payload fields are in `json_extract(labelled_json, \'$.payload.data\')`; original artifacts are in `json_extract(labelled_json, \'$.raw_artifacts\')`. These small sample partitions can return fewer than 20 rows. A snapshot review does not certify the whole historical archive.\n'
(p/'README.md').write_text(md)
# Call this script only after final operational verification succeeds.
if not (p/'operational-verification-passed.json').exists():print('Evidence README written; main reviews await final operational verification.');raise SystemExit(0)
pth=Path('RAW_DATA_VERIFICATION_SCHEDULE.md');text=pth.read_text()
for key,(number,name)in names.items():
 pattern=r'- \[[ xX]\] \*\*'+str(number)+r'\. .*?(?=\n- \[|\n###|\Z)';match=re.search(pattern,text,re.S)
 if not match:raise ValueError('missing schedule entry '+key)
 old=match.group();sql=re.search(r'  Athena SQL: .*',old).group();v=rows[key]
 entry=f'- [x] **{number}. {name}** (`{key}`) — reviewed 11 November 2026, scoped pipeline verification  \n'
 entry+=f'  Raw S3: `s3://data-collection-059416028963-us-east-1-an/research-data/raw/source={key}/`; checksummed originals linked in each record.  \n'
 entry+=f'  Repaired source-specific raw validation and Athena publication. Verified snapshot: **{v[1]} observations / {v[2]} linked collection batches**, all {v[3]} raw-complete for the declared dataset. These are row occurrences, not unique-event or historical-completion counts.  \n'
 entry+='  '+scopes[key]+'  \n'+sql+'  \n'
 entry+='  Daily/historical capture where applicable, metadata and publication continuations verified. **68 tests passed. No new key/account/manual restart action for you.** [Evidence, limitations and bounded sample queries](repair-notes/2026-11-11-grants-patents-procurement/README.md).\n'
 text=text[:match.start()]+entry+text[match.end():]
pth.write_text(text)
status=Path('/home/ec2-user/data-source-status-2026-10-26.md');text=status.read_text();heading='## November 11 — NIH, NIST, awards, TED and patent pipelines reviewed\n\n';intro=heading+'**No new API key, account or manual restart task for you for these seven configured routes.** Your metadata queries now return Athena data. Repaired original-response validators, the USPTO normalized assignment-ledger check, publication and credential placement. Verified fresh API capture, raw evidence and actual Athena payloads, including a NIST method PDF and TED notice XML.\n\n'+'Added bounded metadata continuation/publication and online database queue indexes after the sustained run exposed slow scheduling queries. Restored the older drained NIH historical route under the current scope. Daily/historical patent and assignment continuations use the existing authorised controller role. Approved USPTO document exclusions remain in force. **68 tests passed.**\n\n'+'Review scope matters: Google covers bibliography; full patent text remains a separate gap. USAspending covers selected contract-award summaries for named recipients; assignment histories cover eight applications. One older NIH batch lacks its original commit checkpoint and remains explicitly uncommitted, with raw files retained. Historical completion and every specialist feature are not certified. [Verified counts, exact scope and optional Athena samples](data-collection-processing/repair-notes/2026-11-11-grants-patents-procurement/README.md). This update supersedes older stopped-pipeline/access notes for these sources; unrelated source tasks remain below.\n\n'
if heading not in text:text=text[:text.index('\n')+1]+'\n'+intro+text[text.index('\n')+1:].lstrip('\n')
status.write_text(text);print('Main verification schedule and source status updated.')
