"""Validate FR API listings and full notices against their saved originals."""
import hashlib
import json
import re
from functools import lru_cache
from urllib.parse import parse_qs, urlsplit
from lxml import etree

from federal_register_parser import parse_notice


class ProviderError(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise ProviderError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


@lru_cache(maxsize=1)
def decode(body):
    try:
        return json.loads(body)
    except (ValueError, UnicodeError):
        raise ProviderError('fr_invalid_original_json') from None


def api_url(url, path):
    u = urlsplit(url)
    require(u.scheme == 'https' and u.netloc == 'www.federalregister.gov' and u.path == path
            and not u.fragment, 'fr_untrusted_api_url')
    q = parse_qs(u.query)
    require(not any(k.split('[')[0] in ('fields', 'select', 'callback') for k in q), 'fr_projected_or_wrapped_response')
    return q


def validate_listing(body, record, url):
    q = api_url(url, '/api/v1/documents.json')
    data = record.get('payload', {}).get('data', {})
    require(isinstance(data, dict) and data.get('document_number') == record.get('source_record_id'), 'fr_listing_identity_mismatch')
    result = decode(body)
    require(isinstance(result, dict) and isinstance(result.get('results'), list)
            and type(result.get('count')) is int and result['count'] >= len(result['results']), 'fr_invalid_search_response')
    matches = [r for r in result['results'] if r.get('document_number') == data['document_number']]
    require(len(matches) == 1 and canonical(matches[0]) == canonical(data), 'fr_listing_differs_from_original')
    require(data.get('title') and data.get('type') and data.get('publication_date')
            and isinstance(data.get('agencies'), list), 'fr_listing_content_missing')
    require(record.get('source_url') == data.get('html_url'), 'fr_listing_url_mismatch')
    require((record.get('event_at') or {}).get('value') == data['publication_date'], 'fr_listing_publication_date_mismatch')
    for k, v in record.get('payload', {}).get('scope', {}).get('query', {}).items():
        require(q.get(k) == ([str(x) for x in v] if isinstance(v, list) else [str(v)]), 'fr_search_scope_mismatch')
    require(q.get('conditions[publication_date][gte]', [''])[0] <= data['publication_date']
            <= q.get('conditions[publication_date][lte]', ['9999'])[0], 'fr_listing_outside_requested_dates')
    return {'provider': 'Federal Register API', 'record_type': 'federal_register_notice_listing',
            'document_number': data['document_number'], 'retained_provider_fields': len(data),
            'scope': 'Entire returned search-result record; full notice text and official PDF belong to the companion document stream.'}


def artifact(ref, bucket, kind, size, info):
    key = ref.get('key', '')
    key = key if key.startswith('research-data/') else 'research-data/' + key
    return {'artifact_kind': kind, 's3_uri': 's3://' + bucket + '/' + key,
            'sha256': ref['sha256'], 'bytes': size, 'origin': 'first_party_source',
            'source_url': ref['source_url'], 'retrieved_at': ref.get('retrieved_at'), 'validation': info}


def original(s3, bucket, ref, source='federal_register_documents'):
    from metadata_engine.evidence import object_bytes
    key = ref.get('key', '')
    key = key if key.startswith('research-data/') else 'research-data/' + key
    require(key.startswith('research-data/source_documents/' + source + '/')
            and re.fullmatch(r'[a-f0-9]{64}', ref.get('sha256', '')), 'fr_invalid_original_reference')
    return object_bytes(s3, bucket, key, expected=ref['sha256'])


def pdf(s3, bucket, ref, number, metadata):
    """Check even the 115 MiB official notice without loading it into RAM."""
    url = ref.get('source_url', '')
    u = urlsplit(url)
    require(url == metadata.get('pdf_url') and u.scheme == 'https' and u.netloc in ('www.govinfo.gov', 'www.gpo.gov')
            and u.path.endswith('/' + number + '.pdf') and not u.fragment, 'fr_official_pdf_origin_or_identity_mismatch')
    key = ref.get('key', '')
    key = key if key.startswith('research-data/') else 'research-data/' + key
    require(key.startswith('research-data/source_documents/federal_register_documents/')
            and re.fullmatch(r'[a-f0-9]{64}', ref.get('sha256', '')), 'fr_invalid_pdf_reference')
    response = s3.get_object(Bucket=bucket, Key=key)
    length = response.get('ContentLength');sha = hashlib.sha256();count = 0;prefix = b'';tail = b''
    try:
        require(length is None or 0 < length <= 128*1024*1024, 'fr_pdf_size_limit')
        while True:
            block = response['Body'].read(1024*1024)
            if not block:break
            count += len(block)
            require(count <= 128*1024*1024, 'fr_pdf_size_limit')
            if not prefix:prefix = block[:8]
            tail = (tail + block)[-4096:];sha.update(block)
    finally:response['Body'].close()
    require((length is None or count == length) and count > 0, 'fr_pdf_truncated_download')
    require(sha.hexdigest() == ref['sha256'], 'fr_pdf_checksum_mismatch')
    require(prefix.startswith(b'%PDF-') and b'%%EOF' in tail, 'fr_pdf_invalid_or_truncated')
    return artifact(ref, bucket, 'official_pdf', count,
                    {'provider': 'Federal Register official PDF', 'document_number': number,
                     'scope': 'Official PDF source, full-byte checksum and framing; XML/HTML text validated separately.'})


def document_evidence(record, s3, bucket):
    from metadata_engine.evidence import RawFailure
    payload = record.get('payload', {});data = payload.get('data', {}).get('enrichment', {})
    number = record.get('source_record_id', '')
    require(re.fullmatch(r'(?:[A-Z]\d-)?\d{2,4}-\d{1,6}', number) and data.get('document_number') == number,
            'fr_document_identity_mismatch')
    require(data.get('retrieval_status') == 'complete' and data.get('official_pdf_status') == 'downloaded',
            'fr_full_notice_capture_incomplete')
    refs = payload.get('source_evidence', [])
    metadata_url = 'https://www.federalregister.gov/api/v1/documents/' + number + '.json'
    metadata_ref = next((r for r in refs if r.get('source_url') == metadata_url), None)
    require(metadata_ref is not None, 'fr_original_detail_metadata_missing')
    api_url(metadata_url, '/api/v1/documents/' + number + '.json')
    raw = original(s3, bucket, metadata_ref);metadata = decode(raw)
    require(metadata.get('document_number') == number and metadata.get('html_url') == record.get('source_url'),
            'fr_detail_metadata_identity_mismatch')
    require((record.get('event_at') or {}).get('value') == metadata.get('publication_date'), 'fr_document_publication_date_mismatch')
    for field in ('document_number', 'html_url', 'publication_date', 'title', 'type'):
        listing = payload.get('scope', {}).get('listing', {})
        if field in listing:require(listing[field] == metadata.get(field), 'fr_parent_detail_identity_mismatch')
    full = data
    if data.get('extraction_storage') == 'full_extraction_externalized_to_source_reference':
        full = decode(original(s3, bucket, data.get('full_extraction_source', {}), 'federal_register_extractions'))
        for k, v in full.items():
            if k in data:require(canonical(data[k]) == canonical(v), 'fr_external_extraction_metadata_mismatch')
    body_ref = full.get('body_source', {})
    kind = full.get('extraction_format')
    require(kind in ('xml', 'html') and body_ref.get('source_url') == metadata.get('full_text_xml_url' if kind == 'xml' else 'body_html_url'),
            'fr_body_metadata_url_mismatch')
    require(body_ref in refs, 'fr_original_body_reference_missing')
    u = urlsplit(body_ref['source_url'])
    require(u.scheme == 'https' and u.netloc in ('www.federalregister.gov','www.govinfo.gov','www.gpo.gov')
            and number in u.path, 'fr_untrusted_body_url')
    body = original(s3, bucket, body_ref)
    try:parsed = parse_notice(body, metadata, body_ref, kind)
    except (ValueError, etree.XMLSyntaxError) as error:
        raise RawFailure('fr_original_body_parse_failed:' + str(error)[:160]) from None
    for k, v in parsed.items():
        require(k in full and canonical(full[k]) == canonical(v), 'fr_saved_extraction_differs_from_original:' + k)
    require(parsed['full_text'].strip(), 'fr_empty_full_notice')
    pdf_ref = full.get('official_pdf_source', {})
    require(pdf_ref in refs, 'fr_original_official_pdf_reference_missing')
    info = {'provider': 'Federal Register full notice', 'record_type': 'federal_register_notice',
            'document_number': number, 'full_text_characters': len(parsed['full_text']),
            'paragraphs': len(parsed['paragraphs']), 'chemical_provisions': len(parsed['chemical_provisions']),
            'scope': 'Original detail metadata, complete saved XML/HTML extraction and official PDF; not a current-law or product-applicability determination.'}
    return [artifact(metadata_ref, bucket, 'provider_record', len(raw), info),
            artifact(body_ref, bucket, 'notice_body', len(body), info), pdf(s3, bucket, pdf_ref, number, metadata)]


def evidence(record, s3, bucket):
    from metadata_engine.evidence import RawFailure
    try:
        if record.get('source') == 'federal_register_documents':return document_evidence(record, s3, bucket)
        errors = []
        for ref in record.get('payload', {}).get('source_evidence', []):
            if urlsplit(ref.get('source_url', '')).path != '/api/v1/documents.json':continue
            raw = original(s3, bucket, ref, 'federal_register')
            try:info = validate_listing(raw, record, ref['source_url'])
            except ProviderError as error:errors.append(str(error));continue
            return [artifact(ref, bucket, 'provider_record', len(raw), info)]
        raise ProviderError(errors[0] if errors else 'fr_matching_original_search_response_missing')
    except ProviderError as error:
        raise RawFailure(str(error)) from None
