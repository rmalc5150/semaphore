"""Exact native filing indexes paired with original CNINFO PDFs/OpenDART XML ZIPs."""
import hashlib,json,zipfile,re
from pathlib import PurePosixPath
from functools import lru_cache
from urllib.parse import urlsplit,parse_qs
from metadata_engine.evidence import RawFailure,object_bytes
from regional_source_review import in_scope

@lru_cache(maxsize=2)
def decoded(body):return json.loads(body)

def evidence(record,s3,bucket):
 from metadata_engine.streaming import download,validate_file
 source=record['source'];dart=source=='south_korea_fss_opendart';data=record['payload'].get('data',{});filing=data.get('filing');document=data.get('primary_document');ref=data.get('index_evidence')
 if not isinstance(filing,dict)or not ref or not document:raise RawFailure('filing_original_document_missing')
 rid=str(filing.get('rcept_no'if dart else'announcementId',''))
 if record['source_record_id']!=rid:raise RawFailure('filing_provider_identity_mismatch')
 key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key;body=object_bytes(s3,bucket,key,16*1024**2,expected=ref['sha256']);index=decoded(body);items=index.get('list'if dart else'announcements',[])
 u=urlsplit(ref.get('source_url',''));expected=('opendart.fss.or.kr','/api/list.json')if dart else('www.cninfo.com.cn','/new/hisAnnouncement/query')
 if(u.hostname,u.path)!=expected or u.scheme!='https'or len([r for r in items if r==filing])!=1:raise RawFailure('filing_index_entire_native_row_mismatch')
 artifacts=[{'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':ref['sha256'],'bytes':len(body),'origin':'first_party_source','source_url':ref['source_url'],'retrieved_at':ref.get('retrieved_at'),'validation':{'provider':source,'record_type':'filing_index_row','scope':'Entire returned native index row, including corrections and original identifiers; not inferred issuer matching or availability time.'}}]
 url=document.get('source_url','');du=urlsplit(url)
 if dart:
  if du.scheme!='https'or du.hostname!='opendart.fss.or.kr'or du.path!='/api/document.xml'or parse_qs(du.query)!={'rcept_no':[rid]}:raise RawFailure('dart_original_request_identity_mismatch')
 elif not in_scope(url,source)or du.path.rsplit('/',1)[-1].lower()!=rid+'.pdf':raise RawFailure('cninfo_primary_document_identity_mismatch')
 dk=document['key'];dk=dk if dk.startswith('research-data/')else'research-data/'+dk;entry=download(s3,bucket,dk,document['sha256']);info=validate_file(entry)
 if dart:
  if info['format']!='zip':raise RawFailure('dart_original_is_not_zip')
  count=0
  with zipfile.ZipFile(entry['path'])as archive:
   for member in archive.infolist():
    if member.is_dir():continue
    if member.filename.lower().endswith('.xml')and member.file_size>100:
     if not PurePosixPath(member.filename).stem.startswith(rid):raise RawFailure('dart_xml_receipt_mismatch')
     # The provider's original XML can use its own DTD; no remote DTD is loaded.
     from xml.etree.ElementTree import fromstring,ParseError
     if member.file_size>64*1024**2:raise RawFailure('dart_xml_size_limit')
     raw=archive.read(member)
     try:root=fromstring(raw)
     except ParseError:raise RawFailure('dart_original_xml_invalid')from None
     if len(''.join(root.itertext()).strip())<100:raise RawFailure('dart_original_xml_empty')
     count+=1
  if not count:raise RawFailure('dart_original_xml_missing')
  info={**info,'xml_documents':count}
 elif info['format']!='pdf':raise RawFailure('cninfo_primary_is_not_pdf')
 artifacts.append({'artifact_kind':'primary_document','s3_uri':'s3://'+bucket+'/'+dk,'sha256':document['sha256'],'bytes':entry['bytes'],'origin':'first_party_source','source_url':url,'retrieved_at':document.get('retrieved_at'),'validation':{**info,'provider':source,'record_type':'original_filing_document','scope':'Complete original PDF/XML filing tied to provider receipt identity; no XBRL fact extraction, complete market history or point-in-time vintage asserted.'}})
 return artifacts
