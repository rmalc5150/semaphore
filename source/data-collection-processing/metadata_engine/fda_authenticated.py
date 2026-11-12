"""Verify complete returned FDA dashboard, iRES and PCB records against originals."""
import hashlib,json
from datetime import date,datetime
from urllib.parse import urlsplit
from research_contract import digest
SOURCES={
'fda_dd_compliance_actions':('api-datadashboard.fda.gov','/v1/compliance_actions','ActionTakenDate',['CaseInjunctionID','ActionType']),
'fda_dd_import_refusals':('api-datadashboard.fda.gov','/v1/import_refusals','RefusalDate',['ShipmentID','ProductCode']),
'fda_dd_inspections_citations':('api-datadashboard.fda.gov','/v1/inspections_citations','InspectionEndDate',['InspectionID','CitationID']),
'fda_ires_recalls':('www.accessdata.fda.gov','/rest/iresapi/recalls','eventlmd',['productid']),
'fda_product_codes':('www.accessdata.fda.gov','/rest/pcbapi/v1/industry',None,['INDID','INDDESC'])}
class ProviderError(ValueError):pass

def require(ok,reason):
 if not ok:raise ProviderError(reason)

def table(data):
 rows=data.get('RESULT')
 if isinstance(rows,dict):
  cols,values=rows.get('COLUMNS'),rows.get('DATA')
  require(isinstance(cols,list)and len(set(cols))==len(cols)and isinstance(values,list),'fda_invalid_table_columns')
  require(all(isinstance(v,list)and len(v)==len(cols)for v in values),'fda_invalid_table_width');rows=[dict(zip(cols,v))for v in values]
 require(isinstance(rows,list)and all(isinstance(r,dict)for r in rows),'fda_invalid_result_rows');return rows

_cache_identity=None
_cache_index=None

def provider_index(body,source,url):
 global _cache_identity,_cache_index
 host,path,_,_=SOURCES[source];u=urlsplit(url)
 require(u.scheme=='https'and u.netloc==host and u.path.rstrip('/')==path and not u.fragment,'fda_wrong_endpoint_for_source')
 cache=(hashlib.sha256(body).hexdigest(),source,url)
 if cache==_cache_identity:return _cache_index
 try:data=json.loads(body)
 except(ValueError,UnicodeError):raise ProviderError('fda_invalid_provider_json')from None
 require(isinstance(data,dict),'fda_invalid_response')
 if source.startswith('fda_dd_'):
  require(data.get('statuscode')==400,'fda_dashboard_provider_failure');rows=data.get('result');require(isinstance(rows,list)and data.get('resultcount')==len(rows)and type(data.get('totalrecordcount'))is int and data['totalrecordcount']>=len(rows),'fda_dashboard_counts_invalid')
 else:
  require(data.get('STATUSCODE',data.get('APIRETURNCODE'))==400,'fda_provider_failure');rows=table(data);total=data.get('RESULTCOUNT');require(type(total)is int and total>=len(rows),'fda_invalid_total')
  if source=='fda_product_codes':require(total==len(rows),'fda_incomplete_industry_reference')
 index={}
 for row in rows:
  require(isinstance(row,dict),'fda_invalid_provider_row')
  if source=='fda_ires_recalls':
   lowered={k.lower():v for k,v in row.items()};require(len(lowered)==len(row),'fda_conflicting_column_case');row=lowered;key=str(row.get('productid'))
  else:key=digest(row)
  require(key not in index or index[key]==row,'fda_conflicting_row_identity');index[key]=row
 _cache_identity=cache;_cache_index=index;return index

def validate(body,record,url):
 source=record.get('source');require(source in SOURCES,'fda_unknown_source');data=record.get('payload',{}).get('data');rid=str(record.get('source_record_id'));index=provider_index(body,source,url)
 require(isinstance(data,dict)and index.get(rid)==data,'fda_saved_row_differs_from_original')
 _,_,field,keys=SOURCES[source]
 require(all(data.get(k) not in (None,'')for k in keys),'fda_record_identity_fields_missing')
 u=urlsplit(record.get('source_url',''));host,path,_,_=SOURCES[source];require(u.scheme=='https'and u.netloc==host and u.path.rstrip('/')==path,'fda_record_url_mismatch')
 if field:
  value=str(data.get(field,''))[:10]
  try:day=datetime.strptime(value,'%m/%d/%Y').date().isoformat()if source=='fda_ires_recalls'else date.fromisoformat(value).isoformat()
  except ValueError:raise ProviderError('fda_invalid_source_date')from None
  scope=record.get('payload',{}).get('scope',{});require(scope.get('start','')<=day<scope.get('end',''),'fda_record_date_outside_scope')
 scope='complete_returned_api_record_not_primary_documents_or_historical_vintages'
 if source=='fda_product_codes':scope='current_industry_code_reference_not_full_five_component_taxonomy'
 if source=='fda_ires_recalls':scope='complete_returned_recall_row; legacy_selected_columns_flagged; event_modification_scope_not_recall_initiation_history'
 return {'provider':'FDA authenticated data','source':source,'retained_provider_fields':len(data),'completeness_scope':scope}

def context(record):
 source=record['source'];data=record['payload']['data'];scope=record['payload'].get('scope',{})
 if source=='fda_product_codes':return {'scope':'industry_reference','industry_code':data['INDID'],'industry_description':data['INDDESC'],'full_five_component_taxonomy':False,'historical_vintage_verified':False}
 if source=='fda_ires_recalls':return {'scope':'recall_record','product_id':str(data['productid']),'recall_number':data.get('recallnum'),'selection_date_basis':'eventlmd','legacy_selected_columns':scope.get('display_columns')!='','historical_vintage_verified':False}
 return {'scope':source.removeprefix('fda_dd_'),'date_field':SOURCES[source][2],'provider_date':data.get(SOURCES[source][2]),'fei':data.get('FEINumber'),'entity_match_status':'unresolved','primary_483_or_warning_letter_not_collected':True,'historical_vintage_verified':False}

_body_identity=None
_cached_body=None

def evidence(record,s3,bucket):
 from metadata_engine.evidence import object_bytes,RawFailure
 global _body_identity,_cached_body
 errors=[];source=record['source']
 for ref in record.get('payload',{}).get('source_evidence',[]):
  if not ref.get('key')or not ref.get('sha256')or urlsplit(ref.get('source_url','')).hostname!=SOURCES[source][0]:continue
  key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key;identity=(id(s3),bucket,key,ref['sha256'])
  if identity!=_body_identity:_body_identity=None;_cached_body=object_bytes(s3,bucket,key,expected=ref['sha256']);_body_identity=identity
  body=_cached_body
  try:info=validate(body,record,ref['source_url'])
  except ProviderError as e:errors.append(str(e));continue
  return [{'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'origin':'first_party_source','source_url':ref['source_url'],'retrieved_at':ref.get('retrieved_at'),'validation':info}]
 raise RawFailure(errors[0]if errors else'fda_matching_original_response_missing')
