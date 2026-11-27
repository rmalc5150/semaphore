"""Validate complete Comtrade rows against saved official API responses."""
import json
from urllib.parse import parse_qs, urlsplit
from research_contract import digest

IDENTITY_FIELDS = ('typeCode', 'freqCode', 'period', 'reporterCode', 'cmdCode',
                   'flowCode', 'partnerCode', 'partner2Code', 'customsCode',
                   'motCode', 'classificationCode')


def validate(body, record, url):
    from metadata_engine.evidence import RawFailure
    def require(ok, reason):
        if not ok:
            raise RawFailure('comtrade_' + reason)
    u = urlsplit(url)
    require(u.scheme == 'https' and u.netloc == 'comtradeapi.un.org'
            and u.path in ('/data/v1/get/C/A/HS', '/public/v1/preview/C/A/HS')
            and not u.fragment, 'untrusted_api_url')
    query = parse_qs(u.query)
    require(all(len(v) == 1 for v in query.values()) and 'period' in query
            and 'maxRecords' in query, 'missing_or_ambiguous_query')
    try:
        response = json.loads(body)
        cap = int(query['maxRecords'][0])
    except (ValueError, TypeError):
        raise RawFailure('comtrade_invalid_original_response') from None
    require(isinstance(response, dict) and response.get('error') in (None, '', False), 'provider_error')
    rows = response.get('data')
    require(isinstance(rows, list) and all(isinstance(r, dict) for r in rows)
            and 0 < len(rows) < cap and response.get('count') == len(rows), 'truncated_or_invalid_response')
    payload = record.get('payload', {})
    data = payload.get('data', {})
    data = data.get('trade', data)
    require(isinstance(data, dict) and data in rows, 'original_row_mismatch')
    require(record.get('source_record_id') == digest({k: data.get(k) for k in IDENTITY_FIELDS}), 'identity_mismatch')
    require(data.get('typeCode') == 'C' and data.get('freqCode') == 'A'
            and str(data.get('period')) == query['period'][0], 'period_mismatch')
    for key in ('reporterCode', 'cmdCode', 'flowCode', 'partnerCode', 'partner2Code', 'customsCode', 'motCode'):
        require(key in query and str(data.get(key)) == query[key][0], 'query_dimension_mismatch:' + key)
    scope = payload.get('scope', {})
    if 'year' in scope:
        require(str(scope['year']) == str(data['period']), 'scope_year_mismatch')
    if 'query' in scope:
        require(all(str(data.get(k)) == str(v) for k, v in scope['query'].items()
                    if k in IDENTITY_FIELDS), 'scope_dimension_mismatch')
    require(isinstance(data.get('primaryValue'), (int, float))
            and not isinstance(data['primaryValue'], bool), 'trade_value_missing')
    return {'provider': 'UN Comtrade', 'record_type': 'annual_trade_observation',
            'scope': 'Entire returned annual HS row, original units and estimation flags; configured reporters/commodities/flows only, not all trade or historical vintages.'}


def evidence(record, s3, bucket):
    from metadata_engine.evidence import RawFailure, object_bytes, s3_key
    errors = []
    for ref in record.get('payload', {}).get('source_evidence', []):
        if not ref.get('sha256'):
            continue
        key = ref.get('key') or s3_key(ref.get('s3_uri', ''), bucket)
        key = key if key.startswith('research-data/') else 'research-data/' + key
        if not key.startswith('research-data/source_documents/un_comtrade/'):
            continue
        body = object_bytes(s3, bucket, key, expected=ref['sha256'])
        try:
            info = validate(body, record, ref.get('source_url', ''))
        except RawFailure as error:
            errors.append(str(error))
            continue
        return [{'artifact_kind': 'provider_record', 's3_uri': 's3://' + bucket + '/' + key,
                 'sha256': ref['sha256'], 'bytes': len(body), 'origin': 'first_party_source',
                 'source_url': ref['source_url'], 'retrieved_at': ref.get('retrieved_at'), 'validation': info}]
    raise RawFailure(errors[0] if errors else 'comtrade_matching_original_missing')
