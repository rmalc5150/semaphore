"""Record scoped raw/SQL reviews without clearing unrelated queue findings."""
import json,re
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

P=Path(__file__).parent;ROOT=P.parents[1]
SOURCES={50:('usgs_minerals','USGS minerals'),53:('eia_battery_generators','EIA battery generators'),
 55:('eia_retail_prices','EIA retail prices'),56:('caiso_prices','California ISO prices'),
 57:('bls_wages','BLS wages'),58:('ror_institutions','Research Organization Registry institutions')}
def read(name):return json.loads((P/name).read_text())
raw=read('raw-validation.json');assert len(raw)==12 and all(r['status']=='verified'and r['collection_commit_verified']for r in raw)
assert Counter(r['source']for r in raw)==Counter({s:2 for s,_ in SOURCES.values()})
counts=read('metadata-counts.json');assert counts['state']=='SUCCEEDED'
totals={r['Data'][0]['VarCharValue']:[c.get('VarCharValue')for c in r['Data']]for r in counts['rows'][1:]}
assert set(totals)=={s for s,_ in SOURCES.values()}
assert all(int(r[1])>0 and r[1]==r[2]for r in totals.values())
before=read('before.json');queries={}
for number,(source,title)in SOURCES.items():
 for prefix in ('sample-','metadata-preview-'):
  d=read(prefix+source+'.json');assert d['state']=='SUCCEEDED'and len(d['rows'])>1
  queries[prefix+source]={'query_id':d['query_id'],'state':d['state'],'returned_rows':len(d['rows'])-1,'sql':d['sql']}
stamp=datetime.now(ZoneInfo('Europe/Madrid')).isoformat()
findings={s:{'source_control':before[s]['source'],'job_counts':before[s]['counts'],
 'remaining_findings':[{'job_id':j['job_id'],'state':j['state'],'reason':j['reason'],'input_key':j['input_key']}for j in before[s]['failed_jobs']]}for s,_ in SOURCES.values()}
proof={'reviewed_at':stamp,'catalog_entries':list(SOURCES),'status':'reviewed_scoped_existing_raw_materials_and_SQL',
 'scope':'Two committed raw records per source plus fresh existing committed-data and metadata Athena previews; no full-archive or all-derived-analysis certification.',
 'source_observation_counts':totals,'count_query_id':counts['query_id'],'original_validation':raw,
 'sampled_records':12,'distinct_originals':len({r['original_sha256']for r in raw}),
 'athena_previews':queries,'source_controls_and_remaining_findings':findings,
 'remaining_USGS_metadata_hold':{'state':before['usgs_minerals']['source']['state'],'reason':before['usgs_minerals']['source']['last_reason'],
   'raw_failure_jobs':4,'retry_jobs':1,'cleared':False,'note':'Current sampled raw reports and published SQL pass. This review does not clear older metadata failures or resume the stopped queue.'},
 'verification_method':['Collection manifest, checkpoint terminal-history membership, batch SHA-256, byte count and row count.','Official original SHA-256 and content comparison.','USGS PDF reparse including text, statistics, footnotes, sections and supply-chain fields.','EIA workbook sheet and exact Plant ID/Generator ID row; original report month.','CAISO native ZIP row, archive/member provenance, numeric price and precise interval timing.','BLS exact native series observation and footnotes; ROR entire organization row; EIA exact monthly retail-sales row and units.'],
 'verification_limits':['Observation counts include repeated captures and declared artifact records, not unique entities or full provider coverage.','USGS normalized mineral statistics retain estimates/footnotes; unresolved entity and development claims are not certified.','Battery inventory is not dispatch, firm capacity, commissioning confirmation or supplier matching.','CAISO review covers the requested price component source; companion ancillary/indicator datasets remain separate.','BLS manufacturing earnings are not fully loaded customer labor costs.','ROR identity candidates are not verified grant affiliations or historical registry vintages.','EIA US all-sector retail averages are not site tariffs or wholesale prices.','Existing metadata holds and uncommitted inputs remain recorded; no source pause, contract, service limit or queue state was changed.'],
 'legacy_broad_count':{'query_id':read('committed-counts.json')['query_id'],'state':read('committed-counts.json')['state'],
   'note':'Stopped after the 100-second audit bound; successful scoped metadata counts and per-source previews were used instead.'},
 'owner_action_required_for_this_review':False}
(P/'review-complete.json').write_text(json.dumps(proof,indent=2)+'\n')

summary="SELECT source_key, count(*) AS observations, count_if(raw_completeness_status = 'complete') AS complete_raw_observations FROM optima_metadata_engine.source_observations WHERE source_key IN ("+','.join("'"+s+"'"for s,_ in SOURCES.values())+") GROUP BY source_key;"
sql=['-- us-east-1 / AwsDataCatalog / workgroup optima-collected-data; result reuse off.',
 '-- Counts are published observation occurrences, including repeated captures/artifact records.',summary,'',
 '-- Dated review examples use immutable published job partitions to bound scans.',
 '-- Remove the job_id filter for a wider source preview. Raw/SQL review is not full archive completion.']
for number,(source,title)in SOURCES.items():
 sql.extend(['','-- '+str(number)+'. '+title,queries['metadata-preview-'+source]['sql']+';'])
(P/'review-queries.sql').write_text('\n'.join(sql)+'\n')

notes={
 'usgs_minerals':'Two 2026 lithium/cobalt PDFs matched their originals, reparsed text, statistics, footnotes and sections. The background metadata queue remains **raw_stopped** after four older validation failures, plus one missing-object retry; this finding is open. Published rows remain queryable. This checkbox covers existing raw material/SQL, not recovery of that queue or full history.',
 'eia_battery_generators':'Two September 2026 Planned/Operating generator rows matched the official workbook, sheet, Plant ID, Generator ID and all retained columns. Inventory statuses/units remain explicit; dispatch, firm capacity and supplier/entity matching are outside scope. The source is enabled; two older inputs lacking checkpoint evidence remain excluded.',
 'eia_retail_prices':'Two saved US/all-sector monthly rows matched original API responses, identities and price/sales/revenue/customer units. These are average retail statistics, not wholesale prices or site tariffs. Source enabled; no failed/retry/uncommitted metadata jobs in the scoped control check.',
 'caiso_prices':'Two DAM price components matched official ZIP/member provenance, exact native rows, prices and interval timing. Negative values are retained. This covers caiso_prices only, not all nodes, ancillary datasets, storage indicators or profitability. Source enabled; one older input lacking checkpoint evidence remains excluded.',
 'bls_wages':'Two CES3000000003 observations matched original BLS series rows, periods, values and footnotes. Units are seasonally adjusted manufacturing average hourly earnings in USD/hour, not fully loaded customer labor costs. Source enabled; two older inputs lacking checkpoint evidence remain excluded.',
 'ror_institutions':'Two entire institution records matched original ROR v2 responses, IDs, names, relationships and status. These are current identity candidates, not verified grant affiliations or historical vintages. Source enabled; one older public-receipt validation failure and two uncommitted inputs remain recorded.'}
schedule=ROOT/'RAW_DATA_VERIFICATION_SCHEDULE.md';text=schedule.read_text()
for number,(source,title)in SOURCES.items():
 entry=f'''- [x] **{number}. {title}** (`{source}`) — reviewed 14 November 2026, scoped raw-material/SQL verification  
  Fresh Athena check: **{int(totals[source][1]):,} published observations**, all with complete raw status for their declared record kinds; counts are occurrences, not unique records or completed history. Both committed-data and metadata previews returned substantive rows.  
  {notes[source]}  
  Two raw records checked per source with official-original checksums and collection manifest/checkpoint evidence. Processing for this verification ran on m7; production settings and deliberate pauses are unchanged.  
  [Review evidence and remaining findings](repair-notes/2026-11-14-six-source-review/review-complete.json) · [Verified SQL examples](repair-notes/2026-11-14-six-source-review/review-queries.sql).
'''
 match=re.search(rf'- \[ \] \*\*{number}\. .*?(?=\n- \[|\Z)',text,re.S);assert match,number
 text=text[:match.start()]+entry+text[match.end():]
schedule.write_text(text)

status=Path('/home/ec2-user/data-source-status-2026-10-26.md');text=status.read_text()
text=re.sub(r'^# Data-source status — refreshed .*$', '# Data-source status — refreshed 14 November 2026',text,count=1,flags=re.M)
intro='''
## November 14 — six existing raw-data/SQL sources rechecked

**Entries 50, 53, 55, 56, 57 and 58 are marked reviewed for their existing raw materials and SQL visibility.** Twelve sampled records passed official-original comparisons, checksums and collection-commit checks on m7. Fresh committed-data and metadata previews returned substantive records for every source. Verified published observation snapshot: USGS **84**, EIA battery generators **13,085**, EIA retail prices **322**, CAISO prices **16,256**, BLS wages **802**, ROR institutions **141**. Counts are occurrences, not unique records, full archives or certification of all derived conclusions.

**Open finding: USGS metadata remains stopped** after four older raw-validation failures and has one missing-object retry. Current sampled original reports and published SQL pass; this review does not resume that queue or clear those findings. Older missing-checkpoint inputs for battery, CAISO, BLS and ROR, plus one old ROR receipt failure, remain recorded. No source pauses, contracts, queue states or production limits were changed. No owner action is required to complete this review. [Verified SQL](data-collection-processing/repair-notes/2026-11-14-six-source-review/review-queries.sql) · [Evidence and remaining findings](data-collection-processing/repair-notes/2026-11-14-six-source-review/review-complete.json).

'''
pos=text.index('\n')+1;text=text[:pos]+intro+text[pos:]
for number,(source,title)in SOURCES.items():
 key=str(number).zfill(3)
 block=f'''### q{key}

**{key}. {title} — reviewed 14 November 2026 (existing raw/SQL scope)**

Workgroup: `optima-collected-data`, us-east-1, AwsDataCatalog, result reuse off. {notes[source]}

```sql
SELECT source_key, dataset, source_record_id, ingested_at,
       raw_completeness_status,
       json_extract(labelled_json, '$.payload.data') AS provider_data,
       json_extract(labelled_json, '$.raw_artifacts') AS original_evidence
FROM optima_metadata_engine.source_observations
WHERE source_key = '{source}'
  AND dataset = 'specialist_inputs'
  AND json_extract(labelled_json, '$.payload.data') IS NOT NULL
LIMIT 25;
```

Verified snapshot: **{int(totals[source][1]):,} published observation occurrences**. [Queries with bounded published-partition examples](data-collection-processing/repair-notes/2026-11-14-six-source-review/review-queries.sql).
'''
 match=re.search(rf'### q{key}\n.*?(?=\n### q|\Z)',text,re.S);assert match,key
 text=text[:match.start()]+block+text[match.end():]
 table=re.search(rf'^\| {key} \|.*$',text,re.M);assert table,key
 columns=table.group().split('|');columns[3]=' Raw/SQL rechecked 14 November 2026; current capture/metadata controls and unresolved findings recorded in review evidence '
 columns[5]=f' REVIEWED — {int(totals[source][1]):,} published observations; raw samples passed — [SQL](#q{key}) '
 columns[6]=(' USGS metadata hold and missing-object retry remain open; existing raw/SQL review passed. 'if number==50 else' Scoped raw/SQL review complete; existing uncommitted inputs and limits remain recorded. ')
 text=text[:table.start()]+'|'.join(columns)+text[table.end():]
status.write_text(text)
print('All six scoped raw/SQL reviews recorded; USGS metadata hold retained:',stamp)
