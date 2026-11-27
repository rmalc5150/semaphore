"""Validate SAM notice metadata against its complete archived provider page."""
from functools import lru_cache
from datetime import datetime
import hashlib,json
from urllib.parse import urlsplit,parse_qs

@lru_cache(maxsize=2)
def decode(body):return json.loads(body)

def validate(body,record,url):
 from metadata_engine.evidence import RawFailure
 def require(ok,reason):
  if not ok:raise RawFailure(reason)
 u=urlsplit(url);q=parse_qs(u.query);raw=decode(body);data=record['payload']['data']
 require(u.scheme=='https'and u.netloc=='api.sam.gov'and u.path in ('/opportunities/v2/search','/prod/opportunities/v2/search'),'sam_wrong_original_endpoint')
 rows=raw.get('opportunitiesData');require(isinstance(rows,list)and type(raw.get('totalRecords'))is int and raw['totalRecords']>=len(rows),'sam_invalid_native_page')
 require(data in rows and data.get('noticeId')==record['source_record_id'],'sam_original_notice_mismatch')
 stamp=data['postedDate'][:10];start=datetime.strptime(q['postedFrom'][0],'%m/%d/%Y').date().isoformat();stop=datetime.strptime(q['postedTo'][0],'%m/%d/%Y').date().isoformat()
 require(start<=stamp<=stop and(record.get('event_at')or{}).get('value')==stamp,'sam_posted_date_mismatch')
 return {'provider':'SAM.gov opportunities','record_type':'opportunity_notice_metadata','scope':'Entire returned notice metadata; descriptions and attachments remain separate linked resources, and notices are not proof of awards or historical vintages.'}

def evidence(record,s3,bucket):
 from metadata_engine.evidence import object_bytes,RawFailure
 errors=[]
 for ref in record['payload'].get('source_evidence',[]):
  if not ref.get('sha256')or not ref.get('key'):continue
  key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key
  if not key.startswith('research-data/source_documents/sam_gov_opportunities/'):continue
  body=object_bytes(s3,bucket,key,expected=ref['sha256'])
  try:info=validate(body,record,ref.get('source_url',''))
  except(ValueError,KeyError,TypeError)as error:errors.append(str(error));continue
  return [{'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'origin':'first_party_source','source_url':ref['source_url'],'retrieved_at':ref.get('retrieved_at'),'validation':info}]
 raise RawFailure(errors[0]if errors else'sam_matching_original_notice_missing')
