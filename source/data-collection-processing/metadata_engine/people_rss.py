"""Require checksummed original article evidence and a verified full-text artifact."""
import json,hashlib,re
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit
from metadata_engine.evidence import RawFailure,object_bytes

def usable(text,summary):
    clean=lambda value:' '.join((value or '').split()).strip()
    return isinstance(text,str) and len(text.strip())>=250 and clean(text)!=clean(summary) and not clean(text).endswith(('...','…')) and not re.search(r'(subscribe to continue reading|sign in to continue reading|enable javascript and cookies to continue|verify you are human)',text,re.I)

def extract_html(raw,url,summary):
    import trafilatura
    from lxml import html
    try:document=raw.decode('utf-8-sig') if isinstance(raw,bytes) else raw
    except UnicodeDecodeError:document=raw
    tree=html.fromstring(document);bodies=[]
    for script in tree.xpath('//script[@type="application/ld+json"]/text()'):
        try:
            nodes=[json.loads(script)]
            while nodes:
                node=nodes.pop()
                if isinstance(node,list):nodes.extend(node)
                elif isinstance(node,dict):
                    if node.get('isAccessibleForFree') in (False,'false'):raise RawFailure('rss_article_access_restricted')
                    if isinstance(node.get('articleBody'),str):bodies.append(node['articleBody'])
                    nodes.extend(v for v in node.values() if isinstance(v,(dict,list)))
        except RawFailure:raise
        except (ValueError,TypeError):continue
    body=trafilatura.extract(document,url=url,include_comments=False,include_tables=True,include_links=False,favor_precision=True)
    if body:bodies.append(body)
    candidates=[v.strip()for v in bodies if usable(v,summary)]
    if not candidates:raise RawFailure('rss_article_full_body_not_found')
    return max(candidates,key=len)

def feed_text(fragment):
    return extract_html(('<html><body><article>'+fragment+'</article></body></html>').encode(),'https://publisher.invalid/article','')

def evidence(record,s3,bucket,artifact_source="people_rss"):
    payload=record.get('payload',{});capture=payload.get('full_text',{})
    if capture.get('status')!='captured':raise RawFailure('rss_article_fulltext_'+capture.get('status','missing'))
    url=record['source_url'];p=urlsplit(url)
    if p.scheme not in ('http','https')or not p.hostname:raise RawFailure('rss_invalid_article_url')
    ref=capture.get('reference',{});key=ref.get('key','')
    if not key.startswith('source_documents/'+artifact_source+'_fulltext/'):raise RawFailure('rss_untrusted_fulltext_key')
    raw=object_bytes(s3,bucket,'research-data/'+key,expected=ref.get('sha256'));body=json.loads(raw)
    text=body.get('text','')
    if body.get('article_url')!=url or len(text.strip())<250:raise RawFailure('rss_fulltext_identity_or_body_missing')
    sha=hashlib.sha256(text.encode()).hexdigest()
    if body.get('text_sha256')!=sha or capture.get('text_sha256')!=sha:raise RawFailure('rss_fulltext_hash_mismatch')
    if not usable(text,'' if body.get('capture_basis')=='rss_full_content' else payload.get('data',{}).get('text')):raise RawFailure('rss_summary_or_access_block_is_not_fulltext')
    refs=body.get('source_evidence',[]);originals=[]
    for original in refs:
        k=original.get('key','')
        if body.get('capture_basis')=='rss_full_content' and k.startswith('source_documents/people_rss/'):
            proof=object_bytes(s3,bucket,'research-data/'+k,expected=original.get('sha256'))
            matches=[]
            for node in ET.fromstring(proof).iter():
                if node.tag.rsplit('}',1)[-1] not in ('item','entry'):continue
                links=[n.text or n.attrib.get('href','')for n in node.iter()if n.tag.rsplit('}',1)[-1]=='link']
                full=next((n for n in node.iter()if n.tag in ('{http://purl.org/rss/1.0/modules/content/}encoded','{http://www.w3.org/2005/Atom}content')),None)
                if url in links and full is not None:matches.append(''.join(full.itertext()))
            if len(matches)==1 and feed_text(matches[0])==text:
                originals.append({'artifact_kind':'provider_feed','s3_uri':'s3://'+bucket+'/research-data/'+k,'sha256':original['sha256'],'origin':'first_party_source','source_url':original['source_url']})
            continue
        if not k.startswith('source_documents/'+artifact_source+'_article_content/'):continue
        proof=object_bytes(s3,bucket,'research-data/'+k,expected=original.get('sha256'))
        try:extracted=extract_html(proof,original['source_url'],payload.get('data',{}).get('text'))
        except Exception:continue
        if extracted!=text:continue
        originals.append({'artifact_kind':'publisher_document','s3_uri':'s3://'+bucket+'/research-data/'+k,'sha256':original['sha256'],'origin':'first_party_source','source_url':original['source_url'],'retrieval_method':original.get('retrieval_method','publisher_http')})
    if not originals:raise RawFailure('rss_original_article_evidence_missing')
    return [*originals,{'artifact_kind':'full_text','s3_uri':'s3://'+bucket+'/research-data/'+key,'sha256':ref['sha256'],'origin':'first_party_source','source_url':url,'validation':'original article HTML, extracted body, identity and text checksum verified; no summary substitution'}]
