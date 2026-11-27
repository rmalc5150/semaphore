import json,boto3
from pathlib import Path
from urllib.parse import urlsplit
p=Path(__file__).parent;c=json.load(open('config/metadata-engine.json'));s=boto3.client('s3',region_name=c['region']);jobs=json.load(open(p/'before.json'))['oversized_jobs'];out=[];seen=set()
for j in jobs:
 if j['source_key']in seen:continue
 seen.add(j['source_key']);b=s.get_object(Bucket=c['bucket'],Key=j['input_key'])['Body'].read();rows=[json.loads(x)for x in b.splitlines()if x];r=rows[0];refs=r.get('payload',{}).get('source_evidence',[])
 if j['input_format']=='public_receipt':refs=[{'key':urlsplit(r['artifact_uri']).path.lstrip('/'),'sha256':r['sha256'],'source_url':r['source_url']}]
 entry={'job':j,'record':r,'artifacts':[]}
 for ref in refs[:6]:
  key=ref.get('key')or'';key=key if key.startswith('research-data/')else'research-data/'+key
  h=s.head_object(Bucket=c['bucket'],Key=key);sample=s.get_object(Bucket=c['bucket'],Key=key,Range='bytes=0-1023')['Body'].read();entry['artifacts'].append({'reference':ref,'bytes':h['ContentLength'],'content_type':h.get('ContentType'),'prefix':repr(sample[:180])})
 out.append(entry);print(j['source_key'],[(v['bytes'],v['content_type'],v['prefix'][:100])for v in entry['artifacts']],flush=True)
(p/'artifact-inventory.json').write_text(json.dumps(out,indent=2,default=str))
for name in ('health/latest.json','state/incidents.json','overview/latest.json'):
 try:d=json.loads(s.get_object(Bucket=c['bucket'],Key='research-data/monitoring/'+name)['Body'].read());(p/('monitor-'+name.replace('/','-'))).write_text(json.dumps(d,indent=2));print(name,list(d)[:12])
 except Exception as e:print(name,type(e).__name__)
