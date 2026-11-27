"""Metadata evidence lookup for the shared European PMC raw parser."""
import hashlib
from raw_parsers.epmc_fulltext import (
    VERSION as VERSION, ProviderError as ProviderError, require as require,
    request_pmcid as request_pmcid, parse_original as parse_original,
    validate as validate, enrichment as enrichment,
)

_cache=None
_cached_body=None


def evidence(record,s3,bucket):
 from metadata_engine.evidence import object_bytes,RawFailure
 global _cache,_cached_body
 errors=[]
 for ref in record.get('payload',{}).get('source_evidence',[]):
  try:identity=request_pmcid(ref.get('source_url',''))
  except ProviderError:continue
  if identity!=record.get('source_record_id') or not ref.get('key') or not ref.get('sha256'):continue
  key=ref['key'];key=key if key.startswith('research-data/')else'research-data/'+key;cache=(bucket,key,ref['sha256'])
  if _cache!=cache:
   _cache=None;_cached_body=object_bytes(s3,bucket,key,expected=ref['sha256']);_cache=cache
  try:info=validate(_cached_body,record,ref['source_url'])
  except ProviderError as error:errors.append(str(error));continue
  return [{'artifact_kind':'full_text','s3_uri':'s3://'+bucket+'/'+key,'sha256':hashlib.sha256(_cached_body).hexdigest(),'bytes':len(_cached_body),'origin':'first_party_source','source_url':ref['source_url'],'retrieved_at':ref.get('retrieved_at'),'validation':info}]
 raise RawFailure(errors[0] if errors else'epmc_fulltext_matching_original_article_missing')
