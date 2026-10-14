"""Bounded October source-readiness audit and replayable pilot captures.

Uses AWS's credential chain and an in-memory Secrets Manager credential.
Never resets production cursors or changes existing provider quotas.
"""
import argparse
import base64
import hashlib
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import boto3
import requests
from botocore.config import Config
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'reports' / 'weekly-readiness-2026-10-09'
BUCKET = 'data-collection-059416028963-us-east-1-an'
PREFIX = 'research-data/readiness/2026-10-09'
REGION = 'us-east-1'
SECRET = 'arn:aws:secretsmanager:us-east-1:059416028963:secret:dataForSEO-wMV2J7'


def now():
    return datetime.now(timezone.utc).isoformat()


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_bytes(encoded(value) + b'\n')


def client(service):
    return boto3.client(service, region_name=REGION,
        config=Config(connect_timeout=10, read_timeout=30, retries={'max_attempts': 2}))


def scope():
    universe = json.loads((ROOT / 'config/company-universe.v0.5.json').read_text())
    names = {
        'biotech': ['MODERNA, INC.', 'BioNTech SE', 'ASTRAZENECA PLC'],
        'robotics': ['ABB Ltd', 'INTUITIVE SURGICAL INC', 'Aumann AG'],
        'semiconductors': ['ASML Holding N.V.', 'INTEL CORPORATION', 'APPLIED MATERIALS, INC.'],
        'energy_storage': ['QuantumScape Corp', 'AMERICAN BATTERY TECHNOLOGY Co', '(주)엘지에너지솔루션'],
    }
    queries = ['Moderna', 'BioNTech', 'AstraZeneca', 'ABB robotics', 'Intuitive Surgical',
               'Aumann automation', 'ASML', 'Intel semiconductor', 'Applied Materials',
               'QuantumScape', 'American Battery Technology', 'LG Energy Solution']
    pilot = []
    for sector, selected in names.items():
        for name in selected:
            company = next(c for c in universe['companies'] if c['canonical_name'] == name)
            assert company['collection_enabled'] and company['review_status'] == 'verified'
            assert any(s['sector_id'] == sector for s in company['sectors'])
            pilot.append({'company_id': company['company_id'], 'name': name, 'sector': sector,
                          'query': queries[len(pilot)], 'query_identity': 'discovery lead; entity match must be reviewed'})
    result = {'version': 'readiness-query-set-1.0', 'universe_version': universe['universe_version'],
              'universe_sha256': hashlib.sha256(encoded(universe)).hexdigest(),
              'required_companies': [c['company_id'] for c in universe['companies'] if c.get('collection_enabled')],
              'pending_identities': sum(c.get('review_status') != 'verified' for c in universe['companies'] if c.get('collection_enabled')),
              'pilot': pilot, 'historical_start': '2021-01-01', 'end_exclusive': '2026-10-09',
              'pilot_location': 'United States', 'pilot_location_code': 2840, 'pilot_language': 'en',
              'scope_note': 'Existing enabled global universe retained provisionally. US/English is a bounded pilot assumption, not the global acceptance scope.',
              'limits': 'No new licenses, no IBKR, no optional private acquisition, no NICE training export.'}
    save('scope.json', result)
    return result


def query(athena, sql, workgroup, database):
    config = athena.get_work_group(WorkGroup=workgroup)['WorkGroup']['Configuration']
    if config.get('BytesScannedCutoffPerQuery', 0) > 104857600 or not config.get('BytesScannedCutoffPerQuery') or not config.get('EnforceWorkGroupConfiguration'):
        raise ValueError('Missing enforced <=100 MiB scan cap')
    started = athena.start_query_execution(QueryString=sql, WorkGroup=workgroup,
        QueryExecutionContext={'Database': database, 'Catalog': 'AwsDataCatalog'})
    qid = started['QueryExecutionId']
    for _ in range(90):
        execution = athena.get_query_execution(QueryExecutionId=qid)['QueryExecution']
        state = execution['Status']['State']
        if state in ('SUCCEEDED', 'FAILED', 'CANCELLED'):
            result = {'query_id': qid, 'sql': sql, 'status': execution['Status'], 'statistics': execution['Statistics']}
            if state == 'SUCCEEDED':
                rows = athena.get_query_results(QueryExecutionId=qid, MaxResults=100)['ResultSet']['Rows']
                result['rows'] = [[cell.get('VarCharValue') for cell in row['Data']] for row in rows]
            return result
        time.sleep(1)
    athena.stop_query_execution(QueryExecutionId=qid)
    return {'query_id': qid, 'status': {'State': 'TIMEOUT'}, 'sql': sql}


def audit():
    old = json.loads((ROOT / 'reports/specialist-source-audit-2026-10-05.json').read_text())
    s3, glue, athena = client('s3'), client('glue'), client('athena')
    result = {'checked_at': now(), 'catalog': {}, 'progress': {}, 'workgroups': {}, 'queries': [], 'errors': []}
    for database in old['catalog']:
        try:
            result['catalog'][database] = [{'name': t['Name'], 'columns': t['StorageDescriptor']['Columns'],
                'partitions': t.get('PartitionKeys'), 'location': t['StorageDescriptor'].get('Location')}
                for page in glue.get_paginator('get_tables').paginate(DatabaseName=database) for t in page['TableList']]
        except Exception as exc:
            result['errors'].append({'database': database, 'error': type(exc).__name__})
    for database in ['optima_social_research']:
        try:
            result['catalog'][database] = glue.get_database(Name=database)['Database']['Name']
        except Exception as exc:
            result['catalog'][database] = {'status': 'absent_or_inaccessible', 'error': type(exc).__name__}
    keys = {key for group in old['progress'].values() for key in group}
    for health_key in ['health/latest.json', 'state/latest.json']:
        # Monitoring uses its own prefix; discover from the existing config.
        monitor = json.loads((ROOT / 'config/collection-monitoring.json').read_text())
        monitoring_prefix = monitor.get('s3_prefix', 'collection-monitoring')
        result['monitoring_configuration_keys'] = list(monitor)
        keys.add(health_key)
    for key in sorted(keys):
        try:
            obj = s3.get_object(Bucket=BUCKET, Key='research-data/' + key)
            result['progress'][key] = json.loads(obj['Body'].read())
        except Exception as exc:
            result['errors'].append({'key': key, 'error': type(exc).__name__})
    for workgroup in old['workgroups']:
        try:
            current = athena.get_work_group(WorkGroup=workgroup)['WorkGroup']
            recent = athena.list_query_executions(WorkGroup=workgroup, MaxResults=20)['QueryExecutionIds']
            receipts = athena.batch_get_query_execution(QueryExecutionIds=recent)['QueryExecutions'] if recent else []
            result['workgroups'][workgroup] = {'configuration': current['Configuration'], 'recent': receipts}
            successful = [r for r in receipts if r['Status']['State'] == 'SUCCEEDED' and r.get('StatementType') == 'DML'
                          and re.search(r"window_id\s*=\s*'[a-f0-9]{64}'|publication_month", r['Query'])]
            if successful:
                selected = [successful[0]]
                if successful[-1]['QueryExecutionId'] != selected[0]['QueryExecutionId']:
                    selected.append(successful[-1])
                for receipt in selected:
                    result['queries'].append({'workgroup': workgroup, 'prior_receipt': receipt['QueryExecutionId'],
                        'scope': 'recent receipt' if receipt == selected[0] else 'older of last 20 receipts; not necessarily 2021',
                        **query(athena, receipt['Query'], workgroup, receipt['QueryExecutionContext']['Database'])})
        except Exception as exc:
            result['errors'].append({'workgroup': workgroup, 'error': type(exc).__name__, 'message': str(exc)[:200]})
        save('live-audit.json', result)
        print('Audited', workgroup, flush=True)
    units = subprocess.run(['systemctl', 'list-units', '--all', '--plain', '--no-legend', 'optima-*'], capture_output=True, text=True)
    result['systemd_units'] = units.stdout
    timers = subprocess.run(['systemctl', 'show', '--all', 'optima-*.timer', '--property=Id,ActiveState,UnitFileState,LastTriggerUSec,NextElapseUSecRealtime'], capture_output=True, text=True)
    result['timers'] = timers.stdout
    save('live-audit.json', result)


def capture(name, source_id, url, payload=None, auth=None):
    """Cache each response once; ambiguous paid requests are never retried automatically."""
    path = OUT / 'captures' / (name + '.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        saved = json.loads(path.read_text())
        if saved.get('url') != url or saved.get('request') != payload:
            raise ValueError('Capture name reused for different request; use a versioned capture ID')
        return saved
    pending = path.with_suffix('.pending')
    if pending.exists():
        raise RuntimeError('Unacknowledged request; inspect provider receipt before retry')
    pending.write_text(now())
    headers = {'User-Agent': 'Optima Holdings source-readiness support@optima-holdings.com'}
    if auth:
        headers['Authorization'] = auth
    response = requests.request('POST' if payload is not None else 'GET', url, json=payload,
        headers=headers, timeout=60)
    body = response.content
    digest = hashlib.sha256(body).hexdigest()
    suffix = '.json' if 'json' in response.headers.get('Content-Type', '') else '.raw'
    key = PREFIX + '/raw/' + source_id + '/' + digest + suffix
    s3 = client('s3')
    try:
        s3.put_object(Bucket=BUCKET, Key=key, Body=body, ServerSideEncryption='AES256', IfNoneMatch='*')
    except ClientError as exc:
        if exc.response['Error']['Code'] != 'PreconditionFailed':
            raise
    assert hashlib.sha256(s3.get_object(Bucket=BUCKET, Key=key)['Body'].read()).hexdigest() == digest
    (path.parent / (digest + suffix)).write_bytes(body)
    try:
        data = response.json()
    except ValueError:
        data = None
    result = {'source_id': source_id, 'url': url, 'request': payload, 'observed_at': now(),
              'http_status': response.status_code, 'raw_s3_key': key, 'sha256': digest,
              'bytes': len(body), 'data': data, 'query_set_version': 'readiness-query-set-1.0',
              'history_complete': False, 'training_rights': 'unverified; raw source evidence only'}
    path.write_bytes(encoded(result) + b'\n')
    s3.put_object(Bucket=BUCKET, Key=PREFIX + '/receipts/' + name + '.json', Body=encoded({k: v for k, v in result.items() if k != 'data'}), ServerSideEncryption='AES256', IfNoneMatch='*')
    pending.unlink()
    print('Captured', name, response.status_code, flush=True)
    return result


def pilots():
    selected = scope()
    secret = json.loads(client('secretsmanager').get_secret_value(SecretId=SECRET)['SecretString'])
    token = secret['base64'].strip()
    if token.lower().startswith('basic '):
        token = token[6:]
    # Validate internally without printing or persisting the token.
    decoded = base64.b64decode(token).decode()
    if ':' not in decoded:
        raise ValueError('Secret is not a Basic authentication credential')
    auth = 'Basic ' + token
    keywords = [p['query'] for p in selected['pilot']]
    plans = [('dataforseo-keyword-history', 'dataforseo_labs/google/historical_keyword_data/live',
              {'keywords': keywords, 'location_code': 2840, 'language_code': 'en'}),
             ('dataforseo-trends', 'keywords_data/dataforseo_trends/explore/live',
              {'keywords': keywords[:3], 'location_code': 2840, 'type': 'web', 'date_from': '2021-01-01', 'date_to': '2026-10-08'})]
    plans += [('dataforseo-serp-' + str(i), 'serp/google/organic/live/advanced',
              {'keyword': p['query'], 'location_code': 2840, 'language_code': 'en', 'device': 'desktop', 'depth': 10})
              for i, p in enumerate(selected['pilot'])]
    cost = 0.0
    for name, endpoint, payload in plans:
        if cost > 1:
            print('Pilot stop: USD 1 response-cost threshold', flush=True)
            break
        result = capture(name, 'S65', 'https://api.dataforseo.com/v3/' + endpoint, [payload], auth)
        data = result.get('data') or {}
        cost += float(data.get('cost', 0))
        save('dataforseo-cost.json', {'actual_cost_usd': cost, 'note': 'No automatic paid retry. Replays use saved responses. At most 14 bounded requests.', 'checked_at': now()})
    public = [
        ('epmc-old-trial', 'S28', 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?' + urlencode({'query': 'NCT04280705 AND FIRST_PDATE:[2020-01-01 TO 2021-12-31]', 'format': 'json', 'resultType': 'core', 'pageSize': 3})),
        ('epmc-recent-trial', 'S28', 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?' + urlencode({'query': 'NCT04280705 AND FIRST_PDATE:[2024-01-01 TO 2026-10-08]', 'format': 'json', 'resultType': 'core', 'pageSize': 3})),
        ('pubmed-trial', 'S27', 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?' + urlencode({'db': 'pubmed', 'term': 'NCT04280705', 'retmode': 'json', 'retmax': 3})),
        ('github-intel-org', 'S46', 'https://api.github.com/orgs/intel'),
        ('github-intel-releases', 'S46', 'https://api.github.com/repos/intel/llvm/releases?per_page=3'),
        ('github-intel-license', 'S46', 'https://api.github.com/repos/intel/llvm/license'),
        ('clinicaltrial-remdesivir', 'S17', 'https://clinicaltrials.gov/api/v2/studies/NCT04280705'),
        ('bluesky-search', 'S64', 'https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?' + urlencode({'q': 'QuantumScape', 'limit': 3})),
        ('federal-register-battery', 'S51', 'https://www.federalregister.gov/api/v1/documents.json?' + urlencode({'conditions[term]': 'battery', 'conditions[publication_date][gte]': '2026-01-01', 'conditions[publication_date][lte]': '2026-10-08', 'per_page': 3})),
    ]
    for name, source, url in public:
        try:
            result = capture(name, source, url)
            if source == 'S28' and result.get('data'):
                for article in result['data'].get('resultList', {}).get('result', []):
                    if article.get('isOpenAccess') == 'Y' and article.get('pmcid'):
                        capture('epmc-fulltext-' + article['pmcid'], 'S28', 'https://www.ebi.ac.uk/europepmc/webservices/rest/' + article['pmcid'] + '/fullTextXML')
                        break
            if source == 'S27' and result.get('data'):
                ids = result['data'].get('esearchresult', {}).get('idlist', [])
                if ids:
                    time.sleep(0.4)
                    capture('pubmed-abstracts', 'S27', 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?' + urlencode({'db': 'pubmed', 'id': ','.join(ids), 'retmode': 'xml'}))
        except Exception as exc:
            save(name + '-blocker.json', {'source_id': source, 'exception': type(exc).__name__, 'checked_at': now()})
    award = {'filters': {'keywords': ['APPLIED MATERIALS'], 'award_type_codes': ['A', 'B', 'C', 'D'],
                        'time_period': [{'start_date': '2021-01-01', 'end_date': '2026-10-08'}]},
             'fields': ['Award ID', 'Recipient Name', 'Award Amount', 'Awarding Agency', 'Start Date', 'End Date', 'Description'],
             'page': 1, 'limit': 3, 'sort': 'Award Amount', 'order': 'desc'}
    try:
        capture('usaspending-applied-materials', 'S43', 'https://api.usaspending.gov/api/v2/search/spending_by_award/', award)
    except Exception as exc:
        save('usaspending-blocker.json', {'exception': type(exc).__name__, 'checked_at': now()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['scope', 'audit', 'pilots'])
    mode = parser.parse_args().mode
    {'scope': scope, 'audit': audit, 'pilots': pilots}[mode]()
