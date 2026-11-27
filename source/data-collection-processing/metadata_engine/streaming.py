"""Disk-backed original-artifact validation; enabled only in the isolated lane."""
from contextlib import contextmanager
from contextvars import ContextVar
import codecs,csv,hashlib,io,json,os,re,shutil,sqlite3,tempfile,zipfile
from pathlib import Path,PurePosixPath
from urllib.parse import urlsplit
from metadata_engine.evidence import RawFailure

CHUNK=1024*1024
MAX_DOWNLOAD=512*CHUNK
MAX_EXPANDED=4*1024*CHUNK
_ACTIVE=ContextVar('metadata_streaming_lane',default=None)
class StreamingRequired(RuntimeError):pass

def active():
 return _ACTIVE.get() is not None

@contextmanager
def session():
 base=Path('/opt/constellation/tmp')
 with tempfile.TemporaryDirectory(prefix='metadata-stream-',dir=base if base.exists()else None)as tmp:
  state={'root':Path(tmp),'cache':{}};token=_ACTIVE.set(state)
  try:yield state
  finally:
   for value in state['cache'].values():
    if value.get('db'):value['db'].close()
   _ACTIVE.reset(token)

def _fingerprint(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

class JSONStream:
 """Incremental standard-library decoder with a bounded single-value buffer."""
 def __init__(self,stream):self.stream=stream;self.buffer='';self.eof=False;self.decoder=json.JSONDecoder()
 def more(self):
  value=self.stream.read(65536);self.eof=not value;self.buffer+=value
  if len(self.buffer)>8*CHUNK:raise RawFailure('streaming_json_single_value_limit')
 def space(self):
  while True:
   self.buffer=self.buffer.lstrip()
   if self.buffer or self.eof:return
   self.more()
 def take(self,char):
  self.space()
  if not self.buffer.startswith(char):raise RawFailure('streaming_json_invalid_structure')
  self.buffer=self.buffer[len(char):]
 def value(self):
  while True:
   self.space()
   try:value,end=self.decoder.raw_decode(self.buffer)
   except ValueError:
    if self.eof:raise RawFailure('streaming_json_truncated_or_invalid')from None
    self.more();continue
   if end==len(self.buffer)and not self.eof:self.more();continue
   self.buffer=self.buffer[end:];return value
 def results(self):
  self.take('{');seen=set();found=False
  while True:
   self.space()
   if self.buffer.startswith('}'):
    self.take('}');break
   key=self.value()
   if not isinstance(key,str)or key in seen:raise RawFailure('streaming_json_duplicate_or_invalid_key')
   seen.add(key);self.take(':')
   if key=='results':
    found=True;self.take('[');first=True
    while True:
     self.space()
     if self.buffer.startswith(']'):self.take(']');break
     if not first:self.take(',')
     yield self.value();first=False
   else:self.value()
   self.space()
   if self.buffer.startswith('}'):self.take('}');break
   self.take(',');self.space()
   if self.buffer.startswith('}'):raise RawFailure('streaming_json_trailing_comma')
  self.space()
  if self.buffer or not self.eof:raise RawFailure('streaming_json_trailing_content')
  if not found:raise RawFailure('streaming_json_results_missing')

def download(s3,bucket,key,expected):
 state=_ACTIVE.get()
 if state is None:raise StreamingRequired('streaming_lane_required')
 if not expected:raise RawFailure('streaming_expected_checksum_missing')
 identity=(bucket,key,expected.removeprefix('sha256:'))
 if identity in state['cache']:return state['cache'][identity]
 if len(state['cache'])>=3:
  _,old=state['cache'].popitem()
  if old.get('db'):old['db'].close()
  for file in (old['path'],old.get('index')):
   if file:file.unlink(missing_ok=True)
 response=s3.get_object(Bucket=bucket,Key=key);body=response['Body'];length=response.get('ContentLength');path=state['root']/hashlib.sha256(repr(identity).encode()).hexdigest();count=0;sha=hashlib.sha256()
 try:
  if length is not None and(length>MAX_DOWNLOAD or length<=0):raise RawFailure('streaming_download_size_limit')
  if shutil.disk_usage(state['root']).free<(length or MAX_DOWNLOAD)+256*CHUNK:raise StreamingRequired('streaming_disk_budget_insufficient')
  with path.open('wb')as output:
   while True:
    block=body.read(CHUNK)
    if not block:break
    count+=len(block)
    if count>MAX_DOWNLOAD:raise RawFailure('streaming_download_size_limit')
    sha.update(block);output.write(block)
 finally:body.close()
 if length is not None and count!=length:raise RawFailure('streaming_truncated_download')
 if sha.hexdigest()!=identity[2]:raise RawFailure('raw_artifact_checksum_mismatch')
 value={'path':path,'bytes':count,'sha256':sha.hexdigest()};state['cache'][identity]=value;return value

def validate_file(entry):
 if 'validation'in entry:return entry['validation']
 path=entry['path']
 with path.open('rb')as f:prefix=f.read(16384);f.seek(max(0,entry['bytes']-4096));tail=f.read()
 low=prefix.lower()
 if any(x in low for x in (b'<title>access denied',b'cf-chl-',b'request rate threshold exceeded')):raise RawFailure('raw_artifact_is_access_block_page')
 if prefix.startswith(b'<SEC-DOCUMENT>'):
  if not tail.rstrip().endswith(b'</SEC-DOCUMENT>'):raise RawFailure('streaming_sec_submission_incomplete')
  header=b'';documents=[];inside=False;text=False;content=False;kind=None;filename=None
  with path.open('rb')as f:
   while b'</SEC-HEADER>'not in header:
    line=f.readline(CHUNK)
    if not line or len(header)+len(line)>CHUNK:raise RawFailure('streaming_sec_header_incomplete')
    header+=line
   for line in iter(lambda:f.readline(8*CHUNK+1),b''):
    if len(line)>8*CHUNK:raise RawFailure('streaming_sec_line_limit')
    token=line.strip()
    if token==b'<DOCUMENT>':
     if inside:raise RawFailure('streaming_sec_nested_document')
     inside=True;text=False;content=False;kind=None;filename=None
    elif token==b'</DOCUMENT>':
     if not inside or text or not kind or not filename or not content:raise RawFailure('streaming_sec_document_incomplete')
     documents.append(kind);inside=False
     if len(documents)>10000:raise RawFailure('streaming_sec_document_limit')
    elif inside and token.startswith(b'<TYPE>')and not text:kind=token[6:].decode('ascii').strip()
    elif inside and token.startswith(b'<FILENAME>')and not text:filename=token[10:].decode('ascii').strip()
    elif inside and token==b'<TEXT>':text=True
    elif inside and token==b'</TEXT>':text=False
    elif inside and text and token:content=True
  accession=re.search(rb'ACCESSION NUMBER:\s*([0-9-]+)',header);ciks=re.findall(rb'CENTRAL INDEX KEY:\s*([0-9]+)',header);form=re.search(rb'CONFORMED SUBMISSION TYPE:\s*([^\r\n]+)',header)
  if inside or not documents or not accession or not ciks or not form:raise RawFailure('streaming_sec_submission_incomplete')
  form=form[1].decode('ascii').strip()
  if form not in documents:raise RawFailure('streaming_sec_primary_document_missing')
  value={'format':'sec_sgml','kind':'document','accession':accession[1].decode(),'ciks':[c.decode()for c in ciks],'form':form,'documents':len(documents),'scope':'complete SEC submission; matching header and closed substantive document blocks; document text remains in original'}
 elif prefix.startswith(b'%PDF-'):
  if b'%%EOF'not in tail:raise RawFailure('streaming_pdf_missing_eof')
  from pypdf import PdfReader
  with path.open('rb')as f:pages=len(PdfReader(f).pages)
  if pages<=0:raise RawFailure('streaming_pdf_no_pages')
  value={'format':'pdf','pages':pages,'kind':'document','scope':'complete original PDF integrity and page tree; text extraction separate'}
 elif prefix.startswith(b'PK\x03\x04'):
  total=0;files=[];substantive=0
  with zipfile.ZipFile(path)as archive:
   members=archive.infolist()
   if len(members)>10000:raise RawFailure('streaming_archive_member_limit')
   for m in members:
    if m.is_dir():continue
    name=PurePosixPath(m.filename)
    if name.is_absolute()or'..'in name.parts or m.flag_bits&1:raise RawFailure('streaming_archive_unsafe_or_encrypted_member')
    total+=m.file_size
    if total>MAX_EXPANDED:raise RawFailure('streaming_archive_expansion_limit')
    count=0;sample=b''
    with archive.open(m)as data:
     while True:
      block=data.read(CHUNK)
      if not block:break
      count+=len(block)
      if len(sample)<65536:sample+=block[:65536-len(sample)]
      if count>m.file_size:raise RawFailure('streaming_archive_size_mismatch')
    if count!=m.file_size:raise RawFailure('streaming_archive_truncated_member')
    if name.suffix.lower()in ('.csv','.tsv'):
     try:
      text=codecs.getincrementaldecoder('utf-8-sig')().decode(sample,final=False)
      delimiter='\t'if name.suffix.lower()=='.tsv'else csv.Sniffer().sniff(text.splitlines()[0],delimiters=',;\t').delimiter
      rows=list(csv.reader(io.StringIO(text),delimiter=delimiter))[:2]
     except (UnicodeError,csv.Error):rows=[]
     if len(rows)>1 and len(rows[0])>1:substantive+=1
    elif name.suffix.lower()in('.xml','.json','.xls','.xlsx','.pdf')and count>100:substantive+=1
    elif name.suffix.lower()=='.lis'and re.match(rb'0 HKEX  [0-9]{8}[A-Z0-9 ]+\r?\n',sample)and count>100:
     substantive+=1  # HKEX fixed-width report; CRC/length checked, fields not normalized here.
    if len(files)<32:files.append({'name':m.filename,'bytes':count,'crc32':m.CRC})
  if not substantive:raise RawFailure('streaming_archive_no_dataset_or_document')
  value={'format':'zip','kind':'dataset_file','members':len(members),'uncompressed_bytes':total,'member_sample':files,'scope':'all member CRCs and lengths; dataset/document member detection; analytical rows not published by this validator'}
 elif prefix.lstrip().startswith(b'{'):
  index=path.with_suffix('.sqlite3');db=sqlite3.connect(index);db.execute('CREATE TABLE provider_rows(signature TEXT PRIMARY KEY,provider_id TEXT NOT NULL)');n=0
  with path.open('r',encoding='utf-8-sig')as f:
   for row in JSONStream(f).results():
    if not isinstance(row,dict)or not row.get('id')or not row.get('name')or not row.get('source'):raise RawFailure('trade_screening_invalid_provider_row')
    db.execute('INSERT OR IGNORE INTO provider_rows VALUES(?,?)',(_fingerprint(row),str(row['id'])));n+=1
  db.commit();entry.update(db=db,index=index)
  value={'format':'json','kind':'native_record','rows':n,'scope':'entire JSON response parsed; exact complete provider row required'}
 else:
  n=0;header=None
  csv.field_size_limit(8*CHUNK)
  try:
   with path.open('r',encoding='utf-8-sig',newline='')as f:
    dialect=csv.Sniffer().sniff(prefix.decode('utf-8-sig').splitlines()[0],delimiters=',;\t');reader=csv.reader(f,delimiter=dialect.delimiter);header=next(reader)
    if len(header)<2:raise RawFailure('streaming_csv_missing_columns')
    for row in reader:
     if not row:continue
     if len(row)!=len(header):raise RawFailure('streaming_csv_column_count_mismatch')
     n+=1
  except(UnicodeError,csv.Error,StopIteration):raise RawFailure('streaming_invalid_tabular_file')from None
  if not n:raise RawFailure('streaming_csv_no_data_rows')
  value={'format':'csv','kind':'dataset_file','rows':n,'columns':header,'scope':'complete UTF-8 tabular structure and row widths; analytical rows remain in original export'}
 entry['validation']=value;return value

def evidence(record,ref,contract,s3,bucket,wanted='provider_record'):
 url=ref.get('source_url')or ref.get('url')or record.get('source_url')or''
 if urlsplit(url).hostname not in contract.get('allowed_hosts',[]):raise RawFailure('streaming_unapproved_origin')
 key=ref.get('key')
 if not key:
  from metadata_engine.evidence import s3_key
  key=s3_key(ref.get('s3_uri',''),bucket)
 if not key.startswith('research-data/'):key='research-data/'+key
 entry=download(s3,bucket,key,ref.get('sha256'));info=validate_file(entry)
 if info['format']=='sec_sgml':
  from metadata_engine.sec_documents import validate_url,DocumentError
  try:validate_url(url,info['accession'],info['ciks'])
  except DocumentError as e:raise RawFailure(str(e))from e
 if info['format']=='json':
  if record['source']!='trade_screening' or url!='https://data.trade.gov/downloadable_consolidated_screening_list/v1/consolidated.json':raise RawFailure('streaming_large_json_source_validator_required')
  data=record.get('payload',{}).get('data',{});rid=str(record.get('source_record_id'))
  from research_contract import digest
  provider_id=str(data.get('id'))
  composite=digest({'list':data.get('source'),'id':data.get('id')or digest(data)})
  identity_ok=rid==provider_id or (record.get('source_record_id_basis')=='documented_composite'and rid==composite)
  if not identity_ok or not entry['db'].execute('SELECT 1 FROM provider_rows WHERE signature=? AND provider_id=?',(_fingerprint(data),provider_id)).fetchone():raise RawFailure('trade_screening_original_row_mismatch')
 if wanted in ('full_text','primary_document','patent_document')and info['kind']!='document':raise RawFailure('streaming_required_original_document_missing')
 if record['source']=='hkex_news':
  from hkex_originals import document_url
  document_url(url)
 return {'artifact_kind':wanted,'s3_uri':'s3://'+bucket+'/'+key,'sha256':entry['sha256'],'bytes':entry['bytes'],'origin':'first_party_source','source_url':url,'retrieved_at':ref.get('retrieved_at'),'validation':{'streamed':True,**info}}

def register_source(db,source):
 """Queue discovery is a small cursor, not an all-jobs database scan."""
 from metadata_engine.runtime_db import encoded
 if source in db.cursor('streaming_source_catalog'):
  return
 with db.tx()as c:
  c.execute("INSERT IGNORE INTO engine_cursors VALUES('streaming_source_catalog','{}',UTC_TIMESTAMP(6))")
  c.execute("SELECT cursor_json FROM engine_cursors WHERE cursor_key='streaming_source_catalog' FOR UPDATE");value=json.loads(c.fetchone()['cursor_json'])
  if source in value:return
  value[source]=True
  c.execute("UPDATE engine_cursors SET cursor_json=%s,updated_at=UTC_TIMESTAMP(6) WHERE cursor_key='streaming_source_catalog'",(encoded(value),))
