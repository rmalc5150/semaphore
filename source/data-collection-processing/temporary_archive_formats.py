"""Validate the supplied native export layouts and yield addressable data rows."""
import csv
from datetime import date, datetime
import io
import json
import re
from xml.etree import ElementTree
from zipfile import ZipFile

def csv_rows(body, *, encoding='utf-8-sig', delimiter=',', required, optional_missing=()):
    reader = csv.DictReader(io.StringIO(body.decode(encoding), newline=''), delimiter=delimiter)
    names = [name.strip() for name in (reader.fieldnames or [])]
    if not required <= set(names) or len(set(names)) != len(names):
        raise ValueError('native_csv_columns_missing_or_duplicated')
    reader.fieldnames = names
    for row in reader:
        if all(value in ('', None) for value in row.values()):
            continue
        if None in row or any(value is None and name not in optional_missing for name, value in row.items()):
            raise ValueError('native_csv_row_column_mismatch')
        yield row


def safe_members(archive):
    names = set()
    for item in archive.infolist():
        if item.is_dir():
            continue
        name = item.filename
        if (name in names or any(part in {'', '.', '..'} for part in name.split('/'))
                or '\\' in name or item.file_size > 128 * 1024**2):
            raise ValueError('unsafe_or_duplicate_archive_member')
        names.add(name)
        yield name


def local_day(value, pattern):
    return datetime.strptime(value, pattern).date().isoformat() if value else None


def fluview(archive):
    for name in safe_members(archive):
        match = re.fullmatch(r'(2015-16|2016-17|2016-01-01_to_2026-10-31)/(ILINet|WHO_NREVSS)-[a-z]+-(.+)\.csv', name)
        if not match:
            if name == 'README.txt' or name.startswith('original-pilot-downloads/'):
                continue
            raise ValueError('unexpected_fluview_zip_member')
        scope, family, kind = match.groups()
        table = 'ilinet' if family == 'ILINet' else (
            'lab_clinical' if kind.endswith('_Clinical_Labs') else 'lab_public_health')
        if '_to_' not in scope:
            table += '_pilot'
        for row in csv_rows(archive.read(name), required={'REGION TYPE', 'REGION'}):
            if row.get('YEAR') and row.get('WEEK'):
                year, week = int(row['YEAR']), int(row['WEEK'])
                if not (2015 <= year <= 2026 and 1 <= week <= 53):
                    raise ValueError('invalid_fluview_mmwryear_or_week')
                period, basis = f'{year}-W{week:02}', 'mmwr_week'
            elif row.get('SEASON_DESCRIPTION'):
                period, basis = row['SEASON_DESCRIPTION'], 'cdc_season'
            else:
                raise ValueError('fluview_period_missing')
            yield table, name, None, period, basis, row


def nbim(archive):
    classes = {'eq': 'equity', 'fi': 'fixed_income', 're': 'real_estate', 'ri': 'renewable_infrastructure'}
    for name in safe_members(archive):
        match = re.fullmatch(r'(20\d\d-\d\d-\d\d)-(eq|fi|re|ri)\.csv', name)
        if not match:
            if name in ('2016-annual-report.pdf', 'README.txt'):
                continue
            raise ValueError('unexpected_nbim_zip_member')
        day, category = match.groups()
        date.fromisoformat(day)
        for row in csv_rows(archive.read(name), encoding='utf-16', delimiter=';',
                            required={'Region', 'Country'}, optional_missing={'Incorporation Country'}):
            yield classes[category], name, None, day, 'holdings_snapshot_date', row


def cnmv(archive):
    # Match exported registry numbers to saved publisher HTML. Keep linked
    # individual document URLs as links because those documents aren't in this ZIP.
    required = {'notification_date', 'issuer', 'declarant', 'notification_reason',
                'registry_number', 'original_document_url'}
    names = set(safe_members(archive))
    if 'notifications.csv' not in names:
        raise ValueError('cnmv_results_csv_missing')
    body = archive.read('notifications.csv')
    identifiers = set()
    for row in csv_rows(body, required=required):
        identifier = row['registry_number']
        if not re.fullmatch(r'\d{10}', identifier):
            raise ValueError('invalid_cnmv_registry_number')
        identifiers.add(identifier.encode())
    for name in sorted(names):
        if not re.fullmatch(r'source-pages/(20\d{2}|full)-\d{4}\.html', name):
            continue
        page = archive.read(name)
        if b'Notificaciones de los directivos' not in page[:4096]:
            raise ValueError('unexpected_cnmv_provider_page')
        if identifiers:
            identifiers.difference_update(re.findall(rb'(?<!\d)20\d{8}(?!\d)', page))
    if identifiers:
        raise ValueError(f'cnmv_registry_numbers_missing_from_source_pages:{len(identifiers)}')
    for row in csv_rows(body, required=required):
        day = date.fromisoformat(row['notification_date']).isoformat()
        yield 'current_notifications', 'notifications.csv', row['registry_number'], day, 'notification_date', row


def safety_gate(archive, weekly):
    names = list(safe_members(archive))
    index = {}
    if weekly:
        fields = {'report_reference', 'publication_date', 'original_url', 'saved_filename'}
        index = {row['saved_filename']: row for row in csv_rows(archive.read('publication-index.csv'), required=fields)}
        if set(index) != {name for name in names if name.endswith('.xml')}:
            raise ValueError('safety_gate_weekly_index_does_not_match_originals')
    for name in names:
        if not name.endswith('.xml'):
            continue
        body = archive.read(name)
        if re.search(rb'<!DOCTYPE|<!ENTITY', body, re.IGNORECASE):
            raise ValueError('unexpected_xml_dtd_or_entity_definition')
        root = ElementTree.fromstring(body)
        if root.tag != 'Safety-Gate' or root.findtext('report_language') != 'en':
            raise ValueError('not_an_english_safety_gate_export')
        report = index.get(name)
        if report and local_day(root.findtext('report_date'), '%d/%m/%Y') != report['publication_date']:
            raise ValueError('safety_gate_native_report_date_mismatch')
        table = ('weekly_alerts' if weekly else
                 'monthly_alerts' if re.fullmatch(r'Safety-Gate-20\d\d-\d\d\.xml', name) else 'pre2016_pilot')
        for node in root.findall('notifications'):
            identifier = node.findtext('caseNumber')
            if not identifier or not node.findtext('reference'):
                raise ValueError('safety_gate_alert_identity_missing')
            day = local_day((node.findtext('publicationDate') or '').replace('-', '/'), '%d/%m/%Y')
            yield table, name, identifier, day, 'alert_publication_date', {
                'report': report, 'alert_xml': ElementTree.tostring(node, encoding='unicode'),
            }


def ferc_submissions(archive):
    name = 'CSV_SubmissionsByDate.CSV'
    if set(safe_members(archive)) != {name}:
        raise ValueError('unexpected_ferc_submission_zip_members')
    fields = {'Filing_Organization_Id', 'Quarter', 'SellerName', 'Filing_Date', 'Orig_Refile'}
    for row in csv_rows(archive.read(name), required=fields):
        if not re.fullmatch(r'Q[1-4]:20\d{2}', row['Quarter']) or not row['Filing_Organization_Id'].isdigit():
            raise ValueError('invalid_ferc_submission_identity')
        day = local_day(row['Filing_Date'], '%m/%d/%Y %I:%M:%S %p')
        if day is None:
            raise ValueError('missing_ferc_submission_filing_date')
        yield 'official_submissions', name, row['Filing_Organization_Id'], day, 'filing_date', row


def archive_rows(path, number, key):
    from handoff_formats import PARSERS

    with ZipFile(path) as archive:
        if key in PARSERS:
            yield from PARSERS[key](archive)
        elif key == 'Safety-Gate-Weekly-Recapture.zip':
            for _, member, identifier, day, basis, row in safety_gate(archive, True):
                yield 'weekly_alerts_recapture', member, identifier, day, basis, row
        elif key == 'CDC-FluView-Recapture.zip':
            yield from fluview_recapture(archive)
        elif key == 'NBIM-Holdings-API-Snapshots.zip':
            yield from nbim_api(archive)
        elif key == 'GEM-Current-Assets.zip':
            yield from gem_assets(archive)
        elif number == 189:
            yield from safety_gate(archive, 'Weekly' in key)
        elif number == 235:
            yield from fluview(archive)
        elif number == 255:
            yield from cnmv(archive)
        elif number == 256:
            yield from nbim(archive)
        elif number == 266:
            yield from ferc_submissions(archive)
        else:
            raise ValueError('unsupported_archive_source')


def fluview_recapture(archive):
    categories = {'ILINet.csv': 'ilinet', 'ICL_NREVSS_Clinical_Labs.csv': 'lab_clinical',
                  'ICL_NREVSS_Public_Health_Labs.csv': 'lab_public_health'}
    for name in safe_members(archive):
        if name == 'capture-provenance.json':
            continue
        if not re.fullmatch(r'(ILINet|WHO_NREVSS)-regiontype-[1235]\.zip', name):
            raise ValueError('unexpected_fluview_recapture_member')
        with ZipFile(io.BytesIO(archive.read(name))) as download:
            expected = {'ILINet.csv'} if name.startswith('ILINet') else set(categories)-{'ILINet.csv'}
            members = set(safe_members(download))
            if members != expected:
                raise ValueError('unexpected_fluview_native_tables')
            for member in sorted(members):
                preamble, _, csv = download.read(member).partition(b'\n')
                if not preamble.lstrip(b'\xef\xbb\xbf"').startswith((b'PERCENTAGE OF VISITS', b'*Beginning for the')):
                    raise ValueError('unexpected_fluview_provider_preamble')
                for row in csv_rows(csv, required={'REGION TYPE', 'REGION'}):
                    if row.get('YEAR') and row.get('WEEK'):
                        year, week = int(row['YEAR']), int(row['WEEK'])
                        if not (2015 <= year <= 2100 and 1 <= week <= 53):
                            raise ValueError('invalid_fluview_mmwryear_or_week')
                        period, basis = f'{year}-W{week:02}', 'mmwr_week'
                    elif row.get('SEASON_DESCRIPTION'):
                        period, basis = row['SEASON_DESCRIPTION'], 'cdc_season'
                    else:
                        raise ValueError('fluview_period_missing')
                    yield categories[member]+'_recapture', f'{name}/{member}', None, period, basis, row


def nbim_api(archive):
    for name in safe_members(archive):
        if name == 'capture-provenance.json':
            continue
        day = date.fromisoformat(name.removesuffix('.json')).isoformat()
        identifiers = set()
        for row in json.loads(archive.read(name))['data']:
            identifier = str(row['id'])
            if (identifier in identifiers or not {'id', 'cc', 'n', 'a', 'at'} <= row.keys()
                    or len({'eq', 'fi', 're', 'ri'} & row.keys()) != 1):
                raise ValueError('unexpected_nbim_api_holding')
            identifiers.add(identifier)
            yield 'holdings_api_snapshot', name, identifier, day, 'holdings_snapshot_date', row


def gem_assets(archive):
    names = sorted(name for name in safe_members(archive) if name != 'capture-provenance.json')
    capture_date = json.loads(archive.read('capture-provenance.json'))['capture_date']
    date.fromisoformat(capture_date)
    identifiers = set()
    offset = 0
    total = None
    for name in names:
        match = re.fullmatch(r'assets-(\d{6})\.json', name)
        page = json.loads(archive.read(name))
        rows = page['results']
        total = total if total is not None else page['total']
        if (not match or int(match[1]) != offset or page['offset'] != offset or not rows
                or len(rows) != page['count'] or len(rows) != min(page['limit'], total-offset)
                or page['total'] != total or page['total_asset_count'] != total):
            raise ValueError('gem_asset_page_sequence_mismatch')
        offset += len(rows)
        for row in rows:
            identifier = row.get('asset_id')
            if not identifier or identifier in identifiers or 'asset_type' not in row:
                raise ValueError('gem_missing_or_duplicate_asset_id')
            identifiers.add(identifier)
            yield 'current_assets', name, str(identifier), capture_date, 'api_snapshot_date', row
    if not total or len(identifiers) != total:
        raise ValueError('gem_asset_snapshot_incomplete')
