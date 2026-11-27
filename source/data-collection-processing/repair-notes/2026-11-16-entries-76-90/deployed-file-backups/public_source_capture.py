"""Capture public archives and documents; retrieved pages never certify dated coverage."""
import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urljoin, urlsplit, urlunsplit
import uuid

import boto3
import requests
from constellation.shared_limits import admit
from public_source_scope import in_scope,canonical_link,decoded_response

ROOT = Path(__file__).resolve().parent
BUCKET = 'data-collection-059416028963-us-east-1-an'
PREFIX = 'research-data/constellation-backfill/public-capture'
MAX_BYTES = 128 * 1024**2
DOCUMENT = re.compile(r'\.(?:pdf|csv|zip|xlsx?|json|xml|rds|gz)(?:$|\?)', re.I)
ARCHIVE = re.compile(r'archive|histor|publication|report|download|document|dataset|annual|yearbook|bulletin|statistics|data|20(?:1[6-9]|2[0-6])|[?&](?:page|offset)=', re.I)
FORBIDDEN = re.compile(r'login|logout|sign.?in|register|checkout|subscribe|password|oauth', re.I)

def challenged(body):
    return any(x in body.lower() for x in (b'cf-chl-',b'<title>just a moment',b'captcha challenge',b'verify you are human',b'<title>access denied'))

def rendered(url):
    from decodo_scraping_api import scrape_url
    body=scrape_url(url,headless='html').encode()
    if len(body)>8*1024**2:raise ValueError('public_rendered_page_too_large')
    if challenged(body[:8192]):raise ValueError('public_challenge_unresolved')
    return body


def stamp():
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False) + '\n').encode()


def allowed(url, source):
    p = urlsplit(url)
    return (p.scheme == 'https' and not p.username and not p.password
            and p.port in (None, 443) and p.hostname in source['hosts']
            and not FORBIDDEN.search(p.path))


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = dict(attrs).get('href')
            if href: self.links.append(href)


def discover(body, url, source, depth):
    if depth >= source.get('max_depth', 3): return []
    if source.get('source') == 'doe_storage_program':
        # Follow storage content and its linked originals, rather than DOE's
        # site-wide navigation into unrelated history and administrative files.
        from doe_storage_enrichment import parse_document
        document = parse_document(body, url)
        return [{'url': link['url'], 'depth': depth + 1} for link in document['links']
                if allowed(link['url'], source)]
    # data.gouv.fr dataset endpoints expose the authoritative download URLs in
    # JSON rather than anchor tags.  Treat that response as an index only and
    # enqueue the actual published resources, including their CDN host.
    if source.get('catalog_index')and body.lstrip().startswith(b'{'):
        try:
            data=json.loads(body)
            resources=data.get('resources', [])
            found=[]
            for resource in resources:
                target=resource.get('url') if isinstance(resource,dict) else None
                if isinstance(target,str) and allowed(target,source)and in_scope(target,source,discovery=True):
                    found.append({'url':target,'depth':depth+1})
            return sorted(found,key=lambda r:r['url'])
        except (ValueError,UnicodeError,AttributeError):
            raise ValueError('public_catalog_index_invalid_json') from None
    parser = Links(); parser.feed(body.decode('utf-8', errors='replace'))
    found = []
    for href in parser.links:
        p = urlsplit(canonical_link(href,url,source)); target = urlunsplit((p.scheme, p.netloc, p.path, p.query, ''))
        if allowed(target, source)and in_scope(target,source,discovery=True)and (DOCUMENT.search(target)or ARCHIVE.search(target)or source.get('reviewed_document_discovery')):
            found.append({'url': target, 'depth': depth + 1})
    return sorted(found, key=lambda r: (not bool(DOCUMENT.search(r['url'])), r['url']))


def read_json(s3, key):
    try:
        r = s3.get_object(Bucket=BUCKET, Key=key)
    except s3.exceptions.ClientError as e:
        if e.response['Error']['Code'] in ('NoSuchKey', '404'): return None, None
        raise
    try: return json.loads(r['Body'].read()), r['ETag']
    finally: r['Body'].close()


def put(s3, key, body, media='application/json', **conditions):
    s3.put_object(Bucket=BUCKET, Key=key, Body=body, ContentType=media, ServerSideEncryption='AES256', **conditions)


def capture(s3, source, entry, mode):
    url = entry['url']
    if source['source']=='france_assurance_maladie_open_medic'and urlsplit(url).path.endswith('/download_file.php'):
        from open_medic_download import fresh_download
        url=fresh_download(url)
    if not allowed(url, source): raise ValueError('unreviewed_public_url')
    used_decodo = False
    gateway_representation=None
    # Redirects are individually checked against the reviewed host list.
    for _ in range(6):
        admit(url)
        try:
            response = requests.get(url, headers={'User-Agent': 'ConstellationResearch/1.0 (support@optima-holdings.com)', 'Accept': source.get('accept', '*/*')}, stream=True, timeout=(10, 45), allow_redirects=False)
        except requests.RequestException:
            if not source.get('decodo'):raise
            response=requests.Response();response.status_code=503;response._content_consumed=True
        if response.status_code in (301, 302, 303, 307, 308):
            following = urljoin(url, response.headers.get('Location', '')); response.close()
            if not allowed(following, source): raise ValueError('unreviewed_public_redirect')
            url = following; continue
        break
    else: raise ValueError('public_redirect_limit')
    with response:
        if response.status_code in (403, 429, 503) and source.get('decodo'):
            response.close()
            body = rendered(url); used_decodo = True
            if len(body) > MAX_BYTES: raise ValueError('public_asset_too_large')
            body,media,wrapper=decoded_response(body,url,'text/html; charset=utf-8')
            if wrapper is not None:
                sha=hashlib.sha256(wrapper).hexdigest();wrapper_key=PREFIX+'/objects/'+source['source']+'/'+sha;put(s3,wrapper_key,wrapper,'text/plain');gateway_representation={'s3_uri':'s3://'+BUCKET+'/'+wrapper_key,'sha256':sha,'encoding':'base64'}
            chunks=[body]
        else:
            if response.status_code != 200: raise ValueError('public_http_' + str(response.status_code))
            media = response.headers.get('Content-Type', 'application/octet-stream')
            if int(response.headers.get('Content-Length', 0)) > MAX_BYTES: raise ValueError('public_asset_too_large')
            chunks = response.iter_content(128 * 1024)
        # Scratch is RAM, and both per-process and aggregate memory limits apply.
        scratch=os.environ.get('TMPDIR','/dev/shm')
        if not (scratch=='/dev/shm' or scratch.startswith('/dev/shm/')):scratch='/dev/shm'
        with tempfile.NamedTemporaryFile(dir=scratch) as file:
            checksum = hashlib.sha256(); size = 0; first = b''
            for chunk in chunks:
                size += len(chunk)
                if size > MAX_BYTES: raise ValueError('public_asset_too_large')
                if len(first) < 8192: first += chunk[:8192 - len(first)]
                file.write(chunk); checksum.update(chunk)
            if not size: raise ValueError('public_empty_response')
            catalog_response=bool(source.get('catalog_index')and('json'in media.lower()or first.lstrip().startswith(b'{')))
            html = 'html' in media.lower() or first.lstrip().lower().startswith((b'<!doctype html', b'<html'))
            if source.get('asset_only') and html: raise ValueError('public_download_returned_html')
            if source.get('signature') and not first.startswith(bytes.fromhex(source['signature'])): raise ValueError('public_asset_signature_mismatch')
            if html and challenged(first):
                if not source.get('decodo') or used_decodo:raise ValueError('public_challenge_unresolved')
                body=rendered(url);body,rendered_media,wrapper=decoded_response(body,url,'text/html; charset=utf-8');used_decodo=True;
                if wrapper is not None:
                    sha=hashlib.sha256(wrapper).hexdigest();wrapper_key=PREFIX+'/objects/'+source['source']+'/'+sha;put(s3,wrapper_key,wrapper,'text/plain');gateway_representation={'s3_uri':'s3://'+BUCKET+'/'+wrapper_key,'sha256':sha,'encoding':'base64'}
                size=len(body);first=body[:8192];checksum=hashlib.sha256(body);file.seek(0);file.truncate();file.write(body);media=rendered_media;html='html'in media
            key = PREFIX + '/objects/' + source['source'] + '/' + checksum.hexdigest()
            file.flush(); s3.upload_file(file.name, BUCKET, key, ExtraArgs={'ServerSideEncryption': 'AES256', 'ContentType': media})
            verified = s3.get_object(Bucket=BUCKET, Key=key); actual = hashlib.sha256()
            try:
                for chunk in verified['Body'].iter_chunks(128 * 1024): actual.update(chunk)
            finally: verified['Body'].close()
            if actual.hexdigest() != checksum.hexdigest(): raise ValueError('public_readback_checksum_mismatch')
            file.seek(0); links = discover(file.read(min(size, 8 * 1024**2)), url, source, entry['depth']) if (html or catalog_response) else []
    record = {'source': source['source'], 'catalog_entry': source['catalog_entry'], 'mode': mode, 'retrieved_at': stamp(), 'source_url': url,
              'artifact_uri': 's3://' + BUCKET + '/' + key, 'sha256': checksum.hexdigest(), 'bytes': size, 'media_type': media,
              'artifact_kind': 'discovery_page' if (html or catalog_response) else 'public_document', 'via_decodo': used_decodo,
              'historical_target_start': '2016-01-01', 'historical_coverage': 'not_yet_audited', 'scope_note': source['scope_note']}
    from open_medic_download import stable_public_url
    record['source_url']=stable_public_url(record['source_url'])
    if gateway_representation:record['gateway_representation']=gateway_representation
    # Index pages establish crawl state, never a substantive provider record.
    # Do not send them to metadata labelling where they could only fail the raw
    # artifact contract; the linked document gets its own immutable receipt.
    if record['artifact_kind'] != 'discovery_page' or source.get('publish_discovery_receipts'):
        receipt = PREFIX + '/athena/' + uuid.uuid4().hex + '.jsonl'
        put(s3, receipt, encode(record), 'application/x-ndjson')
    return record, links


def run(source, mode, limit=6, s3=None):
    if source.get('enabled', True) is False:
        raise ValueError('public_source_paused')
    if mode == 'historical' and os.environ.get('CONSTELLATION_ROLE') != 'worker': raise ValueError('historical_capture_requires_c7i')
    if mode == 'daily' and os.environ.get('CONSTELLATION_ROLE', 'controller') != 'controller': raise ValueError('daily_capture_requires_t3')
    s3 = s3 or boto3.client('s3', region_name='us-east-1')
    # A raw-content revision starts a new immutable crawl frontier without
    # deleting the previous audit trail.  Use it when a former discovery-only
    # route gains a substantive-file acquisition path.
    revision = source.get('raw_content_revision')
    key = PREFIX + '/states/' + mode + '/' + source['source'] + (('/' + revision) if revision else '') + '.json'
    state, token = read_json(s3, key)
    today = stamp()[:10]
    if state is None or (mode == 'daily' and state.get('day') != today):
        state = {'day': today, 'frontier': [{'url': u, 'depth': 0} for u in source['seeds']], 'done': {}, 'failures': {}, 'attempts_today': 0}
    obsolete={r['url'] for r in state['frontier'] if r['depth']==0 and r['url'] not in source['seeds']}
    if obsolete:
        state['frontier']=[r for r in state['frontier'] if r['url'] not in obsolete]
        for url in obsolete:
            if url in state['failures']:state.setdefault('retired_failures',{})[url]=state['failures'].pop(url)
    known=set(state['done'])|{r['url'] for r in state['frontier']}
    state['frontier'] += [{'url':u,'depth':0} for u in source['seeds'] if u not in known]
    outcomes = []
    if mode == 'daily': limit = min(limit, max(0, 12 - state['attempts_today']))
    for _ in range(limit):
        ready = next((i for i, r in enumerate(state['frontier']) if r.get('retry_after', '') <= stamp()), None)
        if ready is None: break
        entry = state['frontier'].pop(ready); state['attempts_today'] += 1
        try:
            record, links = capture(s3, source, entry, mode); state['done'][entry['url']] = {'at': record['retrieved_at'], 'sha256': record['sha256'], 'kind': record['artifact_kind']}
            state['failures'].pop(entry['url'], None)
            known = set(state['done']) | {r['url'] for r in state['frontier']}
            for row in links:
                if row['url'] not in known and len(known) < 5000:
                    state['frontier'].append(row); known.add(row['url'])
            outcomes.append({'status': 'captured', **record})
        except Exception as error:
            from datetime import timedelta
            reason = str(error) if type(error) is ValueError or type(error).__name__=='ScrapeError' else type(error).__name__
            state['failures'][entry['url']] = {'at': stamp(), 'reason': reason}
            entry['retry_after'] = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(); state['frontier'].append(entry)
            outcomes.append({'status': 'failed', 'url': entry['url'], 'reason': reason})
        state['updated_at'] = stamp()
        put(s3, key, encode(state), **({'IfMatch': token} if token else {'IfNoneMatch': '*'}))
        _, token = read_json(s3, key)
    report = {'collector': 'public_document_capture', 'source': source['source'], 'catalog_entry': source['catalog_entry'], 'mode': mode,
              'at': stamp(), 'outcomes': outcomes, 'captured_urls': len(state['done']), 'remaining_urls': len(state['frontier']),
              'failed_urls': len(state['failures']), 'route_drained': not state['frontier'],
              'historical_complete': False, 'coverage_note': 'Public archive discovery and raw artifact capture only. No dated coverage or complete structured dataset is certified.'}
    receipt_prefix = os.environ.get('CONSTELLATION_OPERATION_RECEIPT_PREFIX', 'constellation-backfill/public-capture/daily-receipts')
    receipt_key = 'research-data/' + receipt_prefix + '/' + uuid.uuid4().hex + '.json'
    put(s3, receipt_key, encode(report)); print(json.dumps({'report_key': receipt_key.removeprefix('research-data/'), 'public_capture_summary': {k: report[k] for k in ('source', 'mode', 'captured_urls', 'remaining_urls', 'failed_urls')}}), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--source', required=True); parser.add_argument('--mode', required=True, choices=('daily', 'historical')); parser.add_argument('--limit', type=int, default=6)
    args = parser.parse_args(); plan = json.loads((ROOT / 'config/constellation-public-sources.json').read_text())
    source = next(s for s in plan['sources'] if s['source'] == args.source)
    run(source, args.mode, args.limit)


if __name__ == '__main__': main()
