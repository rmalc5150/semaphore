"""Read and adapt the archived source evidence for published observations."""
from collections import OrderedDict
from copy import deepcopy
import io
import json
import re
from urllib.parse import urlsplit

from lxml.etree import LxmlError
from pypdf.errors import PyPdfError

from semiotic_sandbox import encoded, sha

VERSION = 'archived-text-v1'
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
MAX_RUN_BYTES = 96 * 1024 * 1024
MAX_OBSERVATION_CHARS = 32_000
MAX_PDF_PAGES = 30


def item(text, **locator):
    return {'text': ' '.join(text.split()), 'source_locator': locator}


def extract_html(raw, **locator):
    from lxml import html

    root = html.fromstring(raw)
    for node in root.xpath('//script|//style|//noscript|//nav|//footer|//header'):
        node.drop_tree()
    return item(' '.join(root.itertext()), coordinate_system='html_extracted_text', **locator)


def archive_text(raw, observation, artifact):
    source = observation['source_key']
    source_record_id = observation['source_record_id']
    stripped = raw.lstrip()
    if raw.startswith(b'%PDF-'):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw))
        pages = [item(page.extract_text() or '', coordinate_system='pdf_page_extracted_text', pdf_page=i)
                 for i, page in enumerate(reader.pages[:MAX_PDF_PAGES], start=1)]
        return pages, 'pdf_page_limit' if len(reader.pages) > MAX_PDF_PAGES else None
    if source == 'arxiv' and artifact['artifact_kind'] == 'provider_record':
        from lxml import etree

        root = etree.fromstring(raw, parser=etree.XMLParser(resolve_entities=False, no_network=True))
        ns = {'a': 'http://www.w3.org/2005/Atom'}
        matches = [(index, entry) for index, entry in enumerate(root.findall('a:entry', ns), 1)
                   if entry.findtext('a:id', namespaces=ns) == source_record_id]
        if len(matches) != 1:
            raise ValueError('arXiv observation does not identify exactly one Atom entry')
        index, entry = matches[0]
        return [item(entry.findtext(f'a:{field}', default='', namespaces=ns),
                     coordinate_system='atom_field_extracted_text', xml_path=f'/a:feed/a:entry[{index}]/a:{field}')
                for field in ('title', 'summary')], 'citation_and_abstract_only'
    if source == 'google_patents_bigquery' and artifact['artifact_kind'] == 'provider_record':
        from metadata_engine.patent_sources import validate_google

        native = validate_google(raw, {**observation, 'source_url': observation['original_url']},
                                 artifact['source_url'])
        return [item(native[field], coordinate_system='bigquery_record_field', record_id=source_record_id,
                     field=field) for field in ('title', 'abstract') if isinstance(native.get(field), str)], 'bibliography_only'
    if source == 'usa_spending' and artifact['artifact_kind'] == 'provider_record':
        data = observation['payload']['data']
        matches = [index for index, record in enumerate(json.loads(raw)['results']) if record == data]
        if len(matches) != 1:
            raise ValueError('USAspending observation does not identify exactly one result')
        text = data.get('Description')
        return ([item(text, coordinate_system='json_field_extracted_text',
                      json_pointer=f'/results/{matches[0]}/Description')] if isinstance(text, str) else []), 'award_summary_only'
    if source == 'sec_edgar' and raw.startswith(b'<SEC-DOCUMENT>'):
        from metadata_engine.sec_documents import validate_submission

        payload = observation['payload']
        receipt = validate_submission(raw, source_record_id, [r['cik'] for r in payload['issuer_rows']],
                                      payload['form'])
        docs = []
        for doc in receipt['documents']:
            if doc['type'] != payload['form']:
                continue
            block = raw[doc['byte_start']:doc['byte_end']]
            content = re.search(rb'<TEXT>(.*?)</TEXT>', block, re.S)[1]
            docs.append(extract_html(content, filename=doc['filename'],
                                     document_bytes=[doc['byte_start'], doc['byte_end']]))
        return docs, 'primary_filing_only'
    if re.search(rb'<(?:!doctype\s+html|html\b)', stripped[:4096], re.I):
        return [extract_html(raw)], None
    if artifact['artifact_kind'] in ('primary_document', 'full_text') and stripped.startswith(b'<'):
        from lxml import etree

        root = etree.fromstring(raw, parser=etree.XMLParser(resolve_entities=False, no_network=True))
        return [item(' '.join(root.itertext()), coordinate_system='xml_document_extracted_text')], None
    return [], 'structured_or_unsupported_format'


class ArchivedEvidenceReader:
    """Verify each S3 object once per bounded cache and retain extraction receipts."""

    def __init__(self, s3, bucket, *, max_artifact_bytes=MAX_ARTIFACT_BYTES, max_run_bytes=MAX_RUN_BYTES):
        self.s3, self.bucket = s3, bucket
        self.max_artifact_bytes, self.max_run_bytes = max_artifact_bytes, max_run_bytes
        self.cache = OrderedDict()
        self.downloaded = 0

    def fetch(self, artifact):
        parsed = urlsplit(artifact['s3_uri'])
        key = parsed.path.removeprefix('/')
        digest = artifact['sha256'].removeprefix('sha256:')
        if (parsed.scheme != 's3' or parsed.netloc != self.bucket or parsed.query or parsed.fragment
                or not key.startswith('research-data/') or '..' in key.split('/')
                or not re.fullmatch('[a-f0-9]{64}', digest)):
            raise ValueError('archived evidence reference is outside the input scope')
        cache_key = key, digest
        if cache_key in self.cache:
            self.cache.move_to_end(cache_key)
            return self.cache[cache_key]
        if (artifact.get('bytes') or 0) > self.max_artifact_bytes:
            return None
        response = self.s3.get_object(Bucket=self.bucket, Key=key)
        stream = response['Body']
        try:
            size = response['ContentLength']
            if size > self.max_artifact_bytes:
                return None
            if self.downloaded + size > self.max_run_bytes:
                raise RuntimeError('archived-evidence run byte budget exhausted; use fewer jobs')
            raw = stream.read(self.max_artifact_bytes + 1)
        finally:
            stream.close()
        self.downloaded += len(raw)
        if len(raw) != size or sha(raw) != digest:
            raise ValueError(f'archived evidence checksum or size mismatch: {key}')
        if len(self.cache) >= 4:
            self.cache.popitem(last=False)
        self.cache[cache_key] = raw
        return raw

    def hydrate(self, snapshot):
        if sha(encoded(snapshot['observations'])) != snapshot['observations_sha256']:
            raise ValueError('input observations checksum mismatch')
        result = deepcopy(snapshot)
        for observation in result['observations']:
            pages, receipts = [], []
            remaining = MAX_OBSERVATION_CHARS
            seen = set()
            for artifact in observation.get('raw_artifacts', []):
                if artifact.get('representation') or artifact.get('origin') != 'first_party_source':
                    continue
                artifact_key = artifact['s3_uri'], artifact['sha256']
                if artifact_key in seen:
                    continue
                seen.add(artifact_key)
                receipt = {'artifact_sha256': artifact['sha256'], 'artifact_uri': artifact['s3_uri'],
                           'parser_version': VERSION, 'pages_extracted': 0}
                receipts.append(receipt)
                raw = self.fetch(artifact)
                if raw is None:
                    receipt.update(status='artifact_size_limit', limitation='no_text_extracted')
                    continue
                try:
                    candidates, limitation = archive_text(raw, observation, artifact)
                except (ValueError, KeyError, TypeError, SyntaxError, LxmlError, PyPdfError) as exc:
                    receipt.update(status='parse_failed', limitation=type(exc).__name__)
                    continue
                for candidate in candidates:
                    if not candidate['text']:
                        continue
                    if len(candidate['text']) > remaining:
                        limitation = 'observation_text_limit'
                    if remaining <= 0:
                        break
                    text = candidate['text'][:remaining]
                    remaining -= len(text)
                    pages.append({**candidate, 'page': len(pages) + 1, 'text': text,
                                  'artifact_sha256': artifact['sha256']})
                    receipt['pages_extracted'] += 1
                receipt.update(status='extracted' if receipt['pages_extracted'] else 'no_text_extracted',
                               limitation=limitation)
            observation['extracted_pages'] = pages
            observation['raw_extraction'] = {'version': VERSION, 'artifacts': receipts,
                                             'status': 'extracted' if pages else 'no_text_extracted' if receipts
                                             else 'no_original_artifact'}
        result['published_observations_sha256'] = snapshot.get(
            'published_observations_sha256', snapshot['observations_sha256'])
        result['observations_sha256'] = sha(encoded(result['observations']))
        return result
