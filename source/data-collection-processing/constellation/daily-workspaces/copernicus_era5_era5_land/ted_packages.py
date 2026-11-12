"""Official TED daily XML packages, downloaded once and indexed on disk."""
import fcntl
import hashlib
import json
import os
from contextlib import closing
import re
import sqlite3
import tarfile
import tempfile
import time
import zlib
from pathlib import Path
from urllib.request import Request, build_opener
from fda_access import NoRedirect
from regulatory_collection import require, SourceIssue
from research_contract import ROOT

CACHE = ROOT / 'ted-package-cache'
MAX_ARCHIVE = 256 * 1024 * 1024
MAX_XML = 16 * 1024 * 1024


def request(url, body=None):
    return build_opener(NoRedirect()).open(Request(url, data=body, headers={
        'User-Agent': 'ProcurementDataCollector/1.0',
        'Content-Type': 'application/json', 'Accept-Encoding': 'identity'}), timeout=45)


def issue_number(value):
    if isinstance(value, list):
        value = value[0] if len(value) == 1 else ''
    value = str(value or '')
    match = re.fullmatch(r'(\d{1,5})/(\d{4})', value)
    if match:
        return match[2] + match[1].zfill(5)
    require(re.fullmatch(r'\d{9}', value), 'ted_missing_ojs_number')
    return value


def resolve_issue(data, identity, client):
    if data.get('ojs-number'):
        return issue_number(data['ojs-number'])
    # Older saved records did not project OJS number. Resolve their exact notice.
    body = json.dumps({'query': 'publication-number = ' + identity,
        'fields': ['publication-number', 'ojs-number'], 'limit': 1, 'scope': 'ALL',
        'onlyLatestVersions': False, 'checkQuerySyntax': True}).encode()
    url = 'https://api.ted.europa.eu/v3/notices/search'
    try:
        with request(url, body) as response:
            require(response.status == 200, 'ted_package_lookup_http')
            raw = response.read(1024 * 1024 + 1)
        require(len(raw) <= 1024 * 1024, 'ted_package_lookup_oversize')
        result = json.loads(raw)
        require(not result.get('timedOut') and result.get('totalNoticeCount') == 1,
                'ted_package_lookup_count')
        row = result['notices'][0]
        actual = row['publication-number']
        if isinstance(actual, list): actual = actual[0]
        require(str(actual).lstrip('0') == identity.lstrip('0'), 'ted_package_lookup_identity')
        issue = issue_number(row.get('ojs-number'))
        client.save(raw, url, 'application/json')
        return issue
    except SourceIssue:
        raise
    except Exception as exc:
        raise SourceIssue('ted_package_lookup_failed') from exc


def index_archive(stream, db):
    """No filesystem extraction; only regular XML members enter the cache."""
    count = total = 0
    with tarfile.open(fileobj=stream, mode='r|gz') as archive:
        for member in archive:
            if not member.isfile() or not member.name.lower().endswith('.xml'):
                continue
            match = re.fullmatch(r'0*(\d+)_(\d{4})\.xml', Path(member.name).name)
            require(match is not None and 0 < member.size <= MAX_XML, 'ted_package_invalid_member')
            raw = archive.extractfile(member).read(MAX_XML + 1)
            require(len(raw) == member.size, 'ted_package_truncated_member')
            total += len(raw)
            count += 1
            require(total <= 2 * 1024**3 and count <= 50000, 'ted_package_expansion_limit')
            identity = str(int(match[1])) + '-' + match[2]
            checksum = hashlib.sha256(raw).hexdigest()
            old = db.execute('SELECT sha256 FROM notices WHERE id=?', (identity,)).fetchone()
            require(old is None or old[0] == checksum, 'ted_package_conflicting_member')
            db.execute('INSERT OR IGNORE INTO notices VALUES (?,?,?,?)',
                       (identity, member.name, zlib.compress(raw), checksum))
    require(count > 0, 'ted_package_no_xml')
    return count


def prune_cache(cache, keep):
    files = sorted(cache.glob('*.sqlite3'), key=lambda p: p.stat().st_mtime)
    total = sum(p.stat().st_size for p in files)
    for path in files:
        if path.stem == keep or (total <= 512 * 1024**2 and path.stat().st_mtime > time.time() - 14 * 86400):
            continue
        with path.with_suffix('.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                continue
            size = path.stat().st_size
            path.unlink()
            total -= size


def package_xml(data, identity, client, cache=CACHE):
    require(re.fullmatch(r'\d+-\d{4}', identity), 'ted_invalid_notice_number')
    start = len(client.evidence)
    issue = resolve_issue(data, identity, client)
    url = 'https://ted.europa.eu/packages/daily/' + issue
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    prune_cache(cache, issue)
    with (cache / (issue + '.lock')).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with closing(sqlite3.connect(cache / (issue + '.sqlite3'))) as db:
            db.executescript('CREATE TABLE IF NOT EXISTS notices (id TEXT PRIMARY KEY, member TEXT, xml BLOB, sha256 TEXT);'
                             'CREATE TABLE IF NOT EXISTS receipt (id INTEGER PRIMARY KEY, value TEXT);')
            prior = db.execute('SELECT value FROM receipt WHERE id=1').fetchone()
            if prior is None:
                # A failed/unpublished package is retried on the next invocation.
                failure = cache / (issue + '-retry.json')
                if failure.exists():
                    last = json.loads(failure.read_text())
                    require(time.time() >= last['retry_at'], 'ted_package_retry_deferred')
                try:
                    with tempfile.TemporaryFile() as stream:
                        sha = hashlib.sha256()
                        size = 0
                        with request(url) as response:
                            require(response.status == 200, 'ted_package_http_' + str(response.status))
                            length = response.headers.get('Content-Length')
                            if length: require(int(length) <= MAX_ARCHIVE, 'ted_package_too_large')
                            while True:
                                chunk = response.read(1024 * 1024)
                                if not chunk: break
                                size += len(chunk)
                                require(size <= MAX_ARCHIVE, 'ted_package_too_large')
                                stream.write(chunk); sha.update(chunk)
                            require(not length or size == int(length), 'ted_package_truncated_download')
                        stream.seek(0)
                        with db:
                            db.execute('DELETE FROM notices')
                            count = index_archive(stream, db)
                            from collection_storage import now
                            receipt = {'source_url': url, 'retrieved_at': now(), 'archive_sha256': sha.hexdigest(),
                                       'archive_bytes': size, 'members': count}
                            db.execute('INSERT INTO receipt VALUES (1,?)', (json.dumps(receipt),))
                    failure.unlink(missing_ok=True)
                except Exception as exc:
                    failure.write_text(json.dumps({'retry_at': time.time() + 1800}))
                    if isinstance(exc, SourceIssue): raise
                    raise SourceIssue('ted_package_download_or_index_failed') from exc
            else:
                receipt = json.loads(prior[0])
            canonical = str(int(identity.split('-')[0])) + '-' + identity.split('-')[1]
            row = db.execute('SELECT member,xml,sha256 FROM notices WHERE id=?', (canonical,)).fetchone()
            require(row is not None, 'ted_notice_missing_from_daily_package')
            member, compressed, checksum = row
            raw = zlib.decompress(compressed)
            os.utime(cache / (issue + '.sqlite3'), None)
            require(hashlib.sha256(raw).hexdigest() == checksum, 'ted_cached_xml_hash_mismatch')
    # Archive provenance is retained with each independently archived original XML.
    client.save(raw, url, 'application/xml')
    client.evidence[-1].update(package_member=member, package_receipt=receipt)
    return raw, client.evidence[start:]
