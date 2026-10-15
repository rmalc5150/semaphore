#!/usr/bin/env python3
"""Collect public USPTO action text and final petition decisions with original PDFs."""
import argparse
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

from collection_storage import AlreadyComplete, CollectionRun, Conflict, StorageSettings, now, task_spec, write_checked, write_json
from patent_collection import SourceIssue, outcome, require, instant
from research_contract import ROOT, COLLECTION_UNIVERSE, canonical_json, digest, load_json, seal_record
from uspto_patents import application_number, load_api_key
from uspto_rate_limit import pace

VERSION = 'patent-prosecution-1.0'
BASE = 'https://api.uspto.gov'
DATASETS = ('patent_office_actions', 'patent_petition_decisions')
OA_PATH = '/api/v1/patent/oa/oa_actions/v1'
PETITION_PATH = '/api/v1/petition/decisions'


def scalar(value):
    if isinstance(value, list):
        require(len(value) == 1, 'ambiguous_provider_field')
        return value[0]
    return value


def source_day(value):
    if not isinstance(value, str) or value.startswith('0001-'):
        return None
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return None


def time_day(value):
    return {'value': value, 'precision': 'day', 'source_timezone': None} if value else None


def query(dataset, start, end, mode):
    require(dataset in DATASETS and mode in {'historical', 'daily'}, 'invalid_dataset_or_mode')
    field = ('submissionDate' if mode == 'historical' else 'lastModifiedTimestamp') if dataset == DATASETS[0] else (
        'decisionDate' if mode == 'historical' else 'lastModifiedDateTime')
    # Provider timestamps lack zones. Z in the Solr query is search syntax, not
    # evidence that the supplied document dates were UTC instants.
    lo, hi = str(start), str(end)
    if dataset == DATASETS[0]:
        lo += 'T00:00:00Z'; hi += 'T00:00:00Z'
    elif mode == 'daily':
        lo += 'T00:00:00'; hi += 'T00:00:00'
    criteria = f'{field}:[{lo} TO {hi}}}'
    if mode == 'daily':
        from historical_policy import historical_start
        action_field = 'submissionDate' if dataset == DATASETS[0] else 'decisionDate'
        action_start = str(historical_start()) + ('T00:00:00Z' if dataset == DATASETS[0] else '')
        criteria += f' AND {action_field}:[{action_start} TO *]'
    if dataset == DATASETS[1]:
        criteria += ' AND finalPetitionDecisionIndicator:true'
    return field, criteria


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward our API key to a provider-supplied redirect location.
        return None


class Client:
    def __init__(self, store, key_loader=load_api_key, opener=None, gate=pace, sleeper=time.sleep,
                 max_requests=240, max_download_bytes=32 * 1024 * 1024):
        self.store, self.key_loader, self.key = store, key_loader, None
        self.opener = opener or build_opener(NoRedirect()).open
        self.gate, self.sleep = gate, sleeper
        self.max_requests, self.requests = max_requests, 0
        self.max_download_bytes, self.download_bytes = max_download_bytes, 0
        self.evidence = []

    def request(self, path, data=None, content_type=None, pdf=False):
        url = path if path.startswith('https://') else BASE + path
        parts = urlsplit(url)
        require(parts.scheme == 'https' and parts.netloc == 'api.uspto.gov' and not parts.username
                and (not pdf or parts.path.startswith('/api/v1/download/applications/')), 'unsafe_source_url')
        if self.key is None:
            self.key = self.key_loader()
        headers = {'X-API-KEY': self.key, 'Accept': 'application/pdf' if pdf else 'application/json'}
        if content_type:
            headers['Content-Type'] = content_type
        def save(raw):
            checksum = hashlib.sha256(raw).hexdigest()
            key = f'source_documents/uspto_odp/{checksum}'
            write_checked(self.store, key, raw, content_type='application/pdf' if pdf else 'application/json')
            evidence = {'key': key, 'sha256': checksum, 'bytes': len(raw), 'url': url}
            if data is not None:
                evidence['request'] = json.loads(data) if content_type == 'application/json' else data.decode()
            self.evidence.append(evidence)

        def read_response(response, limit):
            raw = response.read(limit + 1)
            if pdf:
                self.download_bytes += len(raw)
            require(len(raw) <= limit, 'document_too_large' if pdf else 'response_too_large')
            length = response.headers.get('Content-Length')
            require(length is None or int(length) == len(raw), 'truncated_response')
            return raw
        for attempt in range(3):
            require(self.requests < self.max_requests, 'request_limit')
            limit = min(16 * 1024 * 1024, self.max_download_bytes - self.download_bytes) if pdf else 16 * 1024 * 1024
            require(limit > 0, 'download_budget')
            self.gate(); self.requests += 1
            try:
                with self.opener(Request(url, data=data, headers=headers), timeout=45) as response:
                    raw = read_response(response, limit)
                if pdf:
                    require(raw.startswith(b'%PDF-'), 'invalid_pdf_response')
                else:
                    try:
                        value = json.loads(raw)
                    except ValueError:
                        raise SourceIssue('invalid_json_response') from None
                save(raw)
                return raw if pdf else value
            except HTTPError as exc:
                if pdf and exc.code in {301, 302, 303, 307, 308}:
                    target = exc.headers.get('Location', '')
                    location = urlsplit(target)
                    require(location.scheme == 'https' and location.netloc == 'data-documents.uspto.gov'
                            and not location.username, 'unsafe_download_redirect')
                    require(self.requests < self.max_requests, 'request_limit')
                    self.gate(); self.requests += 1
                    try:
                        # USPTO's document host redirects are fetched without
                        # API keys. Signed redirect URLs never enter evidence.
                        with self.opener(Request(target, headers={'Accept': 'application/pdf'}), timeout=45) as response:
                            raw = read_response(response, limit)
                    except HTTPError as download_error:
                        raise SourceIssue(f'document_http_{download_error.code}') from None
                    except (URLError, TimeoutError):
                        raise SourceIssue('document_network_error', True) from None
                    require(raw.startswith(b'%PDF-'), 'invalid_pdf_response')
                    save(raw)
                    return raw
                if not pdf and exc.code == 404 and (path.endswith('/search') or path.endswith('/records')):
                    raw = exc.read(65536)
                    try:
                        empty = json.loads(raw)
                    except ValueError:
                        empty = {}
                    if empty.get('detailedMessage') == 'No matching records found, refine your search criteria and try again':
                        save(raw)
                        offset = int(parse_qs(data.decode()).get('start', ['0'])[0]) if content_type == 'application/x-www-form-urlencoded' else 0
                        return {'count': 0, 'petitionDecisionDataBag': [],
                            'response': {'numFound': 0, 'start': offset, 'docs': []}}
                if exc.code not in {429, 500, 502, 503, 504}:
                    raise SourceIssue(f'source_http_{exc.code}') from None
                try:
                    delay = max(2 ** attempt, float(exc.headers.get('Retry-After', '0')))
                except (ValueError, AttributeError):
                    raise SourceIssue('retry_deferred', True) from None
                require(delay <= 30, 'retry_deferred')
                if attempt < 2:
                    self.sleep(delay)
            except (URLError, TimeoutError):
                if attempt < 2:
                    self.sleep(2 ** attempt)
        raise SourceIssue('source_retries_exhausted', True)

    def search(self, dataset, criteria, offset, size):
        if dataset == DATASETS[0]:
            response = self.request(OA_PATH + '/records', urlencode({'criteria': criteria,
                'start': offset, 'rows': size}).encode(), 'application/x-www-form-urlencoded')
            body = response.get('response', {})
            require(body.get('start') == offset, 'source_ignored_offset')
            return body.get('numFound'), body.get('docs')
        response = self.request(PETITION_PATH + '/search', canonical_json({'q': criteria,
            'pagination': {'offset': offset, 'limit': size},
            'sort': [{'field': 'petitionDecisionRecordIdentifier', 'order': 'asc'}]}), 'application/json')
        return response.get('count'), response.get('petitionDecisionDataBag')

    def documents(self, application):
        response = self.request(f'/api/v1/patent/applications/{application}/documents')
        rows = response.get('documentBag')
        require(isinstance(rows, list) and response.get('count') == len(rows), 'incomplete_document_listing')
        return rows


def normalize(dataset, row):
    oa = dataset == DATASETS[0]
    identity = row.get('id' if oa else 'petitionDecisionRecordIdentifier')
    require(isinstance(identity, str) and bool(re.fullmatch(r'[A-Za-z0-9_-]+', identity)), 'missing_document_identity')
    original = scalar(row.get('patentApplicationNumber' if oa else 'applicationNumberText'))
    require(isinstance(original, str), 'missing_application_identity')
    number = application_number(original)
    action = source_day(scalar(row.get('submissionDate' if oa else 'decisionDate')))
    require(action is not None, 'missing_action_date')
    if not oa:
        require(row.get('finalPetitionDecisionIndicator') is True, 'source_ignored_final_filter')
    document_id = scalar(row.get('obsoleteDocumentIdentifier')) if oa else None
    require(not oa or isinstance(document_id, str) and bool(re.fullmatch(r'[A-Za-z0-9_-]+', document_id)),
            'missing_official_document_identity')
    text = row.get('bodyText', []) if oa else row.get('ocrSearchText')
    if isinstance(text, list):
        require(all(isinstance(x, str) for x in text), 'invalid_provider_text')
        text = '\n'.join(text)
    require(text is None or isinstance(text, str), 'invalid_provider_text')
    return {'source_document_id': identity, 'application_number': number, 'original_application_number': original,
        'official_document_id': document_id, 'document_type': scalar(row.get('legacyDocumentCodeIdentifier')) if oa else 'final_petition_decision',
        'action_date': action, 'action_date_precision': 'day',
        'patent_number': scalar(row.get('patentNumber')), 'publication_references': [],
        'title': scalar(row.get('inventionTitle')), 'source_text': text,
        'text_basis': 'provider_body_text' if oa else 'provider_ocr',
        'provider_updated_at': row.get('lastModifiedTimestamp' if oa else 'lastModifiedDateTime'),
        'provider_ingestion_at': row.get('createDateTime' if oa else 'lastIngestionDateTime'),
        'reported_parties': [] if oa or not row.get('firstApplicantName') else [
            {'name': row['firstApplicantName'], 'role': 'reported_applicant'}],
        'structured_source_fields': {'sections': row.get('sections')} if oa else {
            k: row.get(k) for k in ('finalPetitionDecisionIndicator', 'petitionIssueConsideredTextBag',
            'decisionPetitionTypeCode', 'decisionPetitionTypeCodeDescriptionText', 'decidedPetitionTypeCode',
            'decidedPetitionTypeCodeDescriptionText', 'statuteBag', 'ruleBag')},
        'extracted_claims': [], 'extraction_version': None,
        'supporting_passages': [{'field': 'bodyText' if oa else 'ocrSearchText', 'start': 0, 'end': len(text)}] if text else []}


def documents_for(client, dataset, row, data):
    if dataset == DATASETS[0]:
        docs = [d for d in client.documents(data['application_number'])
                if d.get('documentIdentifier') == data['official_document_id']]
        require(len(docs) == 1, 'official_document_not_found')
    else:
        docs = row.get('documentBag')
        if not docs:
            detail = client.request(PETITION_PATH + '/' + data['source_document_id'] + '?includeDocuments=true')
            detail_rows = detail.get('petitionDecisionDataBag', [])
            require(len(detail_rows) == 1 and detail_rows[0].get('petitionDecisionRecordIdentifier') == data['source_document_id'],
                    'petition_detail_mismatch')
            docs = detail_rows[0].get('documentBag')
        require(isinstance(docs, list) and bool(docs), 'official_document_not_found')
    result = []
    for doc in docs:
        identity = doc.get('documentIdentifier')
        require(isinstance(identity, str) and bool(identity), 'missing_official_document_identity')
        pdfs = [d for d in doc.get('downloadOptionBag', []) if d.get('mimeTypeIdentifier') == 'PDF']
        require(len(pdfs) == 1 and isinstance(pdfs[0].get('downloadUrl'), str), 'pdf_download_not_available')
        require(urlsplit(pdfs[0]['downloadUrl']).path ==
                f"/api/v1/download/applications/{data['application_number']}/{identity}.pdf", 'document_application_mismatch')
        result.append({'document_id': identity, 'document_type': doc.get('documentCode'),
            'official_date': doc.get('officialDate'), 'url': pdfs[0]['downloadUrl']})
    return result


def enrich(client, dataset, row, data):
    # The provider content/update fields are part of the cache identity, so a
    # correction refetches bytes. A retry verifies successful cached artifacts.
    identity = digest([VERSION, dataset, row])
    key = f'checkpoints/uspto-prosecution-documents/{identity}.json'
    stored = client.store.get(key)
    saved = json.loads(stored.body) if stored else None
    first_key = f"checkpoints/uspto-prosecution-first-observed/{dataset}/{data['source_document_id']}.json"
    first = client.store.get(first_key)
    if first is None:
        observation = {'application_number': data['application_number'],
            'first_observed_at': saved.get('first_observed_at', saved.get('updated_at')) if saved else now()}
        try:
            write_json(client.store, first_key, observation)
        except Conflict:
            pass  # A concurrent window may have registered the same document.
        first = client.store.get(first_key)
    first_state = json.loads(first.body)
    require(first_state['application_number'] == data['application_number'], 'document_identity_collision')
    first_observed = first_state['first_observed_at']
    if saved and saved['status'] == 'downloaded':
        for doc in saved['documents']:
            obj = client.store.get(doc['key'])
            require(obj is not None and hashlib.sha256(obj.body).hexdigest() == doc['sha256'], 'corrupt_cached_document')
        client.evidence.extend(saved['source_evidence'])
        return {**saved, 'first_observed_at': first_observed}
    before = len(client.evidence)
    successful = {d['document_id']: d for d in saved.get('documents', [])} if saved else {}
    evidence = saved.get('source_evidence', []) if saved else []
    try:
        options = documents_for(client, dataset, row, data)
        for option in options:
            if option['document_id'] in successful:
                doc = successful[option['document_id']]
                obj = client.store.get(doc['key'])
                require(obj is not None and hashlib.sha256(obj.body).hexdigest() == doc['sha256'], 'corrupt_cached_document')
                continue
            client.request(option['url'], pdf=True)
            successful[option['document_id']] = {**option, **client.evidence[-1]}
            state = {'status': 'pending', 'documents': list(successful.values()),
                'source_evidence': evidence + client.evidence[before:], 'updated_at': now(), 'first_observed_at': first_observed}
            token = write_json(client.store, key, state, stored.token if stored else None)
            from collection_storage import Stored
            stored = Stored(canonical_json(state) + b'\n', token)
        state = {'status': 'downloaded', 'documents': list(successful.values()),
            'source_evidence': evidence + client.evidence[before:], 'updated_at': now(), 'first_observed_at': first_observed}
        write_json(client.store, key, state, stored.token if stored else None)
        client.evidence.extend(evidence)
        return state
    except SourceIssue as exc:
        state = {'status': 'failed', 'reason': exc.code, 'documents': list(successful.values()),
            'source_evidence': evidence + client.evidence[before:], 'updated_at': now(), 'first_observed_at': first_observed}
        write_json(client.store, key, state, stored.token if stored else None)
        raise


def envelope(dataset, data, downloads, run, evidence):
    observed = now()
    data = {**data, 'document_retrieval_status': downloads['status'], 'documents': downloads['documents'],
        'first_observed_at': downloads.get('first_observed_at', downloads['updated_at']),
        'capture_at': observed, 'public_availability': None, 'availability_evidence': []}
    return seal_record({'document_type': 'collected_record', 'schema_version': '1.0',
        'source': 'uspto_odp', 'dataset': dataset, 'source_record_id': data['source_document_id'],
        'source_record_id_basis': 'provider', 'source_url': BASE + (OA_PATH + '/records' if dataset == DATASETS[0] else
            PETITION_PATH + '/' + data['source_document_id']),
        'universe_version': run.universe['universe_version'], 'company_ids': [], 'listing_ids': [],
        'product_ids': [], 'person_ids': [], 'entity_match_status': 'unresolved',
        'event_at': time_day(data['action_date']), 'available_at': None, 'source_updated_at': None,
        'ingested_at': observed, 'availability_basis': 'unknown', 'availability_evidence': [], 'run_id': run.run_id,
        'payload': {'record_type': 'patent_prosecution_document', 'contract_version': '1.0', 'data': data,
            'source_evidence': evidence, 'date_basis': run.spec['scope']['date_basis'],
            'review_required': True, 'coverage_note': run.spec['scope']['coverage']}})


def collect(store, settings, universe, taxonomy, dataset, start, end, mode='historical',
            page_size=5, max_pages=10, refresh=False, client=None, lane='collection'):
    require(1 <= page_size <= 20 and max_pages > 0 and start < end, 'invalid_collection_limits')
    field, criteria = query(dataset, start, end, mode)
    scope = {'query': criteria, 'date_basis': field, 'page_size': page_size, 'documents': 'original_pdf', 'lane': lane,
        'selection': 'all_returned_public_records', 'final_petitions_only': dataset == DATASETS[1],
        'coverage': 'Public provider index only; source lag, missing documents and mutable offset pagination limit coverage. Dates are not historical availability.'}
    spec = task_spec('uspto_odp', dataset, mode, instant(start), instant(end), scope, VERSION, universe, taxonomy)
    try:
        run = CollectionRun.start(store, spec, universe, taxonomy, settings, resume=not refresh, refresh=refresh)
    except AlreadyComplete as exc:
        return {'status': 'complete', 'already_complete': True, 'manifest': str(exc)}
    client = client or Client(store)
    state = json.loads(run.cursor) if run.cursor else {'offset': 0, 'total': None}
    source_ids = set()
    for page in run.state['pages']:
        for batch in page['batches']:
            source_ids.update(json.loads(line)['source_record_id'] for line in store.get(batch['key']).body.splitlines())
    def page(offset):
        total, rows = client.search(dataset, criteria, offset, page_size)
        require(type(total) is int and total >= 0 and isinstance(rows, list), 'invalid_search_response')
        require(state['total'] is None or state['total'] == total, 'source_changed_refresh_required')
        require(len(rows) == min(page_size, total - offset), 'incomplete_page')
        return total, rows
    try:
        # Re-query committed boundary pages at resume AND before completion;
        # arbitrary sort parameters are ignored by the OA endpoint.
        if state['offset']:
            for offset, checksum in [(0, state['first_page_hash']), (state['last_page_offset'], state['last_page_hash'])]:
                _, rows = page(offset)
                require(digest(rows) == checksum, 'source_changed_refresh_required')
        pages = 0
        while not run.exhausted:
            if pages >= max_pages:
                return outcome(run, 'partial', 'page_limit')
            client.evidence = []
            total, rows = page(state['offset']); pages += 1
            search_evidence = list(client.evidence)
            records = []; current_ids = set()
            for row in rows:
                data = normalize(dataset, row)
                basis = source_day(scalar(row.get(field)))
                require(basis is not None and str(start) <= basis < str(end), 'source_ignored_date_filter')
                require(data['source_document_id'] not in source_ids | current_ids, 'duplicate_provider_document')
                current_ids.add(data['source_document_id'])
                client.evidence = []
                downloads = enrich(client, dataset, row, data)
                records.append(envelope(dataset, data, downloads, run, search_evidence + client.evidence))
            offset = state['offset']
            state = {**state, 'offset': offset + len(rows), 'total': total,
                'first_page_hash': state.get('first_page_hash', digest(rows)),
                'last_page_offset': offset, 'last_page_hash': digest(rows)}
            exhausted = state['offset'] == total
            if exhausted and offset:
                _, first = page(0)
                require(digest(first) == state['first_page_hash'], 'source_changed_refresh_required')
            run.commit_page(records, next_cursor=None if exhausted else json.dumps(state, sort_keys=True), exhausted=exhausted)
            source_ids.update(current_ids)
        return outcome(run, 'complete')
    except SourceIssue as exc:
        # Failed downloads are durable in their task receipts. The source page
        # remains uncommitted so successful downloads are reused on retry.
        return outcome(run, 'partial', exc.code)
    except Exception:
        if not run.closed:
            run.finish('failed', 'collection_failed')
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', choices=DATASETS)
    parser.add_argument('--start', type=date.fromisoformat)
    parser.add_argument('--end', type=date.fromisoformat, required=True)
    parser.add_argument('--mode', choices=['historical', 'daily'], default='historical')
    parser.add_argument('--page-size', type=int, default=5)
    parser.add_argument('--max-pages', type=int, default=10)
    parser.add_argument('--max-requests', type=int, default=240)
    parser.add_argument('--max-download-bytes', type=int, default=32 * 1024 * 1024)
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--storage-config', type=Path, default=ROOT / 'config/collection-storage.s3.json')
    parser.add_argument('--backend', choices=['local', 's3'])
    parser.add_argument('--output-root')
    parser.add_argument('--universe', type=Path, default=COLLECTION_UNIVERSE)
    parser.add_argument('--taxonomy', type=Path, default=ROOT / 'config/sectors.v1.json')
    args = parser.parse_args(argv)
    if args.start is None:
        if args.mode == 'daily':
            parser.error('daily requires --start')
        from historical_policy import historical_start
        args.start = historical_start()
    settings = StorageSettings.load(args.storage_config, {'backend': args.backend, 'local_root': args.output_root})
    store = settings.store()
    result = collect(store, settings, load_json(args.universe), load_json(args.taxonomy), args.dataset,
        args.start, args.end, args.mode, args.page_size, args.max_pages, args.refresh,
        Client(store, max_requests=args.max_requests, max_download_bytes=args.max_download_bytes))
    print(json.dumps(result), flush=True)
    return 0 if result['status'] == 'complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
