import json,boto3
from pathlib import Path
from metadata_engine.runtime_db import Database
p=Path(__file__).parent;cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');out={}
for folder in p.iterdir():
 if not folder.is_dir()or not(folder/'sample-record.json').exists():continue
 source=folder.name;r=json.loads((folder/'sample-record.json').read_text());refs=r['payload'].get('source_evidence',[]);entries=[]
 # TED pages carry evidence for many notices; save only the search response and matching member.
 if source=='ted_notices':
  identity=r['payload']['data'].get('parent_notice_id')or str(r['source_record_id']).split(':')[0];needle=identity.replace('-','_')
  refs=[ref for ref in refs if ref.get('source_url','').endswith('/search')or needle in ref.get('package_member','')]
 for i,ref in enumerate(refs[:6]):
  if not ref.get('key'):continue
  key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key
  body=s.get_object(Bucket=cfg['bucket'],Key=key)['Body'].read();(folder/('original-'+str(i)+'.bin')).write_bytes(body);entry={'reference':ref,'bytes':len(body),'first_bytes':body[:35].decode(errors='replace')}
  try:
   d=json.loads(body);entry['type']=type(d).__name__;entry['keys']=list(d)[:15]if isinstance(d,dict)else[]
   if source=='nih_reporter':entry['total']=d.get('meta');entry['rows']=len(d.get('results',[]))
   if source=='uspto_assignment_histories':entry['nested_summary']=str(d)[:400]
  except (ValueError,UnicodeError):pass
  entries.append(entry)
 out[source]=entries;print(source,'evidence',json.dumps(entries,default=str)[:1700])
 with db.tx()as c:
  c.execute('SELECT dataset,count(*) n FROM (SELECT SUBSTRING_INDEX(SUBSTRING_INDEX(input_key,\'dataset=\',-1),\'/\',1) dataset FROM engine_jobs WHERE source_key=%s) a GROUP BY dataset',(source,));print('DATASETS',c.fetchall())
(p/'original-index.json').write_text(json.dumps(out,indent=2,default=str))
