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


def issuer_removed_notice(raw, parent):
    from urllib.parse import urlsplit
    from disclosure_collection import visible_text
    url = urlsplit(parent.get('source_url', ''))
    return (parent.get('source') == 'hkex_news' and url.scheme == 'https'
            and url.hostname == 'www1.hkexnews.hk' and url.path == '/listedco/listconews/sehk/dod/en.html'
            and 'The document that you are looking for has been removed by the listed issuer and is no longer available.'
            in visible_text(raw.decode('utf-8', errors='replace')))


def _word_documents(raw):
    import zipfile
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.infolist()
        require(len(members) <= 10000 and sum(m.file_size for m in members) <= 64 * 1024 * 1024,
                'disclosure_workbook_size_limit')
        if 'word/document.xml' not in archive.namelist():
            return None
        require('[Content_Types].xml' in archive.namelist(), 'disclosure_unsupported_zip')
        names = [n for n in archive.namelist() if re.fullmatch(r'word/(document|header[0-9]+|footer[0-9]+|footnotes|endnotes)\.xml', n)]
        documents = []
        ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        for name in sorted(names, key=lambda n: (n != 'word/document.xml', n)):
            tree = ET.fromstring(archive.read(name))
            paragraphs = []
            for paragraph in tree.iter(ns+'p'):
                fragments = []
                for node in paragraph.iter():
                    if node.tag == ns+'t':fragments.append(node.text or '')
                    elif node.tag == ns+'tab':fragments.append('\t')
                    elif node.tag in (ns+'br', ns+'cr'):fragments.append('\n')
                paragraphs.append(''.join(fragments))
            documents.append({'filename': name, 'document_type': 'word_processing', 'page': None,
                              'text': '\n'.join(paragraphs), 'classification_eligible': True})
        return documents


def extract(raw, parent):
    from disclosure_collection import visible_text
    from edinet_pipeline import decode_text
    documents, skipped, presentation_adjustments = [], [], []
    if issuer_removed_notice(raw, parent):
        documents = [{'filename': 'issuer-removal-notice.html', 'document_type': 'publisher_removal_notice',
                      'page': None, 'text': visible_text(raw.decode('utf-8')), 'classification_eligible': False}]
        format_name = 'publisher_removed_document'
    elif raw.startswith(b'PK\x03\x04') and parent['source'] == 'hkex_news' and (word_documents := _word_documents(raw)) is not None:
        documents = word_documents
        format_name = 'docx'
    elif raw.startswith(b'PK\x03\x04') and parent['source'] == 'hkex_news':
        # HKEX publishes spreadsheet filings as well as PDFs. Preserve cells,
        # coordinates and sheet boundaries; never decode ZIP bytes as text.
        import zipfile
        from openpyxl import load_workbook
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            require(len(members) <= 10000 and sum(m.file_size for m in members) <= 64 * 1024 * 1024,
                    'disclosure_workbook_size_limit')
            require('[Content_Types].xml' in archive.namelist() and 'xl/workbook.xml' in archive.namelist(),
                    'disclosure_unsupported_zip')
        # Some HKEX generators emit a presentation-only extension rejected by
        # openpyxl. Normalize a temporary copy; original evidence stays intact.
        import xml.etree.ElementTree as ET
        normalized = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(raw)) as archive, zipfile.ZipFile(normalized, 'w', zipfile.ZIP_DEFLATED) as output:
            for member in archive.infolist():
                body = archive.read(member)
                if member.filename.startswith('xl/worksheets/') and member.filename.endswith('.xml'):
                    tree = ET.fromstring(body)
                    changed = False
                    for element in tree.iter():
                        if element.tag.rsplit('}', 1)[-1] == 'sheetFormatPr' and 'defaultColWidthPt' in element.attrib:
                            del element.attrib['defaultColWidthPt']
                            changed = True
                            presentation_adjustments.append({'member': member.filename, 'attribute': 'defaultColWidthPt'})
                    # Some generators declare A1 despite thousands of stored
                    # cells. Read-only openpyxl would silently omit those cells.
                    from openpyxl.utils.cell import coordinate_to_tuple, get_column_letter
                    ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
                    coordinates = [coordinate_to_tuple(c.attrib['r']) for c in tree.iter(ns+'c') if 'r' in c.attrib]
                    if coordinates:
                        rows, cols = max(r for r,c in coordinates), max(c for r,c in coordinates)
                        require(rows * cols <= 200000, 'disclosure_workbook_cell_limit')
                        dimension = tree.find(ns+'dimension')
                        ref = 'A1:' + get_column_letter(cols) + str(rows)
                        if dimension is not None and dimension.get('ref') not in (ref, 'A1' if rows == cols == 1 else ref):
                            dimension.set('ref', ref); changed = True
                            presentation_adjustments.append({'member':member.filename,'attribute':'dimension.ref'})
                    if changed:
                        body = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
                output.writestr(member, body)
        normalized.seek(0)
        workbook = load_workbook(normalized, read_only=True, data_only=False, keep_links=False)
        try:
            count = 0
            for sheet in workbook:
                require((sheet.max_row or 0) * (sheet.max_column or 0) <= 200000,
                        'disclosure_workbook_cell_limit')
                lines = []
                for row in sheet.iter_rows():
                    count += len(row)
                    require(count <= 200000, 'disclosure_workbook_cell_limit')
                    cells = [cell.coordinate + '=' + str(cell.value) for cell in row if cell.value is not None]
                    if cells:
                        lines.append('\t'.join(cells))
                documents.append({'filename':'report.xlsx', 'sheet_name':sheet.title,
                    'document_type':'spreadsheet', 'page':None,
                    'text':'Sheet: ' + sheet.title + '\n' + '\n'.join(lines),
                    'classification_eligible':True})
        finally:
            workbook.close()
        format_name = 'xlsx'
    elif raw.startswith(b'%PDF-'):
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
    if presentation_adjustments:
        info['ignored_presentation_attributes'] = presentation_adjustments
    if format_name == 'pdf':
        info.update(pages=len(documents), skipped_pages=[d['page'] for d in documents if not d['text'].strip()],
            text_pages=sum(bool(d['text'].strip()) for d in documents), skipped_page_reason='no_extractable_text')
    if format_name not in ('pdf', 'publisher_removed_document'):
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
