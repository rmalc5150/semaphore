"""Verify PubMed citation/abstract records without claiming article full text."""
import hashlib,re,xml.etree.ElementTree as ET
from urllib.parse import urlsplit,parse_qs
from metadata_engine.pubmed_enrichment import enrich
class ProviderError(ValueError):pass
_cache_identity=None
_cache_body=None
_index_sha=None
_index=None

def require(ok,reason):
 if not ok:raise ProviderError(reason)

def request_ids(url):
 u=urlsplit(url);q=parse_qs(u.query)
 require(u.scheme=='https'and u.netloc=='eutils.ncbi.nlm.nih.gov'and u.path=='/entrez/eutils/efetch.fcgi','pubmed_not_original_efetch_url')
 require(q.get('db')==['pubmed']and q.get('retmode')==['xml']and bool(q.get('id'))and set(q)<={'db','id','retmode','tool','email'},'pubmed_incomplete_or_modified_efetch_request')
 ids=q['id'][0].split(',');require(all(re.fullmatch(r'\d+',p)for p in ids),'pubmed_invalid_request_ids');return ids

def primary_id(article):
 if article.tag=='PubmedArticle':return article.findtext('MedlineCitation/PMID')
 if article.tag=='PubmedBookArticle':return article.findtext('BookDocument/PMID')
 return None

def original_index(body):
 global _index_sha,_index
 sha=hashlib.sha256(body).hexdigest()
 if _index_sha==sha:return _index
 _index_sha=None;_index=None
 try:root=ET.fromstring(body)
 except ET.ParseError:raise ProviderError('pubmed_invalid_original_xml')from None
 require(root.tag=='PubmedArticleSet','pubmed_not_full_efetch_article_set');index={}
 for article in root:
  identity=primary_id(article);require(identity and identity.isdigit()and identity not in index,'pubmed_missing_or_duplicate_primary_pmid')
  index[identity]=ET.canonicalize(ET.tostring(article,encoding='unicode'))
 _index=index;_index_sha=sha;return index

def validate(body,record,url):
 rid=record.get('source_record_id');require(isinstance(rid,str)and rid.isdigit(),'pubmed_invalid_record_pmid');require(rid in request_ids(url),'pubmed_pmid_not_requested');data=record.get('payload',{}).get('data',{})
 require(data.get('pmid')==rid and isinstance(data.get('article_xml'),str),'pubmed_missing_article_xml_or_identity')
 try:article=ET.fromstring(data['article_xml']);canonical=ET.canonicalize(data['article_xml'])
 except ET.ParseError:raise ProviderError('pubmed_invalid_saved_article_xml')from None
 require(primary_id(article)==rid,'pubmed_primary_identity_mismatch');require(original_index(body).get(rid)==canonical,'pubmed_original_citation_mismatch')
 if article.tag=='PubmedArticle':require(article.find('MedlineCitation/Article')is not None,'pubmed_article_missing')
 else:require(article.find('BookDocument')is not None,'pubmed_book_document_missing')
 link=urlsplit(record.get('source_url',''));require(link.scheme=='https'and link.netloc=='pubmed.ncbi.nlm.nih.gov'and link.path.rstrip('/')=='/'+rid,'pubmed_record_url_mismatch')
 derived=enrich(data['article_xml'],rid)
 if 'enrichment'in data:require(data['enrichment']==derived,'pubmed_saved_enrichment_differs_from_original_xml')
 sections=article.findall('./MedlineCitation/Article/Abstract/AbstractText')+article.findall('./BookDocument/Abstract/AbstractText')
 return {'provider':'PubMed abstracts','pmid':rid,'provider_record_type':article.tag,'completeness_scope':'entire_pubmed_citation_record_not_article_full_text','abstract_status':'provided'if any(''.join(s.itertext()).strip()for s in sections)else'primary_abstract_not_provided','abstract_sections':len(sections),'article_full_text':'not_retrieved_or_established'}

def evidence(record,s3,bucket):
 from metadata_engine.evidence import RawFailure,object_bytes
 global _cache_identity,_cache_body
 errors=[]
 for ref in record.get('payload',{}).get('source_evidence',[]):
  try:
   if record.get('source_record_id')not in request_ids(ref.get('source_url','')):continue
  except ProviderError:continue
  key=ref.get('key');sha=ref.get('sha256')
  if not key or not sha:continue
  key=key if key.startswith('research-data/')else'research-data/'+key;identity=(bucket,key,sha)
  if identity!=_cache_identity:
   _cache_identity=None;_cache_body=None;_cache_body=object_bytes(s3,bucket,key,expected=sha);_cache_identity=identity
  try:info=validate(_cache_body,record,ref['source_url'])
  except ProviderError as error:errors.append(str(error));continue
  return [{'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':sha,'bytes':len(_cache_body),'origin':'first_party_source','source_url':ref['source_url'],'retrieved_at':ref.get('retrieved_at'),'validation':info}]
 raise RawFailure(errors[0]if errors else'pubmed_matching_original_efetch_xml_missing')
