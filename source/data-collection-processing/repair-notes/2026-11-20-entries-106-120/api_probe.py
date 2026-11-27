from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode
import csv,io,json
from pathlib import Path
import requests
from ops import P, session
from regional_source_review import Page
from additional_source_apis import SECRET
from provider_tls import ca_bundle_for

base='https://api-comexstat.mdic.gov.br/general?language=en'
post={'flow':'export','monthDetail':True,'period':{'from':'2026-09','to':'2026-10'},'filters':[{'filter':'sh6','values':[850760,260400,282520,250410]}],'details':['sh6'],'metrics':['metricFOB','metricKG']}
targets={
 'mdic_post': (base, post),
 'trace_steel': ('https://api.climatetrace.org/v7/sources?year=2025&sectors=manufacturing&subsectors=iron-and-steel&limit=5',None),
 'trace_asset': ('https://api.climatetrace.org/v7/sources/1566956?start=2021&end=2025&timeGranularity=year&gas=co2e_100yr',None),
 'serna_system_ca': ('https://www.sernageomin.cl/anuarios-mineria-chile/',None),
 'geocat_system_ca': ('https://geocatmin.ingemmet.gob.pe/arcgis/rest/services/SERV_CATASTRO_MINERO_WGS84/MapServer/0?f=json',None),
 'scm_header': ('https://dadosabertos.anm.gov.br/SCM/PLG.csv',None),
 'minem_editions': ('https://www.gob.pe/institucion/minem/colecciones/6-boletin-estadistico-minero',None),
}
def fetch(pair):
 name,(url,data)=pair
 try:
  verify='/etc/pki/tls/certs/ca-bundle.crt' if name.endswith('system_ca') else ca_bundle_for(url)
  with requests.request('POST' if data else 'GET',url,json=data,stream=True,timeout=(8,18),verify=verify) as r:
   raw=r.raw.read(750000,decode_content=True)
   (P/f'probe-{name}.bin').write_bytes(raw)
   row={'status':r.status_code,'url':r.url,'content_type':r.headers.get('Content-Type'),'length':r.headers.get('Content-Length'),'prefix':raw[:200].decode(errors='replace')}
  if name in ('serna_system_ca','minem_editions'):
   row['links']=[(a,b) for a,b in Page(raw).links(row['url']) if 'safm_file=' in a or 'anuario' in a.lower() or 'boletin-estadistico-minero-' in a.lower()][:40]
  return name,row
 except Exception as error:return name,{'error':str(error)[:270]}
with ThreadPoolExecutor(max_workers=7) as pool:
 out=dict(pool.map(fetch,targets.items()))
try:
 d=json.loads(session.client('secretsmanager').get_secret_value(SecretId=SECRET)['SecretString'])
 out['configured_access']={name:any(name in str(key).lower().replace('-','') and bool(value) for key,value in d.items()) for name in ('census','importyeti','importgenius','marinetraffic','kpler')}
except Exception as error:out['credential_check']=type(error).__name__
(P/'api-probes.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
for k,v in out.items():print(k,str(v)[:1400])
