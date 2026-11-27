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

from collection_storage import AlreadyComplete, CollectionRun, Conflict, StorageSettings, now, task_spec, write_json
from research_contract import ROOT, digest, load_json, seal_record
from regulatory_collection import EvidenceClient, SourceIssue, require, stamp

VERSION = 'specialist-inputs-1.2'
PLAN = ROOT / 'config/specialist-inputs.json'
OUT = ROOT / 'reports/specialist-expansion-2026-10-09'


class SpecialistClient(EvidenceClient):
    def get(self, url, *args, **kwargs):
        if urlsplit(url).hostname == 'oasis.caiso.com':
            from caiso_transport import throttle
            throttle()
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
    from additional_source_apis import KINDS as ADDITIONAL_KINDS, fetch as additional_fetch
    if kind in ADDITIONAL_KINDS:return additional_fetch(client,job,cursor,item)
    from specialist_authenticated import KINDS as AUTH_KINDS, fetch as auth_fetch
    if kind in AUTH_KINDS:
        return auth_fetch(client, job, cursor, item)
    from specialist_public_apis import KINDS, fetch
    if kind in KINDS:
        return fetch(client, job, cursor, item)
    offset = int(cursor or 0) if kind in {'bls', 'cms'} else 0
    url = p['url']
    if kind == 'nih':
        from nih_pagination import page
        return page(client, job, cursor, item)
    if kind == 'ted':
        position = json.loads(cursor) if cursor else {'token': None, 'seen': 0}
        body = {'query': p['query'], 'fields': list(dict.fromkeys(p['fields'] + ['ojs-number'])), 'limit': 100, 'scope': 'ALL',
                'paginationMode': 'ITERATION', 'checkQuerySyntax': False, 'onlyLatestVersions': False}
        if position['token']:
            body['iterationNextToken'] = position['token']
        data = client.json(url, body=body)
        require(data.get('timedOut') is not True, 'ted_query_timeout')
        rows = data.get('notices')
        require(isinstance(rows, list) and isinstance(data.get('totalNoticeCount'), int), 'ted_response_shape')
        result = []
        xml_failures = 0
        for r in rows:
            identity = r.get('publication-number') or r.get('notice-id')
            require(identity is not None, 'ted_missing_notice_id')
            if isinstance(identity, list):
                identity = identity[0]
            from ted_enrichment import enrich_notice
            try:
                require(xml_failures < 3, 'ted_xml_provider_deferred')
                r, _ = enrich_notice(r, str(identity), client, prefer_package=job.get('mode') == 'daily')
                xml_failures = 0
            except (SourceIssue, ValueError, ET.ParseError) as exc:
                xml_failures += 1
                if job.get('mode') == 'daily':
                    raise SourceIssue('ted_daily_xml_pending', True) from exc
                r = {**r, 'enrichment': {'version': 'ted-xml-v1', 'status': 'retrieval_gap',
                     'error': exc.code if isinstance(exc, SourceIssue) else type(exc).__name__,
                     'specialist_ready': False}}
            from ted_enrichment import bounded_notice_items
            result.extend(bounded_notice_items(str(identity), r,
                'https://ted.europa.eu/en/notice/-/detail/' + str(identity),
                (r.get('publication-date') or '')[:10] or None, item))
        token = data.get('iterationNextToken')
        require(not token or token != position['token'], 'ted_cursor_cycle')
        seen = position['seen'] + len(rows)
        require(seen <= data['totalNoticeCount'], 'ted_count_mismatch')
        require(seen == data['totalNoticeCount'] or bool(rows and token), 'ted_missing_iteration_page')
        return result, json.dumps({'token': token, 'seen': seen}) if seen < data['totalNoticeCount'] else None
    if kind == 'bls':
        from bls_enrichment import daily_page
        return daily_page(client, p, item)
    if kind == 'comtrade':
        data = client.json(url, params=p['query'])
        require(data.get('error') in (None, '', False), 'comtrade_provider_error')
        rows = data.get('data')
        require(isinstance(rows, list), 'comtrade_response_shape')
        require(len(rows) < int(p['query']['maxRecords']), 'comtrade_preview_truncation')
        identity_fields = ('typeCode', 'freqCode', 'period', 'reporterCode', 'cmdCode', 'flowCode', 'partnerCode', 'partner2Code', 'customsCode', 'motCode', 'classificationCode')
        return [item(digest({k: r.get(k) for k in identity_fields}), {'query': p['query'], 'trade': r, 'units': 'provider fields retained'}, url,
                     None, 'derived') for r in rows], None
    if kind == 'fr_enrichment':
        from federal_register_enrichment import NoticeClient, enrich
        notice_client = NoticeClient(client.store)
        try:
            result = enrich(notice_client, p['listing'])
            if result['official_pdf_status'] != 'downloaded' and not p.get('allow_partial'):
                raise SourceIssue('fr_official_pdf_retry_required')
        except (SourceIssue, ValueError) as exc:
            if not p.get('allow_partial'):
                raise
            from federal_register_enrichment import VERSION as FR_VERSION
            result = {'version': FR_VERSION, 'document_number': p['listing']['document_number'],
                'publication_date': p['listing'].get('publication_date'), 'retrieval_status': 'failed',
                'artifact_gaps': [{'artifact': 'full_notice', 'reason': str(exc)[:200]}],
                'review_status': 'pending', 'product_applicability': 'unreviewed_no_valid_full_body'}
        client.evidence.extend(notice_client.evidence)
        return [item(p['listing']['document_number'], {'enrichment': result}, p['listing']['html_url'], result.get('publication_date'))], None
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
        from mlperf_enrichment import summary_page
        if cursor:
            return summary_page(client, json.loads(cursor), item)
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
        return summary_page(client, {'repository': repo, 'commit': commit,
            'summary_file': path, 'summary_blob_sha': files[path]['sha'], 'offset': 0}, item)
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
        fallback = False
        try:
            raw = client.get(url)
        except SourceIssue as exc:
            if exc.code not in {'source_retries_exhausted', 'source_http_500', 'source_http_502', 'source_http_503', 'source_http_504'}:
                raise
            require(bool(re.fullmatch(r'PMC[0-9]+', p['pmcid'])), 'epmc_invalid_pmcid')
            url = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
            params = {'db': 'pmc', 'id': p['pmcid'][3:], 'retmode': 'xml'}
            raw = client.get(url, params=params)
            url += '?' + urlencode(params)
            fallback = True
        try:
            article = ET.fromstring(raw,parser=ET.XMLParser(target=ET.TreeBuilder(insert_pis=True)))
        except ET.ParseError:
            raise SourceIssue('epmc_invalid_article_xml')
        if fallback:
            articles = article.findall('article') if article.tag == 'pmc-articleset' else []
            require(len(articles) == 1, 'epmc_fallback_article_count')
            article = articles[0]
            ids = {n.text for n in article.findall('./front/article-meta/article-id')
                   if n.get('pub-id-type') in {'pmc', 'pmcid'}}
            require(bool(ids.intersection({p['pmcid'], p['pmcid'][3:]})), 'epmc_fallback_identity_mismatch')
            raw = ET.tostring(article, encoding='utf-8')
        require(article.tag == 'article', 'epmc_non_article_response')
        from raw_parsers.epmc_fulltext import parse_original,enrichment,ProviderError
        try:parse_original(raw,p['pmcid'])
        except ProviderError as error:raise SourceIssue(str(error))from None
        licenses = [{'text': ' '.join(node.itertext()), 'attributes': node.attrib} for node in article.findall('.//license')]
        return [item(p['pmcid'], {'pmcid': p['pmcid'], 'license_statements': licenses,
                                 'retrieval_provider': 'NCBI PMC' if fallback else 'Europe PMC',
                                 'article_xml': raw.decode('utf-8'), 'enrichment':enrichment(raw.decode('utf-8'),p['pmcid']), 'training_rights': 'held pending license review'}, url)], None
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
        # OFAC UIDs recur across different lists (e.g. SSI and NS-MBS).
        # List identity is essential; bare IDs would merge distinct restrictions.
        from trade_screening_enrichment import screening_identity
        return [item(screening_identity(r), r, url,
                     basis='derived') for r in rows], None
    if kind == 'caiso':
        from caiso_enrichment import collect_rows
        return collect_rows(client,job,item)
    if kind == 'eia_index':
        from eia_enrichment import index_page
        return index_page(client, job, cursor, item)
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
    if kind == 'nist_robotics':
        from nist_robotics import parse_document
        raw = client.get(url)
        return [item(digest(url), parse_document(raw, url), url, basis='derived')], None
    if kind == 'doe_storage':
        from doe_storage_enrichment import parse_document
        raw = client.get(url)
        return [item(digest(url), parse_document(raw, url), url, basis='derived')], None
    if kind == 'pdf' and job.get('source') == 'usgs_minerals':
        from usgs_minerals_enrichment import capture
        from usgs_archive_urls import resolve
        url = resolve(url)
        raw = client.get(url)
        report = capture(raw, url, client)
        data = {'period': p.get('period'), 'document_type': 'full_mineral_report', 'enrichment': report}
        return [item('report:' + report['report_id'], data, url, basis='derived')], None
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
    event_stamp=stamp(row['date'])
    if row.get('date_precision') in ('year','month'):event_stamp=None
    if event_stamp and row.get('date_precision'):event_stamp['precision']=row['date_precision']
    if run.spec['source']=='caiso_prices' and row['data'].get('enrichment',{}).get('timing'):
        event_stamp={'value':row['data']['enrichment']['timing']['start_utc'],'precision':'second','source_timezone':'UTC'}
    return seal_record({'document_type': 'collected_record', 'schema_version': '1.0',
        'source': run.spec['source'], 'dataset': 'specialist_inputs', 'source_record_id': row['id'],
        'source_record_id_basis': 'documented_composite' if row['basis'] == 'derived' else row['basis'], 'source_url': row['url'],
        'universe_version': run.universe['universe_version'], 'company_ids': [], 'listing_ids': [],
        'person_ids': [], 'product_ids': [], 'entity_match_status': 'unresolved',
        'event_at': event_stamp, 'available_at': None, 'source_updated_at': None,
        'ingested_at': now(), 'availability_basis': 'unknown', 'availability_evidence': [], 'run_id': run.run_id,
            'payload': {'data': row['data'], **({'source_date_status':row['date_status']} if row.get('date_status') else {}), **({'source_date_precision':row['date_precision']} if row.get('date_precision') else {}), 'source_evidence': evidence, 'source_id': run.spec['scope']['source_id'],
                    **({'record_type':'scientific_publication','date_basis':'article_publication_not_clinical_milestone'} if run.spec['source']=='pubmed_abstracts' else {}),
                    'scope': run.spec['scope']['parameters'], 'coverage_note': ('Linked XML parsed; procurement event candidates require specialist review' if run.spec['source']=='ted_notices' and row['data'].get('enrichment', {}).get('specialist_ready') else run.spec['scope']['coverage_note']),
                    'point_in_time_eligible': False, 'entity_link_status': 'unreviewed'}})


def discover_children(store, manifest_key, parent):
    if parent['adapter'] not in {'epmc', 'cms_coverage', 'mlperf', 'mlperf_index', 'nih', 'federal_register'}:
        return
    manifest = json.loads(store.get(manifest_key).body)
    seen_keys = set()
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
                    parameters = {'url': 'https://api.ror.org/v2/organizations', 'query': name,
                                  'originating_application_id': data['appl_id'],
                                  'parent_observation_id': record['observation_id']}
                    # The post-capture grant worker retains every parent link, including
                    # applications sharing this deduplicated institution lookup.
                elif parent['adapter'] == 'epmc':
                    pmcid = data.get('pmcid')
                    if data.get('isOpenAccess') != 'Y' or not pmcid or not re.fullmatch('PMC[0-9]+', pmcid):
                        continue
                    source, adapter, identity = 'europe_pmc_fulltext', 'epmc_fulltext', pmcid
                    parameters = {'pmcid': pmcid, 'url': 'https://www.ebi.ac.uk/europepmc/webservices/rest/' + pmcid + '/fullTextXML'}
                elif parent['adapter'] == 'federal_register':
                    from federal_register_enrichment import VERSION as FR_VERSION
                    source, adapter = 'federal_register_documents', 'fr_enrichment'
                    identity = data['document_number'] + ':' + parent['start'] + ':' + digest(data) + ':' + FR_VERSION
                    parameters = {'url': 'https://www.federalregister.gov/api/v1/documents/' + data['document_number'] + '.json', 'listing': data, 'parent_observation_id': record['observation_id'], 'enrichment_version': FR_VERSION}
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
                key = ('operations/federal-register/discovered-jobs/' if parent['adapter'] == 'federal_register' else __import__('os').environ.get('CONSTELLATION_SPECIALIST_DISCOVERY_PREFIX','operations/specialists/discovered-jobs/')) + digest({'source': source, 'identity': identity}) + '.json'
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                if store.get(key) is not None:
                    continue
                job = {**parent, 'source': source, 'adapter': adapter, 'parameters': parameters,
                       'coverage_note': 'original linked document; first retrieved now; license and dated company/product links remain unreviewed'}
                if parent['adapter'] == 'federal_register':
                    job['execution_lane'] = 'fr_enrichment'
                if parent['adapter'] == 'nih':
                    observed = datetime.now(timezone.utc).date()
                    job.update(source_id='S68', mode='daily', start=observed.isoformat(), end=(observed + timedelta(days=1)).isoformat(),
                               coverage_note='current identity candidate for grant institution; not a historical affiliation or independent validation claim')
                write_json(store, key, job)


def nih_refresh_required(store, spec, job):
    if job['adapter'] not in {'nih','sam_gov','ted'} and not job['adapter'].startswith('additional_') and not (job['adapter']=='drugsfda' and job['parameters'].get('inventory_scope')):return False
    head = store.get('checkpoints/task_' + digest(spec) + '/head.json')
    state = json.loads(head.body) if head else {}
    terminal = store.get(state['terminal_manifest']) if state.get('terminal_manifest') else None
    result = json.loads(terminal.body) if terminal else {}
    if job['adapter'] == 'ted':
        # Retain the failed iteration as evidence. Its old token/count cannot
        # be repaired by requesting the same page again; restart a generation.
        try:
            position = json.loads(state.get('cursor') or '{}')
        except (ValueError, TypeError):
            return False
        return (result.get('status') == 'failed'
                and result.get('reason_code') in {'ted_count_mismatch', 'ted_missing_iteration_page'}
                and isinstance(position, dict) and isinstance(position.get('seen'), int)
                and position['seen'] > 0 and bool(position.get('token')))
    if job['adapter'] == 'sam_gov':
        # SAM removes archived notices from its mutable active inventory. Keep
        # the old run as evidence and restart from page zero in a new generation.
        # Existing quota admission and scheduler retry delays still apply.
        return result.get('status') in {'failed', 'partial'} and (
            result.get('reason_code') == 'sam_source_changed_refresh_required' or
            (result.get('reason_code') == 'sam_count_mismatch' and
             str(state.get('cursor', '')).isdigit() and int(state['cursor']) > 0))
    reasons={'nih_split_count_changed', 'nih_duplicate_page_refresh_required', 'nih_split_final_count_mismatch'} if job['adapter']=='nih' else {'source_changed_refresh_required'}
    if job['adapter']=='additional_biorxiv':reasons|={'additional_duplicate_provider_ids','biorxiv_cursor_identity_upgrade_required'}
    return result.get('status') == 'failed' and result.get('reason_code') in reasons


def collect(job, store, settings, universe, taxonomy, page_budget):
    from source_pauses import is_paused
    if is_paused(job["source"]):
        return {"status": "paused_by_user", "source": job["source"]}
    from reviewed_source_gaps import reviewed_gap
    decision = reviewed_gap(job)
    if decision:
        key = 'operations/specialists/reviewed-gaps/' + digest({'job': job, 'decision': decision}) + '.json'
        evidence = {'status': 'accepted_unavailable', 'job': job, 'decision': decision, 'recorded_at': now()}
        if store.get(key) is None:
            write_json(store, key, evidence)
        return {'status': 'accepted_unavailable', 'reason': decision['reason'],
                'gap_decision': decision, 'gap_receipt': key, 'records': 0}
    if job['adapter'] == 'edinet':
        from edinet_pipeline import collect as collect_edinet
        return collect_edinet(job, store, settings, universe, taxonomy, page_budget)
    spec = task_spec(job['source'], 'specialist_inputs', job['mode'], job['start'] + 'T00:00:00Z',
        job['end'] + 'T00:00:00Z', {k: job[k] for k in ('adapter', 'parameters', 'source_id', 'coverage_note')},
        VERSION + ('-usaspending-single-recipient-1' if job['adapter'] == 'usaspending' else '')
        + ('-pubmed-evidence-context-v1' if job['adapter'] == 'pubmed' else '')
        + ('-epmc-fulltext-jats-context-v1' if job['adapter']=='epmc_fulltext' else '')
        + ('-mlperf-evidence-v1' if job['adapter'] == 'mlperf' else '')
        + ('-usgs-minerals-evidence-v2' if job['source'] == 'usgs_minerals' else '')
        + ('-bls-labor-context-v2' if job['adapter'] == 'bls' else '')
        + ('-eia-index-retail-v1' if job['source'] in {'eia_generator_index','eia_retail_prices'} else '')
        + ('-csl-list-scoped-identity-v1' if job['adapter'] == 'csl' else '')
        + ('-doe-storage-evidence-v2' if job['adapter'] == 'doe_storage' else '')
        + ('-original-filing-documents-v1' if job['adapter']in ('additional_dart','additional_cninfo') else '')
        + ('-nhsbsa-snomed-catalogue-v1' if job['adapter']=='additional_nhsbsa' else '')
        + ('-caiso-market-evidence-v1' if job['adapter'] == 'caiso' else ''), universe, taxonomy)
    try:
        refresh = nih_refresh_required(store, spec, job)
        run = CollectionRun.start(store, spec, universe, taxonomy, settings, resume=not refresh, refresh=refresh)
    except AlreadyComplete as exc:
        return {'status': 'complete', 'manifest': str(exc), 'already_complete': True}
    client = SpecialistClient(store, job['source'])
    if job['adapter']=='additional_dart' and job['mode']=='historical':
        client.dart_batch_size=8
    try:
        pages = 0
        while not run.exhausted and pages < page_budget:
            # NIH >=1 sec; others use a conservative one-second floor too.
            time.sleep(1)
            client.evidence.clear()
            rows, cursor = fetch_page(client, job, run.cursor)
            if getattr(client,'empty_scope_evidence',None):
                write_json(store,run.state['manifest_prefix']+f"/responses/{len(run.state['pages']):08d}-empty-scope.json",client.empty_scope_evidence)
            expected=getattr(client,'expected_records',None)
            if job['adapter'].startswith('additional_') and cursor is None and expected is not None:
                require(run.state['record_count']+len(rows)==expected,'additional_total_count_mismatch')
            run.commit_page((normalized(r, run, r.get('filing_evidence',list(client.evidence))) for r in rows),
                            next_cursor=cursor, exhausted=cursor is None)
            if job['adapter']=='additional_epo':
                from epo_ops import after_commit
                after_commit(client,job)
            pages += 1
            if job['adapter']=='additional_copernicus' and cursor is not None:break
        status = 'complete' if run.exhausted else 'partial'
        manifest = run.finish(status, None if run.exhausted else 'page_budget', expected_records=run.state['record_count'] if run.exhausted else None)
        return {'status': status, 'manifest': manifest, 'records': run.state['record_count'], 'pages': pages, 'reason': None if run.exhausted else 'page_budget'}
    except (Exception, KeyboardInterrupt) as exc:
        status = 'partial' if isinstance(exc, KeyboardInterrupt) or (job['adapter'] == 'ted' and isinstance(exc, SourceIssue) and exc.code == 'ted_daily_xml_pending') or (job['adapter']=='additional_copernicus' and isinstance(exc,SourceIssue) and exc.code=='copernicus_queue_wait') or (job['adapter']=='additional_nhsbsa' and isinstance(exc,SourceIssue) and exc.code=='nhsbsa_release_not_yet_published') or (job['adapter']=='additional_census' and isinstance(exc,SourceIssue) and exc.code=='census_period_not_yet_published') else 'failed'
        code = exc.code if isinstance(exc, SourceIssue) else 'interrupted' if isinstance(exc, KeyboardInterrupt) else 'collection_error'
        if job['adapter']=='additional_biorxiv' and code=='decodo_web_data_daily_budget':status='partial'
        if isinstance(exc,SourceIssue) and code in {'pdf_proxy_daily_budget','pdf_proxy_url_cooldown','pdf_proxy_client_budget'}:status='partial'
        if isinstance(exc, SourceIssue) and exc.diagnostics:
            write_json(store, run.state['manifest_prefix'] + '/failure.json',
                       {'reason': code, 'diagnostics': exc.diagnostics, 'evidence': client.evidence})
        return {'status': status, 'manifest': run.finish(status, code),
                'reason': str(exc)[:200], 'error_type': type(exc).__name__, 'records':run.state['record_count']}


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
    parser.add_argument('--discovery-limit',type=int,default=100)
    args = parser.parse_args()
    if not 1<=args.discovery_limit<=1000:parser.error('Discovery limit must be between 1 and 1000')
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
    plan = load_json(Path(os.environ.get('CONSTELLATION_SPECIALIST_PLAN',str(PLAN))))
    today = datetime.now(timezone.utc).date()
    worker_scope=os.environ.get('CONSTELLATION_SPECIALIST_SCHEDULER_PREFIX')
    if worker_scope:
        scoped_mode=os.environ.get('CONSTELLATION_SPECIALIST_MODE') or ('historical' if os.environ.get('CONSTELLATION_ROLE')=='worker' else 'daily')
        if args.mode!=scoped_mode or not args.source or len(args.source)!=1 or args.publish:
            parser.error('Isolated specialist routes require one source, the host mode, and no inline publication')
    legacy_state_key='operations/specialists/scheduler/' + (args.lane + '-' if args.lane != 'default' else '') + args.mode + '.json'
    state_key=(worker_scope.rstrip('/')+'/'+args.mode+'.json') if worker_scope else legacy_state_key
    stored = store.get(state_key)
    original=store.get(legacy_state_key) if worker_scope and not stored else None
    state = json.loads(stored.body) if stored else json.loads(original.body) if original else {'jobs': {}}
    if worker_scope:
        state['jobs']={k:v for k,v in state.get('jobs',{}).items() if (v.get('job') or {}).get('source',v.get('source')) in args.source and (v.get('job') or {}).get('mode')==args.mode}
    state.setdefault('source_retries', {})
    if args.mode == 'daily':
        cutoff = (today - timedelta(days=14)).isoformat()
        # Immutable manifests/execution receipts retain the audit history;
        # the mutable daily queue stays bounded on this small host.
        state['jobs'] = {k: v for k, v in state['jobs'].items()
                         if v.get('status') != 'complete' or v.get('start', '') >= cutoff}
    active_plan = {**plan, 'sources': [s for s in plan['sources'] if s.get('execution_lane', 'default') == args.lane and (not args.source or s['source'] in args.source)]}
    published_eia_periods = None
    eia_index_error = None
    if args.lane == 'default' and (not args.source or 'eia_battery_generators' in args.source):
        from eia_enrichment import refresh_generator_archives
        try:
            published_eia_periods = refresh_generator_archives(active_plan, store)
        except SourceIssue as exc:
            eia_index_error = exc.code
    all_jobs = list(jobs(active_plan, universe, args.mode, today))
    from window_publication import list_keys
    # Only these child sources are produced by discover_children above.
    # An explicit unrelated source replay must not download the entire child queue.
    child_sources = {'ror_institutions', 'europe_pmc_fulltext', 'cms_coverage_documents', 'mlperf_results'}
    inspect_children = args.lane != 'authenticated' and (not args.source or bool(child_sources.intersection(args.source)))
    if inspect_children:
        from specialist_discovery_queue import discover as discover_bounded
        prefixes=[os.environ.get('CONSTELLATION_SPECIALIST_DISCOVERY_PREFIX','operations/specialists/discovered-jobs/')]
        if worker_scope:prefixes.append('operations/specialists/discovered-jobs/')
        all_jobs.extend(discover_bounded(store,settings,state,prefixes,args.mode,args.lane,universe_hash,VERSION,args.discovery_limit))
    identities = {digest({'job': j, 'universe_hash': universe_hash, 'version': VERSION}) for j in all_jobs}
    for identity, prior in state['jobs'].items():
        if identity not in identities and prior.get('job') and prior.get('status') != 'complete':
            all_jobs.append(prior['job'])
    if args.source:
        all_jobs = [j for j in all_jobs if j['source'] in args.source and j['mode']==args.mode]
    from source_pauses import is_paused
    all_jobs = [j for j in all_jobs if not is_paused(j["source"])]
    candidates = []
    for job in all_jobs:
        identity = digest({'job': job, 'universe_hash': universe_hash, 'version': VERSION})
        prior = state['jobs'].get(identity, {})
        if eia_index_error and job['source'] == 'eia_battery_generators':
            state['jobs'][identity] = {**prior, 'job_id': identity, 'job': job,
                'source': job['source'], 'source_id': job['source_id'], 'start': job['start'],
                'end_exclusive': job['end'], 'status': 'failed',
                'reason': 'eia_published_index_unavailable:' + eia_index_error, 'checked_at': now()}
            continue
        if (published_eia_periods is not None and job['source'] == 'eia_battery_generators'
                and job['parameters']['period'] not in published_eia_periods):
            state['jobs'][identity] = {**prior, 'job_id': identity, 'job': job,
                'source': job['source'], 'source_id': job['source_id'], 'start': job['start'],
                'end_exclusive': job['end'], 'status': 'deferred',
                'reason': 'eia_report_not_published', 'checked_at': now()}
            continue
        if state['source_retries'].get(job['source'], '') > now():
            continue
        if prior.get('status') in {'complete', 'accepted_unavailable'} or prior.get('retry_after', '') > now():
            continue
        candidates.append((prior.get('last_attempt', ''), identity, job))
    # Stable fairness: one attempt per source before a second. Old failures do
    # not starve unattempted providers, and committed pages always resume.
    candidates.sort(key=lambda r: (r[0], r[2]['start'], r[2]['source'], r[1]))
    if args.mode == 'historical' and args.source == ['south_korea_fss_opendart'] and args.max_jobs>0:
        # The page budget is spent on one filing plus its original at a time,
        # so round-robin over months left almost every window partially open.
        # Preserve the former total budget of 48 units, but concentrate it.
        candidates.sort(key=lambda r: (r[2]['start'], r[2]['end'], r[0], r[1]))
        total_pages = args.max_jobs * args.pages
        args.max_jobs = min(args.max_jobs, 3)
        args.pages = max(1,min(2, total_pages // (8*args.max_jobs)))
        if any(s.get('original_document_bridge_end_exclusive') for s in active_plan['sources']):
            boundary=active_plan['backfill_end_exclusive']
            older=[r for r in candidates if r[2]['start']<boundary]
            bridge=[r for r in candidates if r[2]['start']>=boundary]
            if args.max_jobs==1 and os.environ.get('CONSTELLATION_OPENDART_PREFER_BRIDGE')=='1':
                candidates=bridge+older
            elif args.max_jobs==3 and older and bridge:
                newest=bridge[0]
                candidates=older[:2]+[newest]+older[2:]+bridge[1:]
    if (os.environ.get('CONSTELLATION_SPECIALIST_PREFER_INFLIGHT') == '1'
            and args.source == ['copernicus_era5_era5_land']):
        # Poll an already submitted CDS job before walking more dates that
        # cannot be admitted while the provider queue is full.
        since = (datetime.now(timezone.utc) - timedelta(hours=8)).isoformat().replace('+00:00', 'Z')
        pending = [entry for entry in candidates if entry[0] >= since
                   and state['jobs'].get(entry[1], {}).get('reason') == 'page_budget']
        if pending:
            first = max(pending, key=lambda r: r[0])
            candidates.remove(first)
            candidates.insert(0, first)
    if os.environ.get('CONSTELLATION_CDS_RETRIEVE_ONLY') == '1' and args.source == ['copernicus_era5_era5_land']:
        from copernicus_capture import request_spec
        roster=Path('/opt/constellation/trial-specialists/cds-existing-roster.json')
        requests=list(load_json(roster).get('requests', [])) if roster.is_file() else []
        ordered_requests={key:i for i,key in enumerate(requests)}
        def cds_request_key(job):
            p, _, _, spec=request_spec(job)
            return digest({'dataset':p['dataset'],'request':spec})
        filtered=[(ordered_requests[key], item) for item in candidates
                  if (key:=cds_request_key(item[2])) in ordered_requests]
        # A provider result can expire or fail file validation. Try the other
        # existing results before another attempt at the same scope.
        candidates=[item for _,item in sorted(filtered, key=lambda pair:(pair[1][0],pair[0]))]
    # Persist publication deferrals even when no capture is selected. They
    # remain incomplete and will be reconsidered against tomorrow's index.
    if published_eia_periods is not None or eia_index_error or inspect_children:
        from collection_storage import Stored
        token = write_json(store, state_key, state, stored.token if stored else None)
        stored = Stored(b'', token)
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
        # Emit scope identity before capture: an OOM kill cannot write a failure
        # receipt, and the preceding successful source is not the failed one.
        print(json.dumps({'stage': 'capture_started', 'source': job['source'],
                          'job_id': identity, 'start': job['start'], 'end_exclusive': job['end']}), flush=True)
        try:
            result = collect(job, store, settings, universe, taxonomy, args.pages)
        except Conflict:
            # A fenced checkpoint failure belongs to this exact provider scope.
            result = {'status': 'failed', 'reason': 'collection_checkpoint_conflict'}
        row = {**result, 'job_id': identity, 'source': job['source'], 'source_id': job['source_id'],
               'start': job['start'], 'end_exclusive': job['end'], 'last_attempt': now(), 'job': job}
        if result['status'] == 'failed':
            row['retry_after'] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat().replace('+00:00', 'Z')
            reason = result.get('reason', '')
            if reason.startswith(('source_retries_', 'retry_deferred', 'source_http_5')) or reason in {'source_http_401', 'source_http_403', 'source_http_429','additional_request_failed','copernicus_request_failed'}:
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
            if reason in {'epo_daily_request_budget','epo_weekly_byte_budget','epo_concurrency_deferred','comtrade_daily_request_budget'}:
                if reason=='epo_concurrency_deferred':
                    row['retry_after']=(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat().replace('+00:00','Z')
                state['source_retries'][job['source']]=row['retry_after']
        if result.get('reason') == 'ted_daily_xml_pending':
            row['retry_after'] = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat().replace('+00:00', 'Z')
            state['source_retries'][job['source']] = row['retry_after']
        if job['adapter']=='additional_biorxiv' and result.get('reason','').startswith('decodo_web_data_'):
            code=result['reason'];current=datetime.now(timezone.utc)
            retry=((current+timedelta(days=1)).replace(hour=0,minute=5,second=0,microsecond=0)
                   if code=='decodo_web_data_daily_budget' else current+timedelta(hours=1))
            row['retry_after']=retry.isoformat().replace('+00:00','Z')
            state['source_retries'][job['source']]=row['retry_after']
        if job['adapter']=='additional_dart' and result.get('reason') in ('dart_provider_status_020','dart_provider_status_800','filing_provider_http_429'):
            row['retry_after']=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat().replace('+00:00','Z')
            state['source_retries'][job['source']]=row['retry_after']
        if job['source']=='eia_retail_prices' and result['status']=='failed' and (result.get('reason','').startswith('source_http_5') or result.get('reason') in {'authenticated_source_request_failed','source_http_429'}):
            row['retry_after']=(datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat().replace('+00:00','Z')
            state['source_retries'][job['source']]=row['retry_after']
        state['jobs'][identity] = row
        state['updated_at'] = now()
        token = write_json(store, state_key, state, stored.token if stored else None)
        from collection_storage import Stored
        stored = Stored(b'', token)
        if result['status'] in {'complete', 'partial'} and result.get('records', 0):
            discover_children(store, result['manifest'], job)
        if result['status'] == 'complete':
            key = os.environ.get('CONSTELLATION_SPECIALIST_PUBLICATION_PREFIX','operations/specialists/publication-queue/') + identity + '.json'
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
              'accepted_unavailable_jobs': sum(r.get('status') == 'accepted_unavailable' for r in state['jobs'].values()),
              'failed_jobs': sum(r.get('status') == 'failed' for r in state['jobs'].values()),
              'remaining_jobs': sum(state['jobs'].get(digest({'job': j, 'universe_hash': universe_hash, 'version': VERSION}), {}).get('status') not in {'complete', 'accepted_unavailable'} for j in all_jobs)}
    (OUT / ((args.lane + '-' if args.lane != 'default' else '') + args.mode + '-latest.json')).write_text(json.dumps(report, indent=2) + '\n')
    report_key=os.environ.get('CONSTELLATION_OPERATION_RECEIPT_PREFIX','operations/specialists')+'/executions/'+digest(report)+'.json'
    write_json(store, report_key, report)
    print(json.dumps({'report_key':report_key,'specialist_summary':{'remaining_jobs':report['remaining_jobs'],'mode':args.mode}}),flush=True)


if __name__ == '__main__':
    main()
