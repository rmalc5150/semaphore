import json,boto3
from pathlib import Path
p=Path(__file__).parent;s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an';f=json.load(open(p/'hkex-filings-current-failure.json'));m=json.loads(s.get_object(Bucket=b,Key='research-data/'+f['manifest'])['Body'].read());(p/'hkex-failed-manifest.json').write_text(json.dumps(m,indent=2));print('CURSOR',m.get('cursor'),'PAGES',len(m.get('pages',[])))
print('TASK',m['task']);c=json.loads(m['cursor'])if m.get('cursor')else{}
print('CURSOR_FIELDS',c)
for k in [c.get('index_snapshot_key'),c.get('snapshot',{}).get('key')if isinstance(c.get('snapshot'),dict)else None]:
 if k:
  d=json.loads(s.get_object(Bucket=b,Key='research-data/'+k)['Body'].read());(p/'hkex-current-snapshot.json').write_text(json.dumps(d,indent=2));print('SNAPSHOT',list(d));print(json.dumps(d)[:1500])
