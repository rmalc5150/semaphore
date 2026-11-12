import json,re
from pathlib import Path
import boto3
p=Path(__file__).parent
s=Path('/home/ec2-user/.codex/attachments/bcf65c63-1ad6-453d-92cb-db1e28172007/Pasted text.txt').read_text()
client=boto3.client('s3',region_name='us-east-1');out={}
for source in ('fred_alfred','datacite','usgs_minerals','ted_notices'):
 block=next(b for b in s.split('\n\n')if b.startswith('constellation-history/'+source))
 uri=re.findall(r's3://[^\s,]+\.json',block)
 if not uri:continue
 bucket,key=uri[0][5:].split('/',1)
 try:
  d=json.loads(client.get_object(Bucket=bucket,Key=key)['Body'].read());out[source]=d
  print(source,[(x.get('reason'),x.get('job',{}).get('parameters'))for x in d.get('outcomes',[])][:6])
 except Exception as e:print(source,type(e).__name__,str(e)[:180])
(p/'receipts.json').write_text(json.dumps(out,indent=2))
