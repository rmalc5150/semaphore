"""Bounded additional specialist-source collection, with durable page checkpoints.

Archives describe event periods; a download today never establishes past availability.
All entity links remain candidates. No import-time network or credential access.
"""
from __future__ import annotations
import argparse
import csv
import io
import json
import re
import time
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode, urljoin
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

from collection_storage import AlreadyComplete, CollectionRun, StorageSettings, now, task_spec, write_json
from research_contract import ROOT, digest, load_json, seal_record
from regulatory_collection import EvidenceClient, SourceIssue, require, stamp

VERSION = 'specialist-inputs-1.2'
PLAN = ROOT / 'config/specialist-inputs.json'
OUT = ROOT / 'reports/specialist-expansion-2026-10-09'


class SpecialistClient(EvidenceClient):
    def get(self, url, *args, **kwargs):
        if urlsplit(url).hostname == 'eutils.ncbi.nlm.nih.gov':
            # NCBI's public API permits three requests/second without a key.
            self.sleep(max(0, 0.4 - (time.monotonic() - self.last_request)))
        if urlsplit(url).hostname == 'api.github.com':
            import fcntl
            path = ROOT / 'reports/specialist-github-quota.json'
            with (ROOT / '.specialist-github-quota.lock').open('a+') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                current = time.time()
                calls = json.loads(path.read_text()) if path.exists() else []
                calls = [v for v in calls if v > current - 3600]
                require(len(calls) < 40, 'github_public_hour_budget')
                calls.append(current)
                temporary = path.with_suffix('.tmp')
                temporary.write_text(json.dumps(calls))
                temporary.replace(path)
        return super().get(url, *args, **kwargs)


def item(identity, data, url, day=None, basis='provider'):
    from urllib.parse import quote
    return {'id': str(identity), 'data': data, 'url': quote(url, safe=":/?#[]@!$&'()*+,;=%"), 'date': day, 'basis': basis}


def fetch_page(client, job, cursor):
    """Return a validated bounded page and an explicit next cursor, or None."""
    kind, p = job['adapter'], job['parameters']
    from specialist_authenticated import KINDS as AUTH_KINDS, fetch as auth_fetch
    if kind in AUTH_KINDS:
        return auth_fetch(client, job, cursor, item)
    from specialist_public_apis import KINDS, fetch
    if kind in KINDS:
        return fetch(client, job, cursor, item)
    offset = int(cursor or 0) if kind in {'nih', 'bls', 'cms'} else 0
    url = p['url']
    if kind == 'nih':
        require(offset < 15000, 'nih_offset_cap_split_scope_required')
        data = client.json(url, body={'criteria': p['criteria'], 'offset': offset, 'limit': 100,
                                    'sort_field': 'appl_id', 'sort_order': 'asc'})
        rows, total = data.get('results'), data.get('meta', {}).get('total')
        require(isinstance(rows, list) and isinstance(total, int), 'nih_response_shape')
        require(total <= 15000, 'nih_result_cap_split_scope_required')
        require(bool(rows) or offset == total, 'nih_missing_page')
        result = [item(r['appl_id'], r, r.get('project_detail_url') or url,
                       (r.get('project_start_date') or '')[:10] or None) for r in rows]
        return result, str(offset + len(rows)) if offset + len(rows) < total else None
    if kind == 'ted':
        position = json.loads(cursor) if cursor else {'token': None, 'seen': 0}
        body = {'query': p['query'], 'fields': p['fields'], 'limit': 100, 'scope': 'ALL',
                'paginationMode': 'ITERATION', 'checkQuerySyntax': False, 'onlyLatestVersions': False}
        if position['token']:
            body['iterationNextToken'] = position['token']
        data = client.json(url, body=body)
        require(data.get('timedOut') is not True, 'ted_query_timeout')
        rows = data.get('notices')
        require(isinstance(rows, list) and isinstance(data.get('totalNoticeCount'), int), 'ted_response_shape')
        result = []
        for r in rows:
            identity = r.get('publication-number') or r.get('notice-id')
            require(identity is not None, 'ted_missing_notice_id')
            if isinstance(identity, list):
                identity = identity[0]
            result.append(item(identity, r, 'https://ted.europa.eu/en/notice/-/detail/' + str(identity)))
        token = data.get('iterationNextToken')
        require(not token or token != position['token'], 'ted_cursor_cycle')
        seen = position['seen'] + len(rows)
        require(seen <= data['totalNoticeCount'], 'ted_count_mismatch')
        require(seen == data['totalNoticeCount'] or bool(rows and token), 'ted_missing_iteration_page')
        return result, json.dumps({'token': token, 'seen': seen}) if seen < data['totalNoticeCount'] else None
    if kind == 'bls':
        data = client.json(url, params={'startyear': p['year'], 'endyear': p['year']})
        require(data.get('status') == 'REQUEST_SUCCEEDED', 'bls_provider_error')
        series = data.get('Results', {}).get('series', [])
        require(len(series) == 1 and series[0].get('seriesID') == p['series'], 'bls_series_mismatch')
        return [item(p['series'] + ':' + r['year'] + ':' + r['period'],
                     {'series': p['series'], 'unit': p['unit'], **r}, url,
                     None)
                for r in series[0]['data']], None
    if kind == 'comtrade':
        data = client.json(url, params=p['query'])
        require(data.get('error') in (None, '', False), 'comtrade_provider_error')
        rows = data.get('data')
        require(isinstance(rows, list), 'comtrade_response_shape')
        require(len(rows) < int(p['query']['maxRecords']), 'comtrade_preview_truncation')
        identity_fields = ('typeCode', 'freqCode', 'period', 'reporterCode', 'cmdCode', 'flowCode', 'partnerCode', 'partner2Code', 'customsCode', 'motCode', 'classificationCode')
        return [item(digest({k: r.get(k) for k in identity_fields}), {'query': p['query'], 'trade': r, 'units': 'provider fields retained'}, url,
                     None, 'derived') for r in rows], None
    if kind == 'federal_register':
        params = dict(p['query'], page=int(cursor or 1), per_page=100)
        data = client.json(url, params=params)
        if data.get('count') == 0 and 'results' not in data:
            return [], None
        rows = data.get('results')
        require(isinstance(rows, list) and isinstance(data.get('total_pages'), int), 'fr_response_shape')
        require(data['total_pages'] <= 1000, 'fr_split_scope_required')
        return [item(r['document_number'], r, r['html_url'], r.get('publication_date')) for r in rows], \
            str(params['page'] + 1) if params['page'] < data['total_pages'] else None
    if kind == 'epmc':
        data = client.json(url, params={'query': p['query'], 'format': 'json', 'resultType': 'core',
                                       'pageSize': 100, 'cursorMark': cursor or '*'})
        rows = data.get('resultList', {}).get('result')
        require(isinstance(rows, list) and isinstance(data.get('hitCount'), int), 'epmc_response_shape')
        result = [item(r['source'] + ':' + r['id'], r,
                       'https://europepmc.org/article/' + r['source'] + '/' + r['id'], r.get('firstPublicationDate')) for r in rows]
        token = data.get('nextCursorMark')
        return result, token if rows and token and token != (cursor or '*') else None
    if kind == 'github':
        page = int(cursor or 1)
        data = json.loads(client.get(url, params={'per_page': 100, 'page': page}))
        require(isinstance(data, list), 'github_response_shape')
        return [item(r['id'], r, r['html_url'], (r.get('published_at') or '')[:10] or None) for r in data], \
            str(page + 1) if len(data) == 100 else None
    if kind == 'mlperf':
        repo = p['repository']
        metadata = client.json('https://api.github.com/repos/' + repo)
        default = metadata.get('default_branch')
        require(bool(default), 'mlperf_missing_default_branch')
        branch = client.json('https://api.github.com/repos/' + repo + '/branches/' + default)
        commit = branch.get('commit', {}).get('sha')
        tree_sha = branch.get('commit', {}).get('commit', {}).get('tree', {}).get('sha')
        require(bool(commit and tree_sha), 'mlperf_missing_commit')
        tree = client.json('https://api.github.com/repos/' + repo + '/git/trees/' + tree_sha)
        require(tree.get('truncated') is False, 'mlperf_truncated_root_tree')
        files = {r['path']: r for r in tree.get('tree', []) if r['type'] == 'blob'}
        path = 'summary_results.json' if 'summary_results.json' in files else 'summary.csv' if 'summary.csv' in files else None
        if path is None:
            return [item(repo + ':' + r['path'], {'artifact_kind': 'tree', 'repository': repo,
                'commit': commit, 'path': r['path'], 'tree_sha': r['sha']},
                'https://github.com/' + repo + '/tree/' + commit + '/' + r['path'], basis='derived')
                for r in tree['tree'] if r['type'] == 'tree' and r['path'] in {'closed', 'open'}], None
        original = 'https://raw.githubusercontent.com/' + repo + '/' + commit + '/' + path
        raw = client.get(original)
        import hashlib
        blob_sha = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        require(blob_sha == files[path]['sha'], 'mlperf_blob_commit_mismatch')
        rows = json.loads(raw) if path.endswith('.json') else list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
        require(isinstance(rows, list) and bool(rows) and all(isinstance(r, dict) for r in rows), 'mlperf_summary_shape')
        identity_fields = ('ID', 'PrivateID', 'Location', 'Model', 'MlperfModel', 'UsedModel', 'Scenario', 'Category', 'Division', 'Suite', 'System', 'SystemName', 'Units')
        measurements = [item(repo + ':' + digest({k: r.get(k) for k in identity_fields}),
            {'repository': repo, 'commit': commit, 'summary_file': path, 'result': r,
             'measurement_note': 'provider result, units, conditions, accuracy and power fields retained; no missing units or actual power inferred'},
            original, basis='derived') for r in rows]
        directories = [item(repo + ':' + r['path'], {'artifact_kind': 'tree', 'repository': repo,
            'commit': commit, 'path': r['path'], 'tree_sha': r['sha']},
            'https://github.com/' + repo + '/tree/' + commit + '/' + r['path'], basis='derived')
            for r in tree['tree'] if r['type'] == 'tree' and r['path'] in {'closed', 'open'}]
        return measurements + directories, None
    if kind == 'mlperf_index':
        repo, commit = p['repository'], p['commit']
        tree_url = 'https://api.github.com/repos/' + repo + '/git/trees/' + p['tree_sha']
        tree = client.json(tree_url, params={'recursive': 1})
        if tree.get('truncated'):
            tree = client.json(tree_url)
            require(tree.get('truncated') is False, 'mlperf_truncated_subtree')
            recursive = False
        else:
            require(tree.get('truncated') is False, 'mlperf_tree_response_shape')
            recursive = True
        result = []
        for entry in tree.get('tree', []):
            path = p['path'] + '/' + entry['path']
            if not recursive and entry['type'] == 'tree':
                data = {'artifact_kind': 'tree', 'tree_sha': entry['sha']}
            elif entry['type'] == 'blob' and (path.endswith('mlperf_log_summary.txt') or ('/systems/' in path and path.endswith('.json'))):
                data = {'artifact_kind': 'document', 'blob_sha': entry['sha']}
            else:
                continue
            result.append(item(repo + ':' + path, {**data, 'repository': repo, 'commit': commit, 'path': path},
                'https://github.com/' + repo + '/blob/' + commit + '/' + path, basis='derived'))
        return result, None
    if kind == 'mlperf_artifact':
        import hashlib
        raw = client.get(url)
        require(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == p['blob_sha'], 'mlperf_artifact_blob_mismatch')
        data = json.loads(raw) if p['path'].endswith('.json') else raw.decode('utf-8')
        return [item(p['repository'] + ':' + p['path'], {'artifact_kind': 'original benchmark configuration or log',
            'repository': p['repository'], 'commit': p['commit'], 'path': p['path'], 'content': data}, url, basis='derived')], None
    if kind == 'ror':
        data = client.json(url, params={'query.advanced': 'names.value:"' + p['query'].replace('"', '') + '"', 'page': int(cursor or 1)})
        rows = data.get('items')
        require(isinstance(rows, list) and isinstance(data.get('number_of_results'), int), 'ror_response_shape')
        require(data['number_of_results'] <= 10000, 'ror_split_scope_required')
        page = int(cursor or 1)
        return [item(r['id'], r, r['id']) for r in rows], str(page + 1) if page * 20 < data['number_of_results'] else None
    if kind == 'usaspending':
        position = json.loads(cursor) if cursor else {'recipient': 0, 'page': 1}
        names = p['filters']['recipient_search_text']
        index, page = position['recipient'], position['page']
        require(0 <= index < len(names) and page >= 1, 'usaspending_invalid_cursor')
        filters = {**p['filters'], 'recipient_search_text': [names[index]]}
        data = client.json(url, body={'filters': filters, 'fields': p['fields'],
            'page': page, 'limit': 100, 'sort': 'Award ID', 'order': 'asc', 'subawards': False})
        rows = data.get('results')
        require(isinstance(rows, list) and isinstance(data.get('page_metadata', {}).get('hasNext'), bool), 'usaspending_response_shape')
        following = ({'recipient': index, 'page': page + 1} if data['page_metadata']['hasNext']
                     else {'recipient': index + 1, 'page': 1} if index + 1 < len(names) else None)
        return [item(r.get('generated_internal_id') or digest(r), r, url,
                      (r.get('Start Date') or '')[:10] or None,
                      'provider' if r.get('generated_internal_id') else 'derived') for r in rows], \
            json.dumps(following, sort_keys=True) if following else None
    if kind == 'cms_catalog':
        data = json.loads(client.get(url))
        require(isinstance(data, list), 'cms_catalog_response_shape')
        rows = [r for r in data if any(str(y) in r.get('title', '') for y in range(2021, date.today().year + 1))]
        return [item(r['identifier'], r, 'https://openpaymentsdata.cms.gov/dataset/' + r['identifier']) for r in rows], None
    if kind == 'cms_coverage':
        query = dict(p.get('query', {}))
        if cursor:
            query['next_token'] = cursor
        data = client.json(url, params=query)
        require(data.get('meta', {}).get('status', {}).get('id') == 200, 'cms_coverage_provider_error')
        rows = data.get('data')
        require(isinstance(rows, list), 'cms_coverage_response_shape')
        result = [item(str(r.get('document_type', 'NCD')) + ':' + str(r['document_id']) + ':' + str(r['document_version']), r,
            'https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid=' + str(r['document_id']) + '&ncdver=' + str(r['document_version'])) for r in rows]
        return result, data['meta'].get('next_token') or None
    if kind == 'cms_document':
        data = client.json(url, params=p['query'])
        require(data.get('meta', {}).get('status', {}).get('id') == 200 and data.get('data') is not None, 'cms_document_provider_error')
        return [item('NCD:' + str(p['query']['ncdid']) + ':' + str(p['query']['ncdver']),
                     data, url)], None
    if kind == 'epmc_fulltext':
        raw = client.get(url)
        try:
            article = ET.fromstring(raw)
        except ET.ParseError:
            raise SourceIssue('epmc_invalid_article_xml')
        require(article.tag == 'article', 'epmc_non_article_response')
        licenses = [{'text': ' '.join(node.itertext()), 'attributes': node.attrib} for node in article.findall('.//license')]
        return [item(p['pmcid'], {'pmcid': p['pmcid'], 'license_statements': licenses,
                                 'article_xml': raw.decode('utf-8'), 'training_rights': 'held pending license review'}, url)], None
    if kind == 'cms':
        data = client.json(url, body={'conditions': p['conditions'], 'limit': 100, 'offset': offset})
        rows = data.get('results')
        require(isinstance(rows, list) and isinstance(data.get('count'), int), 'cms_response_shape')
        return [item(r.get('record_id') or digest(r), r, url, r.get('date_of_payment'),
                     'provider' if r.get('record_id') else 'derived') for r in rows], \
            str(offset + len(rows)) if offset + len(rows) < data['count'] else None
    if kind == 'csl':
        data = json.loads(client.get(url))
        rows = data.get('results') if isinstance(data, dict) else data
        require(isinstance(rows, list), 'csl_response_shape')
        return [item(r.get('id') or digest(r), r, url, basis='provider' if r.get('id') else 'derived') for r in rows], None
    if kind == 'caiso':
        raw = client.get(url, params=p['query'])
        require(raw[:2] == b'PK', 'caiso_non_zip_response')
        result = []
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            require(sum(i.file_size for i in archive.infolist()) < 32 * 1024 * 1024, 'caiso_expansion_cap')
            for name in archive.namelist():
                require(name.lower().endswith('.csv'), 'caiso_error_or_non_csv_member')
                for r in csv.DictReader(io.TextIOWrapper(archive.open(name), encoding='utf-8-sig')):
                    require('INTERVALSTARTTIME_GMT' in r and ('VALUE' in r or 'MW' in r), 'caiso_columns')
                    result.append(item(digest({k: v for k, v in r.items() if k not in {'VALUE', 'MW'}}),
                                       {'unit': 'USD/MWh for PRC_LMP price components', **r}, url,
                                       r['INTERVALSTARTTIME_GMT'][:10], 'derived'))
        require(bool(result), 'caiso_empty_interval')
        return result, None
    if kind == 'eia_index':
        raw = client.get(url)
        links = sorted({urljoin(url, x) for x in re.findall(r'href=[\"\x27]([^\"\x27]+\.xlsx)', raw.decode('utf-8'), re.I)})
        require(bool(links), 'eia_missing_archive_links')
        return [item(digest(link), {'archive_url': link}, link, basis='derived') for link in links], None
    if kind == 'eia_xlsx':
        import openpyxl
        raw = client.get(url)
        require(raw[:2] == b'PK', 'eia_html_instead_of_xlsx')
        book = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        result = []
        try:
            for sheet in book:
                headers = None
                for values in sheet.iter_rows(values_only=True):
                    cells = [str(v).strip() if v is not None else '' for v in values]
                    if 'Plant ID' in cells and 'Generator ID' in cells:
                        headers = cells
                        continue
                    if headers is None or not any('MWH' == c or 'BAT' == c for c in cells):
                        continue
                    r = {str(i) + ':' + h: c for i, (h, c) in enumerate(zip(headers, cells)) if h}
                    identity = {h: c for h, c in zip(headers, cells) if h in {'Plant ID', 'Generator ID'}}
                    result.append(item(digest({'sheet': sheet.title, 'identity': identity}),
                        {'sheet': sheet.title, 'values': r, 'report_period': p['period'],
                         'scope': 'battery generators; provider header units retained'}, url, None, 'derived'))
        finally:
            book.close()
        require(bool(result), 'eia_no_battery_rows_check_sheet_schema')
        return result, None
    if kind in {'pdf', 'html'}:
        raw = client.get(url)
        if kind == 'pdf':
            require(raw[:5] == b'%PDF-', 'non_pdf_response')
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw))
            result = [item(digest({'url': url, 'page': i}), {'page': i + 1, 'text': page.extract_text(),
                     'period': p.get('period'), 'numeric_extraction': 'not certified'}, url, p.get('event_date'), 'derived')
                      for i, page in enumerate(reader.pages)]
            require(bool(result), 'empty_pdf')
            return result, None
        require(b'<html' in raw.lower()[:4096] or b'<!doctype html' in raw.lower()[:4096], 'non_html_response')
        return [item(digest(url), {'document_kind': 'official source discovery page',
                     'numeric_extraction': 'not implemented'}, url, basis='derived')], None
    raise SourceIssue('adapter_not_implemented')


def normalized(row, run, evidence):
    return seal_record({'document_type': 'collected_record', 'schema_version': '1.0',
        'source': run.spec['source'], 'dataset': 'specialist_inputs', 'source_record_id': row['id'],
        'source_record_id_basis': 'documented_composite' if row['basis'] == 'derived' else row['basis'], 'source_url': row['url'],
        'universe_version': run.universe['universe_version'], 'company_ids': [], 'listing_ids': [],
        'person_ids': [], 'product_ids': [], 'entity_match_status': 'unresolved',
        'event_at': stamp(row['date']), 'available_at': None, 'source_updated_at': None,
        'ingested_at': now(), 'availability_basis': 'unknown', 'availability_evidence': [], 'run_id': run.run_id,
            'payload': {'data': row['data'], 'source_evidence': evidence, 'source_id': run.spec['scope']['source_id'],
                    'scope': run.spec['scope']['parameters'], 'coverage_note': run.spec['scope']['coverage_note'],
                    'point_in_time_eligible': False, 'entity_link_status': 'unreviewed'}})


def discover_children(store, manifest_key, parent):
    if parent['adapter'] not in {'epmc', 'cms_coverage', 'mlperf', 'mlperf_index', 'nih'}:
        return
    manifest = json.loads(store.get(manifest_key).body)
    for page in manifest['pages']:
        for batch in page['batches']:
            for line in store.get(batch['key']).body.splitlines():
                record = json.loads(line)
                data = record['payload']['data']
                if parent['adapter'] == 'nih':
                    name = data.get('organization', {}).get('org_name')
                    if not name:
                        continue
                    source, adapter, identity = 'ror_institutions', 'ror', name
                    parameters = {'url': 'https://api.ror.org/v2/organizations', 'query': name}
                elif parent['adapter'] == 'epmc':
                    pmcid = data.get('pmcid')
                    if data.get('isOpenAccess') != 'Y' or not pmcid or not re.fullmatch('PMC[0-9]+', pmcid):
                        continue
                    source, adapter, identity = 'europe_pmc_fulltext', 'epmc_fulltext', pmcid
                    parameters = {'pmcid': pmcid, 'url': 'https://www.ebi.ac.uk/europepmc/webservices/rest/' + pmcid + '/fullTextXML'}
                elif parent['adapter'] == 'cms_coverage':
                    if data.get('document_type') != 'NCD':
                        continue
                    source, adapter = 'cms_coverage_documents', 'cms_document'
                    identity = str(data['document_id']) + ':' + str(data['document_version'])
                    parameters = {'url': 'https://api.coverage.cms.gov/v1/data/ncd/',
                                  'query': {'ncdid': data['document_id'], 'ncdver': data['document_version']}}
                else:
                    if data.get('artifact_kind') not in {'tree', 'document'}:
                        continue
                    source = 'mlperf_results'
                    adapter = 'mlperf_index' if data['artifact_kind'] == 'tree' else 'mlperf_artifact'
                    checksum = data.get('tree_sha') or data['blob_sha']
                    identity = data['repository'] + ':' + data['path'] + ':' + checksum
                    parameters = {k: v for k, v in data.items() if k != 'artifact_kind'}
                    from urllib.parse import quote
                    parameters['url'] = 'https://raw.githubusercontent.com/' + data['repository'] + '/' + data['commit'] + '/' + quote(data['path'], safe='/')
                # First retrieval per original document/version. A separate
                # correction/revision ledger is required for historical vintages.
                key = 'operations/specialists/discovered-jobs/' + digest({'source': source, 'identity': identity}) + '.json'
                if store.get(key) is not None:
                    continue
                job = {**parent, 'source': source, 'adapter': adapter, 'parameters': parameters,
                       'coverage_note': 'original linked document; first retrieved now; license and dated company/product links remain unreviewed'}
                if parent['adapter'] == 'nih':
                    observed = datetime.now(timezone.utc).date()
                    job.update(source_id='S68', mode='daily', start=observed.isoformat(), end=(observed + timedelta(days=1)).isoformat(),
                               coverage_note='current identity candidate for grant institution; not a historical affiliation or independent validation claim')
                write_json(store, key, job)


def collect(job, store, settings, universe, taxonomy, page_budget):
    if job['adapter'] == 'edinet':
        from edinet_pipeline import collect as collect_edinet
        return collect_edinet(job, store, settings, universe, taxonomy, page_budget)
    spec = task_spec(job['source'], 'specialist_inputs', job['mode'], job['start'] + 'T00:00:00Z',
        job['end'] + 'T00:00:00Z', {k: job[k] for k in ('adapter', 'parameters', 'source_id', 'coverage_note')},
        VERSION + ('-usaspending-single-recipient-1' if job['adapter'] == 'usaspending' else ''), universe, taxonomy)
    try:
        run = CollectionRun.start(store, spec, universe, taxonomy, settings, resume=True)
    except AlreadyComplete as exc:
        return {'status': 'complete', 'manifest': str(exc), 'already_complete': True}
    client = SpecialistClient(store, job['source'])
    try:
        pages = 0
        while not run.exhausted and pages < page_budget:
            # NIH >=1 sec; others use a conservative one-second floor too.
            time.sleep(1)
            client.evidence.clear()
            rows, cursor = fetch_page(client, job, run.cursor)
            run.commit_page((normalized(r, run, list(client.evidence)) for r in rows),
                            next_cursor=cursor, exhausted=cursor is None)
            pages += 1
        status = 'complete' if run.exhausted else 'partial'
        manifest = run.finish(status, None if run.exhausted else 'page_budget', expected_records=run.state['record_count'] if run.exhausted else None)
        return {'status': status, 'manifest': manifest, 'records': run.state['record_count'], 'pages': pages}
    except (Exception, KeyboardInterrupt) as exc:
        status = 'partial' if isinstance(exc, KeyboardInterrupt) else 'failed'
        code = exc.code if isinstance(exc, SourceIssue) else 'interrupted' if isinstance(exc, KeyboardInterrupt) else 'collection_error'
        return {'status': status, 'manifest': run.finish(status, code),
                'reason': str(exc)[:200], 'error_type': type(exc).__name__}


def main():
    import fcntl
    import os
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['daily', 'historical'], required=True)
    parser.add_argument('--max-jobs', type=int, default=24)
    parser.add_argument('--pages', type=int, default=3)
    parser.add_argument('--source', action='append')
    parser.add_argument('--publish', type=int, default=4)
    parser.add_argument('--lane', choices=['default', 'authenticated'], default='default')
    args = parser.parse_args()
    if args.lane == 'authenticated' and args.publish:
        parser.error('Authenticated capture lane queues publication; use --publish 0')
    # Also protects manual invocations. A persistent runner serializes with all
    # existing market/patent/publication jobs, not only with this service.
    lock = None
    if args.lane == 'authenticated' or os.environ.get('OPTIMA_HEAVY_LOCK_HELD') != '1':
        lock = (ROOT / ('.authenticated-job.lock' if args.lane == 'authenticated' else '.heavy-job.lock')).open('a+')
        fcntl.flock(lock, fcntl.LOCK_EX)
    from specialist_plan import jobs
    settings = StorageSettings.load(ROOT / 'config/collection-storage.s3.json')
    store = settings.store()
    universe = load_json(ROOT / 'config/company-universe.v0.5.json')
    taxonomy = load_json(ROOT / 'config/sectors.v1.json')
    universe_hash = digest(universe)
    plan = load_json(PLAN)
    today = datetime.now(timezone.utc).date()
    state_key = 'operations/specialists/scheduler/' + (args.lane + '-' if args.lane != 'default' else '') + args.mode + '.json'
    stored = store.get(state_key)
    state = json.loads(stored.body) if stored else {'jobs': {}}
    state.setdefault('source_retries', {})
    if args.mode == 'daily':
        cutoff = (today - timedelta(days=14)).isoformat()
        # Immutable manifests/execution receipts retain the audit history;
        # the mutable daily queue stays bounded on this small host.
        state['jobs'] = {k: v for k, v in state['jobs'].items()
                         if v.get('status') != 'complete' or v.get('start', '') >= cutoff}
    active_plan = {**plan, 'sources': [s for s in plan['sources'] if s.get('execution_lane', 'default') == args.lane]}
    all_jobs = list(jobs(active_plan, universe, args.mode, today))
    from window_publication import list_keys
    for key in ([] if args.lane == 'authenticated' else list_keys(store, settings, 'operations/specialists/discovered-jobs/')):
        discovered = json.loads(store.get(key).body)
        if discovered['mode'] == args.mode:
            all_jobs.append(discovered)
    identities = {digest({'job': j, 'universe_hash': universe_hash, 'version': VERSION}) for j in all_jobs}
    for identity, prior in state['jobs'].items():
        if identity not in identities and prior.get('job') and prior.get('status') != 'complete':
            all_jobs.append(prior['job'])
    if args.source:
        all_jobs = [j for j in all_jobs if j['source'] in args.source]
    candidates = []
    for job in all_jobs:
        identity = digest({'job': job, 'universe_hash': universe_hash, 'version': VERSION})
        prior = state['jobs'].get(identity, {})
        if state['source_retries'].get(job['source'], '') > now():
            continue
        if prior.get('status') == 'complete' or prior.get('retry_after', '') > now():
            continue
        candidates.append((prior.get('last_attempt', ''), identity, job))
    # Stable fairness: one attempt per source before a second. Old failures do
    # not starve unattempted providers, and committed pages always resume.
    candidates.sort(key=lambda r: (r[0], r[2]['start'], r[2]['source'], r[1]))
    ordered, used = [], set()
    for row in candidates:
        if row[2]['source'] not in used:
            ordered.append(row); used.add(row[2]['source'])
    selected = {r[1] for r in ordered}
    ordered += [r for r in candidates if r[1] not in selected]
    outcomes = []
    for _, identity, job in ordered[:args.max_jobs]:
        if state['source_retries'].get(job['source'], '') > now():
            continue
        result = collect(job, store, settings, universe, taxonomy, args.pages)
        row = {**result, 'job_id': identity, 'source': job['source'], 'source_id': job['source_id'],
               'start': job['start'], 'end_exclusive': job['end'], 'last_attempt': now(), 'job': job}
        if result['status'] == 'failed':
            row['retry_after'] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat().replace('+00:00', 'Z')
            reason = result.get('reason', '')
            if reason.startswith(('source_retries_', 'retry_deferred', 'source_http_5')) or reason in {'source_http_401', 'source_http_403', 'source_http_429'}:
                state['source_retries'][job['source']] = row['retry_after']
            if reason in {'sam_daily_request_budget', 'sam_hourly_request_budget'}:
                current = datetime.now(timezone.utc)
                retry = ((current + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
                         if reason == 'sam_daily_request_budget' else current + timedelta(hours=1))
                row['retry_after'] = retry.isoformat().replace('+00:00', 'Z')
                state['source_retries'][job['source']] = row['retry_after']
            if result.get('reason') == 'github_public_hour_budget':
                row['retry_after'] = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat().replace('+00:00', 'Z')
                state['source_retries'][job['source']] = row['retry_after']
        state['jobs'][identity] = row
        state['updated_at'] = now()
        token = write_json(store, state_key, state, stored.token if stored else None)
        from collection_storage import Stored
        stored = Stored(b'', token)
        if result['status'] in {'complete', 'partial'} and result.get('records', 0):
            discover_children(store, result['manifest'], job)
        if result['status'] == 'complete':
            key = 'operations/specialists/publication-queue/' + identity + '.json'
            if store.get(key) is None:
                write_json(store, key, {'window_id': identity, 'manifests': [result['manifest']], 'queued_at': now()})
        outcomes.append(row)
        print(json.dumps(row), flush=True)
    if args.publish:
        from specialist_publication import publish
        published = publish(store, settings, plan, args.publish)
        print(json.dumps({'publication': published}), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'at': now(), 'mode': args.mode, 'planned_jobs': len(all_jobs), 'outcomes': outcomes,
              'complete_jobs': sum(r.get('status') == 'complete' for r in state['jobs'].values()),
              'failed_jobs': sum(r.get('status') == 'failed' for r in state['jobs'].values()),
              'remaining_jobs': sum(state['jobs'].get(digest({'job': j, 'universe_hash': universe_hash, 'version': VERSION}), {}).get('status') != 'complete' for j in all_jobs)}
    (OUT / ((args.lane + '-' if args.lane != 'default' else '') + args.mode + '-latest.json')).write_text(json.dumps(report, indent=2) + '\n')
    write_json(store, 'operations/specialists/executions/' + digest(report) + '.json', report)


if __name__ == '__main__':
    main()
