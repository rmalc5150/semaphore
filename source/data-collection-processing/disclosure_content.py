"""Preserve full disclosure content with file/page provenance and retrieval chunks."""
import binascii
import hashlib
import io
import json
import re

from collection_storage import now, write_checked
from regulatory_collection import require
from research_contract import digest

VERSION = 'disclosure-content-1.0'


def _pdf(raw, filename, kind):
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(raw))
    if reader.is_encrypted:
        require(bool(reader.decrypt('')), 'encrypted_document_requires_review')
    require(reader.pages, 'empty_or_unparseable_document')
    return [{'filename': filename, 'document_type': kind, 'page': i + 1,
             'text': page.extract_text() or '', 'classification_eligible': True}
            for i, page in enumerate(reader.pages)]


def extract(raw, parent):
    from disclosure_collection import visible_text
    from edinet_pipeline import decode_text
    documents, skipped = [], []
    if raw.startswith(b'%PDF-'):
        documents = _pdf(raw, 'report.pdf', parent.get('payload', {}).get('form'))
        format_name = 'pdf'
    else:
        if parent['source'] == 'sec_edgar':
            try:
                text, encoding = raw.decode('utf-8-sig'), 'utf-8'
            except UnicodeDecodeError:
                text, encoding = raw.decode('cp1252'), 'cp1252'
        else:
            text, encoding = decode_text(raw)
        require(not any(x in text.lower() for x in ('your request originates from an undeclared automated tool',
            'request rate threshold exceeded', '<title>access denied')), 'document_access_blocked')
        if parent['source'] == 'sec_edgar':
            accession = re.search(r'ACCESSION NUMBER:\s*([0-9-]+)', text)
            require(accession is not None and accession.group(1) == parent['source_record_id'], 'sec_document_identity_mismatch')
            blocks = re.findall(r'<DOCUMENT>(.*?)</DOCUMENT>', text, re.S | re.I)
            require(blocks, 'sec_submission_documents_missing')
            for index, block in enumerate(blocks):
                kind = re.search(r'<TYPE>([^\r\n<]+)', block, re.I)
                body = re.search(r'<TEXT>(.*?)</TEXT>', block, re.S | re.I)
                filename = re.search(r'<FILENAME>([^\r\n<]+)', block, re.I)
                require(kind is not None and body is not None, 'sec_submission_block_incomplete')
                kind, body = kind.group(1).strip(), body.group(1)
                filename = filename.group(1).strip() if filename else f'document-{index + 1}'
                binary = re.search(r'(?m)^begin \d{3} [^\r\n]+\r?\n(.*?)^end\s*$', body, re.S | re.M)
                if binary:
                    if not filename.lower().endswith('.pdf'):
                        skipped.append({'filename': filename, 'document_type': kind,
                            'reason': 'binary_preserved_in_original_submission', 'encoded_characters': len(body)})
                        continue
                    decoded_parts = []
                    for line in binary.group(1).splitlines():
                        if not line.strip():
                            continue
                        encoded = line.encode('ascii')
                        try:
                            decoded_parts.append(binascii.a2b_uu(encoded))
                        except binascii.Error:
                            # SEC submissions may pad uuencoded lines. Match the
                            # standard uu decoder's declared-length handling.
                            meaningful = (((encoded[0] - 32) & 63) * 4 + 5) // 3
                            decoded_parts.append(binascii.a2b_uu(encoded[:meaningful]))
                    decoded = b''.join(decoded_parts)
                    if decoded.startswith(b'%PDF-'):
                        documents.extend(_pdf(decoded, filename, kind))
                    else:
                        skipped.append({'filename': filename, 'document_type': kind, 'reason': 'binary_preserved_in_original_submission',
                                        'bytes': len(decoded)})
                    continue
                structured = kind.upper().startswith(('EX-101', 'EX-104', 'XML')) or filename.lower().endswith(('.xbrl', '.xml', '.xsd'))
                documents.append({'filename': filename, 'document_type': kind, 'page': None,
                    'text': body if structured else visible_text(body), 'classification_eligible': not structured,
                    'encoding': encoding})
            format_name = 'sec_submission'
        else:
            documents = [{'filename': 'report.html', 'document_type': None, 'page': None,
                'text': visible_text(text), 'classification_eligible': True, 'encoding': encoding}]
            format_name = 'html_or_text'
    parts, offset, chunks, spans = [], 0, [], []
    for index, document in enumerate(documents):
        document['document_id'] = 'doc_' + digest({'index': index, 'filename': document['filename'], 'page': document['page']})
        document['status'] = 'extracted' if document['text'].strip() else 'no_extractable_text'
        document['text_sha256'] = hashlib.sha256(document['text'].encode()).hexdigest()
        if document['classification_eligible'] and document['text'].strip():
            if parts:
                offset += 1
            spans.append({'document_id': document['document_id'], 'filename': document['filename'],
                'document_type': document['document_type'], 'page': document['page'], 'start': offset,
                'end': offset + len(document['text'])})
            parts.append(document['text'])
            offset += len(document['text'])
        for begin in range(0, len(document['text']), 3700):
            end = min(begin + 4000, len(document['text']))
            chunks.append({'chunk_id': 'chunk_' + digest({'document': document['document_id'], 'start': begin,
                'end': end, 'text_sha256': document['text_sha256']}), 'document_id': document['document_id'],
                'start': begin, 'end': end, 'filename': document['filename'], 'page': document['page']})
    text = '\n'.join(parts)
    info = {'format': format_name, 'documents': len(documents), 'text_documents': sum(bool(d['text'].strip()) for d in documents),
        'skipped_files': skipped, 'ocr_performed': False, 'content_version': VERSION}
    if format_name == 'pdf':
        info.update(pages=len(documents), skipped_pages=[d['page'] for d in documents if not d['text'].strip()],
            text_pages=sum(bool(d['text'].strip()) for d in documents), skipped_page_reason='no_extractable_text')
    if format_name != 'pdf':
        require(len(text.strip()) >= 40, 'empty_or_unparseable_document')
    return {'version': VERSION, 'text': text, 'documents': documents, 'chunks': chunks, 'document_spans': spans,
        'extraction': info, 'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'textless_pdf_pages': sum(d['page'] is not None and not d['text'].strip() for d in documents)}


def persist(store, content, source_url):
    raw = (json.dumps(content, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8')
    checksum = hashlib.sha256(raw).hexdigest()
    key = 'source_documents/disclosure_content/' + checksum
    write_checked(store, key, raw, content_type='application/json')
    return {'key': key, 'sha256': checksum, 'source_url': source_url, 'retrieved_at': now(),
            'bytes': len(raw), 'content_version': VERSION}


def signals(excerpt):
    """Literal passage signals only: no event completion or economics are verified."""
    return {'amount_mentions': [m.group(0) for m in re.finditer(r'(?:US\$|HK\$|USD|EUR|JPY|RMB|\$|€|£)\s*[\d,.]+(?:\s*(?:million|billion|thousand))?', excerpt, re.I)],
        'date_mentions': re.findall(r'\b(?:\d{4}-\d{2}-\d{2}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b', excerpt),
        'party_mentions': re.findall(r'\b(?:[A-Z][\w&.-]*\s+){1,5}(?:Inc\.?|LLC|Ltd\.?|Corporation|plc)\b', excerpt),
        'proposed_language': bool(re.search(r'\b(propos\w*|intend\w*|plan\w*|pending|subject to)\b', excerpt, re.I)),
        'completion_language': bool(re.search(r'\b(completed|closed|consummated)\b', excerpt, re.I)),
        'negation_language': bool(re.search(r'\b(no|not|never|terminated|cancelled|canceled)\b', excerpt, re.I)),
        'verification_status': 'unreviewed_passage_signals'}
