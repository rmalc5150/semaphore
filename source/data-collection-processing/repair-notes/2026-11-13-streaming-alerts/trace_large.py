import json,boto3
from pathlib import Path
from metadata_engine.runtime_db import Database
from metadata_engine.worker import load_input
from metadata_engine.evidence import evidence_for
p=Path(__file__).parent;c=json.load(open('config/metadata-engine.json'));db=Database(c);s=db.session.client('s3');out=[]
class Reader:
 def get_object(self,**kw):
  r=s.get_object(**kw)
  if r.get('ContentLength',0)>32*1024*1024:out.append({'key':kw['Key'],'bytes':r['ContentLength']});print(out[-1],flush=True)
  return r
reader=Reader()
for source in ('personnel_archive','hkex_news'):
 j=next(j for j in json.load(open(p/'before.json'))['oversized_jobs']if j['source_key']==source)
 try:
  rows,_,_=load_input(reader,c['bucket'],j,db);offset=int(j['input_format'].split('@')[1])if'@'in j['input_format']else 0
  for r in rows[offset:offset+32]:
   try:
    if source=='hkex_news':
     from metadata_engine.hkex_documents import expand
     class NoNetwork:
      def get(self,url):raise ValueError('skip_network_probe')
     expand(r,NoNetwork(),reader,c['bucket'])
    evidence_for(r,c['contracts'][source],reader,c['bucket'])
   except Exception as e:
    if 'streaming_adapter'in str(e):print(source,r['source_record_id'],str(e));break
 except Exception as e:print(source,type(e).__name__,str(e)[:150])
(p/'large-trace.json').write_text(json.dumps(out,indent=2))
