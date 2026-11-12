import requests,json,hashlib
from pathlib import Path
from usgs_archive_urls import resolve
from usgs_minerals_enrichment import parse_report
out={};p=Path(__file__).parent
for mineral in ('lithium','cobalt','nickel','graphite'):
 url=resolve(f'https://pubs.usgs.gov/periodicals/mcs2016/mcs2016-{mineral}.pdf')
 try:
  with requests.get(url,timeout=(10,30),stream=True,allow_redirects=False) as r:
   assert r.status_code==200
   chunks=[];size=0
   for part in r.iter_content(65536):
    size+=len(part);assert size<8*1024*1024;chunks.append(part)
  raw=b''.join(chunks);assert raw.startswith(b'%PDF-');d=parse_report(raw,url)
  (p/('usgs-2016-'+mineral+'.pdf')).write_bytes(raw)
  out[mineral]={'status':'parsed','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'edition':d['edition'],'mineral':d['mineral'],'statistics':len(d['statistics']),'gaps':d.get('gaps')}
 except Exception as e:out[mineral]={'status':'failed','reason':getattr(e,'code',type(e).__name__)}
 print(mineral,json.dumps(out[mineral]),flush=True)
(p/'usgs-probes.json').write_text(json.dumps(out,indent=2))
