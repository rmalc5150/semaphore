import json,boto3
from pathlib import Path
from metadata_engine.patent_sources import validate_odp
p=Path(__file__).parent;r=json.loads((p/'uspto_odp/sample-patent_assignment_records.json').read_text());ref=r['payload']['source_evidence'][0];key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key;raw=boto3.client('s3',region_name='us-east-1').get_object(Bucket='data-collection-059416028963-us-east-1-an',Key=key)['Body'].read();(p/'uspto_odp/assignment-original.json').write_bytes(raw);validate_odp(raw,r,ref.get('url')or ref.get('source_url'));print('Provider assignment ledger validated:',r['source_record_id'],len(r['payload']['data']['assignment_history']['events']))
