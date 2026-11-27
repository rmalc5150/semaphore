"""Capture reviewed archive files and commit parsed documents and observations."""
from __future__ import annotations

import argparse
import base64
import bz2
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import re
import struct
import tempfile
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree
from zipfile import ZipFile

import boto3
import requests

from collection_storage import AlreadyComplete, CollectionRun, StorageSettings, task_spec
from constellation.control import settings as infrastructure
from market_source_capture import CHALLENGE, MARKET, get, immutable_put, json_bytes, nested, utcnow
from market_source_register import OWNER_REMOVED, PAID_EXCLUSIONS, ROOT, write
from provider_publication import from_path as publication_from_path
from research_contract import digest, load_json, parse_instant, seal_record
from source_pauses import is_paused


CONFIG = ROOT/'config/market-archive-downloads.v1.json'
RESULTS = ROOT/'config/market-archive-results.v1.json'
VERSION = 'market-archive-import-v1'
MAX_EXPANDED = 1152 * 1024**2


def profiles():
    items = load_json(CONFIG)['downloads']
    identities = set()
    for row in items:
        key = row['key']
        source = row['id']
        if source in OWNER_REMOVED or source in PAID_EXCLUSIONS or key in identities:
            raise ValueError('excluded_or_duplicate_download')
        identities.add(key)
    return [row for row in items if not is_paused(f"market_source_{row['id']}")]


def read_universe(s3, bucket):
    config = infrastructure()
    response = s3.get_object(Bucket=bucket,Key=config['legacy_seed_key'])
    with response['Body'] as body:
        seed=json.load(body)
    entry=seed['paths']['config/company-universe.v0.5.json']
    response=s3.get_object(Bucket=bucket,Key=entry['key'])
    with response['Body'] as body:
        raw=body.read()
    if hashlib.sha256(raw).hexdigest()!=entry['sha256']:
        raise ValueError('universe_checksum_mismatch')
    return json.loads(raw)


def direct_download(spec, target):
    url=spec['url']
    cap=spec.get('max_mb',64)*1024**2
    if spec.get('post'):
        from market_source_capture import allowed, USER_AGENT
        if not allowed(spec,url):
            raise ValueError('unreviewed_post_destination')
        response=requests.post(url,json=spec['post'],headers={'User-Agent':USER_AGENT},stream=True,timeout=(10,45),allow_redirects=False)
        if response.status_code!=200:
            response.close()
            raise ValueError(f'provider_http_{response.status_code}')
    else:
        response=get(requests, spec, url)
    with response,target.open('wb') as out:
        if int(response.headers.get('Content-Length') or 0)>cap:
            raise ValueError('provider_file_exceeds_configured_limit')
        size=0
        for chunk in response.iter_content(128*1024):
            size+=len(chunk)
            if size>cap:
                raise ValueError('provider_file_exceeds_configured_limit')
            out.write(chunk)
        return response.url,response.headers.get('Content-Type','application/octet-stream'),'provider_https'


def rendered_download(spec, target):
    from decodo_scraping_api import scrape_url
    raw=scrape_url(spec['url'],**({'headless':'html'} if spec['format']=='html' else {}))
    if spec['format']=='pdf':
        if not raw.lstrip().startswith('JVBER'):
            raise ValueError('rendering_gateway_did_not_return_original_pdf_bytes')
        data=base64.b64decode(''.join(raw.split()),validate=True)
        media='application/pdf'
    elif spec['format']=='html':
        data=raw.encode()
        media='text/html'
    else:
        raise ValueError('unreviewed_rendered_format')
    if len(data)>spec.get('max_mb',64)*1024**2:
        raise ValueError('rendered_file_exceeds_configured_limit')
    target.write_bytes(data)
    return spec['url'],media,'decodo_public_'+('binary' if spec['format']=='pdf' else 'rendered_html')


def download(spec, target):
    try:
        response=direct_download(spec,target)
        if spec['format'] in ('pdf','html') and spec.get('decodo') and not target.stat().st_size:
            return rendered_download(spec,target)
        return response
    except (ValueError,requests.RequestException):
        if not spec.get('decodo'):
            raise
        return rendered_download(spec,target)


def normalize_value(value):
    if isinstance(value,(date,datetime)):
        return value.isoformat()
    if isinstance(value,float) and not math.isfinite(value):
        return None
    return value


def csv_rows(stream, spec, member):
    with io.TextIOWrapper(stream,encoding=spec.get('encoding','utf-8-sig'),newline='') as text:
        required=spec.get('fields',[])
        reader=csv.DictReader(text,delimiter=spec.get('delimiter',','))
        actual=reader.fieldnames or []
        if len(actual)<2 or not set(map(str.casefold,required))<=set(map(str.casefold,actual)):
            raise ValueError('archive_table_schema_mismatch')
        if len(set(actual))!=len(actual):
            raise ValueError('archive_table_headers_duplicate')
        keys=spec.get('columns') or actual
        for number,row in enumerate(reader,1):
            if None in row or not any(v not in ('',None) for v in row.values()):
                continue
            if spec.get('row_filter') and not re.search(spec['row_filter'][1],str(row.get(spec['row_filter'][0],'')),re.I):
                continue
            yield member,number,{key:row.get(key) for key in keys}


def google_trends_rows(path, spec):
    from metadata_engine.market_archive import trends_rows

    term = spec['term']
    with path.open(encoding='utf-8-sig', newline='') as stream:
        rows = trends_rows(stream, term, spec['year'], spec.get('end_year', spec['year']))
        for line, day, interest in rows:
            yield 'interest_over_time', line, {
                'week_start': day, 'term': term, 'geography': 'Worldwide',
                'category': 'All categories', 'reported_interest': interest,
                'interest_score': None if interest == '<1' else int(interest),
            }


def cmf_ifrs_rows(path, spec):
    columns = ('reference_period', 'issuer_rut', 'issuer_name', 'statement_scope',
               'currency', 'account_description', 'amount', 'taxonomy', 'statement_type')
    periods = {f"{spec['year']}{quarter}" for quarter in ('03', '06', '09', '12')}
    seen = set()
    with path.open(encoding='utf-8', newline='') as stream:
        for ordinal, row in enumerate(csv.reader(stream, delimiter=';', quoting=csv.QUOTE_NONE), 1):
            if (len(row) != len(columns) or row[0] not in periods or not row[1].isdigit()
                    or not row[7].startswith('TAX ') or not row[8].strip()):
                raise ValueError('cmf_ifrs_statement_row_mismatch')
            seen.add(row[0])
            yield 'issuer_ifrs', ordinal, dict(zip(columns, row))
    if seen != periods:
        raise ValueError('cmf_ifrs_statement_periods_missing')


def sheets_rows(workbook,spec):
    for title,rows in workbook:
        if spec.get('sheet_regex') and not re.search(spec['sheet_regex'],title,re.I):
            continue
        for number,row in enumerate(rows,1):
            cells={str(i):normalize_value(value) for i,value in enumerate(row,1) if value not in (None,'')}
            if len(cells)<spec.get('min_cells',2):
                continue
            if spec.get('row_pattern') and not re.search(spec['row_pattern'],' '.join(map(str,cells.values())),re.I):
                continue
            yield title,number,{'worksheet':title,'cells':cells}


def excel_rows(path,spec):
    if spec['format']=='xls':
        import xlrd
        book=xlrd.open_workbook(str(path),on_demand=True)
        try:
            yield from sheets_rows(((sh.name,(sh.row_values(i) for i in range(sh.nrows))) for sh in book.sheets()),spec)
        finally:
            book.release_resources()
    else:
        import openpyxl
        book=openpyxl.load_workbook(path,read_only=True,data_only=True)
        try:
            yield from sheets_rows(((sheet.title,sheet.values) for sheet in book.worksheets),spec)
        finally:
            book.close()


def zip_rows(path,spec):
    with ZipFile(path) as archive:
        members=[m for m in archive.infolist() if not m.is_dir() and re.search(spec['member_regex'],m.filename,re.I)]
        if not members or len(members)>spec.get('max_members',15) or sum(m.file_size for m in members)>MAX_EXPANDED:
            raise ValueError('archive_expected_members_missing_or_over_expansion_limit')
        for member in members:
            with archive.open(member) as file:
                if spec['format']=='zip_csv':
                    yield from csv_rows(file,spec,member.filename)
                elif spec['format']=='zip_excel':
                    import openpyxl
                    if member.file_size>40*1024**2:
                        raise ValueError('archived_workbook_member_too_large')
                    book=openpyxl.load_workbook(io.BytesIO(file.read()),read_only=True,data_only=True)
                    try:
                        worksheets=((f'{member.filename}/{sheet.title}',sheet.values) for sheet in book.worksheets)
                        yield from sheets_rows(worksheets,spec)
                    finally:
                        book.close()
                elif spec['format']=='zip_xpt':
                    import pyreadstat
                    secondary=path.with_name('public-survey.xpt')
                    with secondary.open('wb') as out:
                        import shutil
                        shutil.copyfileobj(file,out,512*1024)
                    usecols=spec['columns']
                    for chunk, _ in pyreadstat.read_file_in_chunks(pyreadstat.read_xport,str(secondary),
                                                                   chunksize=2000,usecols=usecols,output_format='dict'):
                        lengths={len(col) for col in chunk.values()}
                        if len(lengths)!=1:
                            raise ValueError('survey_column_length_mismatch')
                        for index,values in enumerate(zip(*chunk.values(),strict=True)):
                            number=int(values[0]) if spec.get('identity_column')==next(iter(chunk)) else None
                            yield member.filename,number,dict(zip(chunk,(normalize_value(v) for v in values),strict=True))
                    secondary.unlink()


def pdf_rows(path,spec):
    from pypdf import PdfReader
    with path.open('rb') as file:
        if file.read(5)!=b'%PDF-':
            raise ValueError('expected_official_pdf')
        file.seek(-min(4096,path.stat().st_size),2)
        if b'%%EOF' not in file.read():
            raise ValueError('truncated_pdf')
        file.seek(0)
        document=PdfReader(file)
        pages=list(itertools.islice(document.pages,spec.get('max_pages',200)))
        if not pages:
            raise ValueError('pdf_pages_missing')
        found=False
        for index,page in enumerate(pages,1):
            text=page.extract_text(extraction_mode=spec.get('pdf_extraction_mode','layout')).strip()
            if len(text)<70:
                continue
            found|=bool(re.search(spec['text_pattern'],text,re.I))
            yield 'document',index,{'page':index,'text':text,'page_count':len(document.pages)}
        if not found:
            raise ValueError('pdf_missing_expected_source_content')


def indexed_filing(path, index, spec):
    from lxml import html
    from pypdf import PdfReader

    document = html.fromstring(index.read_bytes())
    url = urlsplit(spec['url'])
    rows = []
    for row in document.xpath('//tr[td]'):
        links = [urlsplit(urljoin(spec['filing_index_url'], link)) for link in row.xpath('.//a/@href')]
        if not any((link.hostname, link.path) == (url.hostname, url.path) for link in links):
            continue
        cells = [' '.join(cell.text_content().split()) for cell in row.xpath('./td')]
        if len(cells) < 3:
            raise ValueError('incomplete_companies_house_filing_index_row')
        filed = datetime.strptime(cells[0], '%d %b %Y').date()
        if filed.year != spec['year'] or cells[1] != spec['filing_form']:
            raise ValueError('companies_house_filing_scope_mismatch')
        rows.append((filed.isoformat(), cells[1], cells[2]))
    if len(rows) != 1:
        raise ValueError('companies_house_filing_document_not_unique_in_index')

    with path.open('rb') as document:
        if not document.read(5).startswith(b'%PDF-'):
            raise ValueError('expected_official_pdf')
        document.seek(-min(4096, path.stat().st_size), 2)
        if b'%%EOF' not in document.read():
            raise ValueError('truncated_pdf')
        document.seek(0)
        pages = len(PdfReader(document).pages)
        if not pages:
            raise ValueError('pdf_pages_missing')

    filed, form, title = rows[0]
    return [('filing_index', 1, {'filing_date': filed, 'form': form, 'filing_description': title,
                                 'company_number': spec['company_number'], 'document_page_count': pages})]


def html_rows(path,spec):
    from lxml import html
    document=html.fromstring(path.read_bytes())
    if not document.xpath('boolean(//title)'):
        raise ValueError('original_document_title_missing')
    for node in document.xpath('//script|//style|//noscript|//header|//footer|//nav'):
        node.drop_tree()
    title=' '.join(document.xpath('string(//title)').split())
    body=' '.join(' '.join(n.text_content().split()) for n in document.xpath(spec.get('xpath','//body')))
    if len(body)<300 or not re.search(spec['text_pattern'],title+' '+body,re.I):
        raise ValueError('html_missing_expected_document_content')
    if spec.get('table_xpath'):
        matches=document.xpath(spec['table_xpath'])
        for index,row in enumerate(matches,1):
            cells=[' '.join(v.text_content().split()) for v in row.xpath('./th|./td')]
            if len(cells)>=3 and any(re.fullmatch(r'-?[\d,.]+',v) for v in cells):
                yield 'native_table',index,{'table_title':title,'cells':cells}
        return
    yield 'document',1,{'title':title,'text':body[:220000]}


def json_rows(path,spec):
    value=json.loads(path.read_bytes())
    rows=nested(value,spec.get('path',[]))
    if spec.get('dict_values') and isinstance(rows,dict):
        rows=[{'provider_key':key,**value} for key,value in rows.items() if isinstance(value,dict)]
    if isinstance(rows,dict):
        rows=[rows]
    if not isinstance(rows,list) or not rows:
        raise ValueError('provider_rows_missing')
    for number,data in enumerate(rows,1):
        if not isinstance(data,dict) or not all(nested(data,key.split('.')) is not None for key in spec['fields']):
            raise ValueError('provider_native_field_missing')
        if spec.get('row_filter'):
            key,pattern=spec['row_filter']
            if not re.search(pattern,str(nested(data,key.split('.'))),re.I):
                continue
        yield 'response',number,data


def mrt_rows(path,spec):
    # Parse the public snapshot container and count native records by type and
    # subtype. Payload addresses and peer data stay in the original archive.
    from collections import Counter
    opener=bz2.open if spec['url'].endswith('.bz2') else __import__('gzip').open
    counts=Counter()
    with opener(path,'rb') as file:
        while header:=file.read(12):
            if len(header)!=12:
                raise ValueError('truncated_mrt_header')
            timestamp,kind,subtype,size=struct.unpack('!IHHI',header)
            if not 0<size<=32*1024**2 or len(file.read(size))!=size:
                raise ValueError('truncated_or_oversized_mrt_record')
            day=datetime.fromtimestamp(timestamp,timezone.utc).date().isoformat()
            if not day.startswith(str(spec['year'])):
                raise ValueError('mrt_interval_mismatch')
            counts[(day,kind,subtype)]+=1
    for i,((day,kind,subtype),count) in enumerate(sorted(counts.items()),1):
        yield 'archive',i,{'day':day,'mrt_type':kind,'mrt_subtype':subtype,'record_count':count}


def sec_rows(path,spec):
    from metadata_engine.sec_documents import validate_submission
    body=path.read_bytes()
    header=body.split(b'</SEC-HEADER>',1)[0].decode('ascii','replace')
    form_match=re.search(r'CONFORMED SUBMISSION TYPE:\s*(SC 13[DG](?:/A)?)\s',header)
    filed=re.search(r'FILED AS OF DATE:\s*(\d{8})',header)
    if not form_match or not filed or not filed[1].startswith(str(spec['year'])):
        raise ValueError('sec_ownership_form_or_filing_date_mismatch')
    form=form_match[1]
    if spec['dataset'] not in ('schedule_13d','schedule_13g') or not form.startswith('SC '+spec['dataset'].split('_')[1].upper()):
        raise ValueError('sec_ownership_dataset_mismatch')
    accession=urlsplit(spec['url']).path.rsplit('/',1)[-1].removesuffix('.txt')
    ciks=re.findall(r'CENTRAL INDEX KEY:\s*(\d+)',header)
    proof=validate_submission(body,accession,ciks,form)
    yield 'submission',1,{**proof,'filed_date':datetime.strptime(filed[1],'%Y%m%d').date().isoformat(),
                          'ciks':ciks,'record_type':'beneficial_ownership_filing'}


def xml_rows(path,spec):
    tree=ElementTree.parse(path)
    elements=tree.findall(spec['element_path'],spec.get('namespaces',{}))
    if not elements:
        raise ValueError('missing_native_xml_observations')
    for number,element in enumerate(elements,1):
        yield 'xml',number,{'tag':element.tag,'attributes':element.attrib,'xml':ElementTree.tostring(element,encoding='unicode')}


def entsoe_load_rows(path, spec):
    raw = path.read_bytes()
    if re.search(rb'<!\s*(DOCTYPE|ENTITY)\b', raw, re.IGNORECASE):
        raise ValueError('unexpected_entsoe_xml_declaration')
    document = ElementTree.fromstring(raw)
    for element in document.iter():
        element.tag = element.tag.rsplit('}', 1)[-1]
    if (document.tag != 'GL_MarketDocument' or document.findtext('type') != 'A65'
            or document.findtext('process.processType') != 'A16'):
        raise ValueError('unexpected_entsoe_total_load_document')
    response_created = parse_instant(document.findtext('createdDateTime'))
    envelope = {'document_mrid': document.findtext('mRID'),
                'document_revision': int(document.findtext('revisionNumber')),
                'response_created_at': response_created.isoformat()}
    first, stop = [parse_instant(spec[key]) for key in ('window_start', 'window_end_exclusive')]
    previous_end = first
    ordinal = 0
    for series in document.findall('TimeSeries'):
        zone = series.findtext('outBiddingZone_Domain.mRID')
        curve = series.findtext('curveType')
        if (zone != spec['bidding_zone'] or series.findtext('quantity_Measure_Unit.name') != 'MAW'
                or curve not in ('A01', 'A03')):
            raise ValueError('unexpected_entsoe_total_load_series')
        for period in series.findall('Period'):
            start = parse_instant(period.findtext('timeInterval/start'))
            end = parse_instant(period.findtext('timeInterval/end'))
            resolution = period.findtext('resolution')
            duration = re.fullmatch(r'PT([1-9]\d*)M', resolution or '')
            if not duration or not previous_end <= start < end <= stop:
                raise ValueError('invalid_entsoe_period')
            step = timedelta(minutes=int(duration[1]))
            if (end - start) % step:
                raise ValueError('entsoe_period_resolution_mismatch')
            slots = (end - start) // step
            points = period.findall('Point')
            positions = [int(point.findtext('position')) for point in points]
            if not positions or positions != sorted(set(positions)) or not 1 <= positions[0] <= positions[-1] <= slots:
                raise ValueError('invalid_entsoe_point_positions')
            if curve == 'A03' and positions[0] != 1:
                raise ValueError('missing_entsoe_first_variable_block')
            for point, position, following in zip(points, positions, positions[1:] + [slots + 1]):
                block_start = start + (position - 1) * step
                block_end = start + ((following if curve == 'A03' else position + 1) - 1) * step
                quantity = point.findtext('quantity')
                value = float(quantity)
                if not math.isfinite(value) or value < 0:
                    raise ValueError('invalid_entsoe_load_quantity')
                ordinal += 1
                yield 'actual_total_load', ordinal, {
                    **envelope, 'bidding_zone': zone, 'series_mrid': series.findtext('mRID'),
                    'curve_type': curve, 'resolution': resolution, 'native_position': position,
                    'interval_start': block_start.isoformat(), 'interval_end_exclusive': block_end.isoformat(),
                    'megawatts': value, 'native_quantity': quantity,
                }
            previous_end = end


def rows_for(path,spec):
    with path.open('rb') as file:
        head=file.read(32768)
    if not head or CHALLENGE.search(head):
        raise ValueError('empty_original_or_challenge')
    if head.startswith(b'version https://git-lfs.github.com/spec/v1'):
        raise ValueError('git_lfs_pointer_without_original')
    if spec['format']!='html' and head.lstrip().lower().startswith((b'<!doctype html',b'<html')):
        raise ValueError('provider_returned_html_instead_of_native_file')
    parser={
        'xlsx':excel_rows,'xls':excel_rows,'zip_csv':zip_rows,'zip_excel':zip_rows,'zip_xpt':zip_rows,
        'pdf':pdf_rows,'html':html_rows,'json':json_rows,'sec':sec_rows,'mrt':mrt_rows,'xml':xml_rows,
        'cmf_ifrs':cmf_ifrs_rows,'google_trends_csv':google_trends_rows,'entsoe_load_xml':entsoe_load_rows,
    }
    if spec['format']=='csv':
        with path.open('rb') as stream:
            yield from csv_rows(stream,spec,'file')
    else:
        yield from parser[spec['format']](path,spec)


def prepared_rows(path,spec):
    limit=spec.get('max_rows',100000)
    rows=[]
    occurrences={}
    for name,ordinal,data in rows_for(path,spec):
        if len(rows)>=limit:
            return rows,True
        # Some native formats have no numeric row locator or documented ID.
        ordinal=ordinal or (occurrences.get(name,0)+1)
        occurrences[name]=occurrences.get(name,0)+1
        rows.append((name,ordinal,data))
    if not rows:
        raise ValueError('no_parsed_provider_records')
    return rows,False


def record(run,spec,row,evidence,index_evidence=None):
    name,position,value=row
    identifier=next((str(value[k]) for k in spec.get('id_fields',[]) if value.get(k) not in (None,'')),None)
    identity=digest([spec['key'],name,identifier,position if identifier is None else None]) if spec.get('id_fields') else digest([spec['key'],name,position])
    event=value.get(spec.get('day_field',''))
    if event and re.fullmatch(r'\d{4}-\d{2}-\d{2}',str(event)):
        event={'value':event,'precision':'day','source_timezone':spec.get('timezone','UTC')}
    elif spec.get('timestamp_field'):
        event={'value':value[spec['timestamp_field']],'precision':'second','source_timezone':'UTC'}
    else:
        event=None
    reference_year = int(event['value'][:4]) if event and 'end_year' in spec else spec['year']
    return seal_record({
        'document_type':'collected_record','schema_version':'1.0','source':run.spec['source'],'dataset':spec['dataset'],
        'source_record_id':identity,'source_record_id_basis':'documented_composite',
        'source_url':evidence['source_url'],'event_at':event,
        'available_at':None,'source_updated_at':None,'availability_basis':'unknown','availability_evidence':[],
        'ingested_at':evidence['retrieved_at'],'run_id':run.run_id,'universe_version':run.universe['universe_version'],
        'company_ids':[],'listing_ids':[],'person_ids':[],'product_ids':[],'entity_match_status':'unresolved',
        'payload':{'data':value,'source_evidence':[evidence]+([index_evidence] if index_evidence else []),'native_member':name,'native_row':position,
                   'scope':spec['scope'],'reference_year':reference_year,'point_in_time_eligible':False},
    })


def capture_one(args):
    spec,s3,bucket,store,settings,universe,taxonomy,imports=args
    source=f"market_source_{spec['id']}"
    with tempfile.TemporaryDirectory(prefix='market-archive-') as directory:
        path=Path(directory)/('file.xlsx' if spec['format']=='xlsx' else 'provider-file')
        manual=imports.get(spec['key'])
        if manual:
            if not manual.is_file() or manual.stat().st_size>spec.get('max_mb',64)*1024**2:
                raise ValueError('manual_archive_file_missing_or_too_large')
            import shutil
            shutil.copyfile(manual,path)
            final,media,method=spec['url'],spec.get('manual_content_type','application/octet-stream'),'manual_original'
        elif spec.get('manual_only'):
            raise ValueError('manual_archive_file_required')
        else:
            final,media,method=download(spec,path)
        index_evidence = None
        if spec.get('filing_index_url'):
            index = Path(directory)/'filing-index.html'
            index_spec = {**spec, 'url':spec['filing_index_url'], 'max_mb':2}
            index_final, index_media, index_method = direct_download(index_spec, index)
            records, limited = indexed_filing(path, index, spec), False
            index_evidence = retain_original(s3, bucket, source, spec, index, index_final, index_media, index_method)
            final = spec['url']  # Keep the stable register link instead of the expiring document-storage URL.
        else:
            try:
                records,limited=prepared_rows(path,spec)
            except ValueError:
                if not spec.get('decodo') or method!='provider_https':
                    raise
                final,media,method=rendered_download(spec,path)
                records,limited=prepared_rows(path,spec)
        evidence = retain_original(s3, bucket, source, spec, path, final, media, method)
        sha = evidence['sha256']
        publication = publication_from_path(source, path, spec['format'])
        if index_evidence:
            publication = {'value':records[0][2]['filing_date'], 'precision':'day',
                           'basis':'Companies House public filing index', 'scope':'document',
                           'evidence_uri':index_evidence['s3_uri']}
        if publication:
            evidence['publication_evidence'] = publication
        scope={'source_id':spec['id'],'request':spec['key'],'original_sha256':sha,
               'coverage_note':spec['scope'],'parsed_row_limit':spec.get('max_rows',100000)}
        end_year=spec.get('end_year',spec['year'])
        window=(spec.get('window_start',f"{spec['year']}-01-01T00:00:00Z"),
                spec.get('window_end_exclusive',f"{end_year+1}-01-01T00:00:00Z"))
        task=task_spec(source,spec['dataset'],'historical',*window,scope,VERSION,universe,taxonomy)
        try:
            run=CollectionRun.start(store,task,universe,taxonomy,settings,resume=True)
        except AlreadyComplete as complete:
            key=str(complete)
        else:
            offset=int(run.cursor or 0)
            while offset<len(records):
                boundary=min(offset+2000,len(records))
                end=boundary==len(records)
                run.commit_page((record(run,spec,row,evidence,index_evidence) for row in records[offset:boundary]),
                                next_cursor=None if end else str(boundary),exhausted=end)
                offset=boundary
            key=run.finish('complete',expected_records=len(records))
        final_manifest=json.loads(store.get(key).body)
        return {'id':spec['id'],'source':source,'dataset':spec['dataset'],'scope':spec['scope'],
                'records':final_manifest['record_count'],'bounded_parse':limited,'raw':evidence,'manifest':key}


def retain_original(s3, bucket, source, spec, path, url, media, method):
    first_year, last_year = spec['year'], spec.get('end_year', spec['year'])
    period = str(first_year) if first_year == last_year else f'{first_year}-{last_year}'
    with path.open('rb') as file:
        sha = hashlib.file_digest(file, 'sha256').hexdigest()
        file.seek(0)
        key = f"{MARKET}/historical-exports/{source}/{spec['dataset']}/{period}/{sha}"
        immutable_put(s3, bucket, key, file, sha, media, verify=True)
    return {'s3_uri':f's3://{bucket}/{key}', 'sha256':sha, 'source_url':url,
            'retrieved_at':utcnow().isoformat(), 'bytes':path.stat().st_size, 'method':method}


def capture(args):
    settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json')
    s3=boto3.client('s3',region_name=settings.region)
    store=settings.store(s3)
    current=load_json(RESULTS) if RESULTS.exists() else {}
    taxonomy=load_json(ROOT/'config/sectors.v1.json')
    universe=read_universe(s3,settings.s3_bucket)
    imports={}
    for item in args.file:
        key,sep,path=item.partition('=')
        if not sep:
            raise ValueError('--file requires archive-key=/path/to/original')
        imports[key]=Path(path)
    selection=[row for row in profiles() if (not args.source or row['id'] in args.source) and
               (not args.key or row['key'] in args.key) and (not imports or row['key'] in imports) and
               (not row.get('manual_only') or row['key'] in imports)]
    if set(imports)-{r['key'] for r in selection} or not selection:
        raise ValueError('no_matching_reviewed_download')
    with ThreadPoolExecutor(max_workers=min(max(args.workers,1),5)) as pool:
        futures={pool.submit(capture_one,(row,s3,settings.s3_bucket,store,settings,universe,taxonomy,imports)):row for row in selection}
        for future in as_completed(futures):
            spec=futures[future]
            try:
                result=future.result()
            except Exception as exc:
                reason=str(exc)[:180] if isinstance(exc,ValueError) or exc.__class__.__name__=='ScrapeError' else type(exc).__name__
                result={'id':spec['id'],'dataset':spec['dataset'],'scope':spec['scope'],'url':spec['url'],'error':reason}
            if 'error' in result and current.get(spec['key'],{}).get('manifest'):
                current[spec['key']]['last_attempt_error']=result['error']
            else:
                current[spec['key']]=result
            write(RESULTS,current)
            print(spec['key'],result.get('records'),result.get('error','committed'),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=int,action='append')
    parser.add_argument('--key',action='append')
    parser.add_argument('--file',action='append',default=[])
    parser.add_argument('--workers',type=int,default=4)
    capture(parser.parse_args())


if __name__=='__main__':
    main()
