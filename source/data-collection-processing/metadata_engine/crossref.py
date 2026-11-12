"""Validate complete Crossref proceedings metadata against original API responses."""
import hashlib,json,re
from urllib.parse import urlsplit,parse_qs,unquote
class ProviderError(ValueError):pass
_cache_identity=None
_cache_index=None
_body_identity=None
_cached_body=None

def require(ok,reason):
 if not ok:raise ProviderError(reason)

def doi(value):
 require(isinstance(value,str) and re.fullmatch(r'10\.[0-9]{4,9}/\S+',value.strip(),re.I),'crossref_invalid_doi');return value.strip().lower()

def index(body,url):
 global _cache_identity,_cache_index
 u=urlsplit(url);q=parse_qs(u.query)
 require(u.scheme=='https' and u.netloc=='api.crossref.org' and not u.fragment and (u.path=='/works' or u.path.startswith('/works/')),'crossref_unapproved_api_origin')
 require('select'not in q and 'fields'not in q,'crossref_projected_response_not_complete')
 identity=(hashlib.sha256(body).hexdigest(),url)
 if identity==_cache_identity:return _cache_index
 _cache_identity=None;_cache_index=None
 try:r=json.loads(body)
 except(ValueError,UnicodeError):raise ProviderError('crossref_invalid_provider_json')from None
 require(isinstance(r,dict) and r.get('status')=='ok','crossref_invalid_provider_status');message=r.get('message')
 if u.path=='/works':
  require(isinstance(message,dict)and isinstance(message.get('items'),list)and type(message.get('total-results'))is int,'crossref_invalid_work_list');items=message['items'];require(message['total-results']>=len(items),'crossref_invalid_total')
 else:
  require(isinstance(message,dict) and doi(unquote(u.path[len('/works/'):]))==doi(message.get('DOI')),'crossref_single_work_identity_mismatch');items=[message]
 out={}
 for item in items:
  require(isinstance(item,dict),'crossref_invalid_item');key=doi(item.get('DOI'));require(key not in out,'crossref_duplicate_primary_doi');out[key]=item
 _cache_identity=identity;_cache_index=out;return out

def validate(body,record,url):
 data=record.get('payload',{}).get('data',{});rid=doi(record.get('source_record_id'));require(isinstance(data,dict)and doi(data.get('DOI'))==rid,'crossref_record_doi_mismatch');require(data.get('type')=='proceedings-article','crossref_not_proceedings_article');require(index(body,url).get(rid)==data,'crossref_saved_record_differs_from_original')
 u=urlsplit(record.get('source_url',''));require(u.scheme=='https'and u.netloc=='doi.org'and doi(unquote(u.path.lstrip('/')))==rid,'crossref_record_url_mismatch')
 return {'provider':'Crossref proceedings metadata','doi':rid,'retained_provider_fields':len(data),'abstract_status':'provided'if data.get('abstract')else'not_deposited_in_returned_metadata','full_text_status':'not_collected_by_crossref_metadata_route','completeness_scope':'entire_returned_doi_metadata_record_not_proceedings_paper_or_historical_vintage'}

def evidence(record,s3,bucket):
 from metadata_engine.evidence import object_bytes,RawFailure
 global _body_identity,_cached_body
 errors=[]
 for ref in record.get('payload',{}).get('source_evidence',[]):
  if not ref.get('key')or not ref.get('sha256'):continue
  url=ref.get('source_url','');host=urlsplit(url).hostname
  if host!='api.crossref.org':continue
  key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key;identity=(id(s3),bucket,key,ref['sha256'])
  if identity!=_body_identity:
   _body_identity=None;_cached_body=object_bytes(s3,bucket,key,expected=ref['sha256']);_body_identity=identity
  body=_cached_body
  try:info=validate(body,record,url)
  except ProviderError as error:errors.append(str(error));continue
  return [{'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'origin':'first_party_source','source_url':url,'retrieved_at':ref.get('retrieved_at'),'validation':info}]
 raise RawFailure(errors[0]if errors else'crossref_matching_original_api_record_missing')

def from_public_receipt(receipt,s3,bucket):
 """Expand a saved original API page into DOI records, retaining its evidence."""
 from metadata_engine.evidence import object_bytes,s3_key,RawFailure
 from urllib.parse import quote
 uri=receipt.get('artifact_uri','');key=s3_key(uri,bucket);sha=receipt.get('sha256');require(sha,'crossref_public_receipt_checksum_missing');body=object_bytes(s3,bucket,key,expected=sha)
 try:items=index(body,receipt.get('source_url',''))
 except ProviderError as error:raise RawFailure(str(error))from None
 output=[]
 for rid,data in items.items():
  require(data.get('type')=='proceedings-article','crossref_public_response_wrong_work_type')
  output.append({'source':'crossref_proceedings','dataset':'conference_records','source_record_id':rid,'source_record_id_basis':'provider','ingested_at':receipt['retrieved_at'],'source_url':'https://doi.org/'+quote(rid,safe='/'),'available_at':None,'payload':{'record_type':'conference_publication','title':(data.get('title')or[None])[0],'data':data,'coverage_note':'Complete returned DOI metadata from an original archived API page; page capture does not establish exhaustive archive coverage or full paper access.','source_evidence':[{'key':key,'sha256':sha,'source_url':receipt['source_url'],'retrieved_at':receipt['retrieved_at']}]}})
 return output
