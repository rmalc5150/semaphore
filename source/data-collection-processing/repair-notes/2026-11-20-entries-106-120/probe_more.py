from concurrent.futures import ThreadPoolExecutor
import json
import requests
from ops import P,session
from provider_tls import ca_bundle_for

urls = {
 'comex_spec':'https://api-comexstat.mdic.gov.br/docs/doc.yaml',
 'trace_spec':'https://api.climatetrace.org/v7/docs/openapi.json',
 'trace_mfg':'https://api.climatetrace.org/v7/sources?year=2025&sectors=manufacturing&limit=5',
 'ingemmet_app':'https://geocatminapp.ingemmet.gob.pe/arcgis/rest/services/WGS84_17/WEBGIS_CATASTRO_MINERO_WGS84_17/MapServer/0?f=json',
 'ingemmet_alt':'https://geocatmin.ingemmet.gob.pe/arcgis/rest/services/SERV_CATASTRO_MINERO_WGS84/MapServer/0?f=json',
 'snifa_csv':'https://drive.google.com/uc?export=download&id=1hPEwmUFZpmD7xFbJy-kjhhzjplnUB1mH',
 'snifa_csv_alt':'https://drive.usercontent.google.com/download?id=1hPEwmUFZpmD7xFbJy-kjhhzjplnUB1mH&export=download',
 'anm_process':'https://dadosabertos.anm.gov.br/SIGMINE/PROCESSOS_MINERARIOS/',
 'anm_cadastro':'https://dadosabertos.anm.gov.br/SCM/',
 'cochilco_xlsx':'https://www.cochilco.cl/web/download/1036/2026/16850/base-de-datos-anuario-de-estadisticas-cochilco-2000-2025.xlsx',
 'serna_bare':'https://sernageomin.cl/anuarios-mineria-chile/',
 'siacam_litio':'https://www.mecon.gob.ar/dataset/ipi-minero/ipi-minero-produccion-litio.csv',
}
def get(item):
 name,url=item
 try:
  with requests.get(url,stream=True,verify=ca_bundle_for(url),timeout=(8,18),headers={'User-Agent':'ConstellationResearch/1.0 (support@optima-holdings.com)'}) as r:
   raw=r.raw.read(750000,decode_content=True)
   (P/('probe-'+name+'.bin')).write_bytes(raw)
   return name,dict(status=r.status_code,url=r.url,media=r.headers.get('Content-Type'),length=r.headers.get('Content-Length'),prefix=raw[:140].decode(errors='replace'))
 except Exception as error:
  return name,dict(error=str(error)[:250])
with ThreadPoolExecutor(max_workers=7) as pool:
 out=dict(pool.map(get,urls.items()))
d=json.loads(session.client('secretsmanager').get_secret_value(SecretId='dataSourceAPIkeys-PSTzff')['SecretString'])
out['configured_access']={name:any(name in str(key).lower().replace('-','') and bool(value) for key,value in d.items()) for name in ('census','importyeti','importgenius','marinetraffic','kpler')}
(P/'more-probes.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
