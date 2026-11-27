import json
from ops import remote,T3,session,B,BASE,P,SOURCES
r=remote(T3,'''import json,boto3,subprocess
from pathlib import Path
from constellation.control import Control
sources=SOURCES;out={};s=boto3.client('s3',region_name='us-east-1');control=Control()
plans={n:json.load(open('config/'+n))['sources']for n in ['specialist-inputs.json','constellation-specialist-historical.json','constellation-public-sources.json']}
routes=json.load(open('config/constellation-legacy-routes.json'))['routes']
for source in sources:
 entry={'plans':{n:[r for r in rows if r.get('source')==source]for n,rows in plans.items()},'routes':[],'schedulers':{},'warnings':[]}
 selected=[r for r in routes if r.get('specialist_source')==source or r.get('source')==source or source in r.get('unit','')]
 for row in selected:
  lane={'route':row,'jobs':[]}
  try:
   with control.db()as c:
    c.execute("SELECT status,count(*) jobs FROM backfill_jobs FORCE INDEX(source_status_updated) WHERE source_key=%s GROUP BY status",('legacy:'+row['unit'],));lane['jobs']=c.fetchall()
  except Exception as error:entry['warnings'].append(type(error).__name__+':'+str(error)[:200])
  entry['routes'].append(lane)
 keys=['research-data/constellation-backfill/daily-api-schedulers/'+source+'/daily.json']
 for row in selected:keys.append('research-data/constellation-backfill/specialist-schedulers/'+row['unit']+'/historical.json')
 for key in keys:
  try:entry['schedulers'][key]=json.loads(s.get_object(Bucket=BUCKET,Key=key)['Body'].read(16*1024*1024))
  except s.exceptions.NoSuchKey:pass
  except Exception as error:entry['warnings'].append(type(error).__name__+':'+str(error)[:200])
 out[source]=entry
key=BASE+'source-lanes.json';s.put_object(Bucket=BUCKET,Key=key,Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256');print(json.dumps({'key':key}))
'''.replace('SOURCES',repr(SOURCES)).replace('BUCKET',repr(B)).replace('BASE',repr(BASE)))
raw=session.client('s3').get_object(Bucket=B,Key=json.loads(r['out'])['key'])['Body'].read();(P/'source-lanes.json').write_bytes(raw)
from collections import Counter
for source,e in json.loads(raw).items():print(source,[(r['route']['unit'],r['route']['execution_enabled'],r['jobs'])for r in e['routes']],e['warnings'],[(k.split('/')[-2],dict(Counter(j.get('status')for j in v.get('jobs',{}).values())),max((j.get('last_attempt','')for j in v.get('jobs',{}).values()),default=''))for k,v in e['schedulers'].items()])
