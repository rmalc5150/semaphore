"""Replay reviewed legacy TED issues through the specialist evidence and publication pipeline."""
import argparse
from contextlib import closing
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import zlib
import xml.etree.ElementTree as ET

import boto3

from collection_storage import AlreadyComplete, CollectionRun, StorageSettings, now, task_spec, write_json
from market_archive_import import read_universe
from market_source_capture import immutable_put
from regulatory_collection import require
from research_contract import ROOT, digest, load_json
from specialist_inputs import SpecialistClient, item, normalized
from specialist_publication import publish
from ted_enrichment import bounded_notice_items, local, parse_xml
from ted_packages import MAX_ARCHIVE, index_archive, request


def read_issue(issue, storage, s3, client, codes):
    url = 'https://ted.europa.eu/packages/daily/' + issue
    with tempfile.TemporaryFile() as archive, closing(sqlite3.connect('')) as database:
        digestor = hashlib.sha256()
        total = 0
        with request(url) as response:
            require(response.status == 200, 'ted_archive_bad_status')
            length = response.headers.get('Content-Length')
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                require(total <= MAX_ARCHIVE, 'ted_archive_too_large')
                archive.write(chunk)
                digestor.update(chunk)
            require(length is None or int(length) == total, 'ted_archive_truncated')
        archive.seek(0)
        database.execute('CREATE TABLE notices(id TEXT PRIMARY KEY, member TEXT, xml BLOB, sha256 TEXT)')
        count = index_archive(archive, database)
        archive.seek(0)
        sha = digestor.hexdigest()
        key = 'source_documents/ted_notices/' + sha
        immutable_put(s3, storage.s3_bucket, storage.s3_prefix + '/' + key, archive, sha,
                      'application/gzip', verify=True)
        receipt = {'key': key, 'sha256': sha, 'source_url': url, 'retrieved_at': now(),
                   'archive_bytes': total, 'archive_members': count, 'issue': issue}
        rows = []
        issue_days = set()
        for identity, member, compressed, checksum in database.execute('SELECT * FROM notices ORDER BY id'):
            require(identity.endswith('-' + issue[:4]), 'ted_issue_year_mismatch')
            raw = zlib.decompress(compressed)
            require(hashlib.sha256(raw).hexdigest() == checksum, 'ted_issue_xml_checksum_mismatch')
            require(not re.search(br'<!\s*(DOCTYPE|ENTITY)', raw, re.I), 'ted_xml_entities_rejected')
            root = ET.fromstring(raw)
            days = {(e.text or '') for e in root.iter() if local(e.tag) == 'DATE_PUB'}
            require(len(days) == 1, 'ted_issue_pub_date_ambiguous')
            day = datetime.strptime(days.pop(), '%Y%m%d').date()
            require(day.year == int(issue[:4]), 'ted_issue_pub_year_mismatch')
            issue_days.add(day)
            matched = sorted(codes & {e.get('CODE') for e in root.iter() if local(e.tag) == 'CPV_CODE'})
            if not matched:
                continue
            enrichment = parse_xml(raw, identity)
            enrichment['retrieval_method'] = 'daily_xml_package'
            client.evidence.clear()
            client.save(raw, url, 'application/xml')
            xml = {**client.evidence[-1], 'package_member': member, 'issue': issue}
            row = {'publication-number': identity, 'publication-date': day.isoformat(),
                   'ojs-number': issue, 'classification-cpv': matched,
                   'enrichment': enrichment, 'notice_xml': raw.decode('utf-8-sig')}
            for item_row in bounded_notice_items(identity, row, 'https://ted.europa.eu/en/notice/-/detail/' + identity,
                                                 day.isoformat(), item):
                rows.append((item_row, [xml, receipt]))
        require(len(issue_days) == 1, 'ted_issue_days_inconsistent')
        return issue_days.pop(), receipt, rows


def capture_issue(issue, settings, s3, store, universe, taxonomy, source):
    codes = set(source['cpv'])
    day, receipt, rows = read_issue(issue, settings, s3, SpecialistClient(store, 'ted_notices'), codes)
    params = {'issue': issue, 'archive_sha256': receipt['sha256'], 'cpv': sorted(codes)}
    spec = task_spec('ted_notices', 'specialist_inputs', 'historical', day.isoformat() + 'T00:00:00Z',
                     (day + timedelta(days=1)).isoformat() + 'T00:00:00Z',
                     {'coverage_note': 'Official daily OJ S XML, exact configured CPVs and issue publication dates.',
                      'parameters': params, 'source_id': source['source_id']},
                     'ted-archive-1', universe, taxonomy)
    try:
        run = CollectionRun.start(store, spec, universe, taxonomy, settings, resume=True)
    except AlreadyComplete as complete:
        manifest = str(complete)
    else:
        run.commit_page((normalized(row, run, evidence) for row, evidence in rows), exhausted=True, next_cursor=None)
        manifest = run.finish('complete', expected_records=len(rows))
    window_id = digest(manifest)
    key = 'operations/specialists/publication-queue/' + window_id + '.json'
    if store.get(key) is None:
        write_json(store, key, {'window_id': window_id, 'manifests': [manifest], 'queued_at': now()})
    return {'issue': issue, 'date': day.isoformat(), 'rows': len(rows), 'archive': receipt,
            'notices': len({evidence[0]['sha256'] for _, evidence in rows}),
            'first_xml': rows[0][1][0] if rows else None, 'manifest': manifest, 'window_id': window_id}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--issue', action='append', required=True, metavar='YYYYNNNNN')
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    issues = list(dict.fromkeys(args.issue))
    if len(issues) > 5 or any(not re.fullmatch(r'20[0-9]{7}', issue) or
                              not 1 <= int(issue[4:]) <= 366 for issue in issues):
        parser.error('Provide at most five official OJ S issue IDs, for example 201600001.')
    settings = StorageSettings.load(ROOT / 'config/collection-storage.s3.json')
    s3 = boto3.client('s3', region_name=settings.region)
    store = settings.store(s3)
    plan = load_json(ROOT / 'config/constellation-specialist-historical.json')
    from source_pauses import is_paused
    if is_paused('ted_notices'):
        parser.error('TED historical collection is paused.')
    source = next(source for source in plan['sources'] if source['source'] == 'ted_notices')
    universe = read_universe(s3, settings.s3_bucket)
    taxonomy = load_json(ROOT / 'config/sectors.v1.json')
    results = [capture_issue(issue, settings, s3, store, universe, taxonomy, source) for issue in issues]
    report = {'issues': results}
    if args.publish:
        with tempfile.TemporaryDirectory(prefix='ted-archive-release-') as build_root:
            report['publication'] = publish(store, settings, plan, len(results),
                                            window_ids=[result['window_id'] for result in results],
                                            build_root=Path(build_root))
    print(json.dumps(report, indent=2), flush=True)
    return int(report.get('publication', {}).get('status') == 'failed')


if __name__ == '__main__':
    raise SystemExit(main())
