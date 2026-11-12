"""Validate full CMS dataset descriptors without calling them payment records."""
import hashlib,json,uuid
from urllib.parse import urlsplit
class ProviderError(ValueError):pass

def require(ok,reason):
 if not ok:raise ProviderError(reason)

def identifier(value):
 try:result=str(uuid.UUID(value))
 except (ValueError,TypeError,AttributeError):raise ProviderError('cms_catalog_invalid_identifier')from None
 require(result==value,'cms_catalog_noncanonical_identifier');return result

_cache_identity=None
_cache_index=None

def validate(body,record,url):
 global _cache_identity,_cache_index
 u=urlsplit(url)
 require(u.scheme=='https' and u.netloc=='openpaymentsdata.cms.gov' and u.path.rstrip('/')=='/api/1/metastore/schemas/dataset/items' and not u.query and not u.fragment,'cms_catalog_wrong_api_origin')
 cache=(hashlib.sha256(body).hexdigest(),url)
 if cache!=_cache_identity:
  try:rows=json.loads(body)
  except (ValueError,UnicodeError):raise ProviderError('cms_catalog_invalid_json')from None
  require(isinstance(rows,list)and bool(rows),'cms_catalog_not_dataset_list');index={}
  for row in rows:
   require(isinstance(row,dict),'cms_catalog_invalid_descriptor');rid=identifier(row.get('identifier'))
   require(rid not in index or index[rid]==row,'cms_catalog_conflicting_duplicate_identifier');index[rid]=row
  _cache_identity=cache;_cache_index=index
 data=record.get('payload',{}).get('data');rid=identifier(record.get('source_record_id'))
 require(isinstance(data,dict)and identifier(data.get('identifier'))==rid,'cms_catalog_record_identity_mismatch')
 require(_cache_index.get(rid)==data,'cms_catalog_descriptor_differs_from_original')
 require(data.get('publisher',{}).get('name')=='openpaymentsdata.cms.gov' and bool(data.get('title')),'cms_catalog_invalid_publisher_or_title')
 distributions=data.get('distribution',[])
 require(isinstance(distributions,list)and any(d.get('downloadURL') and urlsplit(d['downloadURL']).scheme=='https' and urlsplit(d['downloadURL']).hostname in ('download.cms.gov','downloads.cms.gov','openpaymentsdata.cms.gov')for d in distributions),'cms_catalog_official_download_missing')
 v=urlsplit(record.get('source_url',''));require(v.scheme=='https'and v.netloc=='openpaymentsdata.cms.gov'and v.path=='/dataset/'+rid and not v.query,'cms_catalog_record_url_mismatch')
 return {'provider':'CMS Open Payments catalog','dataset_id':rid,'retained_provider_fields':len(data),'completeness_scope':'complete_returned_dataset_descriptor_not_individual_financial_records'}

_body_identity=None
_cached_body=None

def evidence(record,s3,bucket):
 from metadata_engine.evidence import object_bytes,RawFailure
 global _body_identity,_cached_body
 errors=[]
 for ref in record.get('payload',{}).get('source_evidence',[]):
  if not ref.get('key')or not ref.get('sha256')or urlsplit(ref.get('source_url','')).hostname!='openpaymentsdata.cms.gov':continue
  key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key;identity=(id(s3),bucket,key,ref['sha256'])
  if identity!=_body_identity:
   _body_identity=None;_cached_body=object_bytes(s3,bucket,key,expected=ref['sha256']);_body_identity=identity
  body=_cached_body
  try:info=validate(body,record,ref['source_url'])
  except ProviderError as e:errors.append(str(e));continue
  return [{'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'origin':'first_party_source','source_url':ref['source_url'],'retrieved_at':ref.get('retrieved_at'),'validation':info}]
 raise RawFailure(errors[0]if errors else'cms_catalog_original_descriptor_missing')
