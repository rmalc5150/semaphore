import subprocess,json,sys,os
sys.path.insert(0,'/opt/constellation/source');os.chdir('/opt/constellation/source');os.environ['CONSTELLATION_ROLE']='worker';os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1'
cmd=['systemd-run','--unit=optima-nist-methods-document-probe-v1','--wait','--property=User=ec2-user','--property=WorkingDirectory=/opt/constellation/source','--property=Slice=constellation-workers.slice','--property=MemoryMax=402653184','--property=CPUQuota=20%','--property=RuntimeMaxSec=180','--setenv=CONSTELLATION_ROLE=worker','--setenv=CONSTELLATION_SHARED_HTTP_LIMITS=1','/opt/constellation/legacy-venv/bin/python','-B','grants_review_capture.py','--probe','--sources','nist_robotics_methods'];r=subprocess.run(cmd,capture_output=True,text=True);print('NIST',r.returncode,r.stderr);print(subprocess.run(['journalctl','-u','optima-nist-methods-document-probe-v1','--no-pager','-n','5'],capture_output=True,text=True).stdout)
from collection_storage import StorageSettings
from regulatory_collection import EvidenceClient
from ted_enrichment import enrich_notice
store=StorageSettings.load('config/collection-storage.s3.json').store();client=EvidenceClient(store,'ted_notices');data=client.json('https://api.ted.europa.eu/v3/notices/search',body={'query':'publication-date >= 20261104 AND publication-date <= 20261111 AND classification-cpv = 31712300','fields':['publication-number','ojs-number'],'limit':1,'scope':'ALL','onlyLatestVersions':False})
if data.get('notices'):
 row=data['notices'][0];rid=row['publication-number'];rid=rid[0]if isinstance(rid,list)else rid
 try:result,_=enrich_notice(row,rid,client,prefer_package=True);print('TED',rid,result['enrichment'])
 except Exception as e:
  chain=[]
  while e:chain.append(type(e).__name__+':'+str(e)[:180]);e=e.__cause__
  print('TED',rid,json.dumps(chain))
