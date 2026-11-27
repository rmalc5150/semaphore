import os,sys,json
from pathlib import Path
root='/opt/constellation/auxiliary-publication/source';os.chdir(root);sys.path.insert(0,root);os.environ['CONSTELLATION_ROLE']='worker';os.environ['CONSTELLATION_SHARED_HTTP_LIMITS']='1'
from collection_storage import StorageSettings
from regulatory_collection import EvidenceClient
from copernicus_capture import call,API
settings=StorageSettings.load(Path('config/collection-storage.s3.json'));client=EvidenceClient(settings.store(),'copernicus_era5_era5_land')
try:
 d=call(client,'GET',API+'/jobs?limit=100');rows=d.get('jobs',[]);print(json.dumps({'job_count':len(rows),'jobs':[{'id':x.get('jobID')or x.get('job_id')or x.get('id'),'status':x.get('status'),'created':x.get('created'),'updated':x.get('updated'),'processID':x.get('processID')}for x in rows],'evidence':client.evidence},default=str))
except Exception as e:print(json.dumps({'provider_error':type(e).__name__,'reason':getattr(e,'code',str(e))}))
