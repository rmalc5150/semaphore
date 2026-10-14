"""Normalize saved pilot evidence and publish an isolated, immutable sample release."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter

import pyarrow as pa
import pyarrow.parquet as pq
from botocore.exceptions import ClientError

from weekly_readiness import OUT, BUCKET, PREFIX, client, encoded, now, query, save

DATABASE = 'optima_source_readiness'
TABLE = 'source_samples_windows'
WORKGROUP = 'optima-eodhd-research'


def normalize():
    rows, captures, coverage = [], [], []
    selected = json.loads((OUT / 'scope.json').read_text())
    by_query = {p['query'].lower(): p['company_id'] for p in selected['pilot']}
    for path in sorted((OUT / 'captures').glob('*.json')):
        receipt = json.loads(path.read_text())
        if 'raw_s3_key' not in receipt:
            continue
        source = receipt['source_id']
        # These first-run receipt labels were corrected after the pilot process
        # had started; keep immutable originals and record the correction.
        if path.stem.startswith('github-intel'):
            source = 'S46'
        if path.stem.startswith('usaspending'):
            source = 'S43'
        if receipt['http_status'] != 200:
            coverage.append({'capture': path.stem, 'source_id': source, 'status': 'blocked', 'http_status': receipt['http_status']})
            continue
        data = receipt['data']
        captures.append({k: v for k, v in receipt.items() if k != 'data'})
        def add(dataset, provider_id, payload, event_date=None, company_id=None, unit=None):
            rows.append({'source_id': source, 'capture_id': path.stem, 'dataset': dataset,
                'provider_id': str(provider_id), 'event_date': event_date, 'company_id': company_id,
                'source_url': receipt['url'], 'observed_at': receipt['observed_at'],
                'raw_s3_key': receipt['raw_s3_key'], 'raw_sha256': receipt['sha256'],
                'unit': unit, 'payload_json': encoded(payload).decode(),
                'point_in_time_eligible': False, 'training_rights': 'not_accepted; source-specific review required'})
        before = len(rows)
        if source == 'S65':
            for task in data.get('tasks', []):
                if task.get('status_code') != 20000:
                    coverage.append({'capture': path.stem, 'status': 'provider_task_error', 'status_code': task.get('status_code')})
                    continue
                for result in task.get('result') or []:
                    if 'keyword-history' in path.stem:
                        for item in result.get('items') or []:
                            keyword = item['keyword']
                            dates = []
                            for history in item.get('history') or []:
                                date = f"{history['year']:04d}-{history['month']:02d}-01"
                                dates.append(date)
                                add('keyword_history', keyword + ':' + date, {'keyword': keyword, **history,
                                    'task_id': task['id'], 'location_code': 2840, 'language_code': 'en'}, date,
                                    by_query.get(keyword.lower()), 'provider keyword_info; search_volume is an average, monthly_searches retains individual months')
                            coverage.append({'capture': path.stem, 'keyword': keyword, 'historical_months': len(dates), 'earliest': min(dates) if dates else None,
                                'latest': max(dates) if dates else None, 'early_2021': 'Documentation starts August 2021; retain any earlier returned months as observed, without assuming coverage.', 'historical_serp': 'not provided'})
                    elif 'trends' in path.stem:
                        keywords = task['data']['keywords']
                        for item_index, item in enumerate(result.get('items') or []):
                            for point in item.get('data') or []:
                                for i, keyword in enumerate(keywords):
                                    add('trend', str(item_index) + ':' + keyword + ':' + point['date_from'], {'keyword': keyword, 'item_type': item.get('type'), 'date_from': point['date_from'],
                                        'date_to': point['date_to'], 'value': point['values'][i], 'task_id': task['id'],
                                        'location_code': 2840, 'query_group': keywords}, point['date_from'], by_query.get(keyword.lower()), 'relative search interest; query-group dependent')
                    else:
                        keyword = task['data']['keyword']
                        for i, item in enumerate(result.get('items') or []):
                            add('serp_snapshot', task['id'] + ':' + str(i), {'keyword': keyword, 'task_id': task['id'],
                                'engine': 'google', 'location_code': 2840, 'language_code': 'en', 'device': 'desktop', **item},
                                result.get('datetime'), by_query.get(keyword.lower()), 'rank_group and rank_absolute; result type retained')
        elif isinstance(data, dict) and 'resultList' in data:
            for article in data['resultList'].get('result', []):
                add('literature_metadata', article['source'] + ':' + article['id'], article, article.get('firstPublicationDate'))
        elif source == 'S43' and isinstance(data, dict):
            for award in data.get('results', []):
                add('award_search_candidate', award.get('generated_internal_id') or award.get('Award ID'), award, award.get('Start Date'), unit='USD obligations; recipient identity match not accepted')
        elif isinstance(data, list):
            for i, item in enumerate(data):
                add('releases' if 'releases' in path.stem else 'repository_inventory', item.get('id') or item.get('path') or item.get('sha') or i,
                    item, item.get('published_at'), unit='release or repository artifact; not adoption')
        elif data is None:
            body = next(p for p in (OUT / 'captures').glob(receipt['sha256'] + '.*')).read_bytes()
            if source in ('S27', 'S28'):
                root = ET.fromstring(body)
                if source == 'S27':
                    for article in root.findall('.//PubmedArticle'):
                        pmid = article.findtext('.//PMID')
                        add('pubmed_abstract', pmid, {'pmid': pmid, 'xml': ET.tostring(article, encoding='unicode')})
                else:
                    license_text = [' '.join(x.itertext()) for x in root.findall('.//license')]
                    add('fulltext_evidence', root.findtext('.//article-id'), {'licenses': license_text,
                        'sections': [{'title': x.findtext('title'), 'text': ' '.join(x.itertext())} for x in root.findall('.//body/sec')],
                        'supplements': [ET.tostring(x, encoding='unicode') for x in root.findall('.//supplementary-material')],
                        'related_articles': [ET.tostring(x, encoding='unicode') for x in root.findall('.//related-article')],
                        'reuse': 'License captured; no training export enabled'})
            elif source == 'S56':
                if not body.startswith(b'PK'):
                    coverage.append({'capture': path.stem, 'source_id': source, 'status': 'not_a_workbook',
                        'note': 'HTTP 200 HTML must not be accepted as an XLSX inventory.'})
                else:
                    import io
                    import openpyxl
                    workbook = openpyxl.load_workbook(io.BytesIO(body), read_only=True, data_only=True)
                    accepted = 0
                    for sheet in workbook:
                        headers = None
                        for values in sheet.iter_rows(values_only=True):
                            strings = [str(v).strip() if v is not None else '' for v in values]
                            if headers is None:
                                if any('Plant ID' in v for v in strings) and any('Generator ID' in v for v in strings):
                                    headers = strings
                                continue
                            record = {k: v for k, v in zip(headers, values) if k}
                            if not any(str(v).strip() == 'MWH' for v in values if v is not None):
                                continue
                            add('generator_inventory_sample', sheet.title + ':' + str(record.get('Plant ID')) + ':' + str(record.get('Generator ID')),
                                {'sheet': sheet.title, 'edition': '2026-08', 'fields_with_original_units': record}, '2026-08-01',
                                unit='Header units retained; MW capacity does not establish MWh energy capacity')
                            accepted += 1
                            if accepted >= 5:
                                break
                        if accepted >= 5:
                            break
                    workbook.close()
                    if not accepted:
                        coverage.append({'capture': path.stem, 'source_id': source, 'status': 'workbook_without_accepted_battery_sample'})
            elif source == 'S48' and path.stem == 'mlperf-intel-summary':
                text = body.decode()
                add('benchmark_performance', receipt['sha256'], {'release': 'inference_results_v5.1', 'division': 'closed',
                    'submitter': 'Intel', 'original_log': text, 'configuration_capture': 'mlperf-intel-system',
                    'note': 'Compare only matched workload/scenario/quality/power boundary; no customer adoption inference'})
            elif source == 'S19' and body.startswith(b'%PDF'):
                import io
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(body))
                for index, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        add('original_fda_review_page', receipt['sha256'] + ':' + str(index + 1),
                            {'product': 'SPIKEVAX', 'sponsor': 'Moderna', 'page': index + 1, 'text': text,
                             'review_date': '2022-01-30', 'trial': 'NCT04470427'}, '2022-01-30')
            elif source == 'S11' or path.stem == 'intel-official-github':
                add('official_website_evidence', receipt['sha256'], {'bytes': len(body), 'parsed': False,
                    'note': 'Original domain captured; facts and linked board/repository ownership require review.'})
        elif source == 'S59' and isinstance(data, dict):
            assert data.get('status') == 'REQUEST_SUCCEEDED', 'BLS request not successful'
            for series in data['Results']['series']:
                for point in series['data']:
                    add('labor_series', series['seriesID'] + ':' + point['year'] + ':' + point['period'],
                        {'series_id': series['seriesID'], **point}, point['year'] + '-' + point['period'][1:] + '-01',
                        unit='USD/hour; average hourly earnings, manufacturing, all employees, seasonally adjusted; not all-in labor cost')
        elif source == 'S51' and isinstance(data, dict):
            for document in data.get('results', []):
                add('rulemaking_document', document['document_number'], document, document.get('publication_date'),
                    unit='document type retained; proposed rule does not establish effective law')
        elif isinstance(data, dict):
            add('original_metadata', data.get('id') or path.stem, data)
        coverage.append({'capture': path.stem, 'source_id': source, 'normalized_rows': len(rows) - before,
                         'history_complete': False, 'status': 'bounded_sample' if len(rows) > before else 'empty_or_unparsed'})
    identities = [(r['source_id'], r['capture_id'], r['dataset'], r['provider_id']) for r in rows]
    duplicates = [identity for identity, count in Counter(identities).items() if count > 1]
    assert not duplicates, 'Duplicate normalized row identity: ' + repr(duplicates[:3])
    save('sample-coverage.json', coverage)
    save('receipt-label-corrections.json', {'github-intel-*': {'original_source_id': 'S48', 'correct_source_id': 'S46'},
        'usaspending-applied-materials': {'original_source_id': 'S42', 'correct_source_id': 'S43'},
        'note': 'Immutable original raw receipts retained; normalized dataset uses canonical checklist IDs.'})
    return rows, captures


def publish():
    rows, captures = normalize()
    release = hashlib.sha256(encoded({'version': 'readiness-sample-1.0', 'rows': rows})).hexdigest()
    location = PREFIX + '/curated/' + release + '/'
    schema = pa.schema([(k, pa.bool_() if k == 'point_in_time_eligible' else pa.string()) for k in rows[0]])
    table = pa.Table.from_pylist(rows, schema=schema)
    path = OUT / ('sample-' + release + '.parquet')
    pq.write_table(table, path, compression='snappy')
    assert pq.read_table(path).to_pylist() == rows
    s3, glue, athena = client('s3'), client('glue'), client('athena')
    body = path.read_bytes()
    key = location + 'part-00000.parquet'
    try:
        s3.put_object(Bucket=BUCKET, Key=key, Body=body, ServerSideEncryption='AES256', IfNoneMatch='*')
    except ClientError as exc:
        if exc.response['Error']['Code'] != 'PreconditionFailed':
            raise
    assert hashlib.sha256(s3.get_object(Bucket=BUCKET, Key=key)['Body'].read()).digest() == hashlib.sha256(body).digest()
    try:
        glue.create_database(DatabaseInput={'Name': DATABASE, 'Description': 'Bounded source-readiness samples; incomplete history and unaccepted training rights.'})
    except ClientError as exc:
        if exc.response['Error']['Code'] != 'AlreadyExistsException':
            raise
    columns = [{'Name': f.name, 'Type': 'boolean' if pa.types.is_boolean(f.type) else 'string'} for f in schema]
    descriptor = {'Columns': columns, 'Location': 's3://' + BUCKET + '/' + location,
        'InputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat',
        'OutputFormat': 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat',
        'SerdeInfo': {'SerializationLibrary': 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'}}
    definition = {'Name': TABLE, 'TableType': 'EXTERNAL_TABLE', 'Parameters': {'classification': 'parquet', 'optima_owner': 'source-readiness'},
        'PartitionKeys': [{'Name': 'release_id', 'Type': 'string'}], 'StorageDescriptor': {**descriptor, 'Location': 's3://' + BUCKET + '/' + PREFIX + '/empty/'}}
    try:
        glue.create_table(DatabaseName=DATABASE, TableInput=definition)
    except ClientError as exc:
        if exc.response['Error']['Code'] != 'AlreadyExistsException':
            raise
        old = glue.get_table(DatabaseName=DATABASE, Name=TABLE)['Table']
        assert old['Parameters'].get('optima_owner') == 'source-readiness' and old['StorageDescriptor']['Columns'] == columns
    partition = {'Values': [release], 'StorageDescriptor': descriptor, 'Parameters': {'optima_owner': 'source-readiness', 'release_id': release}}
    try:
        glue.create_partition(DatabaseName=DATABASE, TableName=TABLE, PartitionInput=partition)
    except ClientError as exc:
        if exc.response['Error']['Code'] != 'AlreadyExistsException':
            raise
        old = glue.get_partition(DatabaseName=DATABASE, TableName=TABLE, PartitionValues=[release])['Partition']
        assert old['StorageDescriptor']['Location'] == descriptor['Location']
    sql = f"SELECT source_id, dataset, count(*) AS records FROM {DATABASE}.{TABLE} WHERE release_id='{release}' GROUP BY source_id,dataset ORDER BY source_id,dataset"
    receipt = query(athena, sql, WORKGROUP, DATABASE)
    expected = [[source, dataset, str(count)] for (source, dataset), count in sorted(Counter((r['source_id'], r['dataset']) for r in rows).items())]
    assert receipt['status']['State'] == 'SUCCEEDED' and receipt['rows'][1:] == expected, 'Athena counts differ'
    sample = query(athena, f"SELECT source_id,provider_id,event_date,raw_s3_key,raw_sha256,point_in_time_eligible FROM {DATABASE}.{TABLE} WHERE release_id='{release}' LIMIT 10", WORKGROUP, DATABASE)
    result = {'verified_at': now(), 'release_id': release, 'database': DATABASE, 'table': TABLE, 'workgroup': WORKGROUP,
        'rows': len(rows), 'parquet_key': key, 'parquet_sha256': hashlib.sha256(body).hexdigest(), 'query': receipt, 'field_sample': sample,
        'expected_counts': expected, 'history_complete': False, 'recurring_capture_verified': False,
        'note': 'Isolated bounded sample publication; does not populate production provider tables or certify point-in-time training data.'}
    result['verification_s3_key'] = PREFIX + '/publications/' + release + '/' + receipt['query_id'] + '.json'
    s3.put_object(Bucket=BUCKET, Key=result['verification_s3_key'], Body=encoded(result), ServerSideEncryption='AES256', IfNoneMatch='*')
    save('publication.json', result)
    print(json.dumps({'release_id': release, 'rows': len(rows), 'query_id': receipt['query_id']}), flush=True)


if __name__ == '__main__':
    publish()
