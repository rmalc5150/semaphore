from concurrent.futures import ThreadPoolExecutor
import json
import requests
from ops import P
from provider_tls import ca_bundle_for
from regional_source_review import Page
urls={
 'serna':'https://www.sernageomin.cl/anuarios-mineria-chile/',
 'serna24':'https://www.sernageomin.cl/?mode=view&safm_file=1&sig=9a6f62fb114b60ca52f8067bd2a2b336c9cb2c10aa2e3a735770e889adc5578c',
 'geocat':'https://geocatmin.ingemmet.gob.pe/arcgis/rest/services/SERV_CATASTRO_MINERO_WGS84/MapServer/0/query?objectIds=1,2,3,4,5&outFields=*&returnGeometry=true&f=json',
 'geocatapp':'https://geocatminapp.ingemmet.gob.pe/arcgis/rest/services/WGS84_17/WEBGIS_CATASTRO_MINERO_WGS84_17/MapServer/0/query?objectIds=1,2,3,4,5&outFields=*&returnGeometry=true&f=json',
 'siacam_variaciones':'https://www.mecon.gob.ar/dataset/ipi-minero/ipi-minero-variaciones.csv',
}
def probe(item):
 name,url=item
 try:
  with requests.get(url,verify=ca_bundle_for(url),stream=True,timeout=(8,20),headers={'User-Agent':'ConstellationResearch/1.0 (support@optima-holdings.com)'}) as r:
   raw=r.raw.read(600000,decode_content=True); v={'status':r.status_code,'url':r.url,'media':r.headers.get('Content-Type'),'bytes':r.headers.get('Content-Length'),'sample_size':len(raw)}
  (P/f'probe-{name}.bin').write_bytes(raw)
  if name=='serna':
   v['links']=[(url,label)for url,label in Page(raw).links(v['url'])if 'safm_file='in url or url.lower().endswith('.pdf')][:35]
  if name.startswith('geocat'):
   d=json.loads(raw); v.update(keys=list(d),features=len(d.get('features',[])),error=d.get('error'),attrs=list(d['features'][0]['attributes'])if d.get('features')else[])
  return name,v
 except Exception as e:return name,{'error':str(e)[:200]}
with ThreadPoolExecutor(max_workers=5) as pool:out=dict(pool.map(probe,urls.items()))
(P/'cert-route-proofs.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
for k,v in out.items():print(k,str(v)[:1900])
