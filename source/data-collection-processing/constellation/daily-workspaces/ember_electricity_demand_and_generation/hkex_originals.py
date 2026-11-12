"""Capture Chinese originals separately from HKEX English availability notices.

Same issuer/release-minute candidates are collected under their own provider
identifiers. They are never asserted to be translations of the English notice.
"""
import copy
from datetime import datetime
import hashlib
from html.parser import HTMLParser
import io
import json
import re
from urllib.parse import urlencode, urljoin, urlsplit
import zipfile

from collection_storage import write_checked, write_json
from research_contract import digest, seal_record

API = 'https://www1.hkexnews.hk/search/titleSearchServlet.do'
NOTICE = 'an announcement has just been published by the issuer in the chinese section of this website'
VERSION = 'hkex-originals-1'

class OriginalError(ValueError):
    pass


def check(value, reason):
    if not value:
        raise OriginalError(reason)


class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.hidden = 0; self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.hidden += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.hidden = max(0, self.hidden - 1)
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)


def text(body):
    value = body.decode('utf-8-sig', errors='replace')
    if '<!--newscontent-->' in value:
        value = value.split('<!--newscontent-->', 1)[1].split('<!--/newscontent-->', 1)[0]
    parser = Text(); parser.feed(value)
    return ' '.join(' '.join(parser.parts).split())


def language_notice(body):
    value = text(body).lower()
    return len(value) < 1500 and NOTICE in value


def document_url(url):
    p = urlsplit(url)
    check(p.scheme == 'https' and p.netloc == 'www1.hkexnews.hk' and not p.query and not p.fragment
          and re.fullmatch(r'/listedco/listconews/(?:sehk|gem)/(?:\d{4}/\d{4}/[A-Za-z0-9_.-]+|dod/(?:en|tc|sc)\.html)', p.path),
          'hkex_original_untrusted_url')
    return url


def validate_original(body, url):
    document_url(url)
    check(body and len(body) <= 32*1024*1024, 'hkex_original_empty_or_oversize')
    low = body[:16384].lower()
    check(not any(x in low for x in (b'<title>access denied', b'captcha', b'cf-chl-', b'request rate threshold exceeded')),
          'hkex_original_access_blocked')
    check(not language_notice(body), 'hkex_language_notice_is_not_original')
    if body.startswith(b'%PDF-'):
        check(b'%%EOF' in body[-4096:], 'hkex_original_truncated_pdf')
        return {'format': 'pdf', 'completeness': 'original PDF bytes with closed EOF marker'}
    if body.startswith(b'PK\x03\x04'):
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            files = z.infolist(); names = {f.filename for f in files}
            check(len(files) <= 10000 and sum(f.file_size for f in files) <= 64*1024*1024,
                  'hkex_original_office_expansion_limit')
            check('[Content_Types].xml' in names and bool({'word/document.xml','xl/workbook.xml'} & names),
                  'hkex_original_unsupported_archive')
            check(z.testzip() is None, 'hkex_original_corrupt_archive')
        return {'format': 'office', 'completeness': 'native Office archive and CRC verified'}
    if b'<html' in low or b'<!doctype html' in low:
        visible = text(body)
        check('has been removed by the listed issuer' not in visible.lower(), 'hkex_original_publisher_removed')
        check(len(visible) >= 120, 'hkex_original_html_not_substantive')
        return {'format': 'html', 'completeness': 'original official document HTML with substantive visible content'}
    raise OriginalError('hkex_original_unsupported_content')


def listing(client, day):
    cached = getattr(client, '_hkex_chinese_listings', {})
    if day in cached:
        return cached[day]
    params = {'sortDir':'0','sortByOptions':'DateTime','category':'0','market':'SEHK','stockId':'',
        'documentType':'','fromDate':day.replace('-',''),'toDate':day.replace('-',''),'title':'',
        'searchType':'0','t1code':'-2','t2Gcode':'-2','t2code':'-2','rowRange':100000,'lang':'ZH'}
    before = len(client.evidence)
    data = client.json(API, params=params)
    rows = json.loads(data['result']) if isinstance(data['result'], str) else data['result']
    check(isinstance(rows, list) and len(rows) == int(data['loadedRecord']) == int(data['recordCnt'])
          and data.get('hasNextRow') is False, 'hkex_chinese_listing_incomplete')
    ids = [str(r.get('NEWS_ID','')) for r in rows]
    check(len(set(ids)) == len(ids) and all(re.fullmatch(r'\d+', i) for i in ids), 'hkex_chinese_listing_identity_invalid')
    for row in rows:
        check(datetime.strptime(row['DATE_TIME'], '%d/%m/%Y %H:%M').date().isoformat() == day,
              'hkex_chinese_listing_wrong_date')
        # Only selected document URLs are fetched; retain unrelated rows as provider evidence.
    result = rows, copy.deepcopy(client.evidence[before:])
    check(result[1], 'hkex_chinese_listing_evidence_missing')
    cached[day] = result; client._hkex_chinese_listings = cached
    return result


def resolve_notice(record, body, client):
    """Return an immutable notice receipt and separately identified originals."""
    check(language_notice(body), 'hkex_expected_language_notice')
    row = record['payload']['data']
    check(str(row['NEWS_ID']) == str(record['source_record_id']), 'hkex_notice_identity_mismatch')
    document_url(record['source_url'])
    identity = digest([VERSION, row['NEWS_ID'], row['STOCK_CODE'], row['DATE_TIME'], hashlib.sha256(body).hexdigest()])
    key = 'checkpoints/task_hkex_originals/resolutions/' + identity + '.json'
    old = client.store.get(key)
    if old:
        receipt = json.loads(old.body)
        check(receipt.get('resolution_id') == identity, 'hkex_resolution_identity_mismatch')
        for entry in receipt['originals']:
            raw = client.store.get(entry['document_evidence']['key'])
            check(raw is not None and hashlib.sha256(raw.body).hexdigest() == entry['document_evidence']['sha256'],
                  'hkex_resolution_artifact_checksum_mismatch')
            validate_original(raw.body, entry['source_url'])
        return receipt
    day = datetime.strptime(row['DATE_TIME'], '%d/%m/%Y %H:%M').date().isoformat()
    rows, proof = listing(client, day)
    candidates = [r for r in rows if r['STOCK_CODE'] == row['STOCK_CODE'] and r['DATE_TIME'] == row['DATE_TIME']]
    check(0 < len(candidates) <= 20, 'hkex_chinese_original_candidates_missing_or_ambiguous_group')
    originals = []
    for candidate in candidates:
        check(str(candidate['NEWS_ID']) != str(row['NEWS_ID']), 'hkex_language_identity_collision')
        url = document_url(urljoin(API, candidate['FILE_LINK']))
        raw = client.get(url); validation = validate_original(raw, url)
        ref = copy.deepcopy(client.evidence[-1])
        check(ref.get('source_url') == url and ref.get('sha256') == hashlib.sha256(raw).hexdigest(),
              'hkex_original_evidence_identity_mismatch')
        originals.append({'row':candidate,'source_url':url,'document_evidence':ref,'bytes':len(raw),
                          'listing_evidence':proof,'validation':validation,'language':'zh-Hant'})
    receipt = {'version':VERSION,'resolution_id':identity,'notice_record_id':str(row['NEWS_ID']),
        'notice_url':record['source_url'],'notice_sha256':hashlib.sha256(body).hexdigest(),
        'english_version_status':'not_linked_in_captured_notice','originals':originals,
        'relation':'same_issuer_same_release_minute_candidates; exact_translation_equivalence_not_asserted',
        'scope_note':'Original Chinese filings retain their own HKEX identifiers. This is not complete Chinese-market coverage.'}
    write_json(client.store, key, receipt)
    receipt['receipt_key'] = key
    return receipt


def original_record(parent, entry, receipt):
    r = copy.deepcopy(parent)
    for key in ('record_id','observation_id','payload_hash'):
        r.pop(key, None)
    row = entry['row']; r['source_record_id'] = str(row['NEWS_ID']); r['source_url'] = entry['source_url']
    r['ingested_at'] = entry['document_evidence']['retrieved_at']
    r['available_at'] = None; r['availability_basis'] = 'unknown'; r['availability_evidence'] = []
    r['company_ids'] = []; r['listing_ids'] = []; r['entity_match_status'] = 'unresolved'
    r['payload'] = {'record_type':'disclosure','title':row['TITLE'],'data':row,'date_basis':'hkex_release_date',
        'document_language':'zh-Hant','company_names':[row['STOCK_NAME']],
        'candidate_company_ids':[],'candidate_sector_ids':[],
        'source_evidence':entry['listing_evidence']+[entry['document_evidence']],
        'document_capture':{'status':'captured','bytes':entry['bytes'],'source_evidence':[entry['document_evidence']]},
        'language_notice_context':{'notice_record_id':receipt['notice_record_id'],'notice_url':receipt['notice_url'],
            'notice_sha256':receipt['notice_sha256'],'resolution_id':receipt['resolution_id'],'relation':receipt['relation']},
        'coverage_note':receipt['scope_note']+' Chinese original captured now; historical public availability remains unverified.'}
    return seal_record(r)
