"""Compare current provider common-stock listings with captured/catalogued scope."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import boto3
import pyarrow.parquet as pq
from eodhd_universe import EODHDClient, parse_token


def main():
    root = Path(__file__).resolve().parent
    config = json.loads((root / 'config/eodhd-universe.json').read_text())
    bucket = 'data-collection-059416028963-us-east-1-an'
    prefix = 'research-data/operations/eodhd/global-audit/2026-10-20/'
    s3 = boto3.client('s3', region_name='us-east-1')
    secret = boto3.client('secretsmanager', region_name=config['region']).get_secret_value(SecretId=config['secret_id'])
    client = EODHDClient(parse_token(secret['SecretString']))
    account = client.account()
    used = account['apiRequests'] if account['apiRequestsDate'] == datetime.now(timezone.utc).date().isoformat() else 0
    assert isinstance(used, int) and used + 150 < min(account['dailyRateLimit'] - 2000, 98000)
    manifest_key = 'research-data/manifests/collection_runs/source=eodhd/dataset=listing_inventory/run_4accc263-2cce-4a36-a647-e63d955517c5/final.json'
    inventory = json.loads(s3.get_object(Bucket=bucket, Key=manifest_key)['Body'].read())
    exchanges = inventory['task']['scope']['exchanges']
    release_key = 'research-data/curated/eodhd/releases/f0e8983c840f2e0ed6e6787174ea9cba4e95c4508bcf22b3e6a0e448ddb0939b/tables/listing_inventory/part-00000.parquet'
    data = s3.get_object(Bucket=bucket, Key=release_key)['Body'].read()
    rows = pq.read_table(io.BytesIO(data), columns=['provider_symbol', 'exchange_code', 'listing_status']).to_pylist()
    old = {(r['provider_symbol'], r['listing_status']) for r in rows}
    original_symbols = {r['provider_symbol'] for r in rows}
    missing = json.loads(s3.get_object(Bucket=bucket, Key=prefix + 'missing_examples.json')['Body'].read())['rows'][1:]
    catalogued = original_symbols - {r[0] for r in missing}
    results = []
    def fetch(code, status):
        params = {'type': 'common_stock'}
        if status == 'delisted':
            params['delisted'] = 1
        try:
            records, raw, url = client.get('exchange-symbol-list/' + code, params)
            if not isinstance(records, list):
                raise ValueError('Expected exchange symbol list')
            checksum = hashlib.sha256(raw).hexdigest()
            key = prefix + 'live-listings/' + code + '/' + status + '-' + checksum + '.json'
            s3.put_object(Bucket=bucket, Key=key, Body=raw, ContentType='application/json', ServerSideEncryption='AES256')
            symbols = {str(r['Code']) + '.' + code for r in records}
            old_symbols = {symbol for symbol, previous_status in old if previous_status == status and symbol.rsplit('.', 1)[1] == code}
            result = {'exchange': code, 'status': status, 'records': len(records), 'distinct_symbols': len(symbols),
                      'added_since_inventory': sorted(symbols - old_symbols), 'removed_since_inventory': sorted(old_symbols - symbols),
                      'live_symbols_not_catalogued': sorted(symbols - catalogued), 'source_key': key, 'source_sha256': checksum,
                      'request_status': 'complete'}
        except Exception as exc:
            result = {'exchange': code, 'status': status, 'request_status': 'failed', 'error_type': type(exc).__name__,
                      'reason': getattr(exc, 'code', 'request_failed')}
        print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in result.items() if k not in {'source_key','source_sha256'}}), flush=True)
        return result
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(fetch, r['Code'], status) for r in exchanges for status in ('active', 'delisted')]
        for future in as_completed(futures):
            results.append(future.result())
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'inventory_observed_at': inventory['finished_at'],
              'instrument_type': 'common_stock', 'exchange_count': len(exchanges), 'requested_statuses': ['active', 'delisted'],
              'failed_requests': [r for r in results if r['request_status'] != 'complete'],
              'live_listing_records': sum(r.get('records', 0) for r in results),
              'added_listing_status_pairs': sum(len(r.get('added_since_inventory', [])) for r in results),
              'removed_listing_status_pairs': sum(len(r.get('removed_since_inventory', [])) for r in results),
              'results': sorted(results, key=lambda r: (r['exchange'], r['status']))}
    s3.put_object(Bucket=bucket, Key=prefix + 'live-inventory-comparison.json', Body=json.dumps(report).encode(),
                  ServerSideEncryption='AES256', ContentType='application/json')
    print('SUMMARY', json.dumps({k: v for k, v in report.items() if k != 'results'}), flush=True)


if __name__ == '__main__':
    main()
