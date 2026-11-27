import json,hashlib,csv,io,gzip,zipfile
from urllib.parse import urlsplit
from metadata_engine.runtime_db import Database
from metadata_engine.evidence import evidence_for,object_bytes
cfg=json.load(open('config/metadata-engine.json'));db=Database(cfg);s=db.session.client('s3');b=cfg['bucket'];base='research-data/constellation-backfill/repairs/entries-62-75-20261114/'
before=json.loads(s.get_object(Bucket=b,Key=base+'before.json')['Body'].read());counts=json.loads(s.get_object(Bucket=b,Key=base+'counts-after.json')['Body'].read());jobs=[];out=[]
for source in ['sam_gov_opportunities','fred_alfred_series_and_vintages','wto_timeseries_api','copernicus_era5_era5_land','bis_sdmx_api','ilostat_labor_statistics']:
 for job in before[source]['native_jobs'][:2]:jobs.append((source,job))
for row in counts['rows'][1:]:
 vals=[v.get('VarCharValue')for v in row['Data']]
 if vals[0]=='uspto_odp'and vals[1]in ('patent_office_actions','patent_petition_decisions'):
  with db.tx()as c:c.execute('SELECT * FROM engine_jobs WHERE job_id=%s',(vals[2],));jobs.append(('uspto_odp',c.fetchone()))
for source,job in jobs:
 result={'source':source,'job_id':job['job_id'],'input_key':job['input_key']}
 try:
  body=object_bytes(s,b,job['input_key']);rows=[json.loads(line)for line in body.splitlines()if line.strip()];record=rows[0];result['dataset']=record.get('dataset','public_documents')
  if 'artifact_uri'in record:
   uri=record['artifact_uri'];key=urlsplit(uri).path.lstrip('/');r=s.get_object(Bucket=b,Key=key);sha=hashlib.sha256();size=0;prefix=bytearray();native=bytearray()
   try:
    while True:
     block=r['Body'].read(1024*1024)
     if not block:break
     size+=len(block);sha.update(block)
     if len(prefix)<65536:prefix.extend(block[:65536-len(prefix)])
     if source=='ilostat_labor_statistics':native.extend(block)
   finally:r['Body'].close()
   assert sha.hexdigest()==record['sha256']and size==record['bytes']
   if source=='bis_sdmx_api':
    header=next(csv.reader(io.StringIO(bytes(prefix).decode('utf-8-sig',errors='strict'))));assert any('TIME_PERIOD'in x for x in header)and any('OBS_VALUE'in x for x in header);result['csv_header']=header
   else:
    decoded=gzip.decompress(native);assert decoded.startswith((b'X\n',b'A\n',b'B\n'));result['decoded_rds_bytes']=len(decoded);result['r_serialization_header_hex']=decoded[:24].hex()
   result['originals']=[{'s3_uri':uri,'sha256':sha.hexdigest(),'bytes':size}]
  else:
   artifacts=evidence_for(record,cfg['contracts'][source],s,b);result['originals']=artifacts
   data=record['payload']['data'];refs=record['payload']['source_evidence']
   if source in ('sam_gov_opportunities','fred_alfred_series_and_vintages','wto_timeseries_api'):
    matched=False
    for ref in refs:
     key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key
     raw=json.loads(object_bytes(s,b,key,expected=ref['sha256']))
     if source=='sam_gov_opportunities':matched=matched or data in raw.get('opportunitiesData',[])
     elif source=='wto_timeseries_api':matched=matched or data in raw.get('Dataset',[])
     else:
      native={k:data[k]for k in ('date','value','realtime_start','realtime_end')};matched=matched or native in raw.get('observations',[])
    assert matched,'exact native row absent';result['exact_native_row_matched']=True
   if source=='copernicus_era5_era5_land':
    refs=[r for r in refs if r['sha256']==data['artifact_sha256']];assert len(refs)==1
    ref=refs[0];key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key
    raw=object_bytes(s,b,key,expected=data['artifact_sha256']);assert len(raw)==data['artifact_bytes']
    if raw.startswith(b'PK'):
     with zipfile.ZipFile(io.BytesIO(raw))as z:
      assert z.testzip()is None and z.namelist()
      for name in z.namelist():
       if not name.endswith('/'):assert z.read(name).startswith((b'CDF',b'\x89HDF'))
     result['netcdf_container']='zip with verified members'
    else:assert raw.startswith((b'CDF',b'\x89HDF'))
    result['native_netcdf_verified']=True
  result['status']='verified'
 except Exception as error:result['status']='failed';result['reason']=type(error).__name__+':'+str(error)
 out.append(result);s.put_object(Bucket=b,Key=base+'other-raw-validation.json',Body=json.dumps(out,default=str).encode(),ServerSideEncryption='AES256');print(json.dumps(result),flush=True)
