"""Exact native filing indexes paired with original CNINFO PDFs/OpenDART XML ZIPs."""
import hashlib,json,zipfile,re
from pathlib import PurePosixPath
from functools import lru_cache
from urllib.parse import urlsplit,parse_qs
from xml.etree.ElementTree import ParseError, fromstring
from metadata_engine.evidence import RawFailure,object_bytes
from regional_source_review import in_scope

@lru_cache(maxsize=2)
def decoded(body):return json.loads(body)


def dart_xml_encoding(raw):
 """Validate the whole document and report a verified Korean encoding fallback."""
 fallback = None
 try:
  root = fromstring(raw)
 except (ParseError, ValueError, LookupError):
  # Legacy originals can carry Korean bytes even under a UTF-8 declaration.
  # Recognize the two legacy encodings only after strict UTF-8 decoding fails.
  try:
   raw.decode('utf-8')
  except UnicodeDecodeError:
   for encoding in ('euc-kr', 'cp949'):
    try:
     text = raw.decode(encoding, errors='strict')
    except UnicodeDecodeError:
     continue
    try:
     root = fromstring(text)
    except (ParseError, ValueError, LookupError):
     raise RawFailure('dart_original_xml_invalid') from None
    fallback = encoding
    break
   else:
    raise RawFailure('dart_original_xml_invalid') from None
  else:
   raise RawFailure('dart_original_xml_invalid') from None
 if len(''.join(root.itertext()).strip()) < 100:
  raise RawFailure('dart_original_xml_empty')
 return fallback


def dart_zip_validation(entry, rid):
 from metadata_engine.streaming import validate_file
 info=validate_file(entry)
 if info['format']!='zip':raise RawFailure('dart_original_is_not_zip')
 count=0;fallbacks=set()
 with zipfile.ZipFile(entry['path'])as archive:
  for member in archive.infolist():
   if member.is_dir():continue
   if member.filename.lower().endswith('.xml')and member.file_size>100:
    if not PurePosixPath(member.filename).stem.startswith(rid):raise RawFailure('dart_xml_receipt_mismatch')
    if member.file_size>64*1024**2:raise RawFailure('dart_xml_size_limit')
    encoding=dart_xml_encoding(archive.read(member))
    if encoding:fallbacks.add(encoding)
    count+=1
 if not count:raise RawFailure('dart_original_xml_missing')
 info={**info,'xml_documents':count}
 if fallbacks:info['xml_encoding_fallbacks']=sorted(fallbacks)
 return info


def evidence(record,s3,bucket,*,xml_only=False):
 from metadata_engine.streaming import download,validate_file
 source=record['source'];dart=source=='south_korea_fss_opendart';data=record['payload'].get('data',{});filing=data.get('filing');document=data.get('primary_document');ref=data.get('index_evidence')
 if not isinstance(filing,dict)or not ref or(not dart and not document):raise RawFailure('filing_original_document_missing')
 rid=str(filing.get('rcept_no'if dart else'announcementId',''))
 if record['source_record_id']!=rid:raise RawFailure('filing_provider_identity_mismatch')
 key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key;body=object_bytes(s3,bucket,key,16*1024**2,expected=ref['sha256']);index=decoded(body);items=index.get('list'if dart else'announcements',[])
 u=urlsplit(ref.get('source_url',''));expected=('opendart.fss.or.kr','/api/list.json')if dart else('www.cninfo.com.cn','/new/hisAnnouncement/query')
 if(u.hostname,u.path)!=expected or u.scheme!='https'or len([r for r in items if r==filing])!=1:raise RawFailure('filing_index_entire_native_row_mismatch')
 artifacts=[{'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':ref['sha256'],'bytes':len(body),'origin':'first_party_source','source_url':ref['source_url'],'retrieved_at':ref.get('retrieved_at'),'validation':{'provider':source,'record_type':'filing_index_row','scope':'Entire returned native index row, including corrections and original identifiers; not inferred issuer matching or availability time.'}}]
 if dart and not document:
  from metadata_engine.dart_xml_repair import repaired
  xml=repaired(s3,bucket,rid,ref['sha256'],'archived_index')
  if xml:return artifacts+[xml]
  if xml_only:raise RawFailure('filing_original_document_missing')
  from metadata_engine.dart_originals import repaired_artifacts
  alternate=repaired_artifacts(s3,bucket,rid,filing,ref['sha256'],anchor='archived_index')
  if alternate:return artifacts+alternate
  raise RawFailure('filing_original_document_missing')
 url=document.get('source_url','');du=urlsplit(url)
 if dart:
  if du.scheme!='https'or du.hostname!='opendart.fss.or.kr'or du.path!='/api/document.xml'or parse_qs(du.query)!={'rcept_no':[rid]}:raise RawFailure('dart_original_request_identity_mismatch')
 elif not in_scope(url,source)or du.path.rsplit('/',1)[-1].lower()!=rid+'.pdf':raise RawFailure('cninfo_primary_document_identity_mismatch')
 dk=document['key'];dk=dk if dk.startswith('research-data/')else'research-data/'+dk;entry=download(s3,bucket,dk,document['sha256'])
 if dart:
  try:info=dart_zip_validation(entry,rid)
  except RawFailure as error:
   from metadata_engine.dart_originals import REPAIR_REASONS,repaired_artifacts
   if str(error) in REPAIR_REASONS:
    from metadata_engine.dart_xml_repair import repaired
    xml=repaired(s3,bucket,rid,document['sha256'],'old_archive')
    if xml:return artifacts+[xml]
    if not xml_only:
     alternate=repaired_artifacts(s3,bucket,rid,filing,document['sha256'])
     if alternate:return artifacts+alternate
   raise
 else:
  info=validate_file(entry)
  if info['format']!='pdf':raise RawFailure('cninfo_primary_is_not_pdf')
 artifacts.append({'artifact_kind':'primary_document','s3_uri':'s3://'+bucket+'/'+dk,'sha256':document['sha256'],'bytes':entry['bytes'],'origin':'first_party_source','source_url':url,'retrieved_at':document.get('retrieved_at'),'validation':{**info,'provider':source,'record_type':'original_filing_document','scope':'Complete original PDF/XML filing tied to provider receipt identity; no XBRL fact extraction, complete market history or point-in-time vintage asserted.'}})
 return artifacts
