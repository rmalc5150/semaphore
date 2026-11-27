"""Validate original trade measurements, environmental exports and mining files."""
import csv
from decimal import Decimal, InvalidOperation
from functools import lru_cache
import io
import json
from pathlib import PurePosixPath
from urllib.parse import parse_qs, urlsplit
from zipfile import ZipFile

from metadata_engine.evidence import RawFailure, object_bytes, s3_key
from metadata_engine import streaming
from trade_mining_sources import COMEXT, GEOCAT, MDIC, NCM, SIACAM, SIGMINE, SNIFA, TRACE, in_scope, mdic_request

NATIVE_DATASETS = {
    MDIC: 'comex_stat_monthly_ncm',
    COMEXT: 'comext_goods_trade',
    GEOCAT: 'geocatmin_concession_features',
    TRACE: 'climate_trace_asset_activity',
}


def finite(value):
    try:
        return Decimal(str(value)).is_finite()
    except InvalidOperation:
        return False


def csv_records(stream, delimiter, required):
    reader = csv.DictReader(stream, delimiter=delimiter, strict=True)
    fields = reader.fieldnames
    if not fields or len(fields) != len(set(fields)) or not required.issubset(fields):
        raise RawFailure('trade_mining_csv_schema_mismatch')
    for row in reader:
        if any(field is None or value is None for field, value in row.items()):
            raise RawFailure('trade_mining_csv_row_width_mismatch')
        yield row


@lru_cache(maxsize=6)
def native_rows(source, url, body):
    if not in_scope(url, source):
        raise RawFailure('trade_mining_native_query_outside_scope')
    parsed = urlsplit(url)
    query = parse_qs(parsed.query)
    if source == MDIC:
        _, request = mdic_request(url)
        document = json.loads(body)
        items = document.get('data', {}).get('list')
        if document.get('success') is not True or not isinstance(items, list):
            raise RawFailure('mdic_query_rejected_or_invalid')
        rows = {}
        for row in items:
            code = row.get('coNcm')
            month = f"{row.get('year')}-{row.get('monthNumber')}"
            if (code not in {str(n) for n in NCM}
                    or not request['period']['from'] <= month <= request['period']['to']
                    or not month[-2:].isdigit() or not 1 <= int(month[-2:]) <= 12
                    or not all(finite(row.get(k)) for k in ('metricFOB', 'metricKG'))):
                raise RawFailure('mdic_measurement_outside_query')
            identity = f"{request['flow']}:{month}:{code}"
            if identity in rows:
                raise RawFailure('mdic_duplicate_native_measurement')
            rows[identity] = row
    elif source == COMEXT:
        dimensions = ('freq', 'reporter', 'partner', 'product', 'flow', 'indicators')
        expected = parsed.path.split('/')[-1].split('.')
        start, end = query['startPeriod'][0], query['endPeriod'][0]
        rows = {}
        with io.StringIO(body.decode('utf-8-sig'), newline='') as data:
            for row in csv_records(data, ',', set(dimensions) | {'DATAFLOW', 'TIME_PERIOD', 'OBS_VALUE'}):
                period = row['TIME_PERIOD']
                if ([row[k] for k in dimensions] != expected or not row['DATAFLOW'].startswith('ESTAT:DS-045409')
                        or not start <= period <= end or not finite(row['OBS_VALUE'])):
                    raise RawFailure('comext_measurement_outside_query')
                identity = ':'.join(expected + [period])
                if identity in rows:
                    raise RawFailure('comext_duplicate_series_period')
                rows[identity] = row
    elif source == GEOCAT:
        document = json.loads(body)
        if (document.get('geometryType') != 'esriGeometryPolygon'
                or document.get('spatialReference', {}).get('wkid') != 4326
                or document.get('error') or document.get('exceededTransferLimit')):
            raise RawFailure('geocatmin_geometry_or_transfer_mismatch')
        asked = set(query['objectIds'][0].split(','))
        rows = {}
        for feature in document.get('features', []):
            attributes = feature.get('attributes', {})
            identity = str(attributes.get('OBJECTID'))
            if (identity not in asked or identity in rows or not attributes.get('CODIGOU')
                    or not feature.get('geometry', {}).get('rings')):
                raise RawFailure('geocatmin_feature_identity_or_geometry_mismatch')
            rows[identity] = feature
    else:
        document = json.loads(body)
        asset = parsed.path.rsplit('/', 1)[-1]
        start, end = (int(query[k][0]) for k in ('start', 'end'))
        if str(document.get('id')) != asset or document.get('subsector') != 'iron-and-steel':
            raise RawFailure('climate_trace_asset_mismatch')
        years = set()
        for observation in document.get('emissions', []):
            year = observation.get('year')
            if (type(year) is not int or year in years or not start <= year <= end
                    or observation.get('gas') != query['gas'][0] or not finite(observation.get('emissionsQuantity'))):
                raise RawFailure('climate_trace_emissions_scope_mismatch')
            years.add(year)
        if not years or not any(finite(row.get('activity')) for row in document['emissions']):
            raise RawFailure('climate_trace_asset_activity_missing')
        rows = {f'{asset}:{start}:{end}:co2e_100yr': document}
    if not rows:
        raise RawFailure('trade_mining_native_query_has_no_observations')
    return rows


@lru_cache(maxsize=6)
def read_native(s3, bucket, key, checksum):
    return object_bytes(s3, bucket, key, limit=4 * 1024**2, expected=checksum)


def from_public_receipt(receipt, s3, bucket):
    source = receipt['source']
    if receipt['artifact_kind'] != 'public_document':
        raise RawFailure('trade_mining_discovery_is_not_native_material')
    url, uri, checksum = (receipt[k] for k in ('source_url', 'artifact_uri', 'sha256'))
    reference = {'s3_uri': uri, 'sha256': checksum, 'source_url': url, 'retrieved_at': receipt['retrieved_at']}
    if source == MDIC:
        endpoint, request = mdic_request(url)
        if receipt.get('provider_request') != {'method': 'POST', 'url': endpoint, 'json': request}:
            raise RawFailure('mdic_missing_recognised_request_provenance')
        reference['provider_request'] = receipt['provider_request']
    body = read_native(s3, bucket, s3_key(uri, bucket), checksum)
    return [{
        'source': source, 'dataset': NATIVE_DATASETS[source], 'source_record_id': identity,
        'ingested_at': receipt['retrieved_at'], 'source_url': url, 'available_at': None,
        'payload': {'data': row, 'source_evidence': [reference]},
    } for identity, row in native_rows(source, url, body).items()]


def shapefile_info(entry):
    with ZipFile(entry['path']) as archive:
        members = [member for member in archive.infolist() if not member.is_dir()]
        if (not members or len(members) > 24 or sum(m.file_size for m in members) > streaming.MAX_EXPANDED
                or any(m.flag_bits & 1 or PurePosixPath(m.filename).is_absolute()
                       or '..' in PurePosixPath(m.filename).parts for m in members)):
            raise RawFailure('sigmine_unexpected_archive_layout')
        files = {PurePosixPath(member.filename.lower()): member for member in members}
        shapes = [p for p in files if p.suffix == '.shp']
        if len(shapes) != 1 or not all(shapes[0].with_suffix(ext) in files for ext in ('.dbf', '.shx', '.prj')):
            raise RawFailure('sigmine_missing_shapefile_component')
        if archive.testzip() is not None:
            raise RawFailure('sigmine_archive_checksum_mismatch')
        with archive.open(files[shapes[0]]) as shape:
            header = shape.read(100)
        if len(header) != 100 or int.from_bytes(header[:4], 'big') != 9994:
            raise RawFailure('sigmine_invalid_shapefile_header')
        if 2 * int.from_bytes(header[24:28], 'big') != files[shapes[0]].file_size:
            raise RawFailure('sigmine_shapefile_length_mismatch')
        with archive.open(files[shapes[0].with_suffix('.dbf')]) as dbase:
            count = int.from_bytes(dbase.read(8)[4:8], 'little')
        index_bytes = files[shapes[0].with_suffix('.shx')].file_size
        if count <= 0 or index_bytes != 100 + count * 8:
            raise RawFailure('sigmine_shape_index_record_count_mismatch')
        return {'format': 'shapefile_zip', 'features': count, 'members': len(members)}


def original_file(entry, source, url):
    path = urlsplit(url).path.lower()
    if source == SIGMINE and path.endswith('.zip'):
        return shapefile_info(entry)
    if source in (SNIFA, SIACAM) or source == SIGMINE and path.endswith('.csv'):
        if source == SNIFA:
            delimiter, required = ';', {'ProcesoSancionId', 'Expediente', 'FechaInicio', 'ProcesoSancionEstado'}
        elif source == SIGMINE:
            delimiter, required = ',', {'Processo', 'Fase Atual'}
        else:
            delimiter = ','
            if path.endswith('produccion-litio.csv'):
                required = {'Periodo', 'Carbonato_de_Litio_TN', 'Carbonatos_de_litio_Numeros_indice'}
            else:
                required = {'Fecha', 'Serie'}
        for encoding in ('utf-8-sig', 'cp1252'):
            try:
                with entry['path'].open(encoding=encoding, newline='') as data:
                    count = sum(1 for _ in csv_records(data, delimiter, required))
                if not count:
                    raise RawFailure('trade_mining_export_empty')
                return {'format': 'csv', 'rows': count, 'encoding': encoding}
            except UnicodeDecodeError:
                continue
        raise RawFailure('trade_mining_csv_encoding_invalid')
    info = streaming.validate_file(entry)
    if path.endswith('.xlsx'):
        if info['format'] != 'zip':
            raise RawFailure('trade_mining_original_workbook_required')
        with ZipFile(entry['path']) as workbook:
            members = set(workbook.namelist())
            if ('xl/workbook.xml' not in members or '[Content_Types].xml' not in members
                    or not any(name.startswith('xl/worksheets/sheet') and name.endswith('.xml') for name in members)):
                raise RawFailure('trade_mining_workbook_schema_invalid')
        return {**info, 'format': 'xlsx'}
    if info['format'] != 'pdf':
        raise RawFailure('trade_mining_original_pdf_required')
    return info


def evidence(record, s3, bucket):
    source = record['source']
    for ref in record.get('payload', {}).get('source_evidence', []):
        url = ref.get('source_url', '')
        if not in_scope(url, source):
            continue
        key = s3_key(ref['s3_uri'], bucket)
        checksum = ref['sha256']
        if source in NATIVE_DATASETS:
            body = read_native(s3, bucket, key, checksum)
            items = native_rows(source, url, body)
            if (record['dataset'] != NATIVE_DATASETS[source]
                    or items.get(record['source_record_id']) != record['payload'].get('data')):
                raise RawFailure('trade_mining_entire_native_row_mismatch')
            info = {'format': 'csv' if source == COMEXT else 'json', 'provider_response_records': len(items)}
            size = len(body)
        else:
            entry = streaming.download(s3, bucket, key, checksum)
            info = original_file(entry, source, url)
            size = entry['bytes']
        return [{
            'artifact_kind': 'provider_record', 's3_uri': ref['s3_uri'], 'sha256': checksum,
            'bytes': size, 'origin': 'first_party_source', 'source_url': url,
            'retrieved_at': ref.get('retrieved_at'),
            'validation': {**info, **({'provider_request': ref['provider_request']} if 'provider_request' in ref else {})},
        }]
    raise RawFailure('trade_mining_original_missing_or_out_of_scope')
