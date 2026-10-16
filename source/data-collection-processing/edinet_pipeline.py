"""EDINET original documents, conservative Japanese decoding, extraction and linkage.

One inventory entry per committed page; credentials never enter stored URLs.
"""
from datetime import datetime
from html.parser import HTMLParser
import csv
import hashlib
import io
import json
from pathlib import PurePosixPath
import re
import time
import unicodedata
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener
import xml.etree.ElementTree as ET
import zipfile

from collection_storage import AlreadyComplete, CollectionRun, now, task_spec, write_json
from regulatory_collection import EvidenceClient, SourceIssue, require
from research_contract import digest, seal_record
from fda_access import NoRedirect

VERSION = 'edinet-documents-1.0'
API = 'https://api.edinet-fsa.go.jp/api/v2'
COVERAGE = ('EDINET daily inventory and all advertised original report formats; Japanese text and raw XBRL/CSV facts extracted; '
    'identifier matches verified only against reviewed universe mappings; unavailable reports and textless pages explicit; '
    'current archive observations, not historical API vintages or certified accounting interpretation')
FORMATS = [('1', 'xbrlFlag', 'main_report'), ('2', 'pdfFlag', 'pdf'),
           ('3', 'attachDocFlag', 'attachments'), ('4', 'englishDocFlag', 'english'), ('5', 'csvFlag', 'csv')]


def repair_japanese(value):
    """Reverse a lossless UTF-8-as-Latin-1/Windows-1252 error only if Japanese increases."""
    if isinstance(value, dict):
        return {k: repair_japanese(v) for k, v in value.items()}
    if isinstance(value, list):
        return [repair_japanese(v) for v in value]
    if not isinstance(value, str):
        return value
    score = lambda s: len(re.findall(r'[\u3040-\u30ff\u3400-\u9fff]', s))
    best = value
    for encoding in ('latin1', 'cp1252'):
        try:
            fixed = value.encode(encoding).decode('utf-8')
        except (UnicodeError, LookupError):
            continue
        if score(fixed) > score(best):
            best = fixed
    return best


def decode_text(raw):
    if raw.startswith((b'\xff\xfe', b'\xfe\xff')):
        return repair_japanese(raw.decode('utf-16')), 'utf-16'
    header = raw[:2048].decode('ascii', errors='ignore')
    declared = re.search(r'(?:charset\s*=\s*[\"\x27]?|encoding\s*=\s*[\"\x27])([\w-]+)', header, re.I)
    options = ([declared.group(1)] if declared else []) + ['utf-8-sig', 'cp932', 'euc_jp']
    for encoding in options:
        try:
            return repair_japanese(raw.decode(encoding)), encoding
        except (UnicodeError, LookupError):
            continue
    raise SourceIssue('edinet_text_encoding_unresolved')


def download(client, doc_id, kind):
    from specialist_authenticated import credentials
    require(re.fullmatch(r'[A-Z0-9]{8}', doc_id) is not None, 'edinet_invalid_document_id')
    require(kind in {f[0] for f in FORMATS}, 'edinet_invalid_document_type')
    key, = credentials('edinet')
    public = API + '/documents/' + doc_id + '?type=' + kind
    # Do not stringify network exceptions: they may contain the private query string.
    try:
        time.sleep(max(0, 1 - (time.monotonic() - client.last_request)))
        client.last_request = time.monotonic()
        with build_opener(NoRedirect()).open(Request(public + '&' + urlencode({'Subscription-Key': key}),
                headers={'User-Agent': 'Optima/1.0 (support@optima-holdings.com)', 'Accept-Encoding': 'identity'}), timeout=60) as response:
            raw = response.read(64 * 1024 * 1024 + 1)
            length = response.headers.get('Content-Length')
        require(len(raw) <= 64 * 1024 * 1024, 'edinet_document_too_large')
        require(length is None or int(length) == len(raw), 'edinet_document_truncated')
        require(raw.startswith(b'%PDF-') if kind == '2' else zipfile.is_zipfile(io.BytesIO(raw)), 'edinet_document_format_invalid')
        client.save(raw, public, 'application/pdf' if kind == '2' else 'application/zip')
        return raw
    except SourceIssue:
        raise
    except HTTPError as exc:
        status = exc.code
        exc.close()
        raise SourceIssue('edinet_document_http_' + str(status), status in (429, 500, 502, 503, 504)) from None
    except Exception:
        raise SourceIssue('edinet_document_request_failed', True) from None


class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'head', 'ix:hidden'):
            self.hidden += 1
        if tag in ('p', 'div', 'br', 'tr', 'td', 'li', 'h1', 'h2', 'h3'):
            self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'head', 'ix:hidden'):
            self.hidden = max(0, self.hidden - 1)
    def handle_data(self, text):
        if not self.hidden:
            self.parts.append(text)


def xml_facts(text):
    require('<!DOCTYPE' not in text.upper() and '<!ENTITY' not in text.upper(), 'edinet_xml_entities_not_supported')
    root = ET.fromstring(text)
    facts, contexts, units = [], {}, {}
    for node in root.iter():
        local = node.tag.rsplit('}', 1)[-1]
        if local in ('context', 'unit') and node.get('id'):
            (contexts if local == 'context' else units)[node.get('id')] = ET.tostring(node, encoding='unicode')
        if node.get('contextRef'):
            facts.append({'concept': node.tag, 'context_ref': node.get('contextRef'), 'unit_ref': node.get('unitRef'),
                'decimals': node.get('decimals'), 'value': ''.join(node.itertext()),
                'nil': node.get('{http://www.w3.org/2001/XMLSchema-instance}nil')})
    return {'facts': facts, 'contexts': contexts, 'units': units}


def extract_file(raw, filename):
    suffix = PurePosixPath(filename).suffix.lower()
    if raw.startswith(b'%PDF-'):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw))
        if reader.is_encrypted:
            # EDINET PDFs can set editing permissions while allowing an empty open password.
            require(bool(reader.decrypt('')), 'edinet_pdf_open_password_required')
        pages = [{'page': i + 1, 'text': repair_japanese(p.extract_text() or '')} for i, p in enumerate(reader.pages)]
        return {'file': filename, 'format': 'pdf', 'pages': pages,
            'text': '\n'.join(p['text'] for p in pages),
            'skipped_pages': [p['page'] for p in pages if not p['text'].strip()], 'ocr_performed': False}
    if suffix not in ('.htm', '.html', '.xhtml', '.xbrl', '.xml', '.csv', '.txt'):
        return {'file': filename, 'format': 'binary', 'status': 'preserved_no_text_extractor'}
    text, encoding = decode_text(raw)
    result = {'file': filename, 'format': suffix.lstrip('.'), 'encoding': encoding}
    if suffix in ('.xbrl', '.xml'):
        result.update(xml_facts(text))
        result['text'] = '\n'.join(f['value'] for f in result['facts'])
    elif suffix in ('.htm', '.html', '.xhtml'):
        parser = Text()
        parser.feed(text)
        result['text'] = '\n'.join(t.strip() for t in ''.join(parser.parts).splitlines() if t.strip())
    elif suffix == '.csv':
        delimiter = '\t' if '\t' in text.partition('\n')[0] else ','
        result['rows'] = list(csv.DictReader(io.StringIO(text), delimiter=delimiter))
        result['text'] = text
    else:
        result['text'] = text
    return result


def extract(raw, kind):
    if kind == '2':
        files = [extract_file(raw, 'report.pdf')]
    else:
        require(zipfile.is_zipfile(io.BytesIO(raw)), 'edinet_invalid_zip')
        files, expanded = [], 0
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            require(len(entries) <= 5000, 'edinet_zip_member_limit')
            for entry in entries:
                if entry.is_dir():
                    continue
                expanded += entry.file_size
                require(expanded <= 128 * 1024 * 1024 and entry.file_size <= 32 * 1024 * 1024,
                        'edinet_zip_expansion_limit')
                # Members are read in memory; no source-controlled path is written to disk.
                files.append(extract_file(archive.read(entry), entry.filename))
    return {'version': VERSION, 'files': files, 'text_characters': sum(len(f.get('text', '')) for f in files),
        'xbrl_facts': sum(len(f.get('facts', [])) for f in files),
        'textless_pdf_pages': sum(len(f.get('skipped_pages', [])) for f in files)}


def normalized_name(value):
    return ''.join(unicodedata.normalize('NFKC', value or '').casefold().split())


class Matcher:
    def __init__(self, universe):
        self.companies = {c['company_id']: c for c in universe['companies']
            if c['collection_enabled'] and c['review_status'] != 'rejected'}
        self.identifiers, self.names, self.tickers = {}, {}, {}
        systems = {'edinet': 'edinetCode', 'edinet_code': 'edinetCode', 'jcn': 'JCN', 'jp_corporate_number': 'JCN'}
        for ref in universe['external_identifiers']:
            if ref['entity_id'] in self.companies and ref['review_status'] == 'verified' and ref['system'] in systems:
                self.identifiers.setdefault((systems[ref['system']], str(ref['value'])), set()).add(ref['entity_id'])
        for cid, c in self.companies.items():
            self.names.setdefault(normalized_name(c['canonical_name']), set()).add(cid)
        for alias in universe['company_aliases']:
            if alias['company_id'] in self.companies and alias['review_status'] != 'rejected':
                self.names.setdefault(normalized_name(alias['alias']), set()).add(alias['company_id'])
        for listing in universe['listings']:
            if listing['company_id'] in self.companies and listing['exchange_mic'] == 'XTKS' and listing['review_status'] != 'rejected':
                self.tickers.setdefault(str(listing['ticker']).upper(), set()).add(listing['company_id'])

    def match(self, row):
        sets = [self.identifiers[(key, str(row[key]))] for key in ('edinetCode', 'JCN')
                if row.get(key) and (key, str(row[key])) in self.identifiers]
        proposed = set().union(*sets) if sets else set()
        candidates = proposed | self.names.get(normalized_name(row.get('filerName')), set())
        sec = str(row.get('secCode') or '')
        if len(sec) == 5 and sec.endswith('0'):
            candidates |= self.tickers.get(sec[:4].upper(), set())
        confirmed = set()
        if sets and len(proposed) == 1:
            confirmed = {cid for cid in proposed if self.companies[cid]['review_status'] == 'verified'
                         and self.companies[cid]['entity_type'] == 'legal_entity'}
        return {'company_ids': sorted(confirmed), 'candidate_company_ids': sorted(candidates - confirmed),
            'company_match_basis': 'verified_edinet_or_jcn' if confirmed else 'unresolved',
            'candidate_match_basis': 'exact_identifier_name_or_tokyo_ticker' if candidates - confirmed else None,
            'entity_link_status': 'matched' if confirmed else 'candidate' if candidates else 'unresolved',
            'conflicting_identifiers': len(proposed) > 1,
            'role': 'filer; fund and subject/issuer companies are not inferred to be the filer'}


def record(run, raw_row, client, listing_evidence, matcher, downloader=download):
    row = repair_japanese(raw_row)
    links = matcher.match(row)
    client.evidence = []
    documents = []
    unavailable = row.get('disclosureStatus') not in (None, '0') or row.get('withdrawalStatus') == '2'
    for kind, flag, label in FORMATS:
        if unavailable or row.get(flag) != '1':
            continue
        before = len(client.evidence)
        raw = downloader(client, row['docID'], kind)
        refs = list(client.evidence[before:])
        require(len(refs) == 1, 'edinet_document_evidence_missing')
        extracted = extract(raw, kind)
        packed = (json.dumps(extracted, ensure_ascii=False, sort_keys=True) + '\n').encode('utf-8')
        checksum = hashlib.sha256(packed).hexdigest()
        key = 'source_documents/edinet_filings_extracted/' + checksum
        from collection_storage import write_checked
        write_checked(run.store, key, packed, content_type='application/json')
        extracted_ref = {'key': key, 'sha256': checksum, 'source_url': refs[0]['source_url'], 'retrieved_at': now()}
        client.evidence.append(extracted_ref)
        documents.append({'type': kind, 'kind': label, 'bytes': len(raw), 'source_evidence': refs,
            'extraction': {'status': 'extracted' if extracted['text_characters'] else 'no_extractable_text',
                'source_evidence': [extracted_ref], 'text_characters': extracted['text_characters'],
                'xbrl_facts': extracted['xbrl_facts'], 'textless_pdf_pages': extracted['textless_pdf_pages'], 'ocr_performed': False}})
    chars = sum(d['extraction']['text_characters'] for d in documents)
    capture_status = 'captured' if documents else 'source_unavailable' if unavailable else 'no_advertised_documents'
    payload = {'source_id': 'S10', 'data': row, 'scope': run.spec['scope']['parameters'], 'coverage_note': COVERAGE,
        'source_evidence': list(listing_evidence) + client.evidence, 'pipeline_version': VERSION,
        'decoding': {'policy': 'strict_utf8_or_declared_encoding; lossless_mojibake_repair',
            'repaired_fields': [k for k in row if row[k] != raw_row[k]]},
        'documents': documents, 'document_capture_status': capture_status,
        'content_extraction_status': 'extracted' if chars else 'no_extractable_text' if documents else 'source_unavailable',
        'textless_pdf_pages': sum(d['extraction']['textless_pdf_pages'] for d in documents),
        'point_in_time_eligible': False, **{k: v for k, v in links.items() if k != 'company_ids'}}
    submitted = row.get('submitDateTime')
    event = {'value': submitted.replace(' ', 'T') + ':00+09:00', 'precision': 'second', 'source_timezone': 'Asia/Tokyo'} if submitted else None
    return seal_record({'document_type': 'collected_record', 'schema_version': '1.0', 'source': 'edinet_filings',
        'dataset': 'specialist_inputs', 'source_record_id': row['docID'], 'source_record_id_basis': 'provider',
        'source_url': API + '/documents/' + row['docID'], 'universe_version': run.universe['universe_version'],
        'company_ids': links['company_ids'], 'listing_ids': [], 'person_ids': [], 'product_ids': [],
        'entity_match_status': 'matched' if links['company_ids'] else 'unresolved', 'event_at': event,
        'available_at': None, 'source_updated_at': None, 'ingested_at': now(), 'availability_basis': 'unknown',
        'availability_evidence': [], 'run_id': run.run_id, 'payload': payload})


def collect(job, store, settings, universe, taxonomy, page_budget, client=None, requester=None, downloader=download):
    from specialist_authenticated import request
    requester = requester or request
    require(job['source'] == 'edinet_filings', 'edinet_wrong_source')
    spec = task_spec('edinet_filings', 'specialist_inputs', job['mode'], job['start'] + 'T00:00:00Z',
        job['end'] + 'T00:00:00Z', {'adapter': 'edinet', 'parameters': job['parameters'], 'source_id': 'S10',
            'coverage_note': COVERAGE}, VERSION, universe, taxonomy)
    try:
        run = CollectionRun.start(store, spec, universe, taxonomy, settings, resume=True)
    except AlreadyComplete as exc:
        return {'status': 'complete', 'manifest': str(exc), 'already_complete': True}
    client = client or EvidenceClient(store, 'edinet_filings')
    snapshot_key = run.state['manifest_prefix'] + '/edinet-inventory.json'
    # A resumed run inherits pages but not its predecessor's manifest prefix.
    cursor = json.loads(run.cursor) if run.cursor else None
    try:
        if cursor:
            from disclosure_collection import get_bytes
            snapshot = json.loads(get_bytes(store, cursor['snapshot_key'], cursor['snapshot_sha256']))
            snapshot_key = cursor['snapshot_key']
            snapshot_sha = cursor['snapshot_sha256']
        else:
            data = requester(client, 'edinet', API + '/documents.json', {'date': job['parameters']['date'], 'type': 2})
            require(str(data.get('metadata', {}).get('status')) == '200', 'edinet_api_status')
            rows = data.get('results')
            count = data.get('metadata', {}).get('resultset', {}).get('count')
            require(isinstance(rows, list) and count is not None and int(count) == len(rows), 'edinet_inventory_count')
            require(all(re.fullmatch(r'[A-Z0-9]{8}', r.get('docID', '')) for r in rows), 'edinet_invalid_document_id')
            require(len({(r['docID'], r.get('seqNumber')) for r in rows}) == len(rows), 'edinet_duplicate_inventory_entry')
            require(bool(client.evidence), 'edinet_inventory_evidence_missing')
            snapshot = {'data': data, 'evidence': list(client.evidence)}
            write_json(store, snapshot_key, snapshot)
            snapshot_sha = hashlib.sha256(store.get(snapshot_key).body).hexdigest()
        rows = snapshot['data']['results']
        offset = cursor['offset'] if cursor else 0
        require(0 <= offset <= len(rows), 'edinet_invalid_cursor')
        matcher = Matcher(universe)
        if not rows and not run.exhausted:
            run.commit_page([], exhausted=True)
        pages = 0
        while not run.exhausted and pages < page_budget:
            entry = record(run, rows[offset], client, snapshot['evidence'], matcher, downloader)
            offset += 1
            following = json.dumps({'offset': offset, 'snapshot_key': snapshot_key, 'snapshot_sha256': snapshot_sha})
            run.commit_page([entry], next_cursor=following if offset < len(rows) else None, exhausted=offset == len(rows))
            pages += 1
        status = 'complete' if run.exhausted else 'partial'
        return {'status': status, 'records': run.state['record_count'], 'manifest': run.finish(status,
            None if run.exhausted else 'page_budget', expected_records=run.state['record_count'] if run.exhausted else None)}
    except (Exception, KeyboardInterrupt) as exc:
        code = exc.code if isinstance(exc, SourceIssue) else 'interrupted' if isinstance(exc, KeyboardInterrupt) else 'edinet_collection_error'
        return {'status': 'partial' if isinstance(exc, KeyboardInterrupt) else 'failed', 'reason': code,
            'manifest': run.finish('partial' if isinstance(exc, KeyboardInterrupt) else 'failed', code)}
