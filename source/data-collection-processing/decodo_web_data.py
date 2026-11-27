"""Bounded, binary-safe public preprint PDFs through Decodo Web Data API.

This product uses a Bearer token, never the legacy scraper's Basic credentials.
No network access occurs on import. Failed downloads cannot become raw evidence.
"""
from functools import lru_cache
import base64
import binascii
import hashlib
import io
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

import requests
from regulatory_collection import SourceIssue, require

API_URL = 'https://data.decodo.com/v1/scrape'
TOKEN_FIELD = 'decodo-web-data-token'
MAX_PDF_BYTES = 16 * 1024 * 1024
MAX_RESPONSE_BYTES = ((MAX_PDF_BYTES + 2) // 3) * 4 + 1024 * 1024
DAILY_REQUEST_LIMIT = 24
_CONTROL = None


def settings():
    path = Path(__file__).resolve().parent / 'config/decodo-web-data.json'
    config = json.loads(path.read_text()) if path.exists() else {}
    limit = config.get('max_requests_per_day', DAILY_REQUEST_LIMIT)
    require(type(limit) is int and 1 <= limit <= 1000, 'decodo_web_data_budget_invalid')
    return {**config, 'max_requests_per_day': limit}


def parse_bearer(value, dedicated=False, field=TOKEN_FIELD):
    if isinstance(value, dict):
        token = value.get(field)
        if dedicated and field == TOKEN_FIELD and not token:
            token = value.get('token') or value.get('key') or value.get('api_key')
    else:
        token = value if dedicated else None
    require(isinstance(token, str) and bool(token.strip()), 'decodo_web_data_bearer_missing')
    token = token.strip()
    if token.startswith('Bearer '):
        token = token[7:]
    require(bool(token) and not re.search(r'\s', token), 'decodo_web_data_bearer_invalid')
    return token


@lru_cache(maxsize=8)
def bearer(secret_id='proxies', region='us-east-1', field=TOKEN_FIELD):
    import boto3
    try:
        response = boto3.client('secretsmanager', region_name=region).get_secret_value(SecretId=secret_id)
        raw = response.get('SecretString')
        if raw is None:
            raw = base64.b64decode(response['SecretBinary']).decode('utf-8')
        try:
            value = json.loads(raw)
        except ValueError:
            value = raw
    except Exception:
        raise SourceIssue('decodo_web_data_credentials_unavailable', True) from None
    return parse_bearer(value, dedicated=secret_id != 'proxies', field=field)


def validate_url(url):
    p = urlsplit(url)
    require(p.scheme == 'https' and p.netloc in ('www.medrxiv.org', 'www.biorxiv.org')
            and not p.query and not p.fragment
            and bool(re.fullmatch(r'/content/10\.\d{4,9}/[A-Za-z0-9._;/()+:-]+v\d+\.full\.pdf', p.path)),
            'decodo_web_data_unreviewed_pdf_url')


def reserve():
    global _CONTROL
    from datetime import datetime, timezone
    if _CONTROL is None:
        from constellation.control import Control
        _CONTROL = Control()
    day = datetime.now(timezone.utc).date()
    with _CONTROL.db() as q:
        q.execute('INSERT INTO backfill_quotas(source_key,quota_day) VALUES(%s,%s) ON DUPLICATE KEY UPDATE source_key=VALUES(source_key)', ('decodo_web_data_pdf', day))
        q.execute('SELECT used_requests FROM backfill_quotas WHERE source_key=%s AND quota_day=%s FOR UPDATE', ('decodo_web_data_pdf', day))
        require(q.fetchone()['used_requests'] < settings()['max_requests_per_day'], 'decodo_web_data_daily_budget')
        q.execute('UPDATE backfill_quotas SET used_requests=used_requests+1 WHERE source_key=%s AND quota_day=%s', ('decodo_web_data_pdf', day))


def decode_pdf(document, expected_doi):
    require(isinstance(document, dict), 'decodo_web_data_response_shape')
    if 'results' in document:
        results = document['results']
        require(isinstance(results, list) and len(results) == 1 and isinstance(results[0], dict),
                'decodo_web_data_response_shape')
        document = results[0]
    if 'status_code' in document:
        require(document['status_code'] == 200, 'decodo_web_data_target_http_' + str(document['status_code']))
    content = document.get('content')
    require(isinstance(content, str) and len(content) <= MAX_RESPONSE_BYTES, 'decodo_web_data_content_shape')
    require(not content.startswith('%PDF-'), 'decodo_web_data_pdf_not_base64')
    try:
        raw = base64.b64decode(content, validate=True)
    except (ValueError, binascii.Error, UnicodeError):
        raise SourceIssue('decodo_web_data_invalid_base64') from None
    require(0 < len(raw) <= MAX_PDF_BYTES, 'decodo_web_data_pdf_size')
    require(raw.startswith(b'%PDF-') and b'%%EOF' in raw[-4096:], 'decodo_web_data_not_complete_pdf')
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw), strict=True)
        require(not reader.is_encrypted, 'decodo_web_data_encrypted_pdf')
        pages = len(reader.pages)
        require(0 < pages <= 1000, 'decodo_web_data_pdf_page_count')
        # A valid PDF from a wrong URL cannot satisfy a different preprint's identity.
        text = ''.join((reader.pages[n].extract_text() or '') for n in range(min(pages, 2)))
        require(expected_doi.lower() in re.sub(r'\s+', '', text).lower(), 'decodo_web_data_pdf_doi_mismatch')
    except SourceIssue:
        raise
    except Exception:
        raise SourceIssue('decodo_web_data_invalid_pdf_structure') from None
    return raw, {'encoding': 'base64', 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                 'pages': pages, 'doi_verified': expected_doi, 'strict_pdf_validation': True}


def capture(client, url, expected_doi, *, probe=False):
    validate_url(url)
    require(bool(re.fullmatch('/content/' + re.escape(expected_doi) + r'v\d+\.full\.pdf', urlsplit(url).path)),
            'decodo_web_data_url_doi_mismatch')
    config = settings()
    require(probe or config.get('enabled') is True, 'decodo_web_data_pending_provider_validation')
    secret_id = os.environ.get('DECODO_WEB_DATA_SECRET_ID') or config.get('secret_id') or 'proxies'
    token = bearer(secret_id, os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'),
                   settings().get('token_field', TOKEN_FIELD))
    reserve()
    from constellation.shared_limits import admit
    admit(API_URL)
    try:
        with requests.post(API_URL, headers={'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json', 'Accept': 'application/json'}, json={'url': url},
                stream=True, timeout=(10, 60), allow_redirects=False) as response:
            require(response.status_code == 200, 'decodo_web_data_http_' + str(response.status_code))
            chunks = []; size = 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                require(size <= MAX_RESPONSE_BYTES, 'decodo_web_data_response_too_large')
                chunks.append(chunk)
            body = b''.join(chunks)
        try:
            document = json.loads(body)
        except (ValueError, UnicodeError):
            raise SourceIssue('decodo_web_data_invalid_json') from None
        # Retain transport evidence separately from the provider's decoded bytes.
        safe = body.replace(token.encode(), b'[REDACTED]')
        client.save(safe, API_URL, 'application/json')
        transport = dict(client.evidence[-1])
        try:
            raw, validation = decode_pdf(document, expected_doi)
        except SourceIssue as exc:
            exc.diagnostics = {'gateway_response': transport,
                               'response_keys': list(document)[:20] if isinstance(document, dict) else []}
            raise
        client.save(raw, url, 'application/pdf')
        return raw, {**validation, 'transport': 'decodo_web_data', 'gateway_response': transport}
    except SourceIssue:
        raise
    except Exception:
        # Requests exceptions can contain authentication; never stringify them.
        raise SourceIssue('decodo_web_data_request_failed', True) from None
