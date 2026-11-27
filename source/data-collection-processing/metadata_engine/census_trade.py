"""Validate Census trade measurements against the original tabular API row."""
from datetime import date
from collections import Counter
from functools import lru_cache
import json
from urllib.parse import parse_qs, urlsplit

from metadata_engine.evidence import RawFailure, object_bytes, s3_key

SOURCE = 'us_census_international_trade_api'
ENDPOINT = '/data/timeseries/intltrade'
FIELDS = {'imports': ('I_COMMODITY', 'GEN_VAL_MO'),
          'exports': ('E_COMMODITY', 'ALL_VAL_MO')}


@lru_cache(maxsize=4)
def native_table(body, commodity_field, value_field, year, month, commodity):
    try:
        header, *rows = json.loads(body)
    except (ValueError, TypeError):
        raise RawFailure('census_trade_invalid_tabular_response') from None
    required = {'CTY_CODE', 'CTY_NAME', commodity_field, value_field, 'YEAR', 'MONTH'}
    if not isinstance(header, list) or not all(isinstance(field, str) for field in header):
        raise RawFailure('census_trade_invalid_header')
    repeats = {field for field, count in Counter(header).items() if count > 1}
    if not repeats.issubset({'CTY_CODE', commodity_field}) or not required.issubset(header) or not rows:
        raise RawFailure('census_trade_missing_native_fields')
    table = {}
    for values in rows:
        if not isinstance(values, list) or len(values) != len(header):
            raise RawFailure('census_trade_row_width_mismatch')
        row = dict(zip(header, values))
        if any(row[field] != value for field, value in zip(header, values) if field in repeats):
            raise RawFailure('census_trade_repeated_predicate_mismatch')
        key = row['CTY_CODE']
        if (not isinstance(key, str) or not key or key in table
                or row['YEAR'] != year or row['MONTH'] != month
                or row[commodity_field] != commodity):
            raise RawFailure('census_trade_native_identity_or_period_mismatch')
        table[key] = row
    return table


@lru_cache(maxsize=4)
def original_response(s3, bucket, key, checksum):
    return object_bytes(s3, bucket, key, limit=16 * 1024**2, expected=checksum)


def evidence(record, s3, bucket):
    payload = record.get('payload', {})
    scope = payload.get('scope', {})
    row = payload.get('data', {})
    direction = scope.get('direction')
    if direction not in FIELDS:
        raise RawFailure('census_trade_direction_missing')
    commodity_field, value_field = FIELDS[direction]
    try:
        year, month = str(row['YEAR']), str(row['MONTH'])
        month_start = date.fromisoformat(f'{year}-{month}-01')
        country = row['CTY_CODE']
        commodity = row[commodity_field]
        if scope.get('data_start') and date.fromisoformat(scope['data_start']) != month_start:
            raise RawFailure('census_trade_observation_outside_scope')
        scoped_code = '-' if scope.get('commodity') == 'TOTAL' else scope.get('commodity')
        if scoped_code != commodity:
            raise RawFailure('census_trade_commodity_outside_scope')
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, RawFailure):
            raise
        raise RawFailure('census_trade_missing_observation_dimensions') from None
    identity = f'{direction}:{year}-{month}:{country}:{commodity}'
    if record['source_record_id'] != identity:
        raise RawFailure('census_trade_observation_identity_mismatch')
    for ref in payload.get('source_evidence', []):
        url = ref.get('source_url', '')
        parsed = urlsplit(url)
        if (parsed.scheme, parsed.netloc, parsed.path) != (
            'https', 'api.census.gov', f'{ENDPOINT}/{direction}/hs'
        ):
            continue
        query = parse_qs(parsed.query, keep_blank_values=True)
        if (query.get('YEAR') != [year] or query.get('MONTH') != [month]
                or query.get(commodity_field) != [commodity]
                or query.get('CTY_CODE') not in (['*'], [country])
                or set(query) != {'get', commodity_field, 'CTY_CODE', 'YEAR', 'MONTH'}):
            continue
        key = ref.get('key')
        if key:
            key = 'research-data/' + key.removeprefix('research-data/')
        else:
            key = s3_key(ref['s3_uri'], bucket)
        if not key.startswith(f'research-data/source_documents/{SOURCE}/') or not ref.get('sha256'):
            raise RawFailure('census_trade_invalid_raw_reference')
        body = original_response(s3, bucket, key, ref['sha256'])
        table = native_table(body, commodity_field, value_field, year, month, commodity)
        if table.get(country) != row:
            raise RawFailure('census_trade_full_native_row_mismatch')
        return [{
            'artifact_kind': 'provider_record',
            's3_uri': f's3://{bucket}/{key}',
            'sha256': ref['sha256'],
            'bytes': len(body),
            'origin': 'first_party_source',
            'source_url': url,
            'retrieved_at': ref.get('retrieved_at'),
            'validation': {
                'format': 'json', 'record_type': 'census_monthly_trade_row',
                'value_field': value_field, 'period': month_start.isoformat()[:7],
                'commodity': commodity, 'country_code': country,
                'scope': 'All fields returned by the configured monthly USD trade value query.',
            },
        }]
    raise RawFailure('census_trade_original_response_missing')
