import json,re,collections,concurrent.futures
from pathlib import Path
import boto3
P=Path(__file__).parent;S=boto3.client('s3',region_name='us-east-1');B='data-collection-059416028963-us-east-1-an';items=json.load(open(P/'email-items.json'));chosen={}
for item in items:
 source=item['title'].split('|')[0].removeprefix('constellation-history/')
 for line in item['evidence']:
  parts=line.split('; ');reason=parts[2]if len(parts)>2 else line[:60];urls=re.findall(r's3://[^\s,]+\.json',line)
  if urls:chosen.setdefault((source,reason),urls[0])
chosen[('finlight','current_failure')]='s3://'+B+'/research-data/manifests/collection_runs/source=finlight/dataset=news_articles/run_6ade1b41-9bdb-4f35-aa1e-0f99a971ed83/final.json'
def get(item):
 (source,reason),url=item;key=url.split('/',3)[3]
 try:
  d=json.loads(S.get_object(Bucket=B,Key=key)['Body'].read());name=re.sub('[^A-Za-z0-9_-]','_',source)+'-'+str(list(chosen).index((source,reason)))+'.json';(P/name).write_text(json.dumps(d,indent=2));return {'source':source,'reason':reason,'key':key,'file':name,'top_keys':list(d)if isinstance(d,dict)else[], 'data':d}
 except Exception as e:return {'source':source,'key':key,'error':str(e)[:400]}
with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:out=list(pool.map(get,chosen.items()))
(P/'receipt-inventory.json').write_text(json.dumps(out,indent=2))
for r in out:
 d=r.get('data',{});print(json.dumps({k:v for k,v in r.items()if k!='data'}));
 if r['source']=='finlight':print('NEWS_FAILURE',json.dumps(d.get('error',d))[:2500])
