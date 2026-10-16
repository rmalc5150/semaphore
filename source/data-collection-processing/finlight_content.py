"""Capture original article bodies without substituting summaries for full text."""
from datetime import datetime, timedelta, timezone
import hashlib
import ipaddress
import json
import re
import socket
import time
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from collection_storage import now, write_checked, write_json
from collection_operations import load_stored
from regulatory_collection import EvidenceClient, SourceIssue, require
from research_contract import digest, parse_instant
from fda_access import NoRedirect

VERSION = 'finlight-fulltext-1.0'


def public_url(url):
    p = urlsplit(url)
    require(p.scheme in ('http', 'https') and p.hostname and not p.username and not p.password,
            'article_url_invalid')
    try:
        addresses = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == 'https' else 80), type=socket.SOCK_STREAM)
    except OSError:
        raise SourceIssue('article_dns_unavailable') from None
    require(addresses and all(ipaddress.ip_address(a[4][0]).is_global for a in addresses), 'article_url_not_public')
    return url


class PublicRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def usable(text, summary):
    if not isinstance(text, str) or len(text.strip()) < 250:
        return False
    clean = lambda s: ' '.join(s.split()).strip()
    value = clean(text)
    return (value != clean(summary or '') and not value.endswith(('...', '…')) and
        not re.search(r'(subscribe to continue reading|sign in to continue reading|enable javascript and cookies to continue|verify you are human)', value, re.I))


def extract_html(raw, url, summary):
    import trafilatura
    from lxml import html
    # lxml defaults to Latin-1 when HTML omits an encoding declaration.
    # Decode valid UTF-8 before parsing embedded JSON-LD to preserve CJK text.
    try:
        document = raw.decode('utf-8-sig') if isinstance(raw, bytes) else raw
    except UnicodeDecodeError:
        document = raw
    tree = html.fromstring(document)
    bodies = []
    for script in tree.xpath('//script[@type="application/ld+json"]/text()'):
        try:
            nodes = [json.loads(script)]
            while nodes:
                node = nodes.pop()
                if isinstance(node, list):
                    nodes.extend(node)
                elif isinstance(node, dict):
                    if node.get('isAccessibleForFree') in (False, 'false'):
                        raise SourceIssue('article_access_restricted')
                    if isinstance(node.get('articleBody'), str):
                        bodies.append(node['articleBody'])
                    nodes.extend(v for v in node.values() if isinstance(v, (dict, list)))
        except (ValueError, TypeError):
            continue
    body = trafilatura.extract(document, url=url, include_comments=False, include_tables=True,
        include_links=False, favor_precision=True)
    if body:
        bodies.append(body)
    candidates = [t.strip() for t in bodies if usable(t, summary)]
    require(candidates, 'article_full_body_not_found')
    return max(candidates, key=len)


class Capture:
    source = 'finlight'
    version = VERSION

    def __init__(self, store, provider_client, max_publisher_requests=100, publisher_daily_cap=1000):
        self.store, self.provider = store, provider_client
        self.evidence = EvidenceClient(store, self.source + '_article_content')
        self.remaining, self.daily_cap = max_publisher_requests, publisher_daily_cap

    def publisher(self, url, summary):
        require(self.remaining > 0, 'fulltext_run_budget_reached')
        key = 'operations/news/fulltext/publisher-budgets/' + now()[:10] + '.json'
        state, token = load_stored(self.store, key)
        count = (state or {}).get('requests', 0)
        if count >= self.daily_cap:
            raise SourceIssue('fulltext_daily_budget_reached', True)
        public_url(url)
        write_json(self.store, key, {'requests': count + 1, 'updated_at': now()}, token)
        self.remaining -= 1
        time.sleep(1)
        try:
            with build_opener(PublicRedirect()).open(Request(url, headers={
                'User-Agent': 'Optima Holdings support@optima-holdings.com', 'Accept-Encoding': 'identity'}), timeout=30) as response:
                raw = response.read(8 * 1024 * 1024 + 1)
                final_url = response.geturl()
                length = response.headers.get('Content-Length')
            require(len(raw) <= 8 * 1024 * 1024, 'article_response_too_large')
            require(length is None or int(length) == len(raw), 'article_response_truncated')
            self.evidence.save(raw, final_url, 'text/html')
            return extract_html(raw, final_url, summary), 'publisher_html'
        except HTTPError as exc:
            status = exc.code
            exc.close()
            raise SourceIssue('article_publisher_http_' + str(status)) from None
        except SourceIssue:
            raise
        except ImportError:
            raise
        except Exception:
            raise SourceIssue('article_publisher_unavailable') from None

    def provider_body(self, url, summary):
        from news_collection import URLS
        if self.provider.remaining <= getattr(self.provider, 'fulltext_api_reserve', 0):
            raise SourceIssue('fulltext_provider_budget_reserved', True)
        self.provider.reserve()
        endpoint = URLS['finlight'] + '/by-link?' + urlencode({'link': url, 'includeContent': 'true'})
        self.provider.sleep(1)
        try:
            with build_opener(NoRedirect()).open(Request(endpoint, headers={
                'X-API-KEY': self.provider.key, 'Accept': 'application/json'}), timeout=45) as response:
                raw = response.read(16 * 1024 * 1024 + 1)
            require(len(raw) <= 16 * 1024 * 1024 and self.provider.key.encode() not in raw, 'article_provider_response_invalid')
            self.evidence.save(raw, endpoint)
            data = json.loads(raw)
            article = data.get('article', {})
            require(data.get('status') == 'ok' and article.get('link') == url, 'article_provider_identity_mismatch')
            require(usable(article.get('content'), summary), 'article_provider_full_body_unavailable')
            return article['content'], 'finlight_by_link'
        except HTTPError as exc:
            status = exc.code
            exc.close()
            raise SourceIssue('article_provider_http_' + str(status), status in (429, 500, 502, 503, 504)) from None
        except SourceIssue:
            raise
        except Exception:
            raise SourceIssue('article_provider_request_failed') from None

    def get(self, row, historical=True, force=False):
        url = row['link']
        key = 'operations/news/fulltext/' + ('content/' if self.source == 'finlight' else self.source + '/content/') + digest(url) + '.json'
        previous, token = load_stored(self.store, key)
        if previous and not force:
            age = datetime.now(timezone.utc) - parse_instant(previous['captured_at'])
            if (previous['status'] == 'captured' and (historical or age < timedelta(days=1))) or (
                    previous['status'] == 'unavailable' and age < timedelta(hours=6)):
                if previous['status'] == 'captured':
                    from disclosure_collection import get_bytes
                    get_bytes(self.store, previous['reference']['key'], previous['reference']['sha256'])
                return previous
        self.evidence.evidence = []
        errors, body, basis = [], None, None
        if usable(row.get('content'), row.get('summary')):
            body, basis = row['content'], 'finlight_response'
        else:
            for fetch in ((self.publisher, self.provider_body) if self.source == 'finlight' else (self.publisher,)):
                try:
                    body, basis = fetch(url, row.get('summary'))
                    break
                except SourceIssue as exc:
                    if exc.partial or exc.code in ('run_request_budget_reached', 'daily_request_budget_reached',
                        'fulltext_run_budget_reached', 'fulltext_daily_budget_reached'):
                        raise SourceIssue(exc.code, True) from None
                    errors.append(exc.code)
        result = {'version': self.version, 'article_url': url, 'captured_at': now(),
            'source_evidence': list(self.evidence.evidence), 'attempt_errors': errors}
        if body is not None:
            text_hash = hashlib.sha256(body.encode()).hexdigest()
            artifact = {'version': self.version, 'article_url': url, 'title': row.get('title'), 'text': body,
                'text_sha256': text_hash, 'capture_basis': basis, 'chunks': [
                    {'chunk_id': digest({'text': text_hash, 'start': i}), 'start': i, 'end': min(i + 4000, len(body))}
                    for i in range(0, len(body), 3700)], 'source_evidence': result['source_evidence']}
            raw = (json.dumps(artifact, ensure_ascii=False, sort_keys=True) + '\n').encode()
            checksum = hashlib.sha256(raw).hexdigest()
            artifact_key = 'source_documents/' + self.source + '_fulltext/' + checksum
            write_checked(self.store, artifact_key, raw, content_type='application/json')
            ref = {'key': artifact_key, 'sha256': checksum, 'source_url': url, 'retrieved_at': result['captured_at']}
            result.update(status='captured', reference=ref, text_characters=len(body), text_sha256=text_hash,
                capture_basis=basis, chunk_count=len(artifact['chunks']))
            result['source_evidence'].append(ref)
        else:
            result.update(status='unavailable', text_characters=0,
                reason='full_article_unavailable; summary_not_substituted')
        write_json(self.store, key, result, token)
        return result


def apply(record, capture, store):
    from copy import deepcopy
    from disclosure_collection import get_bytes
    from research_contract import seal_record
    record = deepcopy(record)
    p = record['payload']
    p['full_text'] = capture
    p['data']['full_text_status'] = capture['status']
    p['source_evidence'] += [r for r in capture['source_evidence'] if r not in p['source_evidence']]
    if capture['status'] == 'captured':
        content = json.loads(get_bytes(store, capture['reference']['key'], capture['reference']['sha256']))
        require(content['text_sha256'] == hashlib.sha256(content['text'].encode()).hexdigest(), 'fulltext_text_checksum_mismatch')
        record['payload']['data'].update(content=content['text'] if len(content['text'].encode()) <= 1024 * 1024 else None,
            full_content_reference=capture['reference'])
    return seal_record(record)
