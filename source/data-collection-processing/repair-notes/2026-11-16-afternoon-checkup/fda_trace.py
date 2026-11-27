import os,sys,json,traceback
from pathlib import Path
from datetime import date
root=Path('/opt/constellation/auxiliary-publication/source');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker';os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1'
from collection_storage import StorageSettings,write_json,now
from research_contract import load_json,digest
from collection_operations import Operations
settings=StorageSettings.load(root/'config/collection-storage.s3.json');store=settings.store();cfg=load_json(root/'config/constellation-core-public.json');cfg['max_pages']=12
u=load_json(root/cfg['universe']);t=load_json(root/cfg['taxonomy']);op=Operations(store,settings,cfg,u,t)
assert op.identity=='935af362e43726fe97e95f4c6848b591ce8083c6cdf1ec5843bef67f9ae9d53f'
def trace(frame,event,arg):
 if event=='exception' and arg[0].__name__=='OperationalError':
  print('SQL_ERROR',str(arg[1])[:350],frame.f_code.co_filename,frame.f_lineno,flush=True)
 return trace
sys.settrace(trace)
for month in [5]:
 start=date(2016,month,1);end=date(2016,month+1,1)
 try:
  result=op.window('fda',start,end,'historical');r={k:v for k,v in result.items() if k in ['status','manifest','reason','records','source','start','end','attempt_receipt']}
  if result['status']=='complete':
   m=json.loads(store.get(result['manifest']).body); wid=digest(m['task']);key='operations/regulatory/publication-queue/'+wid+'.json';previous=store.get(key)
   value={'window_id':wid,'manifests':[result['manifest']],'queued_at':now(),'source':'fda_openfda','dataset':'research_records'}
   if not previous or json.loads(previous.body)['manifests']!=value['manifests']:write_json(store,key,value,previous.token if previous else None)
   r['window_id']=wid;r['records']=m['record_count'];r['queue_key']=key
 except Exception as e:r={'source':'fda','start':str(start),'status':'repair_failed','error':str(e)[:400]};traceback.print_exc()
 write_json(store,'constellation-backfill/repairs/2026-11-16-afternoon/core-fda-'+str(start)+'.json',r);print(json.dumps(r),flush=True)
