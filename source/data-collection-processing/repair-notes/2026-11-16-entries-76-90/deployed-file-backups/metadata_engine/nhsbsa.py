"""Verify an entire original EPD row and declared response dimensions."""
import hashlib,json
from functools import lru_cache
from urllib.parse import urlsplit,parse_qs
from research_contract import digest
@lru_cache(maxsize=2)
def decode(body):return json.loads(body)
def evidence(record,s3,bucket):
 from metadata_engine.evidence import object_bytes,RawFailure
 data=record['payload']['data'];errors=[]
 for ref in record['payload'].get('source_evidence',[]):
  u=urlsplit(ref.get('source_url',''));q=parse_qs(u.query)
  if u.scheme!='https'or u.netloc!='opendata.nhsbsa.net'or u.path!='/api/3/action/datastore_search':continue
  key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key;body=object_bytes(s3,bucket,key,expected=ref['sha256']);raw=decode(body)
  try:
   result=raw['result'];index=data['row_number']-int(q.get('offset',['0'])[0])
   assert raw.get('success')is True and q['resource_id']==[data['resource']]==[result['resource_id']]
   assert index>=0 and result['records'][index]==data['native_record']and result['fields']==data['fields']
   assert str(data['native_record']['YEAR_MONTH'])==data['resource'][4:]
   assert record['source_record_id']==digest([data['resource'],data['row_number'],data['native_record']])
  except(AssertionError,KeyError,ValueError,IndexError,TypeError)as e:errors.append(type(e).__name__);continue
  return [{'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'origin':'first_party_source','source_url':ref['source_url'],'retrieved_at':ref.get('retrieved_at'),'validation':{'provider':'NHSBSA native EPD','record_type':'prescribing_measurement','scope':'Entire native monthly practice/drug/quantity row with all cost/count fields; current released snapshot and provider page position, not patient-level data or full historical coverage.'}}]
 raise RawFailure('nhsbsa_original_row_mismatch:'+','.join(errors))
