"""Integrity and source-scope checks for complete public native files."""
from urllib.parse import urlsplit
from public_source_scope import in_scope,REVIEWED

def evidence(record,s3,bucket):
 from metadata_engine.evidence import RawFailure
 from metadata_engine.streaming import evidence as streamed
 source=record['source'];errors=[]
 for ref in record.get('payload',{}).get('source_evidence',[]):
  url=ref.get('source_url','')
  if not in_scope(url,source):continue
  try:
   artifact=streamed(record,ref,{'allowed_hosts':allowed_hosts(source)},s3,bucket)
  except RawFailure as error:errors.append(str(error));continue
  artifact['validation'].update(provider=source,record_type='public_source_document',scope='Complete original public dataset/report file with checksum and structural integrity; analytical row extraction, interpretation and exhaustive historical coverage are separate.')
  return [artifact]
 raise RawFailure(errors[0]if errors else'public_original_outside_reviewed_scope')

def allowed_hosts(source):
 hosts={
 'ucdp_organized_violence':['ucdp.uu.se'],
 'semi_worldwide_equipment_billings':['www.semi.org','semi.org','www.seaj.or.jp'],
 'sia_wsts_public_semiconductor_sales':['www.wsts.org','wsts.org'],
 'international_federation_of_robotics_world_robotics':['ifr.org','www.ifr.org'],
 'iea_pvps_solar_deployment_reports':['iea-pvps.org','www.iea-pvps.org'],
 'germany_g_ba_drug_benefit_assessments':['g-ba.de','www.g-ba.de'],
 'france_has_medicine_assessment_opinions':['has-sante.fr','www.has-sante.fr','www.data.gouv.fr','static.data.gouv.fr'],
 'canada_cda_amc_cadth_reimbursement_reviews':['www.cda-amc.ca','cda-amc.ca'],
 'france_assurance_maladie_open_medic':['open-data-assurance-maladie.ameli.fr','www.data.gouv.fr','files.data.gouv.fr'],
 }
 return hosts[source]
