"""Parse and verify Canadian SEDI public issuer event history exports."""
from collections import Counter
from datetime import date, datetime
from functools import lru_cache
import io
import re

SOURCE = 'market_source_253'
DATASET = 'issuer_events'
ADAPTER = 'sedi_issuer_events'
SOURCE_URL = 'https://www.sedi.ca/sedi/'
VERSION = '1.0.0'

FILING = re.compile(r'(\d{4}-\d{2}-\d{2})\s{2,}(.+?)\s{2,}(\d{4}-\d{2}-\d{2})')
RANGE = re.compile(r'Date range of filing\s*:\s*(.+?)\s+-\s+(.+)')
HEADING = re.compile(r'Issuer report history\s+-\s+View results\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2} ET)')


def normalized(text):
    return ' '.join(text.replace('\x7f', ' ').split())


def report_date(text):
    return datetime.strptime(text, '%B %d, %Y').date().isoformat()


def parse_pages(pages):
    issuer = current = field = span = generated = None
    rows = []
    occurrences = Counter()
    for page, contents in enumerate(pages, 1):
        page_row = 0
        for line in contents.splitlines():
            text = line.strip()
            if not text or re.fullmatch(r'-\d+-', text):
                continue
            if text.startswith('Filing Date ') and text.endswith('Effective Date'):
                continue
            if re.fullmatch(r'\(YYYY-MM-DD\)\s+\(YYYY-MM-DD\)', text):
                continue
            if match := HEADING.fullmatch(text):
                if generated is not None:
                    raise ValueError('unexpected_repeated_sedi_report_heading')
                generated = match[1]
                continue
            if match := RANGE.fullmatch(text):
                if span is not None:
                    raise ValueError('unexpected_repeated_sedi_filing_range')
                span = tuple(report_date(part) for part in match.groups())
                continue
            at_margin = len(line) - len(line.lstrip()) <= 3
            if at_margin and text.startswith('Issuer Name:'):
                issuer = normalized(text.removeprefix('Issuer Name:'))
                current = field = None
                continue
            if at_margin and (match := FILING.fullmatch(text)):
                if not issuer or not span or not span[0] <= match[1] <= span[1]:
                    raise ValueError('sedi_filing_outside_report_or_missing_issuer')
                date.fromisoformat(match[1])
                date.fromisoformat(match[3])
                page_row += 1
                current = {
                    'issuer_name': issuer, 'filing_date': match[1], 'event_type': normalized(match[2]),
                    'effective_date': match[3], 'pdf_page': page, 'pdf_page_row': page_row,
                }
                rows.append(current)
                field = None
                continue
            if at_margin and text.startswith(('Title:', 'Details:')):
                label, body = text.split(':', 1)
                field = label.lower()
                if current is None or field in current:
                    raise ValueError('sedi_unexpected_event_field')
                current[field] = [normalized(body)]
                continue
            if current is None or field is None or at_margin:
                raise ValueError(f'sedi_unrecognized_pdf_layout_on_page_{page}')
            current[field].append(normalized(text))

    if not generated or not span or span[0] > span[1] or not rows:
        raise ValueError('sedi_native_report_or_issuer_events_missing')
    for row in rows:
        for name in ('title', 'details'):
            if name not in row:
                raise ValueError('sedi_missing_event_field')
            row[name] = '\n'.join(row[name]).strip()
        key = tuple(row[field] for field in ('issuer_name', 'filing_date', 'event_type', 'effective_date', 'title', 'details'))
        occurrences[key] += 1
        row['report_occurrence'] = occurrences[key]
    return {'first_day': span[0], 'last_day': span[1], 'report_generated_at_et': generated, 'rows': rows}


def parse_pdf(body):
    from pypdf import PdfReader

    if not body.startswith(b'%PDF-') or b'%%EOF' not in body[-4096:]:
        raise ValueError('sedi_original_pdf_missing_or_truncated')
    document = PdfReader(io.BytesIO(body))
    return parse_pages(page.extract_text(extraction_mode='layout') for page in document.pages)


@lru_cache(maxsize=2)
def verified_rows(s3, bucket, key, sha):
    from metadata_engine.evidence import object_bytes

    report = parse_pdf(object_bytes(s3, bucket, key, expected=sha))
    return {(row['pdf_page'], row['pdf_page_row']): row for row in report['rows']}


def evidence(record, s3, bucket):
    from metadata_engine.evidence import RawFailure, s3_key
    from market_source_capture import MARKET

    payload = record['payload']
    data = payload['data']
    refs = payload.get('source_evidence', [])
    if len(refs) != 1 or record['dataset'] != DATASET:
        raise RawFailure('sedi_original_report_reference_missing')
    ref = refs[0]
    key = s3_key(ref['s3_uri'], bucket)
    prefix = f'{MARKET}/historical-exports/{SOURCE}/{DATASET}/'
    sha = ref.get('sha256', '')
    if (ref.get('source_url') != SOURCE_URL or not re.fullmatch(r'[0-9a-f]{64}', sha)
            or not key.startswith(prefix) or not key.endswith(f'/{sha}.pdf')):
        raise RawFailure('sedi_original_report_reference_invalid')
    try:
        rows = verified_rows(s3, bucket, key, sha)
    except ValueError as error:
        raise RawFailure('sedi_original_report_invalid') from error
    locator = (data['pdf_page'], data['pdf_page_row'])
    if rows.get(locator) != data:
        raise RawFailure('sedi_event_does_not_match_original_pdf')
    return [{
        'artifact_kind': 'document', 's3_uri': ref['s3_uri'], 'sha256': sha,
        'origin': 'first_party_source', 'representation': 'Original SEDI issuer event history PDF',
        'validation': {'provider': 'SEDI', 'pdf_page': locator[0], 'pdf_page_row': locator[1],
                       'filing_date': data['filing_date'], 'effective_date': data['effective_date']},
    }]


def contract():
    return {
        'source_key': SOURCE, 'catalog_entries': [253], 'datasets': [DATASET], 'state': 'enabled',
        'contract_version': VERSION, 'adapter': ADAPTER, 'adapter_version': VERSION,
        'record_kind': 'issuer_event', 'completeness_scope': 'SEDI issuer event history report row',
        'license_policy_id': 'source-rights-review-required', 'allowed_hosts': ['www.sedi.ca'],
        'raw_requirements': {
            'version': VERSION, 'minimum_completeness': 'complete', 'required_artifact_kinds': ['document'],
            'forbidden_shortcuts': ['metadata_only', 'report_cover_without_filing_row'],
        },
    }
