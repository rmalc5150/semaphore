"""Validate archived EODHD data against its declared dataset, not document rules.

EODHD is the source of the vendor response, not the issuer of a primary filing.
No provider requests, credentials, inferred identity merges or vintage claims.
"""
import json
import re
from datetime import date
from decimal import Decimal,InvalidOperation
from urllib.parse import urlsplit,unquote,parse_qs


class ProviderDataError(ValueError):pass


def require(ok,reason):
    if not ok:raise ProviderDataError('eodhd_'+reason)


def numeric(value,positive=False):
    try:n=Decimal(str(value))
    except (InvalidOperation,ValueError):raise ProviderDataError('eodhd_invalid_numeric') from None
    require(n.is_finite() and (n>0 if positive else n>=0),'invalid_numeric')
    return n


def validate(body,record,url):
    p=record['payload'];parsed=urlsplit(url);path=unquote(parsed.path);query=parse_qs(parsed.query)
    require(parsed.scheme=='https' and parsed.hostname=='eodhd.com','unverified_provider_origin')
    require(not any(k in query for k in ('fields','select','$select')),'unsupported_field_projection')
    dataset=record['dataset'];symbol=p.get('provider_symbol') or p.get('symbol')
    require(isinstance(symbol,str) and '.' in symbol and all(symbol.rsplit('.',1)),'exchange_qualified_symbol_required')
    code,exchange=symbol.rsplit('.',1)
    if dataset=='company_profiles' and p.get('profile_status')=='not_found':
        require(record['source']=='eodhd' and path=='/api/fundamentals/'+symbol and query.get('filter')==['General'],'profile_endpoint_identity_mismatch')
        # The committed collector only sets not_found on HTTP 404. Require
        # corroborating archived response bytes; retain an unavailable outcome,
        # never turn it into a populated profile or an absence-of-company claim.
        text=body.decode('utf-8',errors='replace').lower()
        require(bool(re.search(r'\b404\b|\bnot found\b',text)) and p.get('general') is None,'unavailable_response_not_corroborated')
        require(not any(s in text for s in ('captcha','access denied','rate limit','quota')),'unavailable_response_is_access_error')
        return {'dataset':dataset,'scope':'General','provider_symbol':symbol,'provider_availability':'not_found',
                'profile_content_complete':False,'validation':'committed HTTP-404 outcome with archived corroborating response'}
    try:data=json.loads(body)
    except (ValueError,UnicodeError):raise ProviderDataError('eodhd_malformed_provider_json') from None
    if dataset=='company_profiles':
        require(record['source']=='eodhd' and path=='/api/fundamentals/'+symbol,'profile_endpoint_identity_mismatch')
        require(query.get('filter')==['General'],'profile_scope_must_be_general')
        require(p.get('profile_status')=='available','profile_unavailable_requires_status_evidence')
        general=data.get('General',data) if isinstance(data,dict) else None
        require(isinstance(general,dict) and general.get('Code')==code and bool(general.get('Name')),'profile_identity_missing')
        require(general==p.get('general'),'profile_payload_differs_from_provider')
        # Missing optional LEI/CIK/description is a quality gap, not raw failure.
        return {'dataset':dataset,'scope':'General','provider_symbol':symbol,'row_identity_verified':True}
    if dataset=='listing_inventory':
        require(record['source']=='eodhd' and path=='/api/exchange-symbol-list/'+exchange,'inventory_endpoint_identity_mismatch')
        require(p.get('requested_exchange')==exchange and p.get('listing_status') in ('active','delisted'),'inventory_scope_missing')
        require((query.get('delisted')==['1'])==(p['listing_status']=='delisted'),'inventory_status_scope_mismatch')
        require(isinstance(data,list),'inventory_response_not_list')
        rows=[r for r in data if isinstance(r,dict) and r.get('Code')==code]
        require(len(rows)==1 and bool(rows[0].get('Name')),'inventory_identity_missing_or_duplicate')
        require(rows[0]['Name']==p.get('name'),'inventory_payload_differs_from_provider')
        for raw_key,field in [('Country','country'),('Currency','currency'),('Type','instrument_type'),('Isin','isin')]:
            require(rows[0].get(raw_key)==p.get(field),'inventory_payload_differs_from_provider')
        return {'dataset':dataset,'provider_symbol':symbol,'listing_status':p['listing_status'],'row_identity_verified':True}
    require(dataset=='market_records' and record['source']=='eodhd_market','unsupported_dataset')
    kind=p.get('kind');endpoint={'prices':'eod','dividends':'div','splits':'splits'}.get(kind)
    require(endpoint is not None and path=='/api/'+endpoint+'/'+symbol,'market_endpoint_identity_mismatch')
    require(not query.get('filter'),'market_field_projection_not_supported')
    value=p.get('data',{});day=value.get('date')
    try:date.fromisoformat(day)
    except (TypeError,ValueError):raise ProviderDataError('eodhd_invalid_market_date') from None
    require(isinstance(data,list),'market_response_not_list')
    rows=[r for r in data if isinstance(r,dict) and r.get('date')==day]
    require(len(rows)==1,'market_date_missing_or_duplicate');row=rows[0]
    fields=('open','high','low','close','adjusted_close','volume') if kind=='prices' else ('value',) if kind=='dividends' else ()
    for field in fields:
        require(field in row and field in value,'market_field_missing:'+field)
        if row[field] is None and field=='adjusted_close':require(value[field] is None,'market_value_mismatch')
        else:require(numeric(row[field])==numeric(value[field]),'market_value_mismatch:'+field)
    if kind=='prices':
        require(numeric(row['low'])<=min(numeric(row['open']),numeric(row['close']))<=max(numeric(row['open']),numeric(row['close']))<=numeric(row['high']),'inconsistent_ohlc')
    if kind=='splits':
        pieces=str(row.get('split','')).split('/')
        require(len(pieces)==2 and row.get('split')==value.get('split'),'invalid_split_ratio')
        numeric(pieces[0],True);numeric(pieces[1],True)
    # Preserve every native field; normalization may add derived split fields.
    for field,v in row.items():
        if field not in fields:require(value.get(field)==v,'market_payload_field_mismatch:'+field)
    return {'dataset':dataset,'kind':kind,'provider_symbol':symbol,'date':day,'row_identity_verified':True,
            'vintage_basis':'retrieved_provider_response; original historical availability unknown'}
