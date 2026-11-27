import json,boto3,hashlib
from pathlib import Path
from sec_athena_pilot import run_query
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an';rows=json.loads((p/'publication-status.json').read_text());new=[r for r in rows if (r['receipt']or{}).get('checked_at','').startswith('2026-11-18')];ids=[r['window_id']for r in new]
for r in new:
 proof=s.get_object(Bucket=b,Key='research-data/'+r['receipt']['verification_key'])['Body'].read();assert hashlib.sha256(proof).hexdigest()==r['receipt']['verification_sha256']
where=','.join("'"+wid+"'"for wid in ids)
sql='SELECT window_id, source, count(*) AS records, count_if(length(data_json)>0) AS populated_payloads FROM optima_regulatory_pilot.regulatory_events_windows WHERE window_id IN ('+where+') GROUP BY window_id,source;'
r=run_query(boto3.client('athena'),{'config':{'database':'optima_regulatory_pilot','workgroup':'optima-regulatory-pilot'}},sql);assert len(r['rows'])==3 and all(row[1]=='fda_openfda'and int(row[2])>0 and row[2]==row[3]for row in r['rows']);(p/'FDA-new-windows.sql').write_text(sql+'\n');(p/'fda-new-readback.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
