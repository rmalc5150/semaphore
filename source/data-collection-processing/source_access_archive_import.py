"""Verify and stage the native contents of a source-access export ZIP."""
import argparse
from collections import Counter
import csv
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urlsplit
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import boto3

from research_contract import canonical_json, digest
from temporary_archive_formats import archive_rows, local_day, safe_members
from temporary_archive_intake import exact_bytes, put_checked, put_json
from temporary_archive_stage import BUCKET, CONTROL, EXPORTS, REGION, source_id, staged_key, write_inventory

BUNDLES = {
    'safety-gate': ('Safety-Gate-Weekly-Recapture.zip', 'ec.europa.eu'),
    'cdc': ('CDC-FluView-Recapture.zip', 'gis.cdc.gov'),
    'nbim': ('NBIM-Holdings-API-Snapshots.zip', 'www.nbim.no'),
    'gem': ('GEM-Current-Assets.zip', 'api.globalenergymonitor.org'),
}


def group_files(archive, names, group, host):
    manifests = [name for name in names if name.endswith('/manifest.json') and group in name.split('/')]
    if len(manifests) != 1:
        raise ValueError('missing_or_duplicate_source_access_manifest:'+group)
    manifest = manifests[0]
    entries = json.loads(archive.read(manifest))
    root = manifest.rsplit('/', 1)[0]
    selected, skipped = {}, []
    for entry in entries:
        relative = entry['file']
        file = f'{root}/{relative}' if '/' not in relative else f'source-access/{relative}'
        name = PurePosixPath(relative).name
        url = urlsplit(entry['url'])
        if url.scheme != 'https' or url.hostname != host or not file.startswith(root+'/'):
            raise ValueError('unrecognized_provider_member:'+group)
        if file not in names:
            if group == 'nbim' and re.fullmatch(r'(201[6-9]|2020)-12-31-ri\.csv', name) and 'sha256' not in entry:
                skipped.append(name)
                continue
            raise ValueError('missing_archived_member:'+file)
        body = archive.read(file)
        sha = hashlib.sha256(body).hexdigest()
        if sha != entry['sha256'] or entry.get('bytes', len(body)) != len(body) or name in selected:
            raise ValueError('source_access_manifest_checksum_or_identity_mismatch:'+file)
        captured = datetime.fromisoformat(entry['retrieved_at_utc'].replace('Z', '+00:00'))
        if not captured.tzinfo:
            raise ValueError('capture_timestamp_requires_offset')
        selected[name] = (body, {'source_member': file, 'bytes': len(body), 'sha256': sha,
                                 'url': entry['url'], 'retrieved_at_utc': entry['retrieved_at_utc']})
    if not selected:
        raise ValueError('empty_source_access_group:'+group)
    return selected, skipped


def report_id(name):
    match = re.search(r'Report-(\d{4})-(\d+)\.xml$', name)
    return tuple(map(int, match.groups())) if match else None


def xml(body):
    if re.search(rb'<!DOCTYPE|<!ENTITY', body, re.IGNORECASE):
        raise ValueError('unexpected_xml_dtd_or_entity')
    return ElementTree.fromstring(body)


def index_weekly(index, reports):
    dates = {}
    for row in xml(index).findall('weeklyReport'):
        reference = row.findtext('reference')
        if reference and report_id(reference+'.xml'):
            dates[reference] = local_day(row.findtext('publicationDate').replace('-', '/'), '%d/%m/%Y')
    result = io.StringIO()
    csv_writer = csv.writer(result)
    csv_writer.writerow(['report_reference', 'publication_date', 'original_url', 'saved_filename'])
    for name, (_, evidence) in sorted(reports.items()):
        identifier = name.removesuffix('.xml')
        csv_writer.writerow([identifier, dates[identifier], evidence['url'], name])
    return result.getvalue().encode()


def previous_archives(s3, uri, keys):
    prefix = f's3://{BUCKET}/'
    if not uri.startswith(prefix+CONTROL+'/runs/') or not uri.endswith('.json'):
        raise ValueError('unexpected_previous_intake_receipt')
    result = json.loads(exact_bytes(s3, uri.removeprefix(prefix)))
    for item in result['processed']:
        if item['object'] not in keys:
            continue
        manifest = json.loads(exact_bytes(s3, item['processing_manifest'].removeprefix(prefix)))['raw']
        key = manifest['s3_uri'].removeprefix(prefix)
        yield item['object'], exact_bytes(s3, key, manifest['sha256'])


def make_bundle(path, entries, extras, parent):
    dates = {e['retrieved_at_utc'][:10] for _, e in entries.values()}
    if len(dates) != 1:
        raise ValueError('expected_one_capture_day_per_bundle')
    document = {'attachment': parent, 'capture_date': dates.pop(),
                'original_members': {name: evidence for name, (_, evidence) in sorted(entries.items())}}
    extras = {**extras, 'capture-provenance.json': canonical_json(document)+b'\n'}
    with ZipFile(path, 'w') as bundle:
        for name, body in sorted(list(extras.items())+[(n, body) for n, (body, _) in entries.items()]):
            bundle.writestr(ZipInfo(name), body, compress_type=ZIP_DEFLATED)


def retain_file(s3, path, key, checksum):
    with path.open('rb') as file:
        return put_checked(s3, key, file, checksum, path.stat().st_size, 'application/zip')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--baseline-receipt', required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    args.workspace.mkdir(parents=True, exist_ok=True)
    with args.archive.open('rb') as file:
        sha = hashlib.file_digest(file, 'sha256').hexdigest()
    parent_key = f'{EXPORTS}/intake-attachments/{sha}/original.zip'
    parent = {'s3_uri': f's3://{BUCKET}/{parent_key}', 'sha256': sha, 'bytes': args.archive.stat().st_size}
    s3 = boto3.client('s3', region_name=REGION)
    old = dict(previous_archives(s3, args.baseline_receipt,
                                 {'Safety-Gate-Weekly-Originals.zip', 'NBIM-Holdings-Exports.zip'}))
    if len(old) != 2:
        raise ValueError('missing_previous_safety_gate_or_nbim_archive')
    with ZipFile(args.archive) as archive:
        names = set(safe_members(archive))
        if sum(i.file_size for i in archive.infolist()) > 1024**3:
            raise ValueError('attachment_expands_beyond_size_limit')
        groups = {group: group_files(archive, names, group, host) for group, (_, host) in BUNDLES.items()}
    retained = retain_file(s3, args.archive, parent_key, sha)
    assert retained == parent

    items, audit = [], {}
    for group, (entries, missing) in groups.items():
        key, _ = BUNDLES[group]
        extras = {}
        if group == 'safety-gate':
            report_index, _ = entries.pop('index.xml')
            extras['publication-index.csv'] = index_weekly(report_index, entries)
            with ZipFile(io.BytesIO(old['Safety-Gate-Weekly-Originals.zip'])) as previous:
                prior = {report_id(name): name for name in previous.namelist() if report_id(name)}
                current = {report_id(name): name for name in entries}
                unchanged = sum(previous.read(prior[i]) == entries[current[i]][0] for i in prior.keys() & current.keys())
                audit[group] = {'files': len(current), 'unchanged_bytes': unchanged,
                                       'recaptured_with_changed_bytes': len(current.keys() & prior.keys())-unchanged,
                                       'added_reports': [list(i) for i in sorted(current.keys()-prior.keys())]}
        elif group == 'nbim':
            files = [name for name in entries if name.endswith('.csv')]
            with ZipFile(io.BytesIO(old['NBIM-Holdings-Exports.zip'])) as previous:
                if any(name not in previous.namelist() or entries[name][0] != previous.read(name) for name in files):
                    raise ValueError('nbim_csv_new_or_revised_requires_review_before_deduplication')
            for name in files:
                entries.pop(name)
            entries.pop('init.json', None)
            audit['nbim'] = {'duplicate_csvs': len(files), 'api_edition_files': len(entries),
                             'absent_renewable_infrastructure_exports': missing}
        elif group == 'gem':
            entries.pop('openapi.json')

        path = args.workspace/key
        make_bundle(path, entries, extras, parent)
        totals = Counter(t for t,*_ in archive_rows(path, source_id(key), key))
        if not totals:
            raise ValueError('no_rows_in_checked_bundle:'+key)
        with path.open('rb') as file:
            checksum = hashlib.file_digest(file, 'sha256').hexdigest()
        size = path.stat().st_size
        identity = f'"{checksum}"'
        destination = staged_key(key, identity, size)
        ref = retain_file(s3, path, destination, checksum)
        stamp = s3.head_object(Bucket=BUCKET, Key=destination, ChecksumMode='ENABLED')
        items.append({'inbox_key': key, 'inbox_etag': identity, 'bytes': size, 'source': source_id(key),
                      'key': destination, 'etag': stamp['ETag'], 'sha256_base64': stamp['ChecksumSHA256'],
                      'staged_at': stamp['LastModified'].isoformat(), 'attachment': parent})
        audit[group] = {**audit.get(group, {}), 'native_tables': dict(totals), 'bundle': ref}
        print(json.dumps({'source': group, 'native_rows': dict(totals)}), flush=True)
    inventory, checksum = write_inventory(s3, items, [])
    result = {'inventory': inventory, 'sha256': checksum, 'attachment': parent, 'sources': audit}
    result['audit_uri'] = put_json(s3, f'{CONTROL}/attachment-audits/{checksum}/{digest(result)}.json', result)['s3_uri']
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
