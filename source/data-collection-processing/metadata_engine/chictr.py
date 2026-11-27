"""Match ChiCTR public trial detail HTML to the complete captured field list."""
import re
from datetime import date
from urllib.parse import urlsplit,parse_qs
from raw_parsers.chictr_tables import parse_detail_page
class ProviderError(ValueError):pass

def require(ok,reason):
    if not ok:raise ProviderError(reason)

def project_id(url):
    u=urlsplit(url);q=parse_qs(u.query)
    require(u.scheme=='https' and u.netloc in ('www.chictr.org.cn','chictr.org.cn') and u.path=='/showproj.html' and set(q)=={'proj'} and len(q['proj'])==1 and q['proj'][0].isdigit(),'chictr_not_original_trial_detail')
    return q['proj'][0]

def validate(body,record,url):
    project=project_id(url);data=record.get('payload',{}).get('data',{});rid=record.get('source_record_id')
    require(isinstance(data,dict) and isinstance(rid,str) and re.fullmatch(r'ChiCTR[A-Za-z0-9-]*\d{5,}',rid) is not None,'chictr_invalid_registration_id')
    require(data.get('registrationNumber')==rid and str(data.get('projectId'))==project,'chictr_saved_identity_mismatch')
    require(project_id(record.get('source_url',''))==project and project_id(data.get('detailUrl',''))==project,'chictr_record_url_mismatch')
    try:document=body.decode('utf-8-sig')
    except UnicodeError:raise ProviderError('chictr_invalid_html_encoding')from None
    fields=parse_detail_page(document)
    require(fields and len(fields)>=2,'chictr_missing_trial_fields')
    ids=[f['value'].strip() for f in fields if 'registration number' in f['label'].lower() or '注册号' in f['label']]
    require(rid in ids,'chictr_original_registration_mismatch')
    require(fields==data.get('fields'),'chictr_original_field_list_mismatch')
    dates=[f['value'].strip() for f in fields if 'date of registration' in f['label'].lower() or '注册时间' in f['label']]
    normalized_dates=[]
    for value in dates:
        match=re.fullmatch(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})(?:\s+\d{2}:\d{2}:\d{2})?',value)
        if match:
            try:normalized_dates.append(date(*map(int,match.groups())).isoformat())
            except ValueError:pass
    require(data.get('registrationDate') in normalized_dates,'chictr_registration_date_mismatch')
    require(any(f['value'].strip() for f in fields if 'public title' in f['label'].lower() or '注册题目' in f['label']),'chictr_trial_title_missing')
    return {'provider':'Chinese Clinical Trial Registry','registration_number':rid,'project_id':project,'field_count':len(fields),'scope':'Entire parsed public trial-detail field list and original HTML; current observed version, not original protocol documents or historical registry vintages.'}
