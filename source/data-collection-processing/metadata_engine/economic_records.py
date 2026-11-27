"""Exact original-row validation for WTO, EPO legal events and Ember."""
import hashlib,json
from datetime import date,timedelta
from functools import lru_cache
from urllib.parse import parse_qs,urlsplit
import xml.etree.ElementTree as ET
from research_contract import digest

SOURCES=('wto_quantitative_restrictions_api','wto_eping_sps_tbt_notifications',
         'epo_ops_patent_legal_events','ember_electricity_demand_and_generation')
class ProviderError(ValueError):pass
def require(ok,reason):
 if not ok:raise ProviderError(reason)
@lru_cache(maxsize=1)
def decode(body):
 try:return json.loads(body)
 except(ValueError,UnicodeError):raise ProviderError('economic_original_not_json')from None
def xml_canonical(text):return ET.canonicalize(text,rewrite_prefixes=True)

def validate(body,record,url):
 source=record['source'];payload=record['payload'];data=payload['data'];scope=payload.get('scope',{});u=urlsplit(url);q=parse_qs(u.query)
 require(u.scheme=='https'and not u.username and not u.password and u.port in (None,443),'economic_untrusted_original_url')
 if source=='wto_quantitative_restrictions_api':
  resource=scope.get('resource');require(resource in ('notifications','qrs')and u.netloc=='api.wto.org'and u.path=='/qrs/'+resource,'wto_qr_wrong_endpoint')
  raw=decode(body);rows=raw.get('data');meta=raw.get('meta',{})
  require(isinstance(rows,list)and isinstance(meta.get('total'),int)and meta['total']>=len(rows)
          and meta.get('current_page')==int(q.get('page',['0'])[0]),'wto_qr_invalid_page')
  require(data in rows,'wto_qr_original_row_mismatch')
  identity=str(data.get('id')or data.get('document_symbol')or'');require(identity and record['source_record_id']==resource+':'+identity,'wto_qr_identity_mismatch')
  field='notification_dt'if resource=='notifications'else'in_force_from';stamp=data.get(field,'')
  year=str(scope.get('year'));parameter='notification_year'if resource=='notifications'else'year_of_entry_into_force'
  require(stamp and stamp[:4]==year and q.get(parameter)==[year]and(record.get('event_at')or{}).get('value')==stamp[:10],'wto_qr_date_or_scope_mismatch')
  kind='trade_restriction_notification'if resource=='notifications'else'trade_restriction_record'
  return {'provider':'WTO quantitative restrictions','record_type':kind,'scope':'Entire returned notification/restriction record; linked documents, current legal effect and older restrictions outside query years remain separate.'}
 if source=='wto_eping_sps_tbt_notifications':
  require(u.netloc=='api.wto.org'and u.path=='/eping/notifications/search','wto_eping_wrong_endpoint')
  raw=decode(body);rows=raw.get('items');require(isinstance(rows,list)and type(raw.get('totalCount'))is int and raw['totalCount']>=len(rows)
    and raw.get('currentPage')==int(q.get('page',['0'])[0]),'wto_eping_invalid_page')
  require(data in rows and str(data.get('id'))==record['source_record_id'],'wto_eping_original_row_or_id_mismatch')
  start=q.get('distributionDateFrom',[''])[0];end=q.get('distributionDateTo',[''])[0];stamp=data.get('distributionDate','')[:10]
  require(start<=stamp<=end and scope.get('data_start',start)==start
    and scope.get('data_end',(date.fromisoformat(end)+timedelta(days=1)).isoformat())==(date.fromisoformat(end)+timedelta(days=1)).isoformat()
    and(record.get('event_at')or{}).get('value')==stamp,'wto_eping_distribution_window_mismatch')
  return {'provider':'WTO ePing','record_type':'trade_notification_metadata','scope':'Entire returned English SPS/TBT notification metadata, including revisions/addenda; attachments are links, not downloaded regulatory text.'}
 if source=='ember_electricity_demand_and_generation':
  dataset=scope.get('dataset');require(dataset in ('electricity-generation','electricity-demand')and u.netloc=='api.ember-energy.org'and u.path=='/v1/'+dataset+'/monthly','ember_wrong_dataset_endpoint')
  raw=decode(body);rows=raw.get('data');require(isinstance(rows,list)and raw.get('stats',{}).get('number_of_records')==len(rows),'ember_incomplete_response')
  native={k:v for k,v in data.items()if k not in ('dataset','attribution')};require(native in rows and data.get('dataset')==dataset,'ember_original_row_mismatch')
  identity=digest({'dataset':dataset,**{k:native.get(k)for k in ('entity','entity_code','date','series','is_aggregate_entity','is_aggregate_series')}})
  require(identity==record['source_record_id'],'ember_identity_mismatch')
  period=native.get('date','')[:7];require(scope.get('data_start','')[:7]<=period<scope.get('data_end','')[:7],'ember_month_outside_scope')
  require(q.get('start_date')==[scope['data_start'][:7]]and q.get('end_date')==[(date.fromisoformat(scope['data_end'])-timedelta(days=1)).isoformat()[:7]],'ember_query_window_mismatch')
  return {'provider':'Ember','record_type':'electricity_observation','scope':'Entire returned monthly row with native units and aggregation flags; current released data, missing months not zero; Ember attribution retained.'}
 if source=='epo_ops_patent_legal_events':
  reference=data.get('publication_reference','');require(u.netloc=='ops.epo.org'and u.path=='/3.2/rest-services/legal/publication/docdb/'+reference,'epo_wrong_legal_endpoint')
  root=ET.fromstring(body);require(root.tag=='{http://ops.epo.org}world-patent-data','epo_wrong_xml_envelope')
  from epo_ops import legal_rows
  def item(identity,value,source_url,day=None,basis=None):return {'id':identity,'data':value,'url':source_url,'date':day}
  candidates=legal_rows(root,reference,scope,item)
  wanted=next((r for r in candidates if r['id']==record['source_record_id']),None)
  require(wanted is not None,'epo_original_event_identity_missing')
  require(wanted['data']==data,'epo_original_event_mapping_mismatch')
  expected=wanted['date'];require((record.get('event_at')or{}).get('value')==expected,'epo_gazette_date_mismatch')
  return {'provider':'EPO OPS INPADOC','record_type':'patent_legal_event','scope':'Matched original legal event and family identifiers; gazette, effective, created and exchanged dates remain distinct. Applicant links, current title and historical vintages unverified.'}
 raise ProviderError('economic_source_not_supported')

def evidence(record,s3,bucket):
 from metadata_engine.evidence import object_bytes,s3_key,RawFailure
 errors=[];source=record['source']
 for ref in record.get('payload',{}).get('source_evidence',[]):
  if not ref.get('sha256'):continue
  key=ref.get('key')or s3_key(ref.get('s3_uri',''),bucket);key=key if key.startswith('research-data/')else'research-data/'+key
  if not key.startswith('research-data/source_documents/'+source+'/'):continue
  body=object_bytes(s3,bucket,key,expected=ref['sha256'])
  try:info=validate(body,record,ref.get('source_url',''))
  except(ProviderError,ValueError,ET.ParseError,KeyError,TypeError)as error:errors.append(str(error));continue
  return [{'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),
    'origin':'first_party_source','source_url':ref['source_url'],'retrieved_at':ref.get('retrieved_at'),'validation':info}]
 raise RawFailure(errors[0]if errors else'economic_matching_original_missing')
