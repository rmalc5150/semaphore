"""Verify complete EMA medicine rows against their official bulk JSON report."""
import json
from urllib.parse import urlsplit
REPORT='/en/documents/report/medicines-output-medicines_json-report_en.json'
class ProviderError(ValueError):pass

def validate(body,record,url):
    def require(ok,reason):
        if not ok:raise ProviderError(reason)
    u=urlsplit(url)
    require(u.scheme=='https' and u.netloc=='www.ema.europa.eu' and u.path==REPORT and not u.query,'ema_medicines_untrusted_report_url')
    try:response=json.loads(body)
    except (ValueError,UnicodeError):raise ProviderError('ema_medicines_invalid_json')from None
    require(isinstance(response,dict),'ema_medicines_report_not_object')
    rows=response.get('data')
    if rows is None:
        arrays=[v for v in response.values() if isinstance(v,list)]
        require(len(arrays)==1,'ema_medicines_collection_changed');rows=arrays[0]
    require(isinstance(rows,list),'ema_medicines_missing_rows')
    data=record.get('payload',{}).get('data');identity=record.get('source_record_id')
    require(isinstance(data,dict) and isinstance(identity,str) and bool(identity) and data.get('ema_product_number')==identity,'ema_medicines_identity_mismatch')
    matches=[r for r in rows if isinstance(r,dict)and r.get('ema_product_number')==identity]
    require(len(matches)==1 and matches[0]==data,'ema_medicines_original_row_mismatch')
    require(bool(data.get('name_of_medicine')),'ema_medicines_name_missing')
    link=urlsplit(record.get('source_url',''));expected=data.get('medicine_url')or 'https://www.ema.europa.eu'+REPORT
    require(record.get('source_url')==expected and link.scheme=='https' and link.netloc=='www.ema.europa.eu','ema_medicines_record_url_mismatch')
    return {'provider':'EMA medicines','ema_product_number':identity,'category':data.get('category'),'medicine_status':data.get('medicine_status'),'scope':'Entire current official medicine report row; linked EPAR documents and historical vintages are separate.'}
