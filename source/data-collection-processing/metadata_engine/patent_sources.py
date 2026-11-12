"""Dataset-specific original checks for patent bibliography and USPTO prosecution."""
import hashlib,json,re,io
from urllib.parse import urlsplit
from patent_collection import export_record,odp_record
from patent_bigquery_collection import decode_row
from patent_prosecution import normalize
class ProviderError(ValueError):pass

def require(ok,reason):
 if not ok:raise ProviderError(reason)

def json_body(body):
 try:value=json.loads(body)
 except(ValueError,UnicodeError):raise ProviderError('patent_invalid_original_json')from None
 require(isinstance(value,dict),'patent_invalid_original_envelope');return value

def validate_google(body,record,url):
 u=urlsplit(url);require(u.scheme=='https'and u.netloc=='bigquery.googleapis.com'and re.fullmatch(r'/bigquery/v2/projects/[^/]+/queries/[^/]+',u.path),'patent_unapproved_bigquery_page')
 raw=json_body(body);require(raw.get('jobComplete')is True and isinstance(raw.get('rows'),list)and raw.get('schema',{}).get('fields'),'patent_bigquery_incomplete_response')
 parts=u.path.split('/');ref=raw.get('jobReference',{});require(ref.get('projectId')==parts[4]and ref.get('jobId')==parts[6],'patent_bigquery_job_identity_mismatch')
 rid=record['source_record_id'];matches=[decode_row(raw['schema']['fields'],r)for r in raw['rows']if r.get('f')]
 matches=[r for r in matches if r.get('publication_number')==rid];require(len(matches)==1 and export_record(matches[0])==record['payload']['data'],'patent_bigquery_bibliography_mismatch')
 require(record.get('source_url')=='https://patents.google.com/patent/'+rid,'patent_bigquery_record_url_mismatch');return matches[0]

def validate_odp(body,record,url):
 u=urlsplit(url);require(u.scheme=='https'and u.netloc=='api.uspto.gov','patent_unapproved_odp_origin');raw=json_body(body);dataset=record['dataset'];data=record['payload']['data'];rid=str(record['source_record_id'])
 if dataset in ('patent_records','patent_assignment_records'):
  require(u.path=='/api/v1/patent/applications/search'or re.fullmatch(r'/api/v1/patent/applications/[A-Za-z0-9]+',u.path),'patent_wrong_application_endpoint');rows=raw.get('patentFileWrapperDataBag');require(isinstance(rows,list)and raw.get('count',0)>=len(rows),'patent_application_envelope_invalid');matches=[r for r in rows if r.get('applicationNumberText')==rid];require(len(matches)==1,'patent_application_not_in_original');expected=odp_record(matches[0])
  if dataset=='patent_assignment_records':
   # This collector publishes a normalized ledger, not the raw assignmentBag.
   # Verify provider-derived events; entity-review candidates remain unverified.
   from patent_assignments import normalize_history
   class UnresolvedReviewer:
    def party(self,name,role,recorded):return {'reported_name':name,'role':role}
   history=normalize_history(matches[0],UnresolvedReviewer());actual=data.get('assignment_history',{})
   def provider_fields(value):
    if isinstance(value,dict):return {k:provider_fields(v)for k,v in value.items()if k!='reported_recipient_links'}
    if isinstance(value,list):return [provider_fields(v)for v in value]
    return value
   require(provider_fields(actual)==provider_fields(history),'patent_assignment_ledger_differs_from_original')
   for event in actual.get('events',[]):
    links=event.get('reported_recipient_links',[]);names=[a['assigneeNameText']for a in event.get('assignees',[])if a.get('assigneeNameText')]
    require([v.get('reported_name')for v in links]==names and all(v.get('role')=='assignment_recipient'for v in links),'patent_assignment_reported_names_mismatch')
   expected['assignment_history']=actual
  require(data==expected,'patent_application_mapping_differs_from_original');return matches[0]
 require(dataset in ('patent_office_actions','patent_petition_decisions'),'patent_unsupported_dataset')
 if dataset=='patent_office_actions':
  require(u.path=='/api/v1/patent/oa/oa_actions/v1/records','patent_wrong_office_action_endpoint');rows=raw.get('response',{}).get('docs',[]);key='id'
 else:
  require(u.path in ('/api/v1/petition/decisions/search','/api/v1/petition/decisions/'+rid),'patent_wrong_petition_endpoint');rows=raw.get('petitionDecisionDataBag',[]);key='petitionDecisionRecordIdentifier'
 matches=[r for r in rows if str(r.get(key))==rid];require(len(matches)==1,'patent_prosecution_record_missing');expected=normalize(dataset,matches[0]);require(all(data.get(k)==v for k,v in expected.items()),'patent_prosecution_mapping_differs_from_original');return matches[0]

_body_cache={}
def evidence(record,s3,bucket):
 from metadata_engine.evidence import object_bytes,RawFailure
 global _body_cache
 source=record['source'];refs=record['payload'].get('source_evidence',[]);errors=[]
 def read(ref):
  global _body_cache
  key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key;cache=(id(s3),bucket,key,ref['sha256'])
  if cache not in _body_cache:
   if len(_body_cache)>=4:_body_cache={}
   _body_cache[cache]=object_bytes(s3,bucket,key,expected=ref['sha256'])
  return key,_body_cache[cache]
 provider=None
 for ref in refs:
  url=ref.get('source_url')or ref.get('url')or''
  if not ref.get('key')or not ref.get('sha256'):continue
  if source=='google_patents_bigquery'and '/queries/'not in url:continue
  if source=='uspto_odp'and urlsplit(url).hostname!='api.uspto.gov':continue
  key,body=read(ref)
  if not body.lstrip().startswith(b'{'):continue
  try:rawrow=validate_google(body,record,url)if source=='google_patents_bigquery'else validate_odp(body,record,url)
  except (ProviderError,ValueError)as error:errors.append(str(error));continue
  provider={'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'origin':'first_party_source','source_url':url,'retrieved_at':ref.get('retrieved_at'),'validation':{'provider':'patent source records','dataset':record['dataset'],'original_provider_identity_and_mapping_verified':True}};break
 if provider is None:raise RawFailure(errors[0]if errors else'patent_matching_original_record_missing')
 artifacts=[provider];dataset=record['dataset'];data=record['payload']['data']
 if source=='uspto_odp'and dataset in ('patent_office_actions','patent_petition_decisions'):
  require(data.get('document_retrieval_status')=='downloaded','patent_original_prosecution_pdf_not_downloaded')
  for document in data.get('documents',[]):
   url=document.get('url','');u=urlsplit(url);require(u.scheme=='https'and u.netloc=='api.uspto.gov'and u.path.startswith('/api/v1/download/applications/'+data['application_number']+'/')and u.path.endswith('.pdf'),'patent_pdf_identity_url_mismatch')
   if dataset=='patent_office_actions':require(u.path.rsplit('/',1)[-1]==data['official_document_id']+'.pdf','patent_pdf_document_id_mismatch')
   key,body=read(document);require(body.startswith(b'%PDF-'),'patent_primary_artifact_not_pdf')
   from pypdf import PdfReader
   require(len(PdfReader(io.BytesIO(body)).pages)>0,'patent_pdf_no_pages')
   artifacts.append({'artifact_kind':'primary_document','s3_uri':'s3://'+bucket+'/'+key,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'origin':'first_party_source','source_url':url,'validation':{'provider':'USPTO original prosecution PDF','application_number':data['application_number'],'document_id':document.get('document_id')}})
  require(len(artifacts)>1,'patent_primary_prosecution_pdf_missing')
 return artifacts

def reviewed_exclusion(record,s3,bucket):
 """An owner-approved missing PDF is an exclusion, never a full-document pass."""
 data=record.get('payload',{}).get('data',{})
 if record.get('source')!='uspto_odp' or data.get('document_retrieval_status')!='excluded_by_owner':return None
 from pathlib import Path
 from research_contract import ROOT,canonical_json
 from metadata_engine.evidence import object_bytes,RawFailure
 decision=data.get('document_exception');policies=json.loads((ROOT/'config/patent-document-exceptions.json').read_text())['exceptions']
 if not decision or decision not in policies or decision.get('status')!='active' or decision.get('application_number')!=data.get('application_number') or decision.get('dataset')!=record['dataset'] or (decision.get('official_document_id')and decision['official_document_id']!=data.get('official_document_id')):raise RawFailure('patent_document_exception_not_authorized')
 expected=hashlib.sha256(canonical_json(decision)).hexdigest();refs=record['payload'].get('source_evidence',[])
 proofs=[ref for ref in refs if ref.get('sha256')==expected and ref.get('evidence_type')=='owner_authorized_exception']
 if not proofs:raise RawFailure('patent_document_exception_receipt_missing')
 ref=proofs[0];key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key
 if object_bytes(s3,bucket,key,expected=expected)!=canonical_json(decision):raise RawFailure('patent_document_exception_receipt_mismatch')
 for ref in refs:
  url=ref.get('source_url')or ref.get('url')or''
  if urlsplit(url).hostname!='api.uspto.gov' or not ref.get('key'):continue
  key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key
  try:validate_odp(object_bytes(s3,bucket,key,expected=ref['sha256']),record,url)
  except ProviderError:continue
  return {'source_record_id':record['source_record_id'],'application_number':data['application_number'],'document_id':data.get('official_document_id'),'reason':'owner_accepted_document_access_gap','excluded_from_full_document_observations':True,'exception_sha256':expected}
 raise RawFailure('patent_exclusion_original_index_not_verified')
