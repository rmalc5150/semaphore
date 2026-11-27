"""Match PortWatch and UNIDO measurements to complete saved native responses."""
import hashlib,json
from collections import OrderedDict
from urllib.parse import parse_qs,urlsplit
from research_contract import digest
from public_statistics_apis import PORTWATCH,UNIDO
_CACHE=OrderedDict()

def original(s3,bucket,key,expected,*,portwatch=False):
 from metadata_engine.evidence import object_bytes,RawFailure
 identity=(id(s3),bucket,key,expected,portwatch)
 if identity not in _CACHE:
  body=object_bytes(s3,bucket,key,expected=expected)
  raw=json.loads(body)
  if portwatch:
   if not isinstance(raw.get('features'),list):raise RawFailure('portwatch_original_not_full_feature_page')
   rows={}
   for feature in raw['features']:
    attrs=feature.get('attributes',{})
    oid=attrs.get('ObjectId')
    if type(oid) is not int or oid in rows:raise RawFailure('portwatch_original_object_id_not_unique')
    rows[oid]=attrs
   raw=rows
  if len(_CACHE)>=4:_CACHE.popitem(last=False)
  _CACHE[identity]=(body,raw)
 else:_CACHE.move_to_end(identity)
 return _CACHE[identity]

def evidence(record,s3,bucket):
 from metadata_engine.evidence import object_bytes,RawFailure,s3_key
 source=record['source'];payload=record['payload'];data=payload['data'];scope=payload.get('scope',{});errors=[]
 def require(ok,reason):
  if not ok:raise RawFailure(reason)
 for ref in payload.get('source_evidence',[]):
  if not ref.get('sha256'):continue
  url=ref.get('source_url','');u=urlsplit(url);q=parse_qs(u.query)
  if source=='imf_portwatch_shipping_activity'and url.split('?',1)[0]!=PORTWATCH:continue
  if source=='unido_iip_and_indstat'and url.split('?',1)[0]!=UNIDO+'getData':continue
  key=ref.get('key')or s3_key(ref.get('s3_uri',''),bucket);key=key if key.startswith('research-data/')else'research-data/'+key
  require(key.startswith('research-data/source_documents/'+source+'/'),'statistics_wrong_original_prefix')
  try:
   if source=='imf_portwatch_shipping_activity':
    require(q.get('outFields')==['*'],'portwatch_original_not_full_feature_page')
    body,raw=original(s3,bucket,key,ref['sha256'],portwatch=True)
    require(raw.get(data.get('ObjectId'))==data,'portwatch_original_row_mismatch')
    require(record['source_record_id']==data['portid']+':'+data['date']and(record.get('event_at')or{}).get('value')==data['date'],'portwatch_identity_or_date_mismatch')
    require(data['date']>=scope.get('data_start',data['date'])and data['date']<scope.get('data_end','9999-12-31'),'portwatch_scope_mismatch')
    kind='port_activity_observation';provider='IMF PortWatch native ArcGIS';description='Entire provider port/day attributes; calls and estimated import/export activity, not customs shipments or historical vintages.'
   else:
    body,raw=original(s3,bucket,key,ref['sha256'])
    request=data['request'];native=data['native_observation'];dataset=data['dataset']
    require(q.get('request_sha256')==[digest(request)]and request.get('fullPrecision')is True,'unido_request_provenance_mismatch')
    require(native in raw.get('data',[])and data['response_context']=={k:v for k,v in raw.items()if k!='data'},'unido_original_measurement_mismatch')
    require(native['p']in request['periods']and native['a']in request['activityCodes'],'unido_measurement_outside_request')
    require(record['source_record_id']==digest([dataset,request['countryCode'],request['variableCode'],native['p'],native['a']]),'unido_identity_mismatch')
    require(data['country']['c']==request['countryCode']and data['variable']['c']==request['variableCode'],'unido_dimension_mismatch')
    meta_url=UNIDO+'getDataset/'+dataset;metaref=next((r for r in payload['source_evidence']if r.get('source_url')==meta_url),None)
    require(metaref is not None,'unido_original_catalogue_link_missing')
    mkey=metaref['key'];mkey=mkey if mkey.startswith('research-data/')else'research-data/'+mkey
    _,meta=original(s3,bucket,mkey,metaref['sha256'])
    require(meta['id']==request['datasetId']and data['country']in meta['countries']and data['variable']in meta['variables'],'unido_dynamic_catalogue_mismatch')
    kind='industrial_statistics_observation';provider='UNIDO native data API';description='Matched native measurement plus dynamic dataset/country/variable/activity/period provenance; current vintages, not exhaustive history.'
   return [{'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':ref['sha256'],'bytes':len(body),'origin':'first_party_source','source_url':url,'retrieved_at':ref.get('retrieved_at'),
       'validation':{'provider':provider,'record_type':kind,'scope':description}}]
  except(RawFailure,KeyError,TypeError)as error:errors.append(str(error))
 raise RawFailure(errors[0]if errors else'statistics_matching_native_data_missing')
