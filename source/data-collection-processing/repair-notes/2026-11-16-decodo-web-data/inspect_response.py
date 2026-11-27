import json,boto3
from pathlib import Path
p=Path(__file__).parent;d=json.loads((p/'pilot-result.json').read_text());e=d.get('source_evidence',[])[-1:]
if not e:raise SystemExit('No archived response')
s=boto3.client('s3',region_name='us-east-1');r=s.get_object(Bucket='data-collection-059416028963-us-east-1-an',Key='research-data/'+e[0]['key']);obj=json.loads(r['Body'].read())
def shape(v,depth=0):
 if isinstance(v,dict):return{k:shape(x,depth+1)for k,x in list(v.items())[:20]}
 if isinstance(v,list):return {'type':'list','count':len(v),'first':shape(v[0],depth+1)if v else None}
 if isinstance(v,str):
  # Provider error text helps diagnose schema/auth problems; content is never printed.
  return {'type':'string','length':len(v)}
 return v
print(json.dumps(shape(obj)))
for name in ('message','error','detail','status','success','job_id','id'):
 value=obj.get(name)
 if isinstance(value,(str,bool,int))and name not in('id','job_id'):print(name,str(value)[:600])
