import boto3,json,hashlib
from pathlib import Path
from sec_athena_pilot import run_query
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an';a=boto3.client('athena')
receipts=[]
for f in p.glob('fda-receipt-*.json'):
 r=json.loads(f.read_text());raw=s.get_object(Bucket=b,Key='research-data/'+r['verification_key'])['Body'].read();assert hashlib.sha256(raw).hexdigest()==r['verification_sha256'];receipts.append(r)
sql="""SELECT source, provider_id, event_date, date_basis,
       length(data_json) AS payload_characters,
       substr(data_json, 1, 200) AS payload_preview
FROM optima_regulatory_pilot.regulatory_events_windows
WHERE window_id = 'b494577cf540d8f1ebace452c1b518d682bbc76f7ad309b055a98a5dc3e35910'
LIMIT 3;"""
r=run_query(a,{'config':{'database':'optima_regulatory_pilot','workgroup':'optima-regulatory-pilot'}},sql);assert len(r['rows'])==3 and all(row[0]=='fda_openfda' and int(row[4])>0 for row in r['rows']);(p/'fda-payload-query.json').write_text(json.dumps(r,indent=2));(p/'FDA-Athena-check.sql').write_text(sql+'\n');print(json.dumps(r))
