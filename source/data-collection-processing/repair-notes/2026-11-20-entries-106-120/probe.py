"""Bounded provider checks. No credentials or intake writes."""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
import hashlib
import json
import requests
from ops import P
from regional_source_review import Page
from provider_tls import ca_bundle_for

urls = {
    'comex_docs': 'https://api-comexstat.mdic.gov.br/docs',
    'cochilco': 'https://www.cochilco.cl/web/anuario-de-estadisticas-del-cobre-y-otros-minerales/',
    'sernageomin': 'https://www.sernageomin.cl/anuarios-mineria-chile/',
    'snifa': 'https://snifa.sma.gob.cl/DatosAbiertos',
    'sma_drive': 'https://drive.google.com/embeddedfolderview?id=1O7o60LzQ-qH8xiK_-Ofqw_mZzti_gbEr',
    'minem': 'https://www.gob.pe/institucion/minem/colecciones/6-boletin-estadistico-minero',
    'minem_book': 'https://www.gob.pe/institucion/minem/informes-publicaciones/8451839-cuadros-estadisticos-mineros-prepublicacion-del-bem-junio-2026',
    'siacam': 'https://www.mecon.gob.ar/dataset/ipi-minero/ipi-minero-series.csv',
    'sigmine': 'https://dadosabertos.anm.gov.br/SIGMINE/',
    'anm_root': 'https://dadosabertos.anm.gov.br/',
    'ingemmet': 'https://geocatmin.ingemmet.gob.pe/arcgis/rest/services/SERV_CATASTRO_MINERO_WGS84/MapServer?f=json',
    'comext': 'https://ec.europa.eu/eurostat/api/comext/dissemination/sdmx/2.1/data/DS-045409/A.DE.US.850760.1.VALUE_IN_EUROS?startPeriod=2023&endPeriod=2025&format=SDMX-CSV',
    'comext_tsv': 'https://ec.europa.eu/eurostat/api/comext/dissemination/sdmx/2.1/data/DS-045409/A.DE.US.850760.1.VALUE_IN_EUROS?startPeriod=2023&endPeriod=2025&format=TSV',
    'trace': 'https://api.climatetrace.org/v7/sources?year=2025&sectors=steel&limit=5',
    'trace_openapi': 'https://api.climatetrace.org/v7/docs/index.html',
}

def probe(name_url):
    name, url = name_url
    row = {'url': url}
    try:
        with requests.get(url, stream=True, timeout=(8, 18), verify=ca_bundle_for(url), headers={'User-Agent':'ConstellationResearch/1.0 (support@optima-holdings.com)'}) as response:
            raw = response.raw.read(550000, decode_content=True)
            row.update(status=response.status_code, final_url=response.url, media=response.headers.get('Content-Type'), length=response.headers.get('Content-Length'), sampled=len(raw))
        (P / ('probe-'+name+'.bin')).write_bytes(raw)
        if 'html' in (row['media'] or ''):
            try:
                row['links'] = [[link,label] for link,label in Page(raw).links(row['final_url']) if any(x in link.lower() for x in ('pdf','xlsx','csv','anuario','arcgis','sigmine','cadastro','/informes-publicaciones/','google.com','download','spec','swagger'))][:60]
            except ValueError:
                pass
        else:
            row['prefix']=raw[:300].decode('utf-8',errors='replace')
    except Exception as error:
        row['error']=type(error).__name__+': '+str(error)[:230]
    return name,row

with ThreadPoolExecutor(max_workers=7) as pool:
    result=dict(pool.map(probe,urls.items()))
(P/'provider-probe.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
for name,row in result.items():
    print(name,row.get('status'),row.get('final_url'),row.get('length'),row.get('prefix'),row.get('error'),row.get('links',[])[:3])
