import json,boto3
from pathlib import Path
from collections import Counter
from constellation.control import Control
p=Path(__file__).parent;c=Control();s=boto3.client('s3',region_name='us-east-1');out=[]
for r in json.loads((p/'source-dispatch.json').read_text()):
 d=c.get('job#'+r['job_id']);entry={'job_id':r['job_id'],'unit':r['unit'],'status':d['status'],'attempts':d['attempts'],'result':json.loads(d['result_json']) if d['result_json'] else None}
 key=c.config['prefix']+'/specialist-schedulers/'+r['unit']+'/historical.json'
 try:
  state=json.loads(s.get_object(Bucket=c.config['bucket'],Key=key)['Body'].read());entry['scheduler']={'updated_at':state.get('updated_at'),'statuses':dict(Counter(v.get('status') for v in state['jobs'].values())),'latest':sorted(state['jobs'].values(),key=lambda r:r.get('last_attempt',''),reverse=True)[:1]}
 except Exception as e:entry['scheduler_error']=type(e).__name__
 out.append(entry)
(p/'replay-status.json').write_text(json.dumps(out,indent=2,default=str))
for e in out:print(json.dumps({'unit':e['unit'],'status':e['status'],'attempts':e['attempts'],'scheduler':e.get('scheduler')},default=str))
