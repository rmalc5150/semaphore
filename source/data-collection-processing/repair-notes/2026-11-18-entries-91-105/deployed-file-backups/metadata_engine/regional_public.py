"""Whole native-file validation and exact current TWSE response rows."""
import hashlib,json,re,zlib,struct
from functools import lru_cache
from urllib.parse import urlsplit
from regional_source_review import PROFILES,in_scope,release_info,Page
from metadata_engine.evidence import RawFailure,object_bytes

@lru_cache(maxsize=2)
def decode(body):return json.loads(body)

def original_figures(url,body):
 from urllib.parse import urljoin
 path=urlsplit(url).path.rsplit('/',1)[0]+'/'
 return list(dict.fromkeys(urljoin(url,src)for src,alt in Page(body).images if src and urlsplit(urljoin(url,src)).hostname==urlsplit(url).hostname and urlsplit(urljoin(url,src)).path.startswith(path)and re.search(r'\.(?:png|jpe?g)$',urlsplit(urljoin(url,src)).path,re.I)))

def validate_figure(raw):
 if raw.startswith(b'\x89PNG\r\n\x1a\n'):
  pos=8;ended=False;header=False;image=False
  while pos+12<=len(raw):
   size=int.from_bytes(raw[pos:pos+4],'big');kind=raw[pos+4:pos+8];end=pos+8+size
   if end+4>len(raw)or zlib.crc32(raw[pos+4:end])&0xffffffff!=int.from_bytes(raw[end:end+4],'big'):raise RawFailure('release_png_corrupt')
   if not header and kind!=b'IHDR':raise RawFailure('release_png_header_missing')
   if kind==b'IHDR':
    if header or size!=13 or min(struct.unpack('>II',raw[pos+8:pos+16]))<=0:raise RawFailure('release_png_invalid_dimensions')
    header=True
   if kind==b'IDAT'and size:image=True
   pos=end+4
   if kind==b'IEND':ended=True;break
  if not ended or not header or not image or pos!=len(raw)or size!=0:raise RawFailure('release_png_incomplete')
  return 'png'
 if raw.startswith(b'\xff\xd8')and raw.rstrip().endswith(b'\xff\xd9'):return 'jpeg'
 raise RawFailure('release_figure_invalid')

def evidence(record,s3,bucket):
 from metadata_engine.streaming import download,evidence as streamed
 source=record['source'];profile=PROFILES[source];refs=record['payload'].get('source_evidence',[])
 for ref in refs:
  url=ref.get('source_url','')
  if not in_scope(url,source):continue
  key=ref.get('key')or urlsplit(ref['s3_uri']).path.lstrip('/');key=key if key.startswith('research-data/')else'research-data/'+key
  entry=download(s3,bucket,key,ref['sha256'])
  if profile['kind']=='release'and not re.search(r'\.pdf(?:\?|$)|downfile.jsp',url,re.I):
   if entry['bytes']>4*1024**2:raise RawFailure('release_html_too_large')
   raw=entry['path'].read_bytes();info=release_info(source,url,raw)
   if not info:raise RawFailure('official_release_not_substantive')
   artifacts=[{'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':ref['sha256'],'bytes':len(raw),'origin':'first_party_source','source_url':url,'retrieved_at':ref.get('retrieved_at'),'validation':info}]
   for figure in original_figures(url,raw):
    match=next((r for r in refs if r.get('source_url')==figure),None)
    if not match:raise RawFailure('official_release_figure_missing')
    fk=match.get('key')or urlsplit(match['s3_uri']).path.lstrip('/');fk=fk if fk.startswith('research-data/')else'research-data/'+fk;body=object_bytes(s3,bucket,fk,8*1024**2,expected=match['sha256']);fmt=validate_figure(body)
    artifacts.append({'artifact_kind':'tabular_figure','s3_uri':'s3://'+bucket+'/'+fk,'sha256':match['sha256'],'bytes':len(body),'origin':'first_party_source','source_url':figure,'retrieved_at':match.get('retrieved_at'),'validation':{'format':fmt,'scope':'Original same-release figure bytes verified; no OCR-derived numbers asserted.'}})
   return artifacts
  if profile['kind']=='twse':return twse_evidence(record,ref,entry,bucket)
  if source=='taiwan_customs_trade_statistics'and record.get('dataset')=='taiwan_customs_monthly_clearance':return customs_evidence(record,ref,entry,bucket)
  if source=='japan_mhlw_ndb_open_data'and urlsplit(url).path.lower().endswith('.xlsx'):validate_ndb_workbook(entry)
  if source in ('brazil_anm_mineral_yearbook','brazil_anm_cfem_mining_royalties')and urlsplit(url).path.lower().endswith('.csv'):validate_anm_csv(entry,source)
  # Only source-scoped datasets/PDFs enter the generic structural validator.
  artifact=streamed(record,ref,{'allowed_hosts':profile['hosts']},s3,bucket)
  if source=='cninfo_mainland_china_company_disclosures':artifact['artifact_kind']='primary_document'
  artifact['validation'].update(provider=source,record_type='public_original_file',scope='Complete source-scoped original file, not exhaustive historical coverage or individual numerical extraction.')
  return [artifact]
 raise RawFailure('regional_original_missing_or_outside_scope')

def twse_rows(receipt,s3,bucket):
 from research_contract import digest
 key=urlsplit(receipt['artifact_uri']).path.lstrip('/');body=object_bytes(s3,bucket,key,8*1024**2,expected=receipt['sha256']);rows=decode(body);require_twse(rows,receipt['source_url']);dataset='twse_issuers'if receipt['source_url'].lower().endswith('t187ap03_l')else'twse_monthly_revenue'
 output=[];seen=set()
 for row in rows:
  identity=str(row['公司代號'])+(':'+str(row['資料年月'])if dataset=='twse_monthly_revenue'else'')
  if identity in seen:raise RawFailure('twse_duplicate_provider_identity')
  seen.add(identity);output.append({'source':receipt['source'],'dataset':dataset,'source_record_id':identity,'ingested_at':receipt['retrieved_at'],'source_url':receipt['source_url'],'payload':{'data':row,'source_evidence':[{'s3_uri':receipt['artifact_uri'],'sha256':receipt['sha256'],'source_url':receipt['source_url'],'retrieved_at':receipt['retrieved_at']}]},'available_at':None})
 return output

def require_twse(rows,url):
 if not isinstance(rows,list)or not rows or any(not isinstance(r,dict)or not r.get('公司代號')or not r.get('公司名稱')for r in rows):raise RawFailure('twse_invalid_native_response')
 if url.lower().endswith('t187ap05_l')and any(not r.get('資料年月')or '營業收入-當月營收'not in r for r in rows):raise RawFailure('twse_revenue_fields_missing')

def twse_evidence(record,ref,entry,bucket):
 if entry['bytes']>8*1024**2:raise RawFailure('twse_native_response_too_large')
 rows=decode(entry['path'].read_bytes());require_twse(rows,ref['source_url']);data=record['payload']['data'];matches=[r for r in rows if r==data]
 if len(matches)!=1:raise RawFailure('twse_entire_native_row_mismatch')
 identity=str(data['公司代號'])+(':'+str(data['資料年月'])if record['dataset']=='twse_monthly_revenue'else'')
 if record['source_record_id']!=identity:raise RawFailure('twse_identity_mismatch')
 return [{'artifact_kind':'provider_record','s3_uri':ref.get('s3_uri')or's3://'+bucket+'/research-data/'+ref['key'].removeprefix('research-data/'),'sha256':ref['sha256'],'bytes':entry['bytes'],'origin':'first_party_source','source_url':ref['source_url'],'retrieved_at':ref.get('retrieved_at'),'validation':{'format':'json','record_type':'twse_native_row','scope':'Exact full original issuer or monthly revenue row; reporting month and native units retained, not a complete filing/XBRL archive or original historical vintage.'}}]

@lru_cache(maxsize=2)
def customs_decoded(body):
 import csv,io
 rows=list(csv.DictReader(io.StringIO(body.decode('utf-8-sig'))))
 expected={'年度','月份','出口總值(新臺幣千元)','進口總值(新臺幣千元)'}
 if not rows or any(not expected.issubset(r)or any(k is None or v is None for k,v in r.items())or not r['年度'].isdigit()or not r['月份'].isdigit()or not 1<=int(r['月份'])<=12 for r in rows):raise RawFailure('customs_csv_schema_or_period_invalid')
 return rows

def customs_rows(receipt,s3,bucket):
 key=urlsplit(receipt['artifact_uri']).path.lstrip('/');body=object_bytes(s3,bucket,key,8*1024**2,expected=receipt['sha256']);rows=customs_decoded(body);seen=set();out=[]
 for data in rows:
  identity=data['年度']+':'+data['月份'].zfill(2)
  if identity in seen:raise RawFailure('customs_duplicate_native_period')
  seen.add(identity);out.append({'source':receipt['source'],'dataset':'taiwan_customs_monthly_clearance','source_record_id':identity,'ingested_at':receipt['retrieved_at'],'source_url':receipt['source_url'],'available_at':None,'payload':{'data':data,'source_evidence':[{'s3_uri':receipt['artifact_uri'],'sha256':receipt['sha256'],'source_url':receipt['source_url'],'retrieved_at':receipt['retrieved_at']}]}})
 return out

def customs_evidence(record,ref,entry,bucket):
 rows=customs_decoded(entry['path'].read_bytes());data=record['payload']['data'];identity=data.get('年度','')+':'+data.get('月份','').zfill(2)
 if len([r for r in rows if r==data])!=1 or record['source_record_id']!=identity:raise RawFailure('customs_entire_native_row_mismatch')
 return [{'artifact_kind':'provider_record','s3_uri':ref.get('s3_uri')or's3://'+bucket+'/research-data/'+ref['key'].removeprefix('research-data/'),'sha256':ref['sha256'],'bytes':entry['bytes'],'origin':'first_party_source','source_url':ref['source_url'],'retrieved_at':ref.get('retrieved_at'),'validation':{'format':'csv','record_type':'monthly_customs_clearance','scope':'Exact complete native monthly aggregate clearance row; native reporting year and NTD-thousand fields retained; not detailed HS/country trade or historical vintages.'}}]

def validate_anm_csv(entry,source):
 import csv
 csv.field_size_limit(8*1024*1024)
 for encoding in ('utf-8-sig','cp1252'):
  try:
   with entry['path'].open('r',encoding=encoding,newline='')as f:
    sample=f.read(16384);f.seek(0);dialect=csv.Sniffer().sniff(sample,delimiters=',;\t');reader=csv.reader(f,dialect);columns=next(reader)
    required={'Ano base','UF'}if source=='brazil_anm_mineral_yearbook'else{'Ano','Mês','Processo','ValorRecolhido'}
    if not required.issubset(columns):raise RawFailure('anm_native_csv_schema_mismatch')
    n=0
    for row in reader:
     if not row:continue
     if len(row)!=len(columns):raise RawFailure('anm_csv_column_count_mismatch')
     n+=1
    if not n:raise RawFailure('anm_csv_empty')
   entry['validation']={'format':'csv','kind':'dataset_file','rows':n,'columns':columns,'encoding':encoding,'scope':'Entire ANM native CSV file parsed; original byte encoding retained. Numerical interpretation and original historical vintages not asserted.'};return
  except UnicodeError:continue
  except(csv.Error,StopIteration):raise RawFailure('anm_native_csv_invalid')from None
 raise RawFailure('anm_native_csv_encoding_invalid')

def validate_ndb_workbook(entry):
 import zipfile
 from xml.etree.ElementTree import iterparse,ParseError
 from metadata_engine.streaming import validate_file
 info=validate_file(entry)
 if info['format']!='zip':raise RawFailure('ndb_native_xlsx_required')
 rows=cells=worksheets=0
 with zipfile.ZipFile(entry['path'])as archive:
  if 'xl/workbook.xml'not in archive.namelist()or '[Content_Types].xml'not in archive.namelist():raise RawFailure('ndb_workbook_package_missing')
  for member in archive.infolist():
   if not re.fullmatch(r'xl/worksheets/sheet\d+\.xml',member.filename):continue
   if member.file_size>64*1024**2:raise RawFailure('ndb_worksheet_size_limit')
   worksheets+=1
   with archive.open(member)as data:
    try:
     for _,element in iterparse(data,events=('end',)):
      tag=element.tag.rsplit('}',1)[-1]
      if tag=='row':rows+=1
      if tag in ('v','t')and element.text not in (None,''):cells+=1
      element.clear()
    except ParseError:raise RawFailure('ndb_worksheet_xml_invalid')from None
 if not worksheets or rows<2 or cells<4:raise RawFailure('ndb_workbook_no_native_table')
 entry['validation']={**info,'record_type':'ndb_aggregate_workbook','worksheets':worksheets,'worksheet_rows':rows,'nonempty_value_cells':cells,'scope':'Complete native aggregate workbook with all ZIP-member CRCs and sheet XML checked; native suppression retained, no patient-level records or complete historical coverage asserted.'}
