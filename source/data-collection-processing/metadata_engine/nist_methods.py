"""Validate NIST original documents and repair legacy discovery-only extraction."""
import hashlib
from urllib.parse import urlsplit
from nist_robotics import parse_document,canonical
class ProviderError(ValueError):pass

def evidence(record,s3,bucket):
 from metadata_engine.evidence import object_bytes,RawFailure
 errors=[]
 for ref in record.get('payload',{}).get('source_evidence',[]):
  url=ref.get('source_url')or ref.get('url')or''
  if not ref.get('key')or not ref.get('sha256')or canonical(url)!=url:continue
  if canonical(record.get('source_url',''))!=url:continue
  key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key;body=object_bytes(s3,bucket,key,expected=ref['sha256'])
  try:document=parse_document(body,url)
  except Exception as e:errors.append(type(e).__name__);continue
  if len(document.get('text','').strip())<100:raise RawFailure('nist_substantive_text_missing_or_ocr_required')
  # The parsed original is deterministic; legacy stubs remain in the raw batch.
  data=record.get('payload',{}).get('data',{})
  if data.get('document_kind')!='official source discovery page'and data!=document:raise RawFailure('nist_saved_extraction_differs_from_original')
  return [{'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'origin':'first_party_source','source_url':url,'retrieved_at':ref.get('retrieved_at'),'validation':{'provider':'NIST robotics original','kind':document['kind'],'semantic_hash':document['semantic_hash'],'parsed_document':document}}]
 raise RawFailure('nist_matching_original_document_missing'+(':'+errors[0]if errors else''))

def from_public_receipt(receipt,s3,bucket):
 from metadata_engine.evidence import object_bytes,s3_key
 from research_contract import digest
 url=receipt.get('source_url','')
 if canonical(url)!=url:raise ProviderError('nist_unapproved_receipt_url')
 key=s3_key(receipt.get('artifact_uri',''),bucket);body=object_bytes(s3,bucket,key,expected=receipt.get('sha256'));document=parse_document(body,url)
 if len(document.get('text','').strip())<100:raise ProviderError('nist_receipt_not_substantive_document')
 return [{'source':'nist_robotics_methods','dataset':'specialist_inputs','source_record_id':digest(url),'source_record_id_basis':'derived','source_url':url,'ingested_at':receipt['retrieved_at'],'payload':{'data':document,'source_id':'S47','coverage_note':'Original NIST document with explicit discovery/project/method kind; not inferred benchmark measurements or historical vintages.','source_evidence':[{'key':key,'sha256':receipt['sha256'],'source_url':url,'retrieved_at':receipt['retrieved_at']}]}}]
