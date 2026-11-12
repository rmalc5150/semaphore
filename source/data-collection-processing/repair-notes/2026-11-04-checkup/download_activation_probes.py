import json,hashlib,requests
from pathlib import Path
from urllib.parse import urlsplit
from copernicus_capture import call,API
class Capture:
 def save(self,*args):pass
p=Path(__file__).parent;out={}
for dataset in ['reanalysis-era5-single-levels','reanalysis-era5-land']:
 j=json.loads((p/(dataset+'-activation-probe.json')).read_text())['jobID']
 try:
  d=call(Capture(),'GET',API+'/jobs/'+j+'/results');a=d['asset']['value'];u=urlsplit(a['href']);assert u.scheme=='https' and (u.hostname.endswith('.ecmwf.int') or u.hostname.endswith('.climate.copernicus.eu'))
  size=int(a['file:size']);assert 0<size<=16*1024**2
  with requests.get(a['href'],stream=True,timeout=(10,30),allow_redirects=False) as r:
   assert r.status_code==200
   chunks=[];total=0
   for chunk in r.iter_content(65536):
    total+=len(chunk);assert total<=size;chunks.append(chunk)
  body=b''.join(chunks);assert len(body)==size and body.startswith((b'CDF',b'\x89HDF',b'PK\x03\x04'))
  (p/(dataset+'-sample.nc')).write_bytes(body)
  out[dataset]={'status':'download_verified','bytes':size,'sha256':hashlib.sha256(body).hexdigest(),'job_id':j}
 except Exception as e:out[dataset]={'status':'failed','reason':getattr(e,'code',type(e).__name__)}
(p/'copernicus-download-verification.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
