import os,sys,json,zipfile
os.chdir('/opt/constellation/metadata-engine-runtime');sys.path.insert(0,os.getcwd())
from metadata_engine.runtime_db import Database
from metadata_engine.streaming import session,download,validate_file
c=json.load(open('config/metadata-engine.json'));db=Database(c);s3=db.session.client('s3');bucket=c['bucket']
keys=[('cordis','research-data/constellation-backfill/public-capture/objects/european_commission_cordis/'),('indonesia','research-data/constellation-backfill/public-capture/objects/indonesia_esdm_and_geological_agency_mineral_statistics/4721c556ddcfae0a6319b1b2e1d25f5ab39d223db467de13974a1c7db3a2099d')]
with session():
 for name,key in keys:
  if key.endswith('/'):
   objects=s3.list_objects_v2(Bucket=bucket,Prefix=key)['Contents'];key=next(x['Key']for x in objects if x['Size']>32*1024**2)
  entry=download(s3,bucket,key,key.rsplit('/',1)[1])
  if name=='cordis':
   with zipfile.ZipFile(entry['path'])as z:
    print(json.dumps({'source':name,'members':[{'name':x.filename,'bytes':x.file_size}for x in z.infolist()][:20]}),flush=True)
    with z.open(z.infolist()[0])as f:print(repr(f.read(500)))
  else:print(json.dumps({'source':name,'validation':validate_file(entry)}),flush=True)
