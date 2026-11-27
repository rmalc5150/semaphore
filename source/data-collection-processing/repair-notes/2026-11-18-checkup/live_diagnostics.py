import os,sys,json,subprocess
from pathlib import Path
root=Path('/opt/constellation/summary-worker');os.chdir(root);sys.path.insert(0,str(root));os.environ['CONSTELLATION_ROLE']='worker'
import boto3
s=boto3.client('s3');b='data-collection-059416028963-us-east-1-an';stream='935af362e43726fe97e95f4c6848b591ce8083c6cdf1ec5843bef67f9ae9d53f'
import constellation.gaps as g
print('GAP_MODULE',g.__file__,'HAS_CORE',hasattr(g,'current_core_window'))
def load(k):return json.loads(s.get_object(Bucket=b,Key='research-data/'+k)['Body'].read())
try:
 o=load('operations/streams/'+stream+'/historical/fda/2025-05-01_2025-06-01.json');print('FDA_OUTCOME',o['status'],o.get('reason'),o.get('finished_at'))
 m=load(o['manifest']);h=load('checkpoints/'+m['task_id']+'/head.json');w={'scope':'fda|'+stream+'|configured_legacy_scope','start':'2025-05-01T00:00:00','end':'2025-06-01T00:00:00','status':'failed'};print('FDA_RECONCILE',g.current_core_window(w,o,m,h)['status'])
except Exception as e:print('FDA_ERROR',type(e).__name__,getattr(e,'response',{}).get('Error',{}).get('Code'))
for u in ['optima-m7-aux-collection-daily.service','optima-m7-capture-assignments-reviewed-historical.service','optima-m7-aux-cms-catalog-publication.service','optima-m7-aux-fda-reviewed-publication.service','optima-m7-capture-nist-robotics-daily.service']:
 print('UNIT',u,subprocess.run(['systemctl','show',u,'-p','ActiveState','-p','Result','-p','ExecMainStatus'],capture_output=True,text=True).stdout.replace('\n',' '))
 lines=subprocess.run(['journalctl','-u',u,'-n','3','--no-pager','-o','cat'],capture_output=True,text=True).stdout
 print(lines[-1300:])
