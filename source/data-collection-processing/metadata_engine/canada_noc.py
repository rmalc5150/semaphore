"""Verify an entire Health Canada NOC row against the original bulk response."""
import json,hashlib
from urllib.parse import urlsplit,parse_qs
class ProviderError(ValueError):pass

def product_id(row):
    return 'product:'+hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

_cache_hash=None
_cache_index=None

def original_index(body):
    # One response per process, evicted before decoding a different bulk file.
    # Avoid decoding the same full-country inventory once per metadata row.
    global _cache_hash,_cache_index
    checksum=hashlib.sha256(body).hexdigest()
    if checksum==_cache_hash:return _cache_index
    _cache_hash=None;_cache_index=None
    try:rows=json.loads(body)
    except (ValueError,UnicodeError):raise ProviderError('canada_noc_invalid_json')from None
    if not isinstance(rows,list):raise ProviderError('canada_noc_missing_rows')
    index={}
    for row in rows:
        if not isinstance(row,dict) or row.get('noc_number') is None:raise ProviderError('canada_noc_missing_provider_identity')
        key=product_id(row) if 'noc_br_product_id' in row else str(row['noc_number']);index[key]=None if key in index and index[key]!=row else row
    _cache_index=index;_cache_hash=checksum
    return index

def validate(body,record,url):
    def require(ok,reason):
        if not ok:raise ProviderError(reason)
    u=urlsplit(url)
    require(u.scheme=='https' and u.netloc=='health-products.canada.ca' and u.path in ('/api/notice-of-compliance/noticeofcompliancemain/','/api/notice-of-compliance/drugproduct/'),'canada_noc_untrusted_api_url')
    require(parse_qs(u.query)=={'lang':['en'],'type':['json']},'canada_noc_modified_bulk_query')
    index=original_index(body)
    data=record.get('payload',{}).get('data');identity=record.get('source_record_id')
    require(isinstance(data,dict) and isinstance(identity,str) and bool(identity),'canada_noc_identity_mismatch')
    expected=product_id(data) if u.path.endswith('/drugproduct/') else str(data.get('noc_number'))
    require(identity==expected,'canada_noc_identity_mismatch')
    if u.path.endswith('/drugproduct/'):
        require(all(k in data for k in ('noc_number','noc_br_product_id','noc_br_brand_id','noc_br_brandname','noc_br_din')),'canada_noc_product_fields_missing')
    require(index.get(identity)==data,'canada_noc_original_row_mismatch')
    link=urlsplit(record.get('source_url',''))
    require(link.scheme=='https' and link.netloc==u.netloc and link.path==u.path,'canada_noc_record_url_mismatch')
    return {'provider':'Health Canada NOC','noc_number':str(data['noc_number']),'record_type':'drug_product' if identity.startswith('product:') else 'notice','scope':'Entire current official NOC record; not every marketed drug, review dossiers or superseded dataset vintages.'}
