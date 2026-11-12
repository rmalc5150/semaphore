"""Verify TED search records, complete XML and deterministic content chunks."""
import hashlib,json,re
from urllib.parse import urlsplit
from ted_enrichment import parse_xml,bounded_notice_items
class ProviderError(ValueError):pass

def require(ok,reason):
 if not ok:raise ProviderError(reason)
_cache_key=None
_cache_items=None
_cache_artifacts=None

def evidence(record,s3,bucket):
 from metadata_engine.evidence import object_bytes,RawFailure
 global _cache_key,_cache_items,_cache_artifacts
 data=record['payload']['data'];identity=data.get('parent_notice_id')or str(record['source_record_id']).split(':content:')[0];require(re.fullmatch(r'\d+-\d{4}',identity),'ted_invalid_notice_identity')
 refs=record['payload'].get('source_evidence',[]);api_refs=[r for r in refs if r.get('source_url')=='https://api.ted.europa.eu/v3/notices/search']
 matching=[r for r in refs if identity.replace('-','_')in r.get('package_member','')or r.get('source_url','').endswith('/'+identity+'/xml')]
 require(bool(api_refs),'ted_search_response_missing')
 if not matching:raise RawFailure('ted_matching_original_xml_missing')
 cache=(id(s3),bucket,identity,tuple(r.get('sha256')for r in api_refs+matching))
 if cache!=_cache_key:
  _cache_key=None;api=None;api_art=None
  for ref in api_refs:
   key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key;body=object_bytes(s3,bucket,key,expected=ref['sha256'])
   try:response=json.loads(body)
   except ValueError:continue
   require(response.get('timedOut')is not True and isinstance(response.get('notices'),list),'ted_invalid_search_response')
   def notice_id(row):
    value=row.get('publication-number')or row.get('notice-id');return value[0]if isinstance(value,list)and len(value)==1 else value
   rows=[r for r in response['notices']if notice_id(r)==identity]
   if len(rows)!=1:continue
   api=rows[0];api_art={'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':ref['sha256'],'bytes':len(body),'origin':'first_party_source','source_url':ref['source_url'],'validation':{'provider':'TED notices','notice_id':identity}};break
  require(api is not None,'ted_notice_not_in_original_search')
  ref=matching[0];url=ref['source_url'];u=urlsplit(url);require(u.scheme=='https'and u.netloc=='ted.europa.eu'and (u.path.startswith('/packages/daily/')or u.path.endswith('/'+identity+'/xml')),'ted_unapproved_xml_origin');key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key;body=object_bytes(s3,bucket,key,expected=ref['sha256'])
  try:enrichment=parse_xml(body,identity)
  except Exception as error:raise RawFailure('ted_xml_identity_or_structure_invalid:'+type(error).__name__)from None
  enrichment['retrieval_method']='daily_xml_package'if u.path.startswith('/packages/daily/')else'individual_xml'
  complete={**api,'notice_xml':body.decode('utf-8-sig'),'enrichment':enrichment}
  factory=lambda rid,value,url,day=None:{'id':rid,'data':value}
  items=bounded_notice_items(identity,complete,record['source_url'],None,factory);_cache_items={r['id']:r['data']for r in items};_cache_artifacts=[api_art,{'artifact_kind':'primary_document','s3_uri':'s3://'+bucket+'/'+key,'sha256':ref['sha256'],'bytes':len(body),'origin':'first_party_source','source_url':url,'validation':{'provider':'TED original XML','notice_id':identity}}];_cache_key=cache
 require(_cache_items.get(str(record['source_record_id']))==data,'ted_mapped_notice_or_content_chunk_differs_from_original')
 require(record['source_url']=='https://ted.europa.eu/en/notice/-/detail/'+identity,'ted_notice_url_mismatch')
 return _cache_artifacts
