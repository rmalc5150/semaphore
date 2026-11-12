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


def text(node):return ' '.join(''.join(node.itertext()).split()) if node is not None else ''


def cas_numbers(value):
    valid=[]
    for m in re.finditer(r'\b\d{2,7}-\d{2}-\d\b',value):
        number=m[0];digits=number.replace('-','')
        if sum((i+1)*int(c) for i,c in enumerate(reversed(digits[:-1])))%10==int(digits[-1]):valid.append(number)
    return list(dict.fromkeys(valid))


def pmns(value):
    return list(dict.fromkeys(re.sub(r'[–−]','-',m[0]).upper() for m in re.finditer(r'\bP[-–−]\d{2}[-–−]\d{1,6}\b',value,re.I)))


def stage(metadata):
    action=(metadata.get('action') or '').lower();kind=metadata.get('type')
    if 'withdraw' in action:return 'withdrawal'
    if 'correct' in action:return 'correction'
    if kind=='Proposed Rule' or 'proposed' in action:return 'proposed_rule'
    if 'final' in action:return 'final_rule'
    return {'Rule':'rule_stage_needs_review','Notice':'notice','Presidential Document':'presidential_document'}.get(kind,'stage_needs_review')


def dated(value):
    if not value:return None
    try:return date.fromisoformat(value).isoformat()
    except ValueError:return None


def parse_notice(raw,metadata,source_ref,format='xml'):
    expected=metadata['document_number']
    if format=='xml':
        root=etree.fromstring(raw,etree.XMLParser(resolve_entities=False,no_network=True,load_dtd=False,huge_tree=False))
        require(etree.QName(root).localname in {'RULE','PRORULE','NOTICE','PRESDOC','DOC'},'fr_non_notice_xml')
        marker=' '.join(text(n) for n in root.xpath('//FRDOC'))
        require(bool(re.search(r'(?<!\d)'+re.escape(expected)+r'(?!\d)',marker)),'fr_xml_document_identity_mismatch')
        all_nodes=root.xpath('//P');section_nodes=root.xpath('//SECTION')
    else:
        root=html.fromstring(raw);require(len(text(root))>100,'fr_empty_notice_html')
        all_nodes=root.xpath('//p');section_nodes=[]
    tree=root.getroottree()
    paragraphs=[{'text':text(n),'source_path':tree.getpath(n)} for n in all_nodes if text(n)]
    require(paragraphs,'fr_notice_body_empty')
    provisions=[]
    for section in section_nodes:
        section_text=text(section);heading=text(section.find('SUBJECT'));number=text(section.find('SECTNO'))
        if not pmns(section_text) and not re.search(r'chemical substance identified|CAS(?:RN| Registry| Number)',section_text,re.I):continue
        ps=[{'text':text(n),'source_path':tree.getpath(n)} for n in section.findall('P') if text(n)]
        identifiers=pmns(section_text)
        provisions.append({'cfr_section':number,'reported_chemical_name':heading or None,
           'identity_status':'generic_or_confidential' if re.search(r'\bgeneric\b|confidential',heading,re.I) else 'reported_name_not_independently_resolved',
           'pmn_numbers':identifiers,'cas_numbers':cas_numbers(section_text),
           'paragraphs':ps,'conditions_and_requirements':[p for p in ps if re.search(r'require|must|significant new use|subject to reporting|may not',p['text'],re.I)],
           'exceptions_and_scope_limits':[p for p in ps if re.search(r'do(?:es)? not apply|exempt|except|excluding|excluded',p['text'],re.I)],
           'quantity_time_or_threshold_passages':[p for p in ps if re.search(r'\b\d[\d,.]*\s*(?:days?|hours?|kilograms?|kg|ppm|percent|%)',p['text'],re.I)],
           'source_path':tree.getpath(section),'source_document_sha256':source_ref['sha256'],
           'interpretation_status':'source_provisions_extracted_applicability_unreviewed'})
    return {'version':VERSION,'document_number':expected,'title':metadata.get('title'),'document_type':metadata.get('type'),
       'action':metadata.get('action'),'policy_stage':stage(metadata),'publication_date':dated(metadata.get('publication_date')),
       'effective_date':dated(metadata.get('effective_on')),'comments_close_date':dated(metadata.get('comments_close_on')),
       'source_dates_text':metadata.get('dates'),'docket_ids':metadata.get('docket_ids',[]),'rin_numbers':metadata.get('regulation_id_numbers',[]),
       'cfr_references':metadata.get('cfr_references',[]),'correction_reference':metadata.get('correction_of'),
       'full_text':'\n\n'.join(p['text'] for p in paragraphs),'paragraphs':paragraphs,'chemical_provisions':provisions,
       'extraction_format':format,'chemical_extraction_status':'section_provisions_extracted' if provisions else 'no_section_chemical_provisions_detected_review_needed',
       'notice_level_pmn_mentions':pmns(text(root)),'notice_level_cas_mentions':cas_numbers(text(root)),
       'chemical_mentions_are_not_product_links':True,'product_applicability':'unreviewed_requires_composition_and_use_evidence',
       'historical_availability':'not_established','current_law_status':'not_assessed_against_later_amendments'}


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
