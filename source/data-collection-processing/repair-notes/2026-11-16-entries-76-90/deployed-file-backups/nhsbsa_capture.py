"""Bounded full-field NHSBSA EPD datastore pages; monthly exports can be gigabytes."""
import json,re
from research_contract import digest
from regulatory_collection import require
API='https://opendata.nhsbsa.net/api/3/action/'

def fetch(client,job,cursor,item):
 from additional_source_apis import get_json
 p=job['parameters'];state=json.loads(cursor)if cursor else{}
 catalogue,_=get_json(client,API+'package_show',{'id':'english-prescribing-data-epd'});require(catalogue.get('success')is True,'nhsbsa_catalogue_error')
 resources=[r for r in catalogue['result']['resources']if re.fullmatch(r'EPD_\d{6}',r.get('name',''))and r.get('format','').upper()=='CSV']
 require(resources,'nhsbsa_no_monthly_resources')
 name='EPD_'+p['period']if p.get('period')else max(r['name']for r in resources)
 require(any(r['name']==name for r in resources),'nhsbsa_month_not_published')
 if state:require(state['resource']==name,'source_changed_refresh_required')
 offset=state.get('offset',0);sort='YEAR_MONTH asc,PRACTICE_CODE asc,BNF_CODE asc,QUANTITY asc'
 raw,_=get_json(client,API+'datastore_search',{'resource_id':name,'limit':1000,'offset':offset,'sort':sort})
 require(raw.get('success')is True,'nhsbsa_datastore_error');d=raw['result'];rows=d.get('records');total=d.get('total');require(isinstance(rows,list)and type(total)is int and d.get('resource_id')==name,'nhsbsa_response_shape')
 if state:require(state['total']==total,'source_changed_refresh_required')
 client.expected_records=total
 fields=d['fields'];require(all(isinstance(r,dict)and str(r.get('YEAR_MONTH'))==name[4:]for r in rows),'nhsbsa_period_mismatch')
 values=[]
 for i,row in enumerate(rows):
  value={'resource':name,'row_number':offset+i,'native_record':row,'fields':fields,'dataset_id':'english-prescribing-data-epd'}
  values.append(item(digest([name,offset+i,row]),value,API+'datastore_search',None,basis='derived'))
 following=offset+len(rows);require(following<=total and(rows or following==total),'nhsbsa_truncated_page')
 return values,json.dumps({'resource':name,'total':total,'offset':following})if following<total else None
