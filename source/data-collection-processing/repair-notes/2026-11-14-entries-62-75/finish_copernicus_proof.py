import json,hashlib,io,zipfile
from metadata_engine.runtime_db import Database
from metadata_engine.evidence import evidence_for,object_bytes
from metadata_engine.reviewed_continuation import claim
from metadata_engine.worker import process
from metadata_engine.controller import publish
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');b=cfg['bucket'];base='research-data/constellation-backfill/repairs/entries-62-75-20261114/';proof=json.loads(s.get_object(Bucket=b,Key=base+'copernicus-recovery.json')['Body'].read());result=proof['passes'][-1];assert result['status']=='complete';m=json.loads(s.get_object(Bucket=b,Key='research-data/'+result['manifest'])['Body'].read());verified=[]
for page in m['pages']:
 for batch in page['batches']:
  key='research-data/'+batch['key'];raw=object_bytes(s,b,key,expected=batch['sha256']);rows=[json.loads(l)for l in raw.splitlines()if l.strip()]
  for row in rows:
   artifacts=evidence_for(row,cfg['contracts'][row['source']],s,b);data=row['payload']['data'];ref=next(r for r in row['payload']['source_evidence']if r['sha256']==data['artifact_sha256']);nativekey=ref['key'];nativekey=nativekey if nativekey.startswith('research-data/')else'research-data/'+nativekey;body=object_bytes(s,b,nativekey,expected=data['artifact_sha256']);assert len(body)==data['artifact_bytes']
   if body.startswith(b'PK'):
    with zipfile.ZipFile(io.BytesIO(body))as z:
     assert z.testzip()is None
     for name in z.namelist():
      if not name.endswith('/'):assert z.read(name).startswith((b'CDF',b'\x89HDF'))
   else:assert body.startswith((b'CDF',b'\x89HDF'))
   verified.append({'source_record_id':row['source_record_id'],'native_key':nativekey,'sha256':data['artifact_sha256'],'bytes':len(body),'provider_job_id':data['request_id']})
  db.enqueue('copernicus_era5_era5_land',key,s.head_object(Bucket=b,Key=key)['ETag'],'legacy_batch',550)
processed=[]
for _ in range(3):
 job=claim(db,'copernicus_era5_era5_land')
 if not job:break
 process(db,s,cfg,job);processed.append(job['job_id'])
with db.tx()as c:
 states=[]
 for jobid in processed:
  c.execute('SELECT job_id,state,output_rows,reason FROM engine_jobs WHERE job_id=%s',(jobid,));states.append(c.fetchone())
ids=[r['job_id']for r in states if r['state']=='accepted'];published=publish(db,source_key='copernicus_era5_era5_land',job_ids=ids)if ids else 0
out={'verified_originals':verified,'processed':states,'published':published};s.put_object(Bucket=b,Key=base+'copernicus-metadata-recovery.json',Body=json.dumps(out).encode(),ServerSideEncryption='AES256');print(json.dumps(out))
