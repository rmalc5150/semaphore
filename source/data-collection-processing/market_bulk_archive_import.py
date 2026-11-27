"""Load supplied VAERS and ChileCompra archives into verified Athena windows."""

import argparse
import codecs
from contextlib import contextmanager
import csv
import ctypes
import ctypes.util
from encodings.cp1252 import decoding_table
import hashlib
import io
from itertools import chain
import json
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

import boto3
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as arrow_csv
import pyarrow.parquet as pq

from collection_storage import StorageSettings, write_checked
from market_source_capture import immutable_put
from research_contract import digest
from window_publication import deploy_window

ROOT = Path(__file__).resolve().parent
VERSION = 'market-bulk-archive-v1'
SOURCES = {
    'market_source_226': ('chilecompra', 'https://datos-abiertos.chilecompra.cl/descargas/ordenes-y-licitaciones'),
    'market_source_248': ('vaers', 'https://vaers.hhs.gov/data/datasets.html'),
}
VAERS_TABLES = {'DATA': 'reports', 'VAX': 'vaccines', 'SYMPTOMS': 'symptoms'}
WINDOWS_1252 = ''.join(chr(i) if value == '\ufffe' else value for i, value in enumerate(decoding_table))


class ArchiveWindowsDecoder(codecs.IncrementalDecoder):
    def decode(self, data, final=False):
        # Preserve the few undefined Windows-1252 bytes as their Latin-1 code points.
        return codecs.charmap_decode(data, self.errors, WINDOWS_1252)[0]


def archive_encoding(name):
    if name == 'archive_windows_1252':
        return codecs.CodecInfo(name=name, encode=None, decode=None, incrementaldecoder=ArchiveWindowsDecoder)


codecs.register(archive_encoding)


def file_sha256(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


class SevenZipMember(io.RawIOBase):
    """A sequential stream for the current entry held by libarchive."""

    def __init__(self, archive, read_data, length):
        super().__init__()
        self.archive = archive
        self.read_data = read_data
        self.remaining = length

    def readable(self):
        return True

    def readinto(self, buffer):
        view = (ctypes.c_char * len(buffer)).from_buffer(buffer)
        size = self.read_data(self.archive, view, len(buffer))
        if size < 0 or size > self.remaining or (size == 0 and self.remaining):
            raise ValueError('damaged_7z_member')
        self.remaining -= size
        return size


@contextmanager
def seven_zip_members(path):
    name = ctypes.util.find_library('archive')
    if not name:
        raise RuntimeError('libarchive is required for ChileCompra .7z archives')
    library = ctypes.CDLL(name)
    ptr, text, integer = ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int

    def bind(name, result, *arguments):
        function = getattr(library, name)
        function.restype, function.argtypes = result, arguments
        return function

    new = bind('archive_read_new', ptr)
    support = bind('archive_read_support_format_7zip', integer, ptr)
    open_file = bind('archive_read_open_filename', integer, ptr, text, ctypes.c_size_t)
    next_header = bind('archive_read_next_header', integer, ptr, ctypes.POINTER(ptr))
    entry_name = bind('archive_entry_pathname', text, ptr)
    entry_size = bind('archive_entry_size', ctypes.c_int64, ptr)
    read_data = bind('archive_read_data', ctypes.c_ssize_t, ptr, ptr, ctypes.c_size_t)
    release = bind('archive_read_free', integer, ptr)

    def members(archive):
        entry = ptr()
        status = next_header(archive, ctypes.byref(entry))
        while status == 0:
            filename = entry_name(entry).decode('ascii')
            size = entry_size(entry)
            if not 0 < size < 2 * 1024**3:
                raise ValueError('unexpected_chilecompra_member_size')
            with io.BufferedReader(SevenZipMember(archive, read_data, size)) as member:
                yield filename, member
                if member.raw.remaining:
                    raise ValueError('chilecompra_member_not_consumed')
            status = next_header(archive, ctypes.byref(entry))
        if status != 1:
            raise ValueError('damaged_7z_archive')

    archive = new()
    try:
        if support(archive) != 0 or open_file(archive, bytes(path), 1024 * 1024) != 0:
            raise ValueError('unreadable_7z_archive')
        yield members(archive)
    finally:
        release(archive)


@contextmanager
def vaers_members(path):
    match = re.fullmatch(r'(20\d{2})VAERSData\.zip', path.name)
    if not match:
        raise ValueError('expected_annual_vaers_zip')
    year = match[1]
    expected = {f'{year}VAERS{kind}.csv' for kind in VAERS_TABLES}
    with zipfile.ZipFile(path) as archive:
        files = archive.infolist()
        if {f.filename for f in files} != expected or len(files) != len(expected) or sum(
            f.file_size for f in files
        ) > 2 * 1024**3:
            raise ValueError('vaers_zip_layout_mismatch')

        def members():
            for file in files:
                with archive.open(file) as member:
                    yield file.filename, member

        yield members()


def table_for(owner, member):
    if owner == 'vaers':
        return VAERS_TABLES[re.fullmatch(r'20\d{2}VAERS([A-Z]+)\.csv', member)[1]]
    if not re.fullmatch(r'\d{2}OC(ConvenioMarco|Licitacion|TratoDirecto)\.csv', member):
        raise ValueError('unexpected_chilecompra_member')
    return 'orders'


def parse_date(source, format):
    if format == '%d-%m-%Y':
        source = pc.utf8_slice_codeunits(source, 0, 10)
    return pc.cast(pc.strptime(source, format=format, unit='s', error_is_null=True), pa.date32())


def records(owner, table, member, stream, original_sha):
    delimiter = ';' if owner == 'chilecompra' else ','
    columns = next(csv.reader([stream.readline().decode('cp1252').removeprefix('ï»¿')], delimiter=delimiter))
    columns = [column.lower() for column in columns]
    if len(set(columns)) != len(columns) or not all(re.fullmatch('[a-z][a-z0-9_]*', column) for column in columns):
        raise ValueError('unsupported_archive_header')
    required = {'codigooc', 'fechaenviooc', 'entcode'} if owner == 'chilecompra' else {'vaers_id'}
    if not required <= set(columns):
        raise ValueError('required_archive_columns_missing')
    value_types = {column: pa.string() for column in columns}
    if owner == 'vaers':
        value_types['vaers_id'] = pa.int64()
    # Spontaneous-report narratives and ChileCompra descriptions can span lines.
    reader = arrow_csv.open_csv(
        stream,
        read_options=arrow_csv.ReadOptions(column_names=columns, block_size=8 * 1024**2,
                                           encoding='archive_windows_1252'),
        parse_options=arrow_csv.ParseOptions(delimiter=delimiter, newlines_in_values=True),
        convert_options=arrow_csv.ConvertOptions(column_types=value_types, strings_can_be_null=True, null_values=['']),
    )
    offset = 0
    for batch in reader:
        data = pa.Table.from_batches([batch])
        if owner == 'vaers' and data['vaers_id'].null_count:
            raise ValueError('archive_record_without_provider_id')
        if owner == 'chilecompra':
            data = data.append_column('order_sent_date', parse_date(data['fechaenviooc'], '%d-%m-%Y'))
        elif table == 'reports':
            data = data.append_column('received_date', parse_date(data['recvdate'], '%m/%d/%Y'))
        size = batch.num_rows
        data = data.append_column('source_archive_sha256', pa.repeat(original_sha, size))
        data = data.append_column('source_member', pa.repeat(member, size))
        data = data.append_column('source_row', pa.array(range(offset + 1, offset + size + 1), type=pa.int64()))
        offset += size
        yield data


def describe_column(field):
    types = {pa.string(): 'string', pa.int64(): 'bigint', pa.date32(): 'date'}
    return [field.name, types[field.type]]


def member_batches(owner, table, member, stream, original_sha, scratch):
    if owner == 'chilecompra':
        # Keep libarchive's sequential entry reader on this thread. Arrow may
        # read ahead from its input on a background thread.
        with tempfile.TemporaryFile(dir=scratch) as csv_file:
            shutil.copyfileobj(stream, csv_file, length=1024 * 1024)
            csv_file.seek(0)
            yield from records(owner, table, member, csv_file, original_sha)
    else:
        yield from records(owner, table, member, stream, original_sha)


def build_archive(path, evidence, root):
    source = evidence['source']
    owner, source_url = SOURCES[source]
    factory = seven_zip_members if owner == 'chilecompra' else vaers_members
    date_column = 'order_sent_date' if owner == 'chilecompra' else 'received_date'
    seen = set()
    members = []
    files = {}
    with factory(path) as archive:
        for member, stream in archive:
            table = table_for(owner, member)
            if member in seen:
                raise ValueError('duplicate_archive_csv_member')
            seen.add(member)
            folder = root / table
            folder.mkdir(parents=True, exist_ok=True)
            parquet_path = folder / (Path(member).stem + '.parquet')
            count = invalid_dates = missing_order_ids = 0
            first = last = None
            batches = iter(member_batches(owner, table, member, stream, evidence['sha256'], root))
            first_batch = next(batches, None)
            if first_batch is None:
                raise ValueError('empty_archive_table')
            columns = [describe_column(field) for field in first_batch.schema]
            with pq.ParquetWriter(parquet_path, first_batch.schema, compression='zstd') as writer:
                for batch in chain((first_batch,), batches):
                    count += len(batch)
                    if owner == 'chilecompra':
                        missing_order_ids += batch['codigooc'].null_count
                    if date_column in batch.column_names:
                        dates = batch[date_column]
                        invalid_dates += dates.null_count
                        bounds = pc.min_max(dates).as_py()
                        if bounds['min']:
                            first = min(first, bounds['min']) if first else bounds['min']
                            last = max(last, bounds['max']) if last else bounds['max']
                    writer.write_table(batch)
            if pq.ParquetFile(parquet_path).metadata.num_rows != count:
                raise ValueError('parquet_row_count_mismatch')
            entry = {'member': member, 'rows': count, 'file': str(parquet_path.relative_to(root)),
                     'sha256': file_sha256(parquet_path)}
            if first:
                entry.update(first_observation=first.isoformat(), last_observation=last.isoformat(),
                             rows_without_parsed_date=invalid_dates)
            if missing_order_ids:
                entry['rows_without_order_id'] = missing_order_ids
            members.append(entry)
            info = files.setdefault(table, {'rows': 0, 'columns': columns, 'objects': []})
            if owner == 'chilecompra':
                # The three order mechanisms supply different subsets of the same fields.
                info['columns'] = sorted(dict(info['columns'] + columns).items())
                info['columns'] = [list(column) for column in info['columns']]
            elif info['columns'] != columns:
                raise ValueError('inconsistent_columns_between_members')
            info['rows'] += count
            info['objects'].append(entry)
    expected_tables = set(VAERS_TABLES.values()) if owner == 'vaers' else {'orders'}
    if len(seen) != 3 or set(files) != expected_tables:
        raise ValueError('incomplete_provider_archive')
    for member in members:
        dated = 'first_observation' in member
        if owner == 'chilecompra' and (not dated or member['first_observation'][:4] != '2016'
                                      or member['last_observation'][:4] != '2016'):
            raise ValueError('chilecompra_dates_outside_2016')
        if owner == 'vaers' and dated and (member['first_observation'][:4] != path.name[:4]
                                           or member['last_observation'][:4] != path.name[:4]):
            raise ValueError('vaers_received_dates_outside_archive_year')
    return {'source': source, 'archive': {**evidence, 'source_url': source_url},
            'members': members, 'files': files}


def publish_archive(settings, s3, glue, athena, path, evidence, output):
    owner, _ = SOURCES[evidence['source']]
    if file_sha256(path) != evidence['sha256']:
        raise ValueError('local_archive_checksum_mismatch')
    release_id = digest({'version': VERSION, 'source': evidence['source'], 'archive': evidence['sha256'],
                         'arrow': pa.__version__})
    root = output / release_id
    root.mkdir(parents=True, exist_ok=True)
    cached = root / 'published.json'
    if cached.is_file():
        # Immutable releases can be re-read without rewriting the warehouse.
        return json.loads(cached.read_text())
    config = {'database': f'optima_{owner}_archive', 'workgroup': f'optima-{owner}-archive',
              'region': settings.region, 'curated_prefix': f'curated/{owner}-archive',
              'query_results_prefix': f'athena-results/{owner}-archive'}
    prefix = f"{config['curated_prefix']}/{release_id}"
    report = build_archive(path, evidence, root)
    for table, info in report['files'].items():
        folder = f'{settings.s3_prefix}/{prefix}/{table}/'
        info['location'] = f's3://{settings.s3_bucket}/{folder}'
        for entry in info['objects']:
            local = root / entry['file']
            with local.open('rb') as file:
                key = folder + local.name
                immutable_put(s3, settings.s3_bucket, key, file, entry['sha256'], 'application/vnd.apache.parquet', verify=True)
            entry['s3_uri'] = f's3://{settings.s3_bucket}/{key}'
    report.update(config=config, bucket=settings.s3_bucket, s3_prefix=settings.s3_prefix,
                  release_id=release_id, release_prefix=prefix, archive_import_version=VERSION)
    release_body = (json.dumps(report, indent=2, sort_keys=True) + '\n').encode()
    (root/'release.json').write_bytes(release_body)
    store = settings.store(s3)
    # Only publish the warehouse partitions once every member and raw archive has been verified.
    release_key = prefix + '/release.json'
    previous = store.get(release_key)
    if previous:
        archived = json.loads(previous.body)
        if archived['files'] != report['files'] or archived['archive']['sha256'] != report['archive']['sha256']:
            raise ValueError('bulk_archive_release_conflict')
        (root/'release.json').write_bytes(previous.body)
        report = archived
    else:
        write_checked(store, release_key, release_body)
    verified = deploy_window(store, settings, root, release_id, f'{owner}-archive', glue=glue, athena=athena)
    result = {**report, 'verification': verified}
    cached.write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--retained', required=True, type=Path, help='JSON inventory of checksum-verified originals')
    parser.add_argument('--files-dir', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--source', choices=tuple(SOURCES), required=True)
    args = parser.parse_args()
    records = [r for r in json.loads(args.retained.read_text()) if r['source'] == args.source]
    if not records:
        parser.error('no archive records for the selected source')
    settings = StorageSettings.load(ROOT/'config/collection-storage.s3.json')
    context = boto3.Session(region_name=settings.region)
    s3, glue, athena = [context.client(service) for service in ('s3', 'glue', 'athena')]
    receipts = []
    failures = []
    for evidence in records:
        try:
            result = publish_archive(settings, s3, glue, athena, args.files_dir/evidence['file'], evidence, args.output)
            if args.source == 'market_source_248':
                from metadata_engine.market_archive import retain_receipt, vaers_receipt
                manifest_uri = f"s3://{result['bucket']}/{result['s3_prefix']}/{result['release_prefix']}/release.json"
                receipt = vaers_receipt(result['archive'], result['members'], manifest_uri)
                retain_receipt(s3, settings.s3_bucket, receipt)
        except (OSError, ValueError, RuntimeError) as exc:
            failure = {'file': evidence['file'], 'error_type': type(exc).__name__}
            failures.append(failure)
            print(json.dumps(failure), flush=True)
            continue
        receipts.append(result)
        summary = {table: info['rows'] for table, info in result['files'].items()}
        print(json.dumps({'file': evidence['file'], 'rows': summary,
                          'athena': result['verification']['query']['query_id']}), flush=True)
    (args.output/(args.source+'-verified.json')).write_text(json.dumps(receipts, indent=2) + '\n')
    if failures:
        raise SystemExit(f'{len(failures)} archives require follow-up')


if __name__ == '__main__':
    main()
