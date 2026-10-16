#!/usr/bin/env python3
"""Isolated event experiment: GET saved evidence, freeze samples, replay locally.

No production database, catalog, timer, provider, or S3 write path exists here.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent
VERSION = 'event-pilot-0.1'


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = encoded(value) + b'\n'
    if path.exists() and path.read_bytes() != body:
        raise ValueError('Refusing to overwrite different artifact: ' + str(path))
    path.write_bytes(body)


def jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = b''.join(encoded(row) + b'\n' for row in rows)
    if path.exists() and path.read_bytes() != body:
        raise ValueError('Refusing to overwrite different artifact: ' + str(path))
    path.write_bytes(body)


class MissingEvidence(ValueError):
    pass


class SnapshotReader:
    """Bounded S3 GET-only reader with exact bytes pinned locally."""
    def __init__(self, client, bucket, prefix, output, budget):
        self.client, self.bucket = client, bucket
        self.prefix, self.output = prefix.rstrip('/') + '/', Path(output)
        self.budget, self.downloaded = budget, 0
        self.cache = {}

    def get(self, key, limit, absolute=False):
        full = key if absolute else self.prefix + key
        if full in self.cache:
            receipt = self.cache[full]
            if receipt['bytes'] > limit:
                raise MissingEvidence('object_size_limit')
            return (self.output / receipt['local_path']).read_bytes(), receipt
        remaining = self.budget - self.downloaded
        if remaining <= 0:
            raise MissingEvidence('total_download_budget')
        response = self.client.get_object(Bucket=self.bucket, Key=full)
        stream = response['Body']
        try:
            if response.get('ContentLength', 0) > min(limit, remaining):
                raise MissingEvidence('object_size_limit')
            body = stream.read(min(limit, remaining) + 1)
            self.downloaded += len(body)
            if len(body) > min(limit, remaining):
                raise MissingEvidence('object_size_limit')
        finally:
            stream.close()
        checksum = hashlib.sha256(body).hexdigest()
        relative = 'objects/' + checksum
        path = self.output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(body)
        receipt = {'s3_uri': 's3://' + self.bucket + '/' + full, 'sha256': checksum,
                   'bytes': len(body), 'local_path': relative, 'etag': response.get('ETag'),
                   'version_id': response.get('VersionId')}
        self.cache[full] = receipt
        return body, receipt


def prove_batch(reader, row, metadata_limit):
    """Check live terminal-history membership; partial samples remain labeled."""
    key, source, dataset = row['key'], row['source'], row['dataset']
    match = re.search(r'/run_id=(run_[a-f0-9-]+)/', key)
    if not match:
        raise MissingEvidence('invalid_batch_run')
    manifest_key = f'manifests/collection_runs/source={source}/dataset={dataset}/{match[1]}/final.json'
    body, manifest_ref = reader.get(manifest_key, metadata_limit)
    manifest = json.loads(body)
    task = manifest['task']
    if (task['source'], task['dataset']) != (source, dataset):
        raise MissingEvidence('manifest_scope_mismatch')
    if manifest['task_id'] != 'task_' + digest(task):
        raise MissingEvidence('task_hash_mismatch')
    head_body, head_ref = reader.get('checkpoints/' + manifest['task_id'] + '/head.json', metadata_limit)
    head = json.loads(head_body)
    if manifest_key not in head.get('terminal_history', []):
        raise MissingEvidence('uncommitted_terminal_manifest')
    if head['task_id'] != manifest['task_id'] or head['task'] != task:
        raise MissingEvidence('head_task_mismatch')
    batch = next((b for page in manifest['pages'] for b in page['batches'] if b['key'] == key), None)
    if batch is None or any(batch[k] != row[k] for k in ('sha256', 'bytes', 'records')):
        raise MissingEvidence('manifest_batch_mismatch')
    return {'manifest': manifest_ref, 'checkpoint': head_ref, 'source_task_id': manifest['task_id'],
            'source_status': manifest['status'], 'source_reason': manifest.get('reason_code'),
            'window': task.get('window'), 'verification_query_id': row.get('query_id')}


def error_reason(exc):
    if isinstance(exc, MissingEvidence):
        return str(exc)
    response = getattr(exc, 'response', {})
    return response.get('Error', {}).get('Code', type(exc).__name__)


def capture(output, config):
    """Read a few verified batches per provider/dataset; never query whole tables."""
    import boto3
    from botocore.config import Config
    output = Path(output)
    if output.exists():
        raise ValueError('Capture needs a new directory; use build for offline replay')
    output.mkdir(parents=True)
    storage = load(ROOT / config['storage_config'])
    inventory = load(ROOT / config['inventory'])
    write(output / 'config.json', config)
    write(output / 'inventory.json', inventory)
    write(output / 'taxonomy.json', load(ROOT / config['taxonomy']))
    write(output / 'event-schema.json', load(ROOT / 'schemas/event-pilot.schema.json'))
    reader = SnapshotReader(boto3.client('s3', region_name=storage['region'], config=Config(
        connect_timeout=10, read_timeout=30, retries={'max_attempts': 2})),
        storage['s3_bucket'], storage['s3_prefix'], output, config['max_download_bytes'])
    connection = sqlite3.connect((ROOT / config['index']).resolve().as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    # Read a stable metadata snapshot without changing the production index.
    snapshot = sqlite3.connect(output / 'catalog-index.sqlite3')
    snapshot.execute('PRAGMA cache_size=-2048')
    connection.backup(snapshot)
    connection.close()
    snapshot.row_factory = sqlite3.Row
    pairs = snapshot.execute('SELECT DISTINCT source,dataset FROM batches ORDER BY source,dataset').fetchall()
    outcomes, samples = [], []
    complete = False
    try:
        for pair in pairs:
            source, dataset = pair['source'], pair['dataset']
            sid = config['source_map'].get(source)
            if not sid:
                outcomes.append({'source': source, 'dataset': dataset, 'status': 'unmapped_source', 'samples': 0})
                continue
            result = {'source_id': sid, 'source': source, 'dataset': dataset, 'samples': 0, 'errors': []}
            rows = snapshot.execute('''SELECT b.*,v.query_id FROM batches b JOIN verified_batches v ON b.key=v.key
                WHERE source=? AND dataset=? AND records>0 AND bytes<=? ORDER BY key DESC LIMIT ?''',
                (source, dataset, config['max_batch_bytes'], config['max_batches_per_dataset'])).fetchall()
            seen = set()
            for row in rows:
                try:
                    proof = prove_batch(reader, dict(row), config['max_metadata_bytes'])
                    body, ref = reader.get(row['key'], config['max_batch_bytes'])
                    if hashlib.sha256(body).hexdigest() != row['sha256'] or len(body) != row['bytes']:
                        raise MissingEvidence('batch_checksum_or_size_mismatch')
                    lines = [line for line in body.splitlines() if line.strip()]
                    if len(lines) != row['records']:
                        raise MissingEvidence('batch_record_count_mismatch')
                    # Validate every envelope's scope before selecting samples.
                    records = [json.loads(line) for line in lines]
                    if any((r.get('source'), r.get('dataset')) != (source, dataset) for r in records):
                        raise MissingEvidence('record_scope_mismatch')
                    for line_number, record in enumerate(records, 1):
                        from research_contract import seal_record
                        if seal_record(record)['observation_id'] != record.get('observation_id'):
                            raise MissingEvidence('observation_hash_mismatch')
                        identity = (record.get('record_id'), record.get('payload_hash'))
                        if identity in seen:
                            continue
                        seen.add(identity)
                        samples.append({'source_id': sid, 'record': record, 'provenance': {
                            **proof, 'batch': ref, 'line_number': line_number, 'kind': 'committed_source_batch'}})
                        result['samples'] += 1
                        if result['samples'] >= config['sample_per_dataset']:
                            break
                    if result['samples'] >= config['sample_per_dataset']:
                        break
                except Exception as exc:
                    result['errors'].append({'batch_key': row['key'], 'reason': error_reason(exc)})
            result['status'] = 'sampled' if result['samples'] else 'no_verified_sample'
            outcomes.append(result)
            print(json.dumps({'source': source, 'dataset': dataset, 'samples': result['samples'],
                              'status': result['status']}), flush=True)
            # An interruption still leaves a readable completed-prefix sample.
            (output / 'samples.partial.jsonl').write_bytes(b''.join(encoded(s) + b'\n' for s in samples))
        capture_reddit(reader, config, samples, outcomes)
        capture_search(reader, config, samples, outcomes)
        complete = True
    finally:
        snapshot.close()
        jsonl(output / 'samples.jsonl', samples)
        write(output / 'capture.json', {'version': VERSION, 'captured_at': datetime.now(timezone.utc).isoformat(),
              'status': 'complete' if complete else 'interrupted',
              'sample_policy': 'Latest lexicographic verified batches; first distinct logical records; not random or representative.',
              'bytes_downloaded': reader.downloaded, 'sample_count': len(samples), 'routes': outcomes,
              'samples_sha256': hashlib.sha256((output / 'samples.jsonl').read_bytes()).hexdigest()})
    return output


def capture_reddit(reader, config, samples, outcomes):
    result = {'source_id': 'S63', 'source': 'reddit_refreshable', 'dataset': 'social_records', 'samples': 0, 'errors': []}
    try:
        cfg = load(ROOT / 'config/reddit-access.json')
        if cfg['bucket'] != reader.bucket:
            raise MissingEvidence('reddit_bucket_mismatch')
        body, ref = reader.get(cfg['prefix'] + '/records/current.jsonl', 20 * 1024 * 1024, absolute=True)
        seen = set()
        for line in body.splitlines():
            data = json.loads(line)
            if data['record_id'] in seen:
                continue
            seen.add(data['record_id'])
            rec = special_record('reddit_refreshable', 'social_records', data['record_id'], data,
                                 data.get('source_url'), data.get('observed_utc'))
            samples.append({'source_id': 'S63', 'record': rec, 'provenance': {
                'kind': 'refreshable_snapshot_not_immutable_archive', 'batch': ref,
                'source_status': 'snapshot_only', 'note': 'GET snapshot frozen locally; not shared collection commit.'}})
            result['samples'] += 1
            if result['samples'] >= config['sample_per_dataset']:
                break
        result['status'] = 'sampled' if result['samples'] else 'empty_snapshot'
    except Exception as exc:
        result['status'] = 'no_verified_sample'
        result['errors'].append({'reason': error_reason(exc)})
    outcomes.append(result)


def special_record(source, dataset, identity, data, url=None, ingested=None):
    return {'source': source, 'dataset': dataset, 'source_record_id': str(identity),
            'record_id': 'pilot_rec_' + digest([source, dataset, identity]),
            'observation_id': 'pilot_obs_' + digest([source, dataset, identity, data]),
            'source_url': url, 'ingested_at': ingested, 'event_at': None, 'available_at': None,
            'availability_basis': 'unknown', 'availability_evidence': [], 'payload': {'data': data},
            'company_ids': [], 'product_ids': [], 'person_ids': [], 'listing_ids': []}


def capture_search(reader, config, samples, outcomes):
    result = {'source_id': 'S65', 'source': 'dataforseo', 'dataset': 'saved_search_capture', 'samples': 0, 'errors': []}
    # Existing readiness receipts provide exact source artifact hashes; no paid API calls.
    receipts = ROOT / 'reports/weekly-readiness-2026-10-09/captures'
    for path in sorted(receipts.glob('*.json')):
        receipt = load(path)
        if not isinstance(receipt, dict) or receipt.get('source_id') != 'S65' or receipt.get('http_status') != 200 or not receipt.get('raw_s3_key'):
            continue
        try:
            body, ref = reader.get(receipt['raw_s3_key'], config['max_batch_bytes'], absolute=True)
            if hashlib.sha256(body).hexdigest() != receipt['sha256']:
                raise MissingEvidence('search_receipt_checksum_mismatch')
            data = json.loads(body)
            for task in data.get('tasks', []):
                if task.get('status_code') != 20000:
                    continue
                for block in task.get('result') or []:
                    for item in block.get('items') or []:
                        identity = str(task.get('id')) + ':' + digest(item)
                        rec = special_record('dataforseo', 'saved_search_capture', identity, item,
                                             receipt.get('url'), receipt.get('observed_at'))
                        samples.append({'source_id': 'S65', 'record': rec, 'provenance': {
                            'kind': 'saved_provider_receipt', 'batch': ref, 'source_status': 'saved_pilot_capture',
                            'receipt_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                            'receipt_name': path.name, 'note': 'Existing paid capture reused; no new provider requests.'}})
                        result['samples'] += 1
                        if result['samples'] >= config['sample_per_dataset']:
                            break
                    if result['samples'] >= config['sample_per_dataset']:
                        break
                if result['samples'] >= config['sample_per_dataset']:
                    break
        except Exception as exc:
            result['errors'].append({'reason': error_reason(exc), 'receipt_name': path.name})
        if result['samples'] >= config['sample_per_dataset']:
            break
    result['status'] = 'sampled' if result['samples'] else 'no_verified_sample'
    outcomes.append(result)


def walk(value, prefix='$.payload.data'):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, prefix + '.' + key)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from walk(child, f'{prefix}[{i}]')
    elif value is not None:
        yield prefix, value


def first(data, names):
    if isinstance(data, dict):
        for key, value in data.items():
            if key in names and isinstance(value, (str, int, float)) and str(value).strip():
                return '$.payload.data.' + key, value
    for path, value in walk(data):
        if path.rsplit('.', 1)[-1] in names and isinstance(value, (str, int, float)) and str(value).strip():
            return path, value
    return None


def top_field(data, names):
    if isinstance(data, dict):
        for key, value in data.items():
            if key in names and isinstance(value, (str, int, float)) and str(value).strip():
                return '$.payload.data.' + key, value
    return None


def title_field(data):
    if isinstance(data, dict):
        for key in ('title', 'Title', 'TITLE', 'briefTitle', 'officialTitle', 'name', 'headline'):
            value = data.get(key)
            if isinstance(value, list) and value and all(isinstance(v, str) for v in value):
                return '$.payload.data.' + key, ' / '.join(value)
            if isinstance(value, str) and value.strip():
                return '$.payload.data.' + key, value
    return first(data, TEXT_NAMES)


def clean_url(value):
    if not isinstance(value, str) or not value.startswith(('https://', 'http://')):
        return None
    parts = urlsplit(value)
    # Do not normalize query parameters away: they can distinguish documents.
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ''))


CONTEXT = {'S01', 'S02', 'S03', 'S04', 'S05', 'S06', 'S08', 'S16', 'S26', 'S34',
           'S44', 'S45', 'S47', 'S52', 'S53', 'S54', 'S55', 'S56', 'S57', 'S59',
           'S60', 'S61', 'S62', 'S63', 'S64', 'S65', 'S66', 'S67', 'S68'}
# A single snapshot cannot prove any of these sources changed.
STRUCTURED = {
    'github_sdk': ('technology.release', {'id'}, {'name', 'tag_name'}, 'github'),
    'cpsc_recalls': ('product.recall', {'RecallID', 'RecallNumber'}, {'Title'}, 'cpsc'),
    'fda_ires_recalls': ('product.recall', {'RecallNumber', 'recall_number', 'recallnum'},
                         {'ProductDescription', 'product_description', 'productdescriptiontxt'}, 'fda-recall'),
    'federal_register': ('policy.notice_published', {'document_number'}, {'title'}, 'federal-register'),
    'nih_reporter': ('research.funding_award', {'project_num', 'appl_id'}, {'project_title'}, 'nih'),
    'sam_gov_opportunities': ('procurement.notice', {'noticeId'}, {'title'}, 'sam'),
    'ted_notices': ('procurement.notice', {'publication-number', 'notice-id'}, {'notice-title', 'title'}, 'ted'),
    'usa_spending': ('procurement.award_disclosure', {'generated_internal_id', 'Award ID'},
                      {'Description', 'Award ID'}, 'usaspending'),
    'canada_noc': ('regulatory.authorization_disclosure', {'noc_number', 'NOC_NUMBER', 'drug_identification_number'},
                    {'brand_name', 'BRAND_NAME', 'noc_crp_product_name'}, 'canada-noc'),
    'fda_dd_compliance_actions': ('regulatory.enforcement', {'CaseInjunctionID'}, {'ActionType'}, 'fda-compliance'),
    'fda_dd_import_refusals': ('regulatory.import_refusal', {'ShipmentID'}, {'ProductCodeDescription'}, 'fda-refusal'),
    'fda_dd_inspections_classifications': ('regulatory.inspection_finding', {'InspectionID'}, {'Classification'}, 'fda-inspection'),
    'fda_dd_inspections_citations': ('regulatory.inspection_citation', {'CitationID'}, {'ShortDescription'}, 'fda-inspection-citation'),
}
TEXT_NAMES = {'title', 'Title', 'TITLE', 'name', 'headline', 'summary', 'description', 'text',
              'content', 'body', 'abstract', 'briefTitle', 'officialTitle', 'briefSummary'}
PATTERNS = [
    ('personnel.appointment', r'\b(?:appoint(?:s|ed|ment)?|named|joins?)\b.{0,120}\b(?:CEO|CFO|CTO|chief|officer)\b'),
    ('personnel.departure', r'\b(?:CEO|CFO|CTO|chief|officer)\b.{0,120}\b(?:resign\w*|depart\w*|retir\w*|step\w* down)\b'),
    ('product.launch', r'\b(?:launch(?:es|ed)?|unveil(?:s|ed)?|introduc(?:e|es|ed))\b.{0,120}\b(?:product|platform|robot|chip|battery|therapy|system)\b'),
    ('commercial.partnership', r'\b(?:partnership|licensing agreement|collaboration agreement)\b'),
    ('corporate.financing', r'\b(?:financing|funding round|private placement|public offering)\b'),
    ('corporate.acquisition', r'\b(?:acquires?|(?:announc(?:e|es|ed)|complet(?:e|es|ed)|proposed)\s+(?:the\s+)?acquisition|acquisition\s+of|merger agreement)\b'),
]
ROLE_ROUTES = {
    'patent': ['IP/technology'], 'technology': ['IP/technology', 'Product/commercial'],
    'research': ['Scientific/clinical', 'IP/technology'], 'clinical': ['Scientific/clinical', 'Regulatory'],
    'regulatory': ['Regulatory', 'Scientific/clinical'], 'product': ['Product/commercial'],
    'personnel': ['Leadership/workforce'], 'commercial': ['Product/commercial', 'Financial/market'],
    'corporate': ['Financial/market'], 'procurement': ['Product/commercial', 'Operations/supply chain'],
    'policy': ['Regulatory', 'Product/commercial'],
}


def proposal(event_type, identity, summary, fields, namespace, date=None):
    return {'event_type': event_type, 'identity': identity, 'identity_namespace': namespace,
            'summary': str(summary)[:1000], 'fields': fields, 'proposed_occurrence': date}


def extract(sample):
    """Conservative source-specific milestones + unapproved text suggestions."""
    rec, sid = sample['record'], sample['source_id']
    src, dataset = rec['source'], rec['dataset']
    payload = rec.get('payload', {})
    data = payload.get('data', payload)
    if not isinstance(data, (dict, list)):
        return [], 'needs_evidence', 'unsupported_payload_shape'
    title = title_field(data)
    title_value = title[1] if title else rec.get('source_record_id', '')
    fields = [title] if title else []
    proposals = []
    if dataset in ('patent_office_actions', 'patent_petition_decisions'):
        identity = first(data, {'source_document_id'})
        app = first(data, {'application_number'})
        if identity and app:
            dtype = first(data, {'document_type', 'action_type', 'documentCode'})
            kind = 'patent.petition_decision'
            if dataset == 'patent_office_actions':
                code = str(dtype[1]).upper() if dtype else ''
                kind = ('patent.allowance_notice' if code == 'NOA' else
                        'patent.office_action' if code in {'CTNF', 'CTFR'} else 'patent.prosecution_document')
            day = first(data, {'action_date'})
            proposals.append(proposal(kind, [app[1], identity[1]],
                f'{kind}: application {app[1]}; document {identity[1]}' + (f'; source type {dtype[1]}' if dtype else ''),
                [identity, app] + ([dtype] if dtype else []) + ([day] if day else []), 'uspto-official-document',
                {'value': str(day[1]), 'precision': 'day', 'source_timezone': None} if day else None))
    elif dataset == 'patent_records':
        pub = first(data, {'publication_number'})
        date = first(data, {'publication_date'})
        if pub and date:
            proposals.append(proposal('patent.publication', str(pub[1]).upper(),
                f'Patent publication {pub[1]}: {title_value}', [pub, date] + fields,
                'patent-publication', {'value': str(date[1]), 'precision': 'day', 'source_timezone': None}))
        else:
            return [], 'needs_evidence', 'patent_snapshot_lacks_publication_milestone'
    elif src == 'fda_openfda' and isinstance(data, dict) and data.get('letter_type') and data.get('file_name'):
        # Today's approval_status is not the decision in a historical CRL.
        identity = ('$.payload.data.file_name', data['file_name'])
        letter = ('$.payload.data.letter_type', data['letter_type'])
        proposals.append(proposal('regulatory.letter_disclosure', data['file_name'],
            str(data['letter_type']) + ': ' + str(data.get('application_number', 'unknown application')),
            [identity, letter], 'fda-letter'))
    elif src == 'crossref_proceedings' or src in ('pubmed_abstracts', 'europe_pmc', 'europe_pmc_fulltext'):
        doi = top_field(data, {'DOI', 'doi'})
        pmid = top_field(data, {'pmid', 'PMID'})
        if not doi and isinstance(data, dict) and data.get('article_xml'):
            import xml.etree.ElementTree as ET
            try:
                article = ET.fromstring(data['article_xml'])
                node = article.find(".//PubmedData/ArticleIdList/ArticleId[@IdType='doi']")
                if node is None:
                    node = article.find("./front/article-meta/article-id[@pub-id-type='doi']")
                if node is None:
                    node = article.find(".//ELocationID[@EIdType='doi']")
                if node is not None and node.text:
                    doi = ('$.payload.data.article_xml#doi', node.text)
                node = article.find('.//ArticleTitle')
                if node is None:
                    node = article.find('.//article-title')
                if node is not None:
                    title_value = ''.join(node.itertext())
                    fields = [('$.payload.data.article_xml#article-title', title_value)]
            except ET.ParseError:
                return [], 'needs_evidence', 'invalid_article_xml'
        identity = doi or pmid
        if identity:
            namespace = 'doi' if doi else 'pmid'
            value = str(identity[1]).lower().removeprefix('https://doi.org/')
            proposals.append(proposal('research.publication_disclosure', value, title_value,
                                      [identity] + fields, namespace))
    elif src in STRUCTURED:
        kind, ids, titles, namespace = STRUCTURED[src]
        identity, specific_title = first(data, ids), first(data, titles)
        if identity:
            # IDs such as Github release integers are namespaced by repository URL.
            key = [rec.get('source_url'), identity[1]] if src == 'github_sdk' else identity[1]
            if src == 'fda_dd_inspections_citations':
                inspection = top_field(data, {'InspectionID'})
                if not inspection:
                    return [], 'needs_evidence', 'inspection_id_required_for_citation'
                key = [inspection[1], identity[1]]
            proposals.append(proposal(kind, key, specific_title[1] if specific_title else title_value,
                                      [identity] + ([specific_title] if specific_title else []), namespace))
    elif src == 'clinicaltrials_gov':
        trial = first(data, {'nctId'})
        posted = first(data.get('protocolSection', {}).get('statusModule', {}).get('studyFirstPostDateStruct', {}), {'date'})
        if trial and posted:
            proposals.append(proposal('clinical.registration_disclosure', trial[1], title_value,
                                      [trial, ('$.payload.data.protocolSection.statusModule.studyFirstPostDateStruct.date', posted[1])] + fields,
                                      'clinicaltrials-gov-registration'))
    # Snapshot/context feeds must not turn each refreshed row into a development.
    if not proposals and (sid in CONTEXT or src in {'fda_product_codes', 'doe_storage_program', 'nist_robotics_methods',
                                                   'eia_generator_index', 'cms_payments_catalog', 'trade_screening'}):
        return [], 'context_only', 'snapshot_or_series_requires_comparable_versions_or_explicit_action'
    if not proposals:
        texts = [(path, str(value)) for path, value in walk(data)
                 if path.rsplit('.', 1)[-1] in TEXT_NAMES and isinstance(value, str)]
        for path, text in texts:
            for kind, pattern in PATTERNS:
                match = re.search(pattern, text, re.I | re.S)
                if match:
                    # Source-scoped tentative claim: no automatic cross-source fuzzy merge.
                    locator = [rec.get('record_id'), path, match.start(), kind]
                    snippet = text[max(0, match.start() - 100):match.end() + 180]
                    proposals.append(proposal(kind, locator, snippet, [(path, snippet)], 'text-suggestion'))
        if proposals:
            unique = {}
            for item in proposals:
                unique.setdefault(item['event_type'], item)
            proposals = list(unique.values())
    if not proposals:
        return [], 'needs_evidence', 'no_supported_milestone_rule_or_original_text_requires_review'
    return proposals, 'event_candidate', 'structured_milestone' if proposals[0]['identity_namespace'] != 'text-suggestion' else 'unreviewed_text_suggestion'


def classify(rec, taxonomy):
    """Keep candidate labels distinct from verified, dated classifications."""
    payload = rec.get('payload', {})
    labels = []
    valid = {s['sector_id']: {x['subsector_id'] for x in s['subsectors']} for s in taxonomy['sectors']}
    for item in payload.get('technology_classifications', []):
        sid = item.get('sector_id')
        if sid in valid:
            labels.append({'sector_id': sid, 'subsector_id': None, 'status': 'candidate',
                           'basis': 'source_technology_classification; not independently reviewed'})
    for sid in payload.get('candidate_sector_ids', []):
        if sid in valid and not any(x['sector_id'] == sid for x in labels):
            labels.append({'sector_id': sid, 'subsector_id': None, 'status': 'candidate',
                           'basis': 'collector_search_scope; not established event relevance'})
    return labels


def construct(samples, config, taxonomy):
    events, outcomes = {}, []
    seen = set()
    for sample in samples:
        rec = sample['record']
        obs = rec['observation_id']
        if obs in seen:
            continue
        seen.add(obs)
        proposals, status, reason = extract(sample)
        outcome = {'source_id': sample['source_id'], 'source': rec['source'], 'dataset': rec['dataset'],
                   'observation_id': obs, 'outcome': status, 'reason': reason, 'event_ids': []}
        for item in proposals:
            # Pilot IDs are deterministic within the experiment, never production UUIDs.
            eid = 'test_evt_' + digest([item['event_type'], item['identity_namespace'], item['identity']])
            evidence = {'observation_id': obs, 'record_id': rec.get('record_id'), 'source': rec['source'],
                        'dataset': rec['dataset'], 'source_id': sample['source_id'], 'source_url': rec.get('source_url'),
                        'source_record_id': rec.get('source_record_id'), 'available_at': rec.get('available_at'),
                        'availability_basis': rec.get('availability_basis', 'unknown'),
                        'availability_evidence': rec.get('availability_evidence', []),
                        'ingested_at': rec.get('ingested_at'), 'source_event_at': rec.get('event_at'),
                        'supporting_fields': [{'path': path, 'value': value} for path, value in item['fields']],
                        'provenance': sample['provenance']}
            if eid not in events:
                sectors = classify(rec, taxonomy)
                roles = ROLE_ROUTES.get(item['event_type'].split('.')[0], [])
                events[eid] = {'schema_version': '0.1', 'event_id': eid, 'event_type': item['event_type'],
                    'summary': item['summary'], 'status': 'candidate', 'review_status': 'pending',
                    'match_key': {'namespace': item['identity_namespace'], 'value': item['identity']},
                    'occurrence': item['proposed_occurrence'], 'occurrence_basis': 'explicit_source_field' if item['proposed_occurrence'] else 'unknown',
                    'source_dates_note': 'source_event_at retained per evidence; not automatically the occurrence of this proposed milestone',
                    'entities': {k: rec.get(k, []) for k in ('company_ids', 'product_ids', 'person_ids', 'listing_ids')},
                    'entity_status': 'source_assertions_require_review', 'classifications': sectors,
                    'specialist_routes': [{'role': role, 'status': 'proposed', 'specialist_id': None,
                        'basis': 'event-type routing only; actual sector/subsector layer unresolved'} for role in roles],
                    'missing_fields': ['reviewed_entity_roles', 'verified_sector', 'verified_subsector',
                                       'actual_specialist_layer_ids', 'historical_availability'],
                    'point_in_time_eligible': False, 'model_outputs': None,
                    'extractor_version': VERSION, 'evidence': []}
            events[eid]['evidence'].append(evidence)
            outcome['event_ids'].append(eid)
        outcomes.append(outcome)
    for event in events.values():
        event['evidence'].sort(key=lambda e: e['observation_id'])
        # Same original URL is not independent reporting; unknown lineage stays unknown.
        urls = {clean_url(e.get('source_url')) for e in event['evidence']} - {None}
        event['source_observation_count'] = len(event['evidence'])
        event['distinct_source_urls'] = len(urls)
        event['independent_reporting_count'] = None
        event['event_version_id'] = 'test_ver_' + digest(event)
    return sorted(events.values(), key=lambda e: e['event_id']), outcomes


def verify_capture(directory):
    directory = Path(directory)
    receipt = load(directory / 'capture.json')
    if receipt.get('status') != 'complete':
        raise ValueError('Capture is not complete; failed/interrupted captures are not build inputs')
    if hashlib.sha256((directory / 'samples.jsonl').read_bytes()).hexdigest() != receipt['samples_sha256']:
        raise ValueError('Sample file hash mismatch')
    samples = [json.loads(line) for line in (directory / 'samples.jsonl').read_text().splitlines() if line]
    checked = set()
    for sample in samples:
        for ref in sample['provenance'].values():
            if not isinstance(ref, dict) or 'local_path' not in ref:
                continue
            path = (directory / ref['local_path']).resolve()
            if not path.is_relative_to(directory.resolve()):
                raise ValueError('Artifact path escapes capture')
            if str(path) not in checked:
                body = path.read_bytes()
                if len(body) != ref['bytes'] or hashlib.sha256(body).hexdigest() != ref['sha256']:
                    raise ValueError('Frozen evidence hash mismatch')
                checked.add(str(path))
        proof = sample['provenance']
        if proof['kind'] == 'committed_source_batch':
            body = (directory / proof['batch']['local_path']).read_bytes()
            record = json.loads(body.splitlines()[proof['line_number'] - 1])
            if record != sample['record']:
                raise ValueError('Sample differs from frozen batch')
    return samples


def build(directory):
    directory = Path(directory)
    samples = verify_capture(directory)
    config, taxonomy, inventory = (load(directory / name) for name in ('config.json', 'taxonomy.json', 'inventory.json'))
    events, outcomes = construct(samples, config, taxonomy)
    from jsonschema import Draft7Validator
    validator = Draft7Validator(load(directory / 'event-schema.json'))
    for event in events:
        validator.validate(event)
    identity = digest({'samples': load(directory / 'capture.json')['samples_sha256'],
                       'config': config, 'taxonomy': taxonomy, 'version': VERSION,
                       'schema': load(directory / 'event-schema.json'),
                       'inventory': inventory,
                       'implementation': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    output = directory / 'builds' / identity
    output.mkdir(parents=True, exist_ok=True)
    implementation = Path(__file__).read_bytes()
    implementation_path = output / 'implementation.py'
    if implementation_path.exists() and implementation_path.read_bytes() != implementation:
        raise ValueError('Implementation snapshot mismatch')
    implementation_path.write_bytes(implementation)
    jsonl(output / 'events.jsonl', events)
    jsonl(output / 'outcomes.jsonl', outcomes)
    jsonl(output / 'review-template.jsonl', [{'event_id': e['event_id'], 'event_version_id': e['event_version_id'],
          'decision': None, 'reviewer': None, 'reason': None, 'proposed_changes': {}} for e in events])
    create_sqlite(output / 'events.sqlite3', events, outcomes)
    coverage = []
    capture_rows = load(directory / 'capture.json')['routes']
    for source in inventory['sources']:
        sid = source['source_id']
        matching = [o for o in outcomes if o['source_id'] == sid]
        routes = [r for r in capture_rows if r.get('source_id') == sid]
        coverage.append({'source_id': sid, 'name': source['name'], 'samples': len(matching),
             'outcomes': dict(Counter(o['outcome'] for o in matching)), 'routes': routes,
             'status': 'sampled' if matching else 'no_sample',
             'remaining_requirement': source.get('remaining_requirement'),
             'source_modes': source.get('modes'), 'event_rule': config['source_rules'][sid]})
    counts = dict(Counter(o['outcome'] for o in outcomes))
    findings = {'version': VERSION, 'build_id': identity, 'observations': len(outcomes),
                'events': len(events), 'source_families_total': len(coverage),
                'source_families_sampled': sum(c['samples'] > 0 for c in coverage),
                'provider_dataset_routes_sampled': sum(r['samples'] > 0 for r in capture_rows),
                'outcomes': counts, 'event_types': dict(Counter(e['event_type'] for e in events)),
                'multi_source_events': sum(len({x['source'] for x in e['evidence']}) > 1 for e in events),
                'eligible_for_models': 0, 'production_writes': 0}
    write(output / 'coverage.json', coverage)
    write(output / 'summary.json', findings)
    write_report(output, findings, coverage, events)
    # Export reviewable local Parquet; output includes a SQL recipe, never registers AWS tables.
    parquet_export(output, events, outcomes)
    file_manifest = {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(output.iterdir()) if p.is_file() and p.name != 'manifest.json'}
    write(output / 'manifest.json', {'build_id': identity, 'files': file_manifest,
          'input_capture_sha256': hashlib.sha256((directory / 'capture.json').read_bytes()).hexdigest()})
    print(json.dumps({'build': str(output), **findings}, indent=2))
    return output


def create_sqlite(path, events, outcomes):
    if path.exists():
        with sqlite3.connect(path) as existing:
            actual_events = existing.execute('SELECT event_json FROM events ORDER BY event_id').fetchall()
            actual_outcomes = existing.execute('SELECT outcome_json FROM outcomes ORDER BY observation_id').fetchall()
            actual_evidence = existing.execute('SELECT event_id,evidence_json FROM evidence ORDER BY event_id,observation_id').fetchall()
        expected_evidence = sorted((e['event_id'], encoded(row).decode()) for e in events for row in e['evidence'])
        if (actual_events != [(encoded(e).decode(),) for e in sorted(events, key=lambda e: e['event_id'])] or
            actual_outcomes != [(encoded(o).decode(),) for o in sorted(outcomes, key=lambda o: o['observation_id'])] or
            sorted(actual_evidence) != expected_evidence):
            raise ValueError('Existing SQLite artifact is incomplete or changed')
        return
    conn = sqlite3.connect(path)
    conn.executescript('''CREATE TABLE events(event_id TEXT PRIMARY KEY,event_version_id TEXT,event_type TEXT,status TEXT,summary TEXT,event_json TEXT);
      CREATE TABLE evidence(event_id TEXT,observation_id TEXT,source TEXT,dataset TEXT,evidence_json TEXT,PRIMARY KEY(event_id,observation_id));
      CREATE TABLE outcomes(observation_id TEXT PRIMARY KEY,source_id TEXT,source TEXT,dataset TEXT,outcome TEXT,reason TEXT,outcome_json TEXT);''')
    for e in events:
        conn.execute('INSERT INTO events VALUES (?,?,?,?,?,?)', (e['event_id'], e['event_version_id'], e['event_type'],e['status'], e['summary'], encoded(e).decode()))
        for row in e['evidence']:
            conn.execute('INSERT INTO evidence VALUES (?,?,?,?,?)',(e['event_id'],row['observation_id'],row['source'],row['dataset'],encoded(row).decode()))
    for o in outcomes:
        conn.execute('INSERT INTO outcomes VALUES (?,?,?,?,?,?,?)',(o['observation_id'],o['source_id'],o['source'],o['dataset'],o['outcome'],o['reason'],encoded(o).decode()))
    conn.commit()
    conn.close()


def md(value):
    return str(value).replace('|', '\\|').replace('\n', ' ').replace('\r', ' ')


def write_report(output, summary, coverage, events):
    lines = ['# Event pilot review', '', 'Local experiment; every event remains pending review and excluded from model inputs.', '',
             f"Inspected {summary['observations']} observations across {summary['provider_dataset_routes_sampled']} provider/dataset routes and {summary['source_families_sampled']} of {summary['source_families_total']} source families.",
             f"Constructed {summary['events']} candidate events. Outcomes: `{json.dumps(summary['outcomes'], sort_keys=True)}`.", '',
             'Samples are deliberately small and biased toward recent capture batches; event yield is not an estimate of full-source quality.', '',
             '## Source coverage', '', '| Source | Samples | Outcomes | Gap |', '|---|---:|---|---|']
    for c in coverage:
        gap = c['remaining_requirement'] if not c['samples'] else '; '.join(
            sorted({err['reason'] for r in c['routes'] for err in r.get('errors', [])}))
        lines.append(f"| {md(c['name'])} | {c['samples']} | {md(c['outcomes'])} | {md(gap or '')} |")
    lines += ['', '## Candidate events', '', 'Full source records are frozen in `../../samples.jsonl`; evidence paths in JSON resolve from the capture directory.',
              'Use `events.jsonl` for full evidence fields and `review-template.jsonl` for decisions. A decision records feedback only; it does not publish to production.', '']
    for e in events:
        lines += [f"### {e['event_type']} — {e['event_id']}", '', md(e['summary']), '',
                  f"Evidence observations: {len(e['evidence'])}; sources: {', '.join(sorted({x['source'] for x in e['evidence']}))}.",
                  f"Occurrence: `{json.dumps(e['occurrence'])}`. Proposed sectors: `{json.dumps(e['classifications'], ensure_ascii=False)}`.",
                  'Proposed roles: ' + ', '.join(r['role'] for r in e['specialist_routes']) + '.', '',
                  'Review: Is the action real and sufficiently specific? Are the actor/product, occurrence date, sector/subsector, and affected specialist layers supported? Should this merge with another candidate?', '']
        for evidence in e['evidence']:
            for field in evidence['supporting_fields']:
                lines.append('- `' + field['path'] + '`: ' + md(str(field['value'])[:550]))
        lines.append('')
    lines += ['## Changes to decide before production', '',
              '- Add real entity-role resolution, reviewed event taxonomy/subsector rules and the actual 20 specialist layer IDs; current routes are proposals.',
              '- Expand source-specific structured fields and multilingual prose extraction. Context/no-rule outcomes are deliberate review targets, not accepted events.',
              '- Compare dated source versions before asserting a change; the first captured snapshot is a baseline.',
              '- Collect event-focused follow-up samples after reviewing this broad sample; three arbitrary records rarely include cross-source corroboration.',
              '- Validate same-event versus related milestones and source provenance with reviewer feedback; no fuzzy merges are applied automatically.',
              '- Establish claim/version public availability and correction/retraction handling before training or production publication.',
              '- Implement the RDS outbox, committed event releases, Athena deployment and resource-measured scheduling only after this experiment is reviewed.', '']
    path = output / 'REVIEW.md'
    body = '\n'.join(lines)
    if path.exists() and path.read_text() != body:
        raise ValueError('Review report changed under same build identity')
    path.write_text(body)


def parquet_export(output, events, outcomes):
    import pyarrow as pa
    import pyarrow.parquet as pq
    tables = {
        'events': [{'event_id': e['event_id'], 'event_type': e['event_type'], 'status': e['status'],
                    'summary': e['summary'], 'event_json': encoded(e).decode()} for e in events],
        'outcomes': [{'observation_id': o['observation_id'], 'source_id': o['source_id'], 'source': o['source'],
                      'dataset': o['dataset'], 'outcome': o['outcome'], 'reason': o['reason']} for o in outcomes]}
    columns = {'events': ['event_id','event_type','status','summary','event_json'],
               'outcomes': ['observation_id','source_id','source','dataset','outcome','reason']}
    for name, rows in tables.items():
        schema = pa.schema([(n, pa.string()) for n in columns[name]])
        table = pa.Table.from_pylist(rows, schema=schema)
        path = output / (name + '.parquet')
        if not path.exists():
            pq.write_table(table, path, compression='snappy')
        if not pq.read_table(path).equals(table):
            raise ValueError('Parquet round-trip mismatch')
    sql = """-- LOCAL SQLite queries (open events.sqlite3); this file does not provision Athena.
SELECT source_id,source,dataset,outcome,count(*) FROM outcomes GROUP BY 1,2,3,4;
SELECT e.event_id,e.event_type,e.summary,count(d.observation_id) AS evidence_count
FROM events e JOIN evidence d ON e.event_id=d.event_id GROUP BY 1,2,3;
-- The two local Parquet exports can later be published under an isolated
-- experiments/events/<capture>/<build>/ prefix and a separate optima_events_pilot
-- Athena database. No objects, catalog entries or workgroups are deployed by this tool.
"""
    (output / 'queries.sql').write_text(sql)


def record_feedback(directory, decisions):
    """Store validated immutable feedback without mutating extracted candidates."""
    directory = Path(directory)
    candidates = {e['event_id']: e for e in (json.loads(s) for s in (directory / 'events.jsonl').read_text().splitlines())}
    rows = [json.loads(line) for line in Path(decisions).read_text().splitlines() if line]
    seen = set()
    if not rows:
        raise ValueError('Empty feedback file')
    for row in rows:
        event = candidates.get(row.get('event_id'))
        if not event or event['event_version_id'] != row.get('event_version_id'):
            raise ValueError('Unknown event or stale version')
        if row['event_id'] in seen:
            raise ValueError('Duplicate decision')
        seen.add(row['event_id'])
        if row.get('decision') not in {'accept_candidate', 'reject', 'revise', 'merge_proposal', 'needs_evidence'}:
            raise ValueError('Choose an explicit pilot decision')
        if not all(isinstance(row.get(k), str) and row[k].strip() for k in ('reviewer', 'reason')):
            raise ValueError('Reviewer and reason are required')
    target = directory / 'feedback' / (digest(rows) + '.jsonl')
    jsonl(target, rows)
    return target


def compare_builds(before, after):
    def read_events(path):
        return {e['event_id']: e for e in (json.loads(line) for line in
                (Path(path) / 'events.jsonl').read_text().splitlines() if line)}
    old, new = read_events(before), read_events(after)
    return {'before': str(before), 'after': str(after),
            'added': sorted(new.keys() - old.keys()), 'removed': sorted(old.keys() - new.keys()),
            'changed': [{'event_id': key, 'fields': sorted(field for field in old[key].keys() | new[key].keys()
                        if old[key].get(field) != new[key].get(field))}
                        for key in sorted(old.keys() & new.keys()) if old[key] != new[key]],
            'outcomes_before': load(Path(before) / 'summary.json')['outcomes'],
            'outcomes_after': load(Path(after) / 'summary.json')['outcomes']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT / 'config/event-pilot.v1.json')
    sub = parser.add_subparsers(dest='command', required=True)
    cap = sub.add_parser('capture'); cap.add_argument('--output', type=Path, required=True)
    replay = sub.add_parser('build'); replay.add_argument('--capture', type=Path, required=True)
    review = sub.add_parser('feedback'); review.add_argument('--build', type=Path, required=True); review.add_argument('--decisions', type=Path, required=True)
    compare = sub.add_parser('compare'); compare.add_argument('--before', type=Path, required=True); compare.add_argument('--after', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'capture':
        config = load(args.config)
        capture(args.output, config)
    elif args.command == 'build':
        build(args.capture)
    elif args.command == 'feedback':
        print(record_feedback(args.build, args.decisions))
    else:
        print(json.dumps(compare_builds(args.before, args.after), indent=2))


if __name__ == '__main__':
    main()
