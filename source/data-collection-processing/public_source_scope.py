"""Bounded source-specific public-document discovery; indexes are never records."""
import base64,re
from datetime import datetime
from zipfile import BadZipFile, ZipFile
from urllib.parse import urlsplit,urljoin,urlunsplit
from trade_mining_sources import SOURCES as TRADE_MINING_SOURCES

REGIONAL_KEYS={'japan_mhlw_ndb_open_data','cninfo_mainland_china_company_disclosures','china_nbs_industrial_production','china_miit_electronics_and_battery_statistics','china_nea_power_statistics','china_nhsa_reimbursement_and_procurement','china_mofcom_export_controls','taiwan_twse_mops_issuer_and_revenue_archives','taiwan_customs_trade_statistics','india_ibm_mineral_production','indonesia_esdm_and_geological_agency_mineral_statistics','brazil_anm_mineral_yearbook','brazil_anm_cfem_mining_royalties'}

CAPES_CATALOGUES = {
 '/dataset/catalogo-de-teses-e-dissertacoes-de-2013-a-2016',
 '/dataset/2017-2020-catalogo-de-teses-e-dissertacoes-da-capes',
 '/dataset/2021-a-2024-catalogo-de-teses-e-dissertacoes-brasil',
}
CAPES_PACKAGES = {
 '4b0780eb-5ba4-48d4-8d6a-0b77c56f2fd7',
 '36d1c92c-f9e0-4da1-a4f0-633e6ebefe03',
 'dbb9b83e-7779-4b99-89d2-1ff8099f36f6',
}
EIA_860 = re.compile(r'/electricity/data/eia860/(?:archive/)?xls/eia860(20\d{2})\.zip')
HKEX_QUOTATION = re.compile(r'/eng/stat/smstat/dayquot(?:_12m)?/d(\d{6})e\.htm')
HKEX_QUOTATION_INDEX = '/eng/stat/smstat/dayquot/qtn.asp'
STRICT_NATIVE_ROUTES = {'eia_generator_index', 'brazil_capes_theses_and_dissertations', 'hkex_prices'}

REVIEWED=REGIONAL_KEYS|TRADE_MINING_SOURCES|STRICT_NATIVE_ROUTES|{'ucdp_organized_violence','sia_wsts_public_semiconductor_sales','international_federation_of_robotics_world_robotics','iea_pvps_solar_deployment_reports','germany_g_ba_drug_benefit_assessments','france_has_medicine_assessment_opinions','canada_cda_amc_cadth_reimbursement_reviews','france_assurance_maladie_open_medic','semi_worldwide_equipment_billings'}


def capes_download(path):
 parts = path.split('/')
 return (len(parts) == 7 and parts[1] == 'dataset' and parts[2] in CAPES_PACKAGES
         and parts[3] == 'resource' and re.fullmatch(r'[a-f0-9-]{36}', parts[4])
         and parts[5] == 'download'
         and re.fullmatch(
             r'br-capes-btd-(?:2013a2016-\d{4}-\d{2}-\d{2}_2016|20(?:1[7-9]|2\d)-\d{4}-\d{2}-\d{2})\.csv',
             parts[6]))


def verify_expected_asset(source, url, file, first):
 path = urlsplit(url).path.lower()
 if source == 'hkex_prices' and (match := HKEX_QUOTATION.fullmatch(path)):
  with open(file, 'rb') as report:
   header = report.read(128 * 1024)
  date = re.search(rb'DATE:\s*(\d{1,2}\s+[A-Z]{3}\s+20\d{2})\s*\(', header)
  if not date or any(word not in header for word in
                     (b'DAILY QUOTATIONS', b'MAIN BOARD', b'SHARES TRADED', b'NAME OF STOCK')):
   raise ValueError('hkex_quotation_rows_or_header_missing')
  report_day = datetime.strptime(b' '.join(date[1].split()).decode('ascii'), '%d %b %Y').date()
  if report_day.strftime('%y%m%d') != match[1]:
   raise ValueError('hkex_quotation_date_mismatch')
  return {'dataset': 'main_board_daily_quotations', 'report_date': report_day.isoformat()}
 if source == 'eia_generator_index' and (match := EIA_860.fullmatch(path)):
  try:
   with ZipFile(file) as archive:
    if any(re.fullmatch(r'(?:3_1_+)?generator_?y' + match[1] + r'\.xlsx?',
                        name.rsplit('/', 1)[-1].lower()) for name in archive.namelist()):
     return
  except BadZipFile:
   pass
  raise ValueError('eia860_missing_annual_generator_workbook')
 if source == 'brazil_capes_theses_and_dissertations' and capes_download(path):
  header = first.splitlines()[0].upper()
  if (b'AN_BASE' not in header or
      not any(value in header for value in (b'DT_DEFESA', b'DT_TITULACAO')) or
      not any(value in header for value in (b'NM_PRODUCAO', b'NM_TITULO'))):
   raise ValueError('capes_theses_csv_schema_mismatch')

def decoded_response(body,url,media):
 # Decodo represents some binary responses as base64 even with HTML rendering.
 # Decode only a complete, signature-matching PDF; retain its original wrapper
 # separately in capture, so a browser/error page cannot become a document.
 if urlsplit(url).path.lower().endswith('.pdf')and body.lstrip().startswith(b'JVBER'):
  encoded=body;decoded=base64.b64decode(b''.join(body.split()),validate=True)
  if not decoded.startswith(b'%PDF-')or b'%%EOF'not in decoded[-4096:]:raise ValueError('public_encoded_pdf_invalid')
  return decoded,'application/pdf',encoded
 return body,media,None

def in_scope(url,source,discovery=False):
 key=source if isinstance(source,str)else source['source'];u=urlsplit(url);p=u.path.lower()
 if key in TRADE_MINING_SOURCES:
  if isinstance(source,dict) and not source.get('scoped_trade_mining'):
   return True
  from trade_mining_sources import in_scope as trade_mining_scope
  return trade_mining_scope(url,key,discovery)
 if key in REGIONAL_KEYS:
  from regional_source_review import in_scope as regional_scope
  return regional_scope(url,key,discovery)
 if key not in REVIEWED:return True
 if key=='eia_generator_index':
  match=EIA_860.fullmatch(p)
  return bool((match and int(match[1])>=2016) or (discovery and p=='/electricity/data/eia860/'))
 if key=='brazil_capes_theses_and_dissertations':
  return bool(capes_download(p) or (discovery and p.rstrip('/') in CAPES_CATALOGUES))
 if key=='hkex_prices':
  return bool(HKEX_QUOTATION.fullmatch(p) or (discovery and p==HKEX_QUOTATION_INDEX))
 if key=='ucdp_organized_violence':return bool(re.fullmatch(r'/downloads/(?:ged/ged\d+-csv\.zip|candidateged/gedevent_v[\d_]+\.csv)',p)or(discovery and p=='/downloads/'))
 if key=='germany_g_ba_drug_benefit_assessments':return bool((p.startswith('/downloads/')and p.endswith('.pdf')and any(k in p for k in ('nutzenbewertung','beschluss','tragende','dossier','modul','information')))
  or(discovery and re.fullmatch(r'/bewertungsverfahren/nutzenbewertung/(?:\d+/|letzte-aenderungen/)?',p)))
 if key=='france_has_medicine_assessment_opinions':return bool((p.startswith(('/upload/docs/evamed/ct-','/upload/docs/eva-med/ct-'))and p.endswith('.pdf'))or(p.startswith('/resources/evaluation-des-medicaments/')and p.endswith(('.csv','.xlsx')))
  or(discovery and (p=='/api/1/datasets/evaluation-des-medicaments/'or re.fullmatch(r'/jcms/[cp]_\d+/?',p)or re.fullmatch(r'/jcms/[^/]+/fr/(?:avis-et-decisions-sur-les-medicaments|open-data|.+-avis-ct.+)',p))))
 if key=='canada_cda_amc_cadth_reimbursement_reviews':return bool((p.startswith('/sites/default/files/')and p.endswith('.pdf')and any(k in p for k in ('/drr/','/cdr/','/sr','reimbursement','recommendation')))
  or(discovery and any(k in p for k in ('reimbursement-review','/projects/'))))
 if key=='france_assurance_maladie_open_medic':return bool((u.hostname=='open-data-assurance-maladie.ameli.fr'and p.startswith('/medicaments/'))or(p.startswith('/api/1/datasets/open-medic-')))
 if key=='sia_wsts_public_semiconductor_sales':return bool((p.startswith('/esracms/extension/media/')and p.endswith(('.pdf','.xls','.xlsx','.csv'))and any(k in p for k in ('monthly','billings','data','histor')))
  or(discovery and p=='/67/historical-billings-report'))
 if key=='international_federation_of_robotics_world_robotics':return bool(((p.startswith('/downloads/')or p.startswith('/img/worldrobotics/'))and p.endswith('.pdf'))or(discovery and(p.startswith('/ifr-press-releases/')or p.startswith('/worldrobotics'))))
 if key=='iea_pvps_solar_deployment_reports':return bool((p.startswith('/wp-content/uploads/')and p.endswith('.pdf')and any(k in p for k in ('snapshot','trends','national-survey','nsr','national_report')))or(discovery and(p=='/publications/'or p.startswith('/trends_reports/')or p.startswith('/snapshot-reports/'))))
 if key=='semi_worldwide_equipment_billings':return bool((u.hostname=='www.seaj.or.jp'and p.startswith('/english/statistics/')and p.endswith('.pdf'))or(discovery and((u.hostname=='www.seaj.or.jp'and p=='/english/statistics/index.html')or p.startswith('/en/news-resources/press')or p.startswith('/en/semi-press-release/'))))
 return False

def canonical_link(href,url,source):
 if source['source']=='france_has_medicine_assessment_opinions'and href.startswith('jcms/'):
  u=urlsplit(url);return u.scheme+'://'+u.netloc+'/'+href
 target=urljoin(url,href)
 if source['source']=='france_assurance_maladie_open_medic':
  from open_medic_download import stable_public_url
  target=stable_public_url(target)
 return target
