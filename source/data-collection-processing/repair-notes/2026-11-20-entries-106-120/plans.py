from pathlib import Path
import json
from urllib.parse import urlsplit
from datetime import date
from metadata_engine.source_policies import build
from trade_mining_sources import (
    MDIC, COCHILCO, SERNAGEOMIN, SNIFA, MINEM, SIACAM, SIGMINE, GEOCAT, COMEXT, TRACE,
    HOSTS, in_scope, request_seeds,
)
P = Path(__file__).resolve().parent
root = P.parents[1]
probes = json.loads((P/'provider-probe.json').read_text())
serna = json.loads((P/'cert-route-proofs.json').read_text())['serna']
cadastre = json.loads((P/'geocat-query.json').read_text())
old = {s['source']:s for s in json.loads((root/'config/constellation-public-sources.json').read_text())['sources']}

cochilco_index = probes['cochilco']['url']
cochilco_files = list(dict.fromkeys(url for url,_ in probes['cochilco']['links'] if in_scope(url,COCHILCO)))
serna_files = list(dict.fromkeys(url for url,label in serna['links'] if in_scope(url,SERNAGEOMIN) and label.startswith('Anuario de la Minería')))
minem_collection = probes['minem']['url']
minem_native = list(dict.fromkeys(url for url,_ in probes['minem_book']['links'] if in_scope(url,MINEM)))
minem_january = 'https://cdn.www.gob.pe/uploads/document/file/9670753/7914628-bem-enero-2026.pdf'
minem_yearbook = json.loads((P/'minem-yearbook.json').read_text())
minem_yearbook_index = 'https://www.gob.pe/institucion/minem/colecciones/2400-anuario-minero'
siacam_files = ['https://www.mecon.gob.ar/dataset/ipi-minero/ipi-minero-'+suffix+'.csv'
                for suffix in ('series','variaciones','produccion-litio')]
anm_small = ['https://dadosabertos.anm.gov.br/SIGMINE/PROCESSOS_MINERARIOS/AC.zip',
             'https://dadosabertos.anm.gov.br/SCM/PLG.csv']
sma_export = 'https://drive.usercontent.google.com/download?id=1hPEwmUFZpmD7xFbJy-kjhhzjplnUB1mH&export=download'
assert len(serna_files)>5 and len(cochilco_files)>10 and minem_native
sources = {
    MDIC: (request_seeds(MDIC,'daily',date.today().isoformat()), None,
           'Brazil monthly import and export totals for four fixed NCM products. Original FOB USD and net kilograms. Historical windows from 2016.'),
    COCHILCO: ([cochilco_files[1],cochilco_index],cochilco_files[2:]+[cochilco_index],
               'Official copper and other mining economics workbooks and annual reports. The current workbook covers 2000–2025.'),
    SERNAGEOMIN: ([serna_files[0],serna['url']],serna_files[1:]+[serna['url']],
                  'Official Chilean mining yearbooks, as whole PDF files. Checks daily for archive changes.'),
    SNIFA: ([sma_export],[sma_export],
            'The official historical sanctioning-proceedings CSV linked by SNIFA. Inspection, final sanction and regulated-unit exports are separate datasets.'),
    MINEM: ([minem_native[0],minem_collection,minem_yearbook_index],
            [*minem_yearbook['files'],minem_january,*minem_native[:3],minem_yearbook_index,minem_collection],
            'Official mining bulletins, yearbooks and statistical annexes collected as original files.'),
    SIACAM: (siacam_files,siacam_files,
             'Official mining industrial production index series, changes and lithium production CSV exports.'),
    SIGMINE: (anm_small+['https://dadosabertos.anm.gov.br/SIGMINE/PROCESSOS_MINERARIOS/',
                        'https://dadosabertos.anm.gov.br/SCM/'],anm_small,
              'Current SIGMINE state shapefiles and Cadastro Mineiro public CSVs. Historical dates in records represent concession events.'),
    GEOCAT: ([cadastre['url']],[cadastre['url']],
             'Bounded Tacna concession snapshot. Eight native cadastral features with their returned attributes and geometry.'),
    COMEXT: (request_seeds(COMEXT,'daily',date.today().isoformat()),None,
             'German imports and exports with the US in four mineral and battery HS6 groups. Native DS-045409 euro values and returned flags. Monthly refresh and annual series since 2016.'),
    TRACE: (request_seeds(TRACE,'daily',date.today().isoformat()),None,
            'Five fixed iron-and-steel assets selected from the official 2025 ranking. Annual emissions and activity estimates since 2021 where available.'),
}
large = {COCHILCO: 'public-cochilco-daily', SERNAGEOMIN: 'public-sernageomin-daily',
         SNIFA: 'public-snifa-daily', MINEM: 'public-minem-daily', SIGMINE: 'public-sigmine-daily'}
updates = {}
for source,(daily,historical,scope) in sources.items():
    row = {**old[source],'hosts':HOSTS[source],'seeds':daily,'enabled':True,
           'max_depth':3,'raw_content_revision':'review-20261120','decodo':False,'scoped_trade_mining':True,
           'http_transient_retries':1,'scope_note':scope,
           'daily_execution':'worker' if source in large else 'controller'}
    if historical:
        row['historical_seeds'] = historical
    assert all(in_scope(url,source,discovery=True) for url in daily + (historical or [])),source
    updates[source] = row
policies = build(root)
subset = set(updates)|{'us_census_international_trade_api'}
(P/'capture-updates.json').write_text(json.dumps(updates,ensure_ascii=False,indent=2)+'\n')
(P/'policies.json').write_text(json.dumps({s:policies[s] for s in sorted(subset)},indent=2)+'\n')
(P/'daily-worker-map.json').write_text(json.dumps({v:k for k,v in large.items()},indent=2)+'\n')
