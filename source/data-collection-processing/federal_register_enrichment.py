"""Original Federal Register evidence and source-located policy/chemical provisions."""
import hashlib
import json
import re
from datetime import date
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler,build_opener
from lxml import etree,html
from regulatory_collection import EvidenceClient,SourceIssue,require
from collection_storage import write_checked,now

VERSION='fr-full-notice-provisions-v1'
HOSTS={'www.federalregister.gov','www.govinfo.gov','www.gpo.gov'}


def allowed(url):
    p=urlsplit(url)
    return p.scheme=='https' and p.hostname in HOSTS and not p.username and not p.password and p.port in {None,443}


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        require(allowed(newurl),'fr_unexpected_redirect_host')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


class NoticeClient(EvidenceClient):
    def __init__(self,store):
        super().__init__(store,'federal_register_documents',opener=build_opener(SafeRedirect()).open)
    def get(self,url,*args,**kwargs):
        require(allowed(url),'fr_unexpected_source_host')
        return super().get(url,*args,**kwargs)
    def response_limit(self,url):
        # Some official notices exceed 100 MiB. Keep the general API/body
        # bound while permitting their original PDFs on the document worker.
        return 128*1024*1024 if urlsplit(url).path.lower().endswith('.pdf') else super().response_limit(url)


from federal_register_parser import text,cas_numbers,pmns,stage,dated,parse_notice


def enrich(client,listing):
    client.evidence=[]
    number=listing['document_number'];require(bool(re.fullmatch(r'\d{4}-\d{3,6}',number)),'fr_invalid_document_number')
    metadata=client.json('https://www.federalregister.gov/api/v1/documents/'+number+'.json')
    require(metadata.get('document_number')==number,'fr_metadata_document_identity_mismatch')
    gaps=[];result=None
    for key,format in [('full_text_xml_url','xml'),('body_html_url','html')]:
        url=metadata.get(key)
        if not url:continue
        require(allowed(url) and number in urlsplit(url).path,'fr_invalid_notice_body_url')
        try:
            raw=client.get(url);ref=client.evidence[-1]
            result=parse_notice(raw,metadata,ref,format);result['body_source']=ref;break
        except (SourceIssue,ValueError,etree.XMLSyntaxError) as exc:
            gaps.append({'artifact':key,'reason':str(exc)[:200]})
    require(result is not None,'fr_no_valid_full_notice_body')
    pdf=metadata.get('pdf_url')
    try:
        require(pdf and allowed(pdf) and urlsplit(pdf).path.endswith('/'+number+'.pdf'),'fr_official_pdf_url_missing_or_mismatched')
        raw=client.get(pdf);require(raw.startswith(b'%PDF-'),'fr_non_pdf_response')
        result['official_pdf_source']=client.evidence[-1]
        result['official_pdf_status']='downloaded'
    except (SourceIssue,ValueError) as exc:
        result['official_pdf_status']='missing';gaps.append({'artifact':'official_pdf','reason':str(exc)[:200]})
    # XML failure followed by a valid HTML body remains explicit, while the body is usable.
    result.update(retrieved_at=now(),artifact_gaps=gaps,
       retrieval_status='complete' if result['official_pdf_status']=='downloaded' else 'partial',
       review_status='pending')
    # Preserve the entire extraction artifact even for notices too large for one observation.
    raw=(json.dumps(result,ensure_ascii=False,sort_keys=True)+'\n').encode();checksum=hashlib.sha256(raw).hexdigest()
    key='source_documents/federal_register_extractions/'+checksum
    write_checked(client.store,key,raw,content_type='application/json')
    ref={'key':key,'sha256':checksum,'source_url':metadata['html_url'],'retrieved_at':now()}
    result['full_extraction_source']=ref
    if len(raw)>3*1024*1024:
        result={k:v for k,v in result.items() if k not in {'full_text','paragraphs','chemical_provisions'}}
        result['extraction_storage']='full_extraction_externalized_to_source_reference'
    return result
