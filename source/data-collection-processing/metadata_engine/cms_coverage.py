"""Verify original CMS national coverage inventories and full NCD API records."""
import hashlib
import html
import json
import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

class ProviderError(ValueError):
    pass

def require(ok, reason):
    if not ok:
        raise ProviderError(reason)

def number(value):
    require(re.fullmatch(r'[1-9][0-9]*', str(value)) is not None, 'cms_invalid_document_identity')
    return str(value)

def identity(row):
    return 'NCD:' + number(row.get('document_id')) + ':' + number(row.get('document_version'))

class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]
        self.hidden=0
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style'): self.hidden+=1
        if tag in ('p','br','div','li','tr'): self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script','style'): self.hidden=max(0,self.hidden-1)
        if tag in ('p','div','li','tr'): self.parts.append('\n')
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)

def text(value):
    value=value or ''
    for _ in range(3):
        decoded=html.unescape(value)
        if decoded==value: break
        value=decoded
    p=Text();p.feed(value);p.close()
    return '\n'.join(' '.join(line.split()) for line in ''.join(p.parts).splitlines() if line.strip())

def enrichment(data):
    row=data['data'][0]
    return {'version':'cms-ncd-context-1','document_id':str(row['document_id']),
            'document_version':row['document_version'],'title':row['title'],
            'coverage_criteria_text':text(row.get('indications_limitations')),
            'item_service_description_text':text(row.get('item_service_description')),
            'revision_history_text':text(row.get('revision_history')),
            'benefit_category':row.get('benefit_category'),
            'effective_date_as_supplied':row.get('effective_date'),
            'effective_end_date_as_supplied':row.get('effective_end_date'),
            'historical_vintage_verified':False}

_cached_identity=None
_cached_response=None

def response(body, url):
    global _cached_identity,_cached_response
    u=urlsplit(url)
    require(u.scheme=='https' and u.netloc=='api.coverage.cms.gov' and not u.fragment, 'cms_unapproved_api_origin')
    key=(hashlib.sha256(body).hexdigest(),url)
    if key==_cached_identity: return _cached_response
    try: data=json.loads(body)
    except (ValueError,UnicodeError): raise ProviderError('cms_invalid_provider_json') from None
    require(isinstance(data,dict) and data.get('meta',{}).get('status',{}).get('id')==200 and isinstance(data.get('data'),list),'cms_invalid_provider_response')
    _cached_identity=key;_cached_response=data
    return data

def validate(body,record,url):
    original=response(body,url);u=urlsplit(url);q=parse_qs(u.query)
    data=record.get('payload',{}).get('data');source=record.get('source');rid=record.get('source_record_id')
    if source=='cms_coverage':
        require(u.path.rstrip('/') in ('/v1/reports/national-coverage-annual','/v1/reports/national-coverage-ncd'),'cms_wrong_inventory_endpoint')
        if u.path.rstrip('/').endswith('annual'):
            require(q.get('document_type')==['NCD'] and len(q.get('year',[]))==1 and re.fullmatch(r'20[0-9]{2}',q['year'][0]),'cms_invalid_inventory_scope')
        require(isinstance(data,dict) and data.get('document_type','NCD')=='NCD' and identity(data)==rid,'cms_inventory_identity_mismatch')
        require(any(row==data for row in original['data']),'cms_inventory_record_differs_from_original')
        v=urlsplit(record.get('source_url',''));vq=parse_qs(v.query)
        require(v.scheme=='https' and v.netloc=='www.cms.gov' and v.path=='/medicare-coverage-database/view/ncd.aspx' and vq.get('ncdid')==[number(data['document_id'])] and vq.get('ncdver')==[number(data['document_version'])],'cms_inventory_record_url_mismatch')
        require(bool(data.get('title')),'cms_inventory_title_missing')
        scope='complete_returned_ncd_inventory_row_not_policy_body'
    else:
        require(source=='cms_coverage_documents' and u.path.rstrip('/')=='/v1/data/ncd','cms_wrong_document_endpoint')
        require(data==original,'cms_document_differs_from_original')
        require(len(original['data'])==1 and not original['meta'].get('next_token'),'cms_document_response_not_complete_single_record')
        row=original['data'][0]
        require(identity(row)==rid and q.get('ncdid')==[number(row['document_id'])] and q.get('ncdver')==[number(row['document_version'])],'cms_document_identity_mismatch')
        require(bool(row.get('title')) and any(text(row.get(field)).strip().lower() not in ('','n/a') for field in ('indications_limitations','item_service_description')),'cms_document_coverage_body_missing')
        scope='complete_returned_ncd_version_and_coverage_body_not_historical_api_vintage'
    return {'provider':'CMS national coverage','source':source,'document_identity':rid,'completeness_scope':scope,'retained_provider_fields':len(data) if source=='cms_coverage' else len(data['data'][0])}

_body_identity=None
_cached_body=None

def evidence(record,s3,bucket):
    from metadata_engine.evidence import object_bytes,RawFailure
    global _body_identity,_cached_body
    errors=[]
    for ref in record.get('payload',{}).get('source_evidence',[]):
        if not ref.get('key') or not ref.get('sha256') or urlsplit(ref.get('source_url','')).hostname!='api.coverage.cms.gov': continue
        key=ref['key'];key=key if key.startswith('research-data/') else 'research-data/'+key
        cache=(id(s3),bucket,key,ref['sha256'])
        if cache!=_body_identity:
            _body_identity=None;_cached_body=object_bytes(s3,bucket,key,expected=ref['sha256']);_body_identity=cache
        body=_cached_body
        try: info=validate(body,record,ref['source_url'])
        except ProviderError as error: errors.append(str(error));continue
        return [{'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+key,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'origin':'first_party_source','source_url':ref['source_url'],'retrieved_at':ref.get('retrieved_at'),'validation':info}]
    raise RawFailure(errors[0] if errors else 'cms_matching_original_response_missing')
