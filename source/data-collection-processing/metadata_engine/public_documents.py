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
   if source=='france_has_medicine_assessment_opinions'and urlsplit(url).path.lower().endswith('.csv'):
    from metadata_engine.streaming import download
    key=ref.get('key')or urlsplit(ref['s3_uri']).path.lstrip('/');key=key if key.startswith('research-data/')else'research-data/'+key
    entry=download(s3,bucket,key,ref['sha256']);validate_has_export(entry)
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


def validate_has_export(entry):
 import csv
 from metadata_engine.evidence import RawFailure
 path=entry['path'];last=None
 csv.field_size_limit(8*1024*1024)
 with path.open('rb')as f:bom=f.read(4)
 encodings=['utf-16']if bom.startswith((b'\xff\xfe',b'\xfe\xff'))else['utf-8-sig','cp1252']
 for encoding in encodings:
  try:
   with path.open('r',encoding=encoding,newline='')as f:
    sample=f.read(65536);f.seek(0);delimiter=csv.Sniffer().sniff(sample.splitlines()[0],delimiters=';,\t').delimiter;quotechar='$'if sample.lstrip().startswith('$')else'"';reader=csv.reader(f,delimiter=delimiter,quotechar=quotechar);columns=next(reader);count=0;header_present=True
    if len(columns)==2 and __import__('re').fullmatch(r'CT-\d+',columns[0])and columns[1].startswith('https://www.has-sante.fr/jcms/'):
     columns=['assessment_code','opinion_page_url'];count=1;header_present=False
    if len(columns)<2:raise RawFailure('has_export_missing_columns')
    for row in reader:
     if not row:continue
     if len(row)!=len(columns):raise RawFailure('has_export_column_count_mismatch')
     count+=1
   if not count:raise RawFailure('has_export_empty')
   entry['validation']={'format':'csv','kind':'dataset_file','rows':count,'columns':columns,'encoding':encoding,'quote_character':quotechar,'header_present':header_present,'scope':'Entire native HAS medicine-evaluation export parsed with native character encoding; original bytes unchanged and assessment interpretation separate.'};return
  except UnicodeError as error:last=error
  except(csv.Error,StopIteration)as error:raise RawFailure('has_export_invalid_csv')from error
 raise RawFailure('has_export_unknown_encoding')from last
