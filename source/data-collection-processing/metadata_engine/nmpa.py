"""Verify NMPA inventory, full detail, and evidence-supported derived events."""
import hashlib,re
from html import unescape
from datetime import datetime
from urllib.parse import urlsplit,parse_qs
from raw_parsers.nmpa_tables import TableParser,parse_detail_page,structured_detail,digest
class ProviderError(ValueError):pass

def require(ok,reason):
 if not ok:raise ProviderError(reason)

def endpoint(url):
 u=urlsplit(url);require(u.scheme=='https' and u.netloc in ('www.chinadrugtrials.org.cn','chinadrugtrials.org.cn'),'nmpa_untrusted_origin')
 q=parse_qs(u.query,keep_blank_values=True)
 if u.path=='/clinicaltrials.searchlistdetail.dhtml':
  require(set(q)=={'reg_no'} and len(q['reg_no'])==1 and re.fullmatch(r'CTR20\d{6,}',q['reg_no'][0]),'nmpa_invalid_detail_identity');return 'detail',q['reg_no'][0]
 require(u.path=='/clinicaltrials.searchlist.dhtml' and set(q)<= {'keywords','currentpage'} and len(q.get('currentpage',[]))==1 and q['currentpage'][0].isdigit(),'nmpa_invalid_listing_url');return 'listing',int(q['currentpage'][0])

def inventory_rows(document):
 parser=TableParser();parser.feed(document);rows={}
 for cells in parser.rows:
  columns=[c['text']for c in cells];match=re.search(r'\bCTR20\d{6,}\b',' | '.join(columns))
  if match:
   rid=match[0];require(rid not in rows,'nmpa_duplicate_inventory_identity');rows[rid]=columns
 return rows

def validate_listing(document,record,url):
 kind,page=endpoint(url);require(kind=='listing','nmpa_inventory_requires_original_listing');p=record['payload'];rid=record['source_record_id'];rows=inventory_rows(document)
 require(p.get('registration_number')==rid and p.get('listing_page')==page and rows.get(rid)==p.get('search_result_columns'),'nmpa_original_inventory_row_mismatch')
 require(endpoint(record['source_url'])==('detail',rid) and endpoint(p.get('detail_url',''))==('detail',rid),'nmpa_inventory_detail_link_mismatch')
 visible=unescape(re.sub(r'<[^>]+>',' ',document));m=re.search(r'当前第\s*(\d+)\s*页\s*[,，]\s*共\s*(\d+)\s*页\s*[,，]\s*共\s*(\d+)\s*条记录',visible)
 require(m is not None and tuple(map(int,m.groups()))==(page,p.get('advertised_total_pages'),p.get('advertised_total_records')),'nmpa_inventory_page_totals_mismatch')
 require(rows[rid][-1]==p.get('title'),'nmpa_inventory_title_mismatch')
 return {'provider':'NMPA trials','registration_number':rid,'record_type':'registry_inventory','completeness_scope':'original_inventory_row_only_not_full_trial','listing_page':page,'column_count':len(rows[rid])}

def _evidence(record,s3,bucket):
 from metadata_engine.evidence import RawFailure,object_bytes
 p=record.get('payload',{});data=p.get('data',{});rid=record.get('source_record_id','');inventory=record.get('dataset')=='registry_inventory';registration=rid if inventory else data.get('registrationNumber');require(re.fullmatch(r'CTR20\d{6,}',registration or'')is not None,'nmpa_invalid_registration_number')
 docs=[];errors=[];artifacts=[];seen=set()
 for ref in p.get('source_evidence',[]):
  try:kind,identity=endpoint(ref.get('source_url',''))
  except ProviderError:continue
  if inventory and (kind!='listing' or identity!=p.get('listing_page')):continue
  if not inventory and kind=='detail' and identity!=registration:continue
  if not inventory and kind=='listing' and p.get('record_type')!='regulatory_event':continue
  key=ref.get('key');sha=ref.get('sha256')
  if not key or not sha or (key,sha)in seen:continue
  seen.add((key,sha));key=key if key.startswith('research-data/')else'research-data/'+key;body=object_bytes(s3,bucket,key,expected=sha)
  try:
   document=body.decode('utf-8-sig')
   if inventory:info=validate_listing(document,record,ref['source_url'])
   elif kind=='detail':
    facts=structured_detail(document,registration);fields=parse_detail_page(document);info={'provider':'NMPA trials','registration_number':registration,'record_type':p.get('record_type'),'completeness_scope':'current_original_trial_detail','field_count':len(fields)}
    if p.get('record_type')=='regulatory_event':docs.append((facts,ref));continue
    require(rid==registration and endpoint(record['source_url'])==('detail',registration),'nmpa_trial_record_identity_mismatch')
    require(fields==data.get('fields'),'nmpa_original_detail_fields_mismatch')
    if data.get('structured')is not None:require(facts==data['structured'],'nmpa_original_structured_facts_mismatch')
    dates=[m['date']for m in facts['milestones']if m['kind']=='FIRST_PUBLIC_DISCLOSURE'];require(data.get('firstPublicDisclosureDate')in dates or (not dates and data.get('firstPublicDisclosureDate')is None),'nmpa_first_disclosure_mismatch')
   else:
    columns=inventory_rows(document).get(registration)
    if columns:docs.append(({'registration_number':registration,'status':columns[2]if len(columns)>2 else None,'drug_name':columns[3]if len(columns)>3 else None,'indication':columns[4]if len(columns)>4 else None},ref))
    continue
  except (ValueError,UnicodeError)as error:errors.append(str(error));continue
  artifacts.append({'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'origin':'first_party_source','source_url':ref['source_url'],'retrieved_at':ref.get('retrieved_at'),'validation':info})
 if not inventory and p.get('record_type')=='regulatory_event':
  try:
   action=data.get('action');basis=data.get('date_basis');date=data.get('date');require(endpoint(record['source_url'])==('detail',registration),'nmpa_event_url_mismatch')
   matches=[]
   if basis=='explicit_source_date':
    require(rid==data.get('id')==f'{registration}:milestone:{action}:{date}','nmpa_milestone_identity_mismatch');matches=[(f,r)for f,r in docs if data.get('source_fact')in f.get('milestones',[]) and data['source_fact']['kind']==action and data['source_fact']['date']==date]
   elif action=='FIRST_OBSERVED':
    require(basis=='first_observed_not_trial_start' and rid==data.get('id')==registration+':first_observed','nmpa_observation_event_identity_mismatch');datetime.fromisoformat(date.replace('Z','+00:00'));matches=[(f,r)for f,r in docs if f.get('version')=='nmpa-structured-changes-v1']
   elif action=='TRIAL_CHANGE_OBSERVED':
    interval=data.get('observation_interval',{});delta=data.get('changes',{});require(basis=='observed_change_not_actual_change_date' and delta and date==interval.get('on_or_before') and datetime.fromisoformat(interval['after'].replace('Z','+00:00'))<datetime.fromisoformat(date.replace('Z','+00:00')),'nmpa_change_interval_invalid')
    require(rid==data.get('id')==registration+':change:'+digest([interval['after'],date,delta]),'nmpa_change_identity_mismatch')
    before=[(f,r)for f,r in docs if all(f.get(k)==v.get('before')for k,v in delta.items())];after=[(f,r)for f,r in docs if all(f.get(k)==v.get('after')for k,v in delta.items())];require(before and after,'nmpa_change_both_source_versions_required');matches=before+after
   require(matches,'nmpa_unsupported_or_unmatched_event')
   for facts,ref in matches:
    key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key
    artifacts.append({'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':ref['sha256'],'origin':'first_party_source','source_url':ref['source_url'],'validation':{'provider':'NMPA trials','registration_number':registration,'record_type':'regulatory_event','date_basis':basis,'completeness_scope':'matched_source_milestone'if basis=='explicit_source_date'else'collector_observation_not_actual_trial_change_date'}})
  except (ValueError,KeyError,TypeError)as error:errors.append(str(error))
 if not artifacts:raise RawFailure(errors[0]if errors else'nmpa_matching_original_evidence_missing')
 return artifacts


def evidence(record,s3,bucket):
 from metadata_engine.evidence import RawFailure
 try:return _evidence(record,s3,bucket)
 except ProviderError as error:raise RawFailure(str(error))from None
