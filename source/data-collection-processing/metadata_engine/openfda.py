"""Validate approval events and CRL records against complete openFDA results."""
import hashlib,json
from urllib.parse import urlsplit,parse_qs

class ProviderError(ValueError):pass

def require(ok,reason):
    if not ok:raise ProviderError(reason)

def validate(body,record,url):
    u=urlsplit(url)
    require(u.scheme=='https' and u.netloc=='api.fda.gov' and u.path in ('/drug/drugsfda.json','/transparency/crl.json'),'openfda_untrusted_api_url')
    require(not any(k.lower()in ('fields','select','$select','count')for k in parse_qs(u.query)),'openfda_projected_or_aggregate_response')
    try:response=json.loads(body)
    except (ValueError,UnicodeError):raise ProviderError('openfda_invalid_json')from None
    require(isinstance(response,dict) and isinstance(response.get('results'),list),'openfda_missing_results')
    data=record.get('payload',{}).get('data',{});rid=record.get('source_record_id','');link=urlsplit(record.get('source_url',''))
    require(link.scheme=='https' and link.netloc=='api.fda.gov' and link.path==u.path,'openfda_record_url_mismatch')
    if record.get('source')=='drugsfda_applications' or record.get('source_key')=='drugsfda_applications':
        require(u.path=='/drug/drugsfda.json','drugsfda_wrong_endpoint')
        require(isinstance(data,dict) and data.get('application_number')==rid and bool(rid),'drugsfda_application_identity_mismatch')
        require(data in response['results'],'drugsfda_original_application_mismatch')
        require(isinstance(data.get('products'),list) and bool(data['products']),'drugsfda_application_products_missing')
        return {'provider':'FDA Drugs@FDA','application_number':rid,'product_count':len(data['products']),'scope':'Entire current provider application, products and supplied submissions; not all linked documents or historical vintages.'}
    if u.path=='/drug/drugsfda.json':
        app=data.get('application');sub=data.get('submission')
        require(isinstance(app,dict) and isinstance(sub,dict) and data.get('action')=='APPROVAL','openfda_missing_approval_application')
        number=app.get('application_number');require(isinstance(number,str) and bool(number),'openfda_missing_application_id')
        matches=[r for r in response['results'] if isinstance(r,dict)and r.get('application_number')==number and r==app]
        require(bool(matches),'openfda_original_application_mismatch')
        require(sub.get('submission_status')=='AP' and sub in app.get('submissions',[]) and sub.get('submission_type') and sub.get('submission_number'),'openfda_original_submission_mismatch')
        expected='approval:'+':'.join(str(x)for x in (number,sub['submission_type'],sub['submission_number']))
        if ':variant:'in rid:
            checksum=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
            expected+=':variant:'+checksum
        require(rid==expected,'openfda_approval_identity_mismatch')
        identity={'application_number':number,'submission_type':sub['submission_type'],'submission_number':sub['submission_number']}
    else:
        filename=data.get('file_name');require(isinstance(filename,str)and bool(filename) and str(data.get('letter_type','')).upper()=='COMPLETE RESPONSE','openfda_invalid_crl_identity')
        expected='crl:'+filename
        if ':variant:'in rid:
            expected+=':variant:'+hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
        require(rid==expected and data in response['results'],'openfda_original_crl_mismatch')
        identity={'file_name':filename}
    return {'provider':'FDA openFDA',**identity,'endpoint':u.path,'scope':'Complete API application/CRL record and matched approval event; linked documents and historical vintages are separate.'}
