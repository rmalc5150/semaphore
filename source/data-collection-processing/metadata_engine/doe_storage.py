"""DOE original-document and source-attributed extraction validation."""
import hashlib
import json
from functools import lru_cache
from doe_storage_enrichment import canonical, parse_document, facts, relevant, VERSION
from research_contract import digest

SOURCES = ('doe_storage_program', 'doe_storage_documents', 'doe_storage_benchmarks', 'doe_storage_funding')


@lru_cache(maxsize=1)
def parsed(body, url):
    # Match the capture contract. Limits are retained, never called full extraction.
    require(not body.startswith(b'%PDF-') or b'%%EOF' in body[-4096:], 'truncated_pdf')
    return parse_document(body, url, max_pages=250, max_cells=30000)


def require(ok, reason):
    from metadata_engine.evidence import RawFailure
    if not ok:
        raise RawFailure('doe_' + reason)


def original(ref, s3, bucket, prefix, public=False):
    from metadata_engine.evidence import object_bytes, s3_key
    require(bool(ref.get('sha256')), 'checksum_missing')
    key = ref.get('key') or s3_key(ref.get('s3_uri', ''), bucket)
    key = key if key.startswith('research-data/') else 'research-data/' + key
    expected = ('research-data/constellation-backfill/public-capture/objects/doe_storage_program/'
                if public else 'research-data/source_documents/' + prefix + '/')
    require(key.startswith(expected), 'unexpected_artifact_prefix')
    return object_bytes(s3, bucket, key, expected=ref['sha256']), key


def evidence(record, s3, bucket):
    from metadata_engine.evidence import RawFailure
    source = record['source'];payload = record.get('payload', {});data = payload.get('data', {})
    url = record.get('source_url', '')
    require(canonical(url) == url, 'untrusted_document_url')
    prefix = 'doe_storage_program' if source == 'doe_storage_program' else 'doe_storage_documents'
    public = source == 'doe_storage_program' and payload.get('record_type') == 'original_public_document'
    ref = next((r for r in payload.get('source_evidence', []) if r.get('source_url') == url), None)
    require(ref is not None, 'matching_original_missing')
    body, key = original(ref, s3, bucket, prefix, public=public)
    try:
        document = parsed(body, url)
    except Exception as error:
        raise RawFailure('doe_original_parse_failed:' + type(error).__name__) from None
    require(document.get('kind') in ('html', 'pdf', 'csv', 'xlsx')
            and len(document.get('text', '').strip()) >= 100
            and document.get('extraction_status') == 'text_extracted', 'substantive_document_or_ocr_required')
    identity = digest(url) if source == 'doe_storage_program' else digest([url, document['semantic_hash']])
    require(record.get('source_record_id') == identity, 'document_identity_mismatch')
    info = {'provider': 'DOE storage originals', 'scope': 'Complete original bytes and matched declared extraction; source statements require units, stage and entity review; not exhaustive history.',
            'semantic_hash': document['semantic_hash'], 'extraction_limits': document['limits']}
    if source == 'doe_storage_program':
        if public:
            require(document['kind'] != 'html' and relevant(url, document['title']), 'public_document_outside_storage_scope')
        # Old landing stubs are reparsed in the labelled output; raw batches stay immutable.
        legacy = data.get('document_kind') == 'official source discovery page'
        require(legacy or data == document, 'landing_extraction_differs_from_original')
        info.update(record_type='storage_original_document' if public else 'storage_program_page', parsed_document=document)
    else:
        extraction_ref = payload.get('extraction_reference', {})
        extraction_body, extraction_key = original(extraction_ref, s3, bucket, 'doe_storage_extractions')
        extraction = json.loads(extraction_body)
        require(extraction.get('version') == VERSION == extraction_ref.get('version')
                and extraction.get('source_url') == url == extraction_ref.get('source_url')
                and extraction.get('raw_sha256') == ref['sha256'] == extraction_ref.get('raw_sha256'), 'extraction_original_link_mismatch')
        require(extraction.get('document') == document, 'saved_extraction_differs_from_original')
        extracted_facts = facts(document)
        require(extraction.get('facts') == extracted_facts, 'saved_facts_differ_from_original')
        if source == 'doe_storage_documents':
            expected = {k: document[k] for k in ('title', 'kind', 'source_date', 'semantic_hash', 'extraction_status', 'limits', 'technologies', 'links')}
            expected.update(section_count=len(document['sections']), table_count=len(document['tables']),
                            fact_counts={k: len(extracted_facts[k]) for k in ('technical', 'funding')}, fact_limits=extracted_facts['limits'])
            require(data == expected, 'document_summary_mismatch')
            info['record_type'] = 'storage_original_document'
        else:
            category = 'technical' if source == 'doe_storage_benchmarks' else 'funding'
            references = extracted_facts[category + '_tables']
            tables = [{'table_index': r['table_index'], 'table': document['tables'][r['table_index']]} for r in references[:3]]
            if data.get('table_index_note') == 'Full extracted tables in extraction_reference; inline preview omitted for size':
                tables = []
            require(data.get('document_id') == record['source_record_id']
                    and data.get('facts') == extracted_facts[category]
                    and data.get('table_references') == references
                    and data.get('tables') == tables
                    and data.get('title') == document['title'] and data.get('source_date') == document['source_date']
                    and data.get('limits') == extracted_facts['limits'], 'source_attributed_facts_mismatch')
            info['record_type'] = 'storage_technical_evidence' if category == 'technical' else 'storage_funding_evidence'
        info['extraction_reference'] = {'s3_uri': 's3://' + bucket + '/' + extraction_key, 'sha256': extraction_ref['sha256']}
    return [{'artifact_kind': 'provider_record', 's3_uri': 's3://' + bucket + '/' + key,
             'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body), 'origin': 'first_party_source',
             'source_url': url, 'retrieved_at': ref.get('retrieved_at'), 'validation': info}]


def from_public_receipt(receipt, s3, bucket):
    require(receipt.get('artifact_kind') == 'public_document', 'discovery_is_not_document')
    url = receipt.get('source_url', '')
    require(canonical(url) == url, 'untrusted_document_url')
    ref = {'s3_uri': receipt['artifact_uri'], 'sha256': receipt['sha256'], 'source_url': url,
           'retrieved_at': receipt['retrieved_at']}
    body, key = original(ref, s3, bucket, 'doe_storage_program', public=True)
    document = parsed(body, url)
    record = {'source': 'doe_storage_program', 'dataset': 'specialist_inputs',
              'source_record_id': digest(url), 'source_record_id_basis': 'derived',
              'source_url': url, 'ingested_at': receipt['retrieved_at'], 'available_at': None,
              'payload': {'data': document, 'source_evidence': [ref], 'record_type': 'original_public_document',
                          'coverage_note': 'Original public storage document; extraction limits retained; not historical availability or certified performance.'}}
    evidence(record, s3, bucket)
    return [record]
