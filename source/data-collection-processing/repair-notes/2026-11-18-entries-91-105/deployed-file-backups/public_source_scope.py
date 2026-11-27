"""Bounded source-specific public-document discovery; indexes are never records."""
import base64,re
from urllib.parse import urlsplit,urljoin,urlunsplit

REGIONAL_KEYS={'japan_mhlw_ndb_open_data','cninfo_mainland_china_company_disclosures','china_nbs_industrial_production','china_miit_electronics_and_battery_statistics','china_nea_power_statistics','china_nhsa_reimbursement_and_procurement','china_mofcom_export_controls','taiwan_twse_mops_issuer_and_revenue_archives','taiwan_customs_trade_statistics','india_ibm_mineral_production','indonesia_esdm_and_geological_agency_mineral_statistics','brazil_anm_mineral_yearbook','brazil_anm_cfem_mining_royalties'}

REVIEWED=REGIONAL_KEYS|{'ucdp_organized_violence','sia_wsts_public_semiconductor_sales','international_federation_of_robotics_world_robotics','iea_pvps_solar_deployment_reports','germany_g_ba_drug_benefit_assessments','france_has_medicine_assessment_opinions','canada_cda_amc_cadth_reimbursement_reviews','france_assurance_maladie_open_medic','semi_worldwide_equipment_billings'}

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
 if key in REGIONAL_KEYS:
  from regional_source_review import in_scope as regional_scope
  return regional_scope(url,key,discovery)
 if key not in REVIEWED:return True
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
