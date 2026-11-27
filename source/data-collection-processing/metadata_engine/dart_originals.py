"""Recover complete same-receipt originals from the official Korean DART viewer."""

from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
from io import BytesIO
import json
import re
import unicodedata
from urllib.parse import parse_qs, urlencode, urlsplit

from botocore.exceptions import ClientError
from pypdf import PdfReader
from pypdf.errors import PyPdfError
import requests

from metadata_engine.evidence import RawFailure, object_bytes


HOST = 'https://dart.fss.or.kr'
PREFIX = 'research-data/constellation-backfill/metadata-engine/runtime-v2/dart-original-repair'
REPAIR_REASONS = ('dart_original_xml_invalid', 'dart_original_xml_empty',
                  'streaming_archive_unsafe_or_encrypted_member', 'filing_original_document_missing')
MAX_HTML = 2 * 1024**2
MAX_PDF = 32 * 1024**2
MAX_ATTACHMENTS = 16


def viewer_url(receipt):
    return HOST + '/dsaf001/main.do?' + urlencode({'rcpNo': receipt})


def download_url(path, receipt, document):
    return HOST + path + '?' + urlencode({'rcp_no': receipt, 'dcm_no': document})


def registry_key(receipt, anchor_sha, anchor):
    if (anchor not in ('old_archive', 'archived_index') or not re.fullmatch(r'\d{14}', receipt)
            or not re.fullmatch(r'[a-f0-9]{64}', anchor_sha)):
        raise RawFailure('dart_repair_invalid_identity')
    stem = f'index-{anchor_sha}' if anchor == 'archived_index' else anchor_sha
    return f'{PREFIX}/receipts/{receipt}/{stem}.json'


class Viewer(HTMLParser):
    def __init__(self):
        super().__init__()
        self.selected = []
        self.attachments = []
        self.buttons = []
        self.links = []
        self.title = ''
        self.in_title = False
        self.select = None

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == 'title':
            self.in_title = True
        elif tag == 'select':
            self.select = attrs.get('id')
        elif tag == 'option' and self.select == 'family' and 'selected' in attrs:
            self.selected.append((attrs.get('value', ''), attrs.get('title', '')))
        elif tag == 'option' and self.select == 'att' and attrs.get('value') not in (None, 'null'):
            self.attachments.append(attrs['value'])
        elif tag == 'button' and 'btnDown' in attrs.get('class', '').split():
            click = attrs.get('onclick', '').strip()
            if click.startswith('openPdfDownload('):
                self.buttons.append(click)
        elif tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        elif tag == 'select':
            self.select = None

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def normalized(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', text or '')).casefold()


def report_name(text):
    text = normalized(text)
    text = re.sub(r'^(?:\[(?:기재정정|첨부정정|첨부추가|정정)\])+', '', text)
    return re.sub(r'\(\d{4}\.\d{1,2}\)$', '', text)


def parse_view(body, receipt, filing):
    view = Viewer()
    view.feed(body.decode('utf-8-sig'))
    if view.selected and (len(view.selected) != 1 or parse_qs(view.selected[0][0]) != {'rcpNo': [receipt]}):
        raise RawFailure('dart_repair_viewer_report_mismatch')
    title = view.title.rsplit('/', 2)
    if len(title) != 3 or not normalized(filing.get('corp_name')) or normalized(title[0]) != normalized(filing['corp_name']):
        raise RawFailure('dart_repair_viewer_issuer_mismatch')
    selected = report_name(view.selected[0][1] if view.selected else title[1])
    archived = report_name(filing.get('report_nm'))
    # DART's viewer omits the fund name from this one documented title form.
    fund_title = ('투자설명서(집합투자증권)' == selected
                  and archived.startswith(selected + '(') and archived.endswith(')'))
    if not selected or selected != report_name(title[1]) or not (selected == archived or fund_title):
        raise RawFailure('dart_repair_viewer_report_mismatch')
    if len(view.buttons) != 1:
        raise RawFailure('dart_repair_document_identity_missing')
    button = re.fullmatch(r"\s*openPdfDownload\(\s*'([0-9]{14})'\s*,\s*'([0-9]{1,12})'\s*\)\s*;?\s*", view.buttons[0])
    if not button or button[1] != receipt:
        raise RawFailure('dart_repair_document_identity_missing')
    ids = [button[2]]
    for attachment in view.attachments:
        values = parse_qs(attachment)
        receipts = values.get('rcpNo', [])
        identifiers = values.get('dcmNo', [])
        if (set(values) != {'rcpNo', 'dcmNo'} or len(receipts) != 1 or not re.fullmatch(r'[0-9]{14}', receipts[0])
                or len(identifiers) != 1 or not re.fullmatch(r'[0-9]{1,12}', identifiers[0])):
            raise RawFailure('dart_repair_attachment_identity_mismatch')
        # The selector also lists attachments from other receipts in the filing family.
        if receipts[0] == receipt and identifiers[0] not in ids:
            ids.append(identifiers[0])
    if len(ids) - 1 > MAX_ATTACHMENTS:
        raise RawFailure('dart_repair_attachment_limit')
    return ids


def confirm_pdf_link(body, receipt, document):
    popup = Viewer()
    popup.feed(body.decode('utf-8-sig'))
    match = []
    for href in popup.links:
        url = urlsplit(href)
        if ((url.scheme, url.netloc) not in (('', ''), ('https', 'dart.fss.or.kr'))
                or url.path != '/pdf/download/pdf.do' or url.fragment):
            continue
        if parse_qs(url.query) == {'rcp_no': [receipt], 'dcm_no': [document]}:
            match.append(href)
    if not match:
        raise RawFailure('dart_repair_complete_pdf_not_offered')


def pdf_pages(body):
    if not body.startswith(b'%PDF-') or not body.rstrip().endswith(b'%%EOF'):
        raise RawFailure('dart_repair_invalid_pdf_container')
    try:
        pdf = PdfReader(BytesIO(body), strict=True)
        count = len(pdf.pages)
        if not 1 <= count <= 1500 or pdf.is_encrypted:
            raise RawFailure('dart_repair_pdf_pages_invalid')
        has_content = False
        for page in pdf.pages:
            contents = page.get_contents()
            if contents is not None and contents.get_data().strip():
                has_content = True
        if not has_content:
            raise RawFailure('dart_repair_pdf_has_no_content')
    except (PyPdfError, KeyError, ValueError, RecursionError) as error:
        if isinstance(error, RawFailure):
            raise
        raise RawFailure('dart_repair_pdf_unreadable') from None
    return count


def read_repair(s3, bucket, receipt, anchor_sha, anchor):
    key=registry_key(receipt,anchor_sha,anchor)
    try:
        return json.loads(object_bytes(s3, bucket, key, 64*1024))
    except ClientError as error:
        code=error.response['Error']['Code']
        if code in ('NoSuchKey', '404', 'NotFound'):
            return None
        if code in ('AccessDenied', '403'):
            listing=s3.list_objects_v2(Bucket=bucket,Prefix=key,MaxKeys=1)
            if not any(item['Key']==key for item in listing.get('Contents', [])):
                return None
        raise


def archived_part(s3, bucket, part, suffix, max_bytes):
    sha=part.get('sha256', '')
    if not re.fullmatch(r'[a-f0-9]{64}', sha):
        raise RawFailure('dart_repair_artifact_hash_invalid')
    key=f'{PREFIX}/originals/{sha}.{suffix}'
    if part.get('key') != key:
        raise RawFailure('dart_repair_artifact_path_invalid')
    return object_bytes(s3,bucket,key,max_bytes,expected=sha)


def repaired_artifacts(s3, bucket, receipt, filing, anchor_sha, *, anchor='old_archive'):
    repair=read_repair(s3,bucket,receipt,anchor_sha,anchor)
    if repair is None:
        return None
    if repair.get('receipt') != receipt or repair.get(anchor+'_sha256') != anchor_sha:
        raise RawFailure('dart_repair_receipt_mismatch')
    view=archived_part(s3,bucket,repair['viewer'],'html',MAX_HTML)
    ids=parse_view(view,receipt,filing)
    if ids != [item.get('document') for item in repair['documents']]:
        raise RawFailure('dart_repair_receipt_package_incomplete')
    artifacts=[]
    for index, item in enumerate(repair['documents']):
        document=item['document']
        popup=archived_part(s3,bucket,item['download_page'],'html',MAX_HTML)
        confirm_pdf_link(popup,receipt,document)
        pdf=archived_part(s3,bucket,item['pdf'],'pdf',MAX_PDF)
        pages=pdf_pages(pdf)
        artifacts.append({'artifact_kind':'primary_document','s3_uri':f's3://{bucket}/{item["pdf"]["key"]}',
                          'sha256':item['pdf']['sha256'],'bytes':len(pdf),'origin':'first_party_source',
                          'source_url':download_url('/pdf/download/pdf.do',receipt,document),
                          'retrieved_at':repair['retrieved_at'],
                          'validation':{'format':'pdf','pages':pages,'provider':'south_korea_fss_opendart',
                                        'record_type':'filing_body' if index==0 else 'same_receipt_attachment',
                                        'receipt':receipt,'document':document,
                                        ('original_xml_archive_sha256' if anchor=='old_archive'
                                         else 'archived_index_sha256'):anchor_sha,
                                        'scope':'Official Korean DART full-report PDF tied to the archived receipt and download page.'}})
    return artifacts


def fetch_part(client, url, size, *, referer=None):
    from constellation.shared_limits import admit
    admit(url)
    try:
        with client.get(url,headers={'Referer':referer} if referer else {},timeout=(8,35),
                        stream=True,allow_redirects=False) as response:
            if response.status_code != 200:
                raise RawFailure(f'dart_repair_http_{response.status_code}')
            body=bytearray()
            for chunk in response.iter_content(65536):
                body.extend(chunk)
                if len(body)>size:
                    raise RawFailure('dart_repair_response_size_limit')
            return bytes(body)
    except requests.RequestException as error:
        raise RawFailure('dart_repair_transport_'+type(error).__name__) from None


def recover(s3, bucket, client, receipt, filing, anchor_sha, *, anchor='old_archive'):
    from metadata_engine.worker import put
    key=registry_key(receipt,anchor_sha,anchor)
    if read_repair(s3,bucket,receipt,anchor_sha,anchor):
        return

    def save(body, suffix, media):
        sha=hashlib.sha256(body).hexdigest()
        part=f'{PREFIX}/originals/{sha}.{suffix}'
        put(s3,bucket,part,body,media)
        return {'key':part,'sha256':sha}

    url=viewer_url(receipt)
    raw_view=fetch_part(client,url,MAX_HTML)
    ids=parse_view(raw_view,receipt,filing)
    repair={'receipt':receipt,anchor+'_sha256':anchor_sha,'retrieved_at':datetime.now(timezone.utc).isoformat(),
            'viewer':save(raw_view,'html','text/html'),'documents':[]}
    for document in ids:
        popup_url=download_url('/pdf/download/main.do',receipt,document)
        popup=fetch_part(client,popup_url,MAX_HTML,referer=url)
        confirm_pdf_link(popup,receipt,document)
        pdf=fetch_part(client,download_url('/pdf/download/pdf.do',receipt,document),MAX_PDF,referer=popup_url)
        pdf_pages(pdf)
        repair['documents'].append({'document':document,'download_page':save(popup,'html','text/html'),
                                    'pdf':save(pdf,'pdf','application/pdf')})
    data=json.dumps(repair,sort_keys=True,separators=(',',':')).encode()
    try:
        s3.put_object(Bucket=bucket,Key=key,Body=data,ContentType='application/json',
                      ServerSideEncryption='AES256',IfNoneMatch='*')
    except ClientError as error:
        if error.response['Error']['Code'] not in ('412','PreconditionFailed'):
            raise
