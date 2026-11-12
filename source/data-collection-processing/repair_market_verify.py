import json,boto3,subprocess,csv
from pathlib import Path
from committed_data_athena import query
P=Path('repair-notes/2026-10-21-market-coverage')
events=[json.loads(x) for x in (P/'mapping-replay.log').read_text().splitlines() if x.startswith('{')]
ids=next(x['window_ids'] for x in events if x.get('stage')=='market_mapping_publication')
where="window_id IN ("+','.join("'"+x+"'" for x in ids)+")"
base='optima_market_research.market_prices_windows'
sql=f"SELECT window_id, json_extract_scalar(record_json, '$.payload.provider_symbol') AS provider_symbol, min(event_date), max(event_date), count(*) AS rows, count(DISTINCT event_date) AS dates FROM {base} WHERE {where} GROUP BY 1,2 ORDER BY 1,2"
checks={'counts':sql,'incorrect_boundary':f"SELECT count(*) FROM {base} WHERE {where} AND ((event_date < '2025-03-19' AND json_extract_scalar(record_json, '$.payload.provider_symbol') <> 'AADI.US') OR (event_date >= '2025-03-19' AND json_extract_scalar(record_json, '$.payload.provider_symbol') <> 'WHWK.US'))",'samples':f'SELECT * FROM {base} WHERE {where} ORDER BY rand() LIMIT 20'}
a=boto3.client('athena',region_name='us-east-1');out={k:query(a,v) for k,v in checks.items()}
(P/'athena-verification.json').write_text(json.dumps(out,indent=2))
(P/'SQL-checks.md').write_text('# Repaired AADI / Whitehawk market windows\n\nThese queries are partition-bounded. The pinned symbol stays AADI.US; the actual requested ticker is in record_json.payload.provider_symbol.\n\n'+'\n\n'.join('## '+k+'\n\n```sql\n'+v+';\n```' for k,v in checks.items()))
print(json.dumps({k:v for k,v in out.items() if k!='samples'}))
r=subprocess.run(['systemctl','list-timers','optima*','--all','--no-pager','--output=json'],capture_output=True,text=True)
(P/'schedule-verification.json').write_text(r.stdout)
rows=list(csv.DictReader((P/'coverage-review.csv').open()));decisions=json.loads((P/'decisions.json').read_text())+json.loads((P/'covestro-decisions.json').read_text())
for row in rows:
 row['resolution']='unresolved: listing-specific evidence still required'
 for d in decisions:
  if row['symbol']==d['symbol'] and d['start']<=row['start'] and row['end_exclusive']<=d['end_exclusive']:row['resolution']='excluded with reviewed primary evidence: '+d['reason']
 if row['symbol']=='AADI.US' and row['start']>='2025-01-01':row['resolution']='replayed using reviewed AADI to WHWK mapping; see Athena verification'
with (P/'coverage-review.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
