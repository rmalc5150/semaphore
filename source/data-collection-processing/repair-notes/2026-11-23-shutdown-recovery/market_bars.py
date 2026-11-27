import json,boto3
from pathlib import Path
from decimal import Decimal
p=Path(__file__).parent;s=boto3.client('s3');out=[]
for f in p.glob('market-bad-*-failure.json'):
 d=json.loads(f.read_text());e=d['evidence'][0];rows=json.loads(s.get_object(Bucket='data-collection-059416028963-us-east-1-an',Key='research-data/'+e['key'])['Body'].read());bad=[]
 for r in rows:
  v={k:Decimal(str(r[k]))for k in ['open','high','low','close']}
  if not v['low']<=min(v['open'],v['close'])<=max(v['open'],v['close'])<=v['high']:bad.append(r)
 item={'symbol':f.stem.removeprefix('market-bad-').removesuffix('-failure'),'rows':len(rows),'bad_rows':bad,'evidence':e};out.append(item);print(item['symbol'],'rows',len(rows),'bad',len(bad),'example',bad[:2])
(p/'market-invalid-bars.json').write_text(json.dumps(out,indent=2))
