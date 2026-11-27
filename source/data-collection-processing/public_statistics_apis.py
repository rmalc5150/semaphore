"""Bounded PortWatch pages and dynamically discovered UNIDO data requests."""
import json
from datetime import date,timedelta
from urllib.parse import urlencode
import requests
from regulatory_collection import require,SourceIssue
from research_contract import digest
PORTWATCH='https://services9.arcgis.com/weJ1QsnbMYJlCHdG/ArcGIS/rest/services/Daily_Ports_Data/FeatureServer/0/query'
UNIDO='https://stat.unido.org/portal/dataset/'

def post_unido(client,query):
 from constellation.shared_limits import admit
 url=UNIDO+'getData';admit(url)
 try:
  with requests.post(url,json=query,timeout=(10,35),stream=True,allow_redirects=False)as r:
   body=bytearray()
   for chunk in r.iter_content(65536):
    body.extend(chunk);require(len(body)<=16*1024*1024,'unido_response_too_large_split_scope')
   client.save(bytes(body),url+'?request_sha256='+digest(query),r.headers.get('Content-Type','application/json'))
   require(r.status_code==200,'source_http_'+str(r.status_code))
   return json.loads(body)
 except SourceIssue:raise
 except(ValueError,requests.RequestException):raise SourceIssue('unido_request_or_json_failed',True)from None

def fetch(client,job,cursor,item):
 from additional_source_apis import get_json
 p=job['parameters'];state=json.loads(cursor)if cursor else{};start=job['start'];end=job['end']
 if job['adapter']=='additional_portwatch':
  require(p['url']==PORTWATCH,'portwatch_unreviewed_endpoint')
  where="date >= DATE '"+start+"' AND date < DATE '"+end+"'"
  total,_=get_json(client,PORTWATCH,{'where':where,'returnCountOnly':'true','f':'json'})
  total=total.get('count');require(type(total)is int and total>=0,'portwatch_missing_count')
  if state:require(state['total']==total,'source_changed_refresh_required')
  client.expected_records=total
  if total==0:return [],None
  offset=state.get('offset',0)
  response,_=get_json(client,PORTWATCH,{'where':where,'outFields':'*','returnGeometry':'false','orderByFields':'ObjectId ASC','resultRecordCount':1000,'resultOffset':offset,'f':'json'})
  require(not response.get('error')and isinstance(response.get('features'),list),'portwatch_invalid_features')
  rows=[];last=state.get('last_object_id',-1)
  for feature in response['features']:
   value=feature['attributes'];day=value['date'];oid=value['ObjectId']
   require(start<=day<end and type(oid)is int and oid>last,'portwatch_date_or_order_mismatch');last=oid
   require(value.get('portid')and all(k in value for k in ('portcalls','import','export')),'portwatch_fields_missing')
   rows.append(item(value['portid']+':'+day,value,PORTWATCH,day,basis='derived'))
  following=offset+len(rows);require(rows and following<=total,'portwatch_truncated_or_changed_page')
  if following<total:
   require(response.get('exceededTransferLimit')is True,'portwatch_unexplained_partial_page')
   return rows,json.dumps({'offset':following,'total':total,'last_object_id':last})
  return rows,None
 require(job['adapter']=='additional_unido','unknown_public_statistics_adapter')
 dataset=p['dataset'];require(dataset in ('IIP','INDSTAT/4'),'unido_unreviewed_dataset')
 metadata,_=get_json(client,UNIDO+'getDataset/'+dataset)
 require(type(metadata.get('id'))is int and isinstance(metadata.get('countries'),list),'unido_catalogue_shape')
 countries=[c for c in metadata['countries']if not p.get('country_code')or c['c']==p['country_code']]
 variables=[v for v in metadata['variables']if not p.get('variable_code')or v['c']==p['variable_code']]
 periods=[v for v in metadata['periods']if start[:4]<=str(v)[:4]<end[:4]or(start[:4]==end[:4]and str(v).startswith(start[:4]))]
 activities=[v['c']for v in metadata['activities']]
 require(countries and variables and activities,'unido_empty_request_dimensions')
 revision=digest(metadata)
 if state:require(state['catalogue_sha256']==revision,'source_changed_refresh_required')
 cpos=state.get('country_position',0);vpos=state.get('variable_position',0)
 require(cpos<len(countries)and vpos<len(variables),'unido_cursor_outside_catalogue')
 query={'datasetId':metadata['id'],'countryCode':countries[cpos]['c'],'variableCode':variables[vpos]['c'],
        'activityCodes':activities,'periods':periods,'fullPrecision':True}
 response=post_unido(client,query)if periods else{'data':[],'ym':[],'am':[]}
 require(isinstance(response,dict)and isinstance(response.get('data'),list),'unido_data_response_shape')
 rows=[]
 for native in response['data']:
  require(isinstance(native,dict)and all(k in native for k in ('p','a'))and any(k in native for k in ('v','c','cn'))and native['p']in periods and native['a']in activities,'unido_measurement_outside_request')
  value={'dataset':dataset,'country':countries[cpos],'variable':variables[vpos],
         'native_observation':native,'request':query,'response_context':{k:v for k,v in response.items()if k!='data'}}
  identity=digest([dataset,query['countryCode'],query['variableCode'],native['p'],native['a']])
  # Provider period strings include annual, monthly and quarterly forms. Preserve
  # them without inventing a day or publication time.
  rows.append(item(identity,value,UNIDO+'getData',None,basis='derived'))
 following_variable=vpos+1;following_country=cpos
 if following_variable>=len(variables):following_variable=0;following_country+=1
 if following_country<len(countries):
  return rows,json.dumps({'country_position':following_country,'variable_position':following_variable,'catalogue_sha256':revision})
 return rows,None
