"""Exact original-response checks for NIH grants and federal award/assignment rows."""
import hashlib,json
from urllib.parse import urlsplit
from research_contract import digest
SOURCES={'nih_reporter':('api.reporter.nih.gov','/v2/projects/search'), 'usa_spending':('api.usaspending.gov','/api/v2/search/spending_by_award'), 'uspto_assignment_histories':('api.uspto.gov','/api/v1/patent/applications/')}
class ProviderError(ValueError):pass

def require(ok,reason):
 if not ok:raise ProviderError(reason)
_cache_key=None
_cache_value=None

def original(body,url,source):
 global _cache_key,_cache_value
 u=urlsplit(url);host,path=SOURCES[source]
 require(u.scheme=='https'and u.netloc==host and not u.fragment and (u.path.startswith(path)if source=='uspto_assignment_histories'else u.path.rstrip('/')==path),'award_unapproved_api_endpoint')
 key=(hashlib.sha256(body).hexdigest(),url,source)
 if key==_cache_key:return _cache_value
 try:data=json.loads(body)
 except(ValueError,UnicodeError):raise ProviderError('award_invalid_original_json')from None
 require(isinstance(data,dict),'award_invalid_original_shape');_cache_key=key;_cache_value=data;return data

def validate(body,record,url):
 source=record.get('source');require(source in SOURCES,'award_unknown_source');original_data=original(body,url,source);data=record.get('payload',{}).get('data');rid=str(record.get('source_record_id'));require(isinstance(data,dict),'award_missing_data')
 if source=='nih_reporter':
  rows=original_data.get('results');meta=original_data.get('meta',{});require(isinstance(rows,list)and type(meta.get('total'))is int and meta['total']>=len(rows),'nih_invalid_response_counts');require(str(data.get('appl_id'))==rid and any(r==data for r in rows),'nih_entire_application_record_mismatch')
  v=urlsplit(record.get('source_url',''));require(v.scheme=='https'and v.netloc=='reporter.nih.gov'and v.path=='/project-details/'+rid,'nih_record_url_mismatch');scope='entire_returned_project_application_not_grant_proposal_or_historical_vintage'
 elif source=='usa_spending':
  rows=original_data.get('results');require(isinstance(rows,list)and isinstance(original_data.get('page_metadata',{}).get('hasNext'),bool),'usaspending_invalid_response');require(any(r==data for r in rows)and str(data.get('generated_internal_id')or digest(data))==rid,'usaspending_full_selected_award_row_mismatch');require(data.get('Award ID')and 'Award Amount'in data,'usaspending_award_identity_or_amount_missing');scope='complete_returned_selected_award_summary_not_transactions_all_recipients_or_full_award_detail'
 else:
  rows=original_data.get('patentFileWrapperDataBag');application=data.get('application_number');require(original_data.get('count')==1 and isinstance(rows,list)and len(rows)==1 and rows[0].get('applicationNumberText')==application,'assignment_application_mismatch');require(urlsplit(url).path=='/api/v1/patent/applications/'+application,'assignment_endpoint_identity_mismatch')
  events=rows[0].get('assignmentBag');require(isinstance(events,list)and data.get('original_chain')==events and data.get('event')in events,'assignment_original_chain_or_event_mismatch');require(rid==digest({'application':application,'event':data['event']}),'assignment_event_identity_mismatch');scope='complete_returned_recorded_assignment_chain_and_selected_event_not_recorded_deed_image_or_established_current_title'
 return {'provider':'official grants and award records','source':source,'retained_provider_fields':len(data),'completeness_scope':scope}

def context(record):
 source=record['source'];d=record['payload']['data']
 if source=='nih_reporter':return {'scope':'project_application','application_id':str(d['appl_id']),'project_number':d.get('project_num'),'award_notice_date':d.get('award_notice_date'),'project_start_date':d.get('project_start_date'),'award_amount_as_supplied':d.get('award_amount'),'historical_vintage_verified':False,'grant_proposal_document_collected':False}
 if source=='usa_spending':return {'scope':'selected_award_summary','transactions_collected':False,'full_award_detail_collected':False,'entity_match_status':'unresolved','historical_vintage_verified':False}
 return {'scope':'recorded_assignment_events','recorded_deed_images_collected':False,'current_ownership_established':False,'entire_returned_chain_retained':True}
_body_key=None
_body=None

def evidence(record,s3,bucket):
 from metadata_engine.evidence import object_bytes,RawFailure
 global _body_key,_body
 errors=[];source=record['source']
 for ref in record.get('payload',{}).get('source_evidence',[]):
  url=ref.get('source_url')or ref.get('url')or''
  if not ref.get('key')or not ref.get('sha256')or urlsplit(url).hostname!=SOURCES[source][0]:continue
  key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key;cache=(id(s3),bucket,key,ref['sha256'])
  if cache!=_body_key:_body_key=None;_body=object_bytes(s3,bucket,key,expected=ref['sha256']);_body_key=cache
  try:info=validate(_body,record,url)
  except ProviderError as e:errors.append(str(e));continue
  return [{'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':hashlib.sha256(_body).hexdigest(),'bytes':len(_body),'origin':'first_party_source','source_url':url,'retrieved_at':ref.get('retrieved_at'),'validation':info}]
 raise RawFailure(errors[0]if errors else'award_matching_original_missing')
