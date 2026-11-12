"""Match complete ClinicalTrials.gov study records to their original v2 response."""
import json,re
from urllib.parse import urlsplit,parse_qs
class ProviderError(ValueError):pass
def require(ok,reason):
    if not ok:raise ProviderError(reason)
def validate(body,record,url):
    parsed=urlsplit(url)
    require(parsed.scheme=='https' and parsed.netloc=='clinicaltrials.gov' and (parsed.path=='/api/v2/studies' or re.fullmatch(r'/api/v2/studies/NCT\d{8}',parsed.path)),'clinicaltrials_untrusted_api_url')
    require(not any(parse_qs(parsed.query).get(k) for k in ('fields','formatFields','select')),'clinicaltrials_projected_response_not_complete')
    try:data=json.loads(body)
    except (ValueError,UnicodeError):raise ProviderError('clinicaltrials_invalid_json')from None
    require(isinstance(data,dict),'clinicaltrials_response_not_object')
    studies=data.get('studies') if 'studies'in data else [data]
    require(isinstance(studies,list),'clinicaltrials_studies_not_list')
    identity=record['source_record_id'];require(re.fullmatch(r'NCT\d{8}',identity)is not None,'clinicaltrials_invalid_nct_id')
    matches=[s for s in studies if isinstance(s,dict)and s.get('protocolSection',{}).get('identificationModule',{}).get('nctId')==identity]
    require(len(matches)==1,'clinicaltrials_study_identity_missing_or_duplicate');study=matches[0];protocol=study['protocolSection']
    require(isinstance(protocol.get('statusModule'),dict) and bool(protocol['statusModule']),'clinicaltrials_protocol_status_missing')
    require(study==record.get('payload',{}).get('data'),'clinicaltrials_saved_study_differs_from_provider')
    link=urlsplit(record.get('source_url',''))
    require(link.scheme=='https'and link.netloc=='clinicaltrials.gov'and link.path in ('/study/'+identity,'/api/v2/studies/'+identity),'clinicaltrials_record_url_mismatch')
    return {'provider':'ClinicalTrials.gov','nct_id':identity,'protocol_modules':sorted(protocol),'has_results':study.get('hasResults'),'scope':'Entire provider study object retained; current registry version, not a past-vintage snapshot or guaranteed optional results.'}
