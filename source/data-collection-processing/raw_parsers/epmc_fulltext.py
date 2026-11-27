"""Verify complete first-party JATS article evidence and preserve article identity."""
import re,xml.etree.ElementTree as ET
from urllib.parse import urlsplit,parse_qs
VERSION='epmc-fulltext-1.0'
class ProviderError(ValueError):pass

def require(ok,reason):
 if not ok:raise ProviderError(reason)

def request_pmcid(url):
 u=urlsplit(url)
 require(u.scheme=='https' and not u.fragment,'epmc_fulltext_unapproved_origin')
 if u.netloc=='www.ebi.ac.uk':
  m=re.fullmatch(r'/europepmc/webservices/rest/(PMC[0-9]+)/fullTextXML',u.path)
  require(m is not None and not u.query,'epmc_fulltext_unapproved_endpoint');return m[1]
 require(u.netloc=='eutils.ncbi.nlm.nih.gov' and u.path=='/entrez/eutils/efetch.fcgi','epmc_fulltext_unapproved_origin')
 q=parse_qs(u.query);require(q.get('db')==['pmc'] and q.get('retmode')==['xml'] and len(q.get('id',[]))==1 and re.fullmatch('[0-9]+',q['id'][0]) and set(q)<={'db','id','retmode','tool','email'},'epmc_fulltext_invalid_fallback_request');return 'PMC'+q['id'][0]

def parse_original(body,pmcid):
 require(isinstance(pmcid,str) and re.fullmatch('PMC[0-9]+',pmcid),'epmc_fulltext_invalid_pmcid')
 try:root=ET.fromstring(body,parser=ET.XMLParser(target=ET.TreeBuilder(insert_pis=True)))
 except ET.ParseError:raise ProviderError('epmc_fulltext_invalid_xml')from None
 if root.tag=='pmc-articleset':
  articles=root.findall('article');require(len(articles)==1,'epmc_fulltext_fallback_article_count');root=articles[0]
 require(root.tag=='article','epmc_fulltext_not_article');meta=root.find('front/article-meta');require(meta is not None,'epmc_fulltext_missing_article_metadata')
 ids={n.text.strip() for n in meta.findall('article-id') if n.get('pub-id-type') in {'pmc','pmcid'} and n.text}
 require(bool(ids.intersection({pmcid,pmcid[3:]})),'epmc_fulltext_primary_identity_mismatch')
 title=' '.join(''.join(meta.find('title-group/article-title').itertext()).split()) if meta.find('title-group/article-title')is not None else ''
 article_body=root.find('body');body_text=' '.join(' '.join(article_body.itertext()).split()) if article_body is not None else ''
 require(title and body_text,'epmc_fulltext_missing_title_or_article_body')
 return root,{'provider':'Europe PMC full text','pmcid':pmcid,'title':title,'article_type':root.get('article-type'),'body_characters':len(body_text),'body_sections':len(article_body.findall('.//sec')),'completeness_scope':'entire_returned_jats_article_not_external_supplements_or_historical_vintages'}

def validate(body,record,url):
 data=record.get('payload',{}).get('data',{});pmcid=record.get('source_record_id');require(data.get('pmcid')==pmcid==request_pmcid(url),'epmc_fulltext_record_identity_mismatch');require(record.get('source_url')==url,'epmc_fulltext_record_url_mismatch')
 article,info=parse_original(body,pmcid)
 try:saved=ET.canonicalize(data.get('article_xml',''),rewrite_prefixes=True)
 except ET.ParseError:raise ProviderError('epmc_fulltext_saved_xml_invalid')from None
 require(saved==ET.canonicalize(ET.tostring(article,encoding='unicode'),rewrite_prefixes=True),'epmc_fulltext_saved_article_differs_from_original')
 if 'enrichment'in data:require(data['enrichment']==enrichment(data['article_xml'],pmcid),'epmc_fulltext_derived_context_mismatch')
 return info

def enrichment(xml,pmcid):
 root,info=parse_original(xml.encode(),pmcid);meta=root.find('front/article-meta');body=root.find('body')
 return {**info,'version':VERSION,'body_text':' '.join(' '.join(body.itertext()).split()),'abstracts':[' '.join(''.join(n.itertext()).split())for n in meta.findall('abstract')],'identifiers':[{**n.attrib,'value':n.text}for n in meta.findall('article-id')],'publication_dates':[{**n.attrib,'year':n.findtext('year'),'month':n.findtext('month'),'day':n.findtext('day')}for n in meta.findall('pub-date')],'license_statements':[{'text':' '.join(n.itertext()),'attributes':n.attrib}for n in meta.findall('.//license')]}
