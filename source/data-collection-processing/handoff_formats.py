"""Read verified provider records from the global data handoff."""
from collections import Counter
from datetime import date, datetime, timezone
import csv
import gzip
import hashlib
import io
import json
from pathlib import PurePosixPath
import re
from urllib.parse import parse_qs, urlsplit

from temporary_archive_formats import csv_rows, local_day, nbim_api, safe_members


def jsonl(archive, name):
    with archive.open(name) as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def provider_url(url, hosts):
    parsed = urlsplit(url)
    return parsed.scheme=='https' and parsed.hostname in hosts


def cnmv_legacy(archive):
    manifest = json.loads(archive.read('manifest.json'))
    names = set(safe_members(archive))
    pages = {name: archive.read(name) for name in names if name.endswith('.html')}
    count = 0
    for row in jsonl(archive,'records.jsonl'):
        day = date.fromisoformat(row['registration_date']).isoformat()
        member = 'originals/'+PurePosixPath(row['file']).name
        pdf = archive.read(member)
        if (not manifest['start'] <= day <= manifest['end'] or not pdf.startswith(b'%PDF-')
                or hashlib.sha256(pdf).hexdigest()!=row['sha256'] or not provider_url(row['original_url'],{'www.cnmv.es','cnmv.es'})):
            raise ValueError('cnmv_legacy_original_identity_mismatch')
        token = parse_qs(urlsplit(row['original_url']).query).get('e',[])
        matches = [name for name,body in pages.items() if token and token[0].encode() in body]
        if not matches:
            encoded = urlsplit(row['original_url']).query.encode()
            matches = [name for name,body in pages.items() if encoded and encoded in body]
        if not matches:
            raise ValueError('cnmv_legacy_result_page_missing')
        count += 1
        yield 'legacy_filing_documents', member, row['sha256'], day, 'notification_date', {
            **row,'matched_result_pages':sorted(matches),'original_archive_member':member,
        }
    if count!=manifest['notice_count']:
        raise ValueError('cnmv_legacy_notice_count_mismatch')


def cnmv_modern(archive):
    manifest = json.loads(archive.read('manifest.json'))
    known = set(json.loads(archive.read('prior-registration-ids.json')))
    records = {}
    for row in jsonl(archive,'records.jsonl'):
        identifier = str(row['registration_number'])
        if (not re.fullmatch(r'\d{10}',identifier) or identifier in records
                or not provider_url(row['original_url'],{'www.cnmv.es','cnmv.es'})):
            raise ValueError('invalid_or_duplicate_cnmv_registration')
        records[identifier] = row
    if len(records)!=manifest['unique_notices']:
        raise ValueError('cnmv_modern_notice_count_mismatch')
    locators = {}
    for file in manifest['files']:
        name = PurePosixPath(file['file']).name
        raw = archive.read(name)
        if hashlib.sha256(raw).hexdigest()!=file['sha256']:
            raise ValueError('cnmv_modern_source_page_digest_mismatch')
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            page = stream.read(4*1024**2+1)
        if len(page)>4*1024**2 or b'Notificaciones de los directivos' not in page[:5000]:
            raise ValueError('cnmv_unexpected_publisher_page')
        for identifier in re.findall(rb'(?<!\d)20\d{8}(?!\d)',page):
            identifier = identifier.decode()
            if identifier in records:
                locators.setdefault(identifier,name)
    if set(records)!=locators.keys():
        raise ValueError('cnmv_register_rows_missing_from_original_pages')
    for identifier,row in records.items():
        day = local_day(row['registration_date'],'%d/%m/%Y')
        yield 'modern_registration_snapshot',locators[identifier],identifier,day,'notification_date',{
            **row,'already_in_prior_register':identifier in known,
        }


def fca_notices(archive):
    required={'Filing Date/Time','Publication Date/Time','Disclosing Organisation LEI','Category','Download Link'}
    manifest = json.loads(archive.read('manifest.json'))
    seen = set()
    for item in manifest['files']:
        member = PurePosixPath(item['file']).name
        raw = archive.read(member)
        if hashlib.sha256(raw).hexdigest()!=item['sha256']:
            raise ValueError('fca_export_sha256_mismatch')
        count = 0
        for row in csv_rows(raw,required=required):
            count += 1
            identity = tuple(sorted(row.items()))
            if identity in seen:
                continue
            seen.add(identity)
            if not provider_url(row['Download Link'], {'data.fca.org.uk','data.fca.gov.uk','www.fca.org.uk','fca.org.uk','api.data.fca.org.uk'}):
                raise ValueError('unexpected_fca_document_host')
            timestamp = row['Publication Date/Time'] or row['Filing Date/Time']
            moment = datetime.fromisoformat(timestamp.replace('Z','+00:00'))
            if not moment.tzinfo:
                raise ValueError('fca_notice_timestamp_lacks_offset')
            period = moment.astimezone(timezone.utc).isoformat()
            basis = 'notice_publication_timestamp' if row['Publication Date/Time'] else 'notice_filing_timestamp'
            yield 'pdmr_notice_index',member,row['Download Link'],period,basis,row
        if count!=item['rows']:
            raise ValueError('fca_export_row_count_mismatch')
    expected = {tuple(sorted(row.items())) for row in jsonl(archive,'notices-deduplicated.jsonl')}
    if expected!=seen or len(seen)!=manifest['unique_full_rows']:
        raise ValueError('fca_combined_rows_disagree_with_original_csvs')


def gem_entities(archive):
    manifest = json.loads(archive.read('manifest.json'))
    count = 0
    identifiers = set()
    for entry in sorted(manifest,key=lambda e:e['file']):
        name = PurePosixPath(entry['file']).name
        raw = archive.read(name)
        if (not re.fullmatch(r'entities-\d{6}\.json',name)
                or not provider_url(entry['url'],{'api.globalenergymonitor.org'})
                or hashlib.sha256(raw).hexdigest()!=entry['sha256']):
            raise ValueError('gem_entity_page_identity_mismatch')
        page = json.loads(raw)
        if (page['offset']!=count or page['count']!=len(page['results'])
                or page['count']!=entry['count'] or page['total']!=entry['total'] or not page['count']):
            raise ValueError('gem_entities_incomplete_pagination')
        for row in page['results']:
            identifier=row['entity_id']
            if not identifier or identifier in identifiers:
                raise ValueError('gem_entity_missing_or_duplicate_id')
            identifiers.add(identifier)
            yield 'current_entities',name,str(identifier),'2026-11-25','api_snapshot_date',row
        count += page['count']
    if count!=len(identifiers) or any(entry['total']!=count for entry in manifest):
        raise ValueError('gem_entity_snapshot_count_mismatch')


def nbim_opening(archive):
    day = '2015-12-31'
    member = day+'.json'
    classes={'eq':'equity','fi':'fixed_income','re':'real_estate'}
    csv_counts={}
    for code in classes:
        name=f'{day}-{code}.csv'
        csv_counts[code]=sum(1 for _ in csv_rows(archive.read(name),encoding='utf-16',delimiter=';',
                                 required={'Region','Country'},optional_missing={'Incorporation Country'}))
    seen=set()
    counts=Counter()
    for row in json.loads(archive.read(member))['data']:
        key=classes.keys() & row.keys()
        if len(key)!=1 or row['id'] in seen:
            raise ValueError('nbim_opening_missing_type_or_unique_id')
        code,=key
        seen.add(row['id'])
        if code=='re':
            properties=row['re']
            counts[code]+=len(properties)
            if len({item['id'] for item in properties})!=len(properties):
                raise ValueError('nbim_opening_duplicate_property_id')
            for item in properties:
                yield 'real_estate_opening_2015',member,f"{row['id']}:{item['id']}",day,'holdings_snapshot_date',{
                    **item,'parent_holding_id':row['id'],'parent_country_code':row['cc'],
                    'parent_holding_name':row['n'],
                }
        else:
            counts[code]+=1
            yield 'holdings_opening_2015',member,str(row['id']),day,'holdings_snapshot_date',row
    if counts!=csv_counts:
        raise ValueError(f'nbim_api_and_csv_opening_counts_differ:{dict(counts)}:{csv_counts}')


PARSERS = {
    'CNMV-Legacy-2016.zip':cnmv_legacy,
    'CNMV-Modern-Register-Snapshot.zip':cnmv_modern,
    'FCA-PDMR-Notice-Index.zip':fca_notices,
    'GEM-Current-Entities.zip':gem_entities,
    'NBIM-Opening-2015.zip':nbim_opening,
}
