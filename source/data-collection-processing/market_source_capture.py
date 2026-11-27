"""Bounded original-file capture for the market workbook using Constellation S3."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
from html.parser import HTMLParser
import itertools
import json
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

import requests
from botocore.exceptions import ClientError
from provider_publication import from_path as publication_from_path

ROOT = Path(__file__).resolve().parent
ROUTES = ROOT / 'config/market-source-routes.v1.json'
ACTIVATION = ROOT / 'config/market-source-activation.v1.json'
PREFIX = 'research-data/constellation-backfill/public-capture'
MARKET = PREFIX + '/market-workbook-v1'
USER_AGENT = 'ConstellationResearch/1.0 (support@optima-holdings.com)'
CHALLENGE = re.compile(rb'cf-chl-|<title>\s*(?:just a moment|access denied|sign in)|request rate threshold exceeded', re.I)


def utcnow():
    return datetime.now(timezone.utc)


def configuration():
    return json.loads(ROUTES.read_text())


def active_routes():
    return json.loads(ACTIVATION.read_text()) if ACTIVATION.exists() else {}


def utc(day):
    return datetime.combine(day, datetime.min.time(), timezone.utc)


def boundaries(kind, start, end):
    start = utc(start)
    end = utc(end)
    while start < end:
        if kind == '15min':
            following = start + timedelta(minutes=15)
        elif kind == 'hour':
            following = start + timedelta(hours=1)
        elif kind == 'day':
            following = start + timedelta(days=1)
        elif kind in ('month', 'quarter'):
            months = start.year * 12 + start.month - 1
            stride = 3 if kind == 'quarter' else 1
            months = (months // stride + 1) * stride
            following = start.replace(year=months // 12, month=months % 12 + 1, day=1)
        elif kind in ('year', 'cycle'):
            following = start.replace(year=start.year + (2 if kind == 'cycle' else 1), month=1, day=1)
        else:
            raise ValueError(f'unknown partition type {kind}')
        yield start, min(following, end)
        start = following


def request_url(template, start, stop):
    last = stop - timedelta(seconds=1)
    return template.format(
        date=start.date(), date_iso=start.date(), end=stop.date(), last=last.date(),
        last_iso=last.date(), year=start.year, next_year=start.year+1,
        quarter=(start.month-1)//3+1, month=start.month, month02=f'{start.month:02d}', hour=start.hour,
        start_compact=start.strftime('%Y%m%d'), last_compact=last.strftime('%Y%m%d'),
        stamp=start.strftime('%Y%m%d%H%M%S'), start_epoch=int(start.timestamp()), last_epoch=int(last.timestamp()),
    )


def plan(profile, mode, cutoff, today):
    templates = profile['history' if mode == 'historical' else 'current']
    if not templates:
        return iter(())
    kind = profile.get('history_step' if mode == 'historical' else 'current_step')
    if not kind:
        return iter([('release_index', templates)])
    lagged = today - timedelta(days=profile.get('lag_days', 0))
    if mode == 'historical':
        start = date(2015 if kind == 'cycle' else 2016, 1, 1)
        end = min(cutoff, lagged)
    else:
        if kind == 'year':
            start = date(lagged.year, 1, 1)
        elif kind == 'cycle':
            start = date(lagged.year - (lagged.year + 1) % 2, 1, 1)
        elif kind == 'quarter':
            start = date(lagged.year, ((lagged.month-1)//3)*3+1, 1)
        elif kind == 'month':
            start = (lagged.replace(day=1) - timedelta(days=1)).replace(day=1)
        else:
            start = lagged - timedelta(days=1)
        end = lagged + timedelta(days=1)

    def partitions():
        for left, right in boundaries(kind, start, end):
            if profile.get('weekdays') and left.weekday() >= 5:
                continue
            yield left.strftime('%Y-%m-%dT%H%M'), [request_url(template, left, right) for template in templates]

    return partitions()


def nested(value, parts):
    for part in parts:
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def date_value(value):
    if isinstance(value, int):
        if 1900 <= value <= 2100:
            return str(value)
        if 946684800 <= value <= 4102444800:
            return datetime.fromtimestamp(value, timezone.utc).date().isoformat()
    if isinstance(value, str) and re.fullmatch(r'\d{1,2}/\d{1,2}/\d{4}', value):
        return datetime.strptime(value,'%m/%d/%Y').date().isoformat()
    if isinstance(value, str) and re.match(r'^(?:19|20)\d{2}(?:\d{4}|-\d{2}-\d{2})?', value):
        raw = re.match(r'^(?:19|20)\d{2}(?:\d{4}|-\d{2}-\d{2})?', value)[0]
        if len(raw) == 8:
            return f'{raw[:4]}-{raw[4:6]}-{raw[6:]}'
        return raw
    return None


def validated(path, profile, url):
    fmt = profile['format']
    with path.open('rb') as file:
        head = file.read(32768)
    if not head or CHALLENGE.search(head):
        raise ValueError('empty_or_access_challenge')
    html = head.lstrip().lower().startswith((b'<!doctype html', b'<html'))
    if html and fmt != 'html':
        raise ValueError('provider_returned_html_instead_of_data')
    tokens = profile.get('tokens', [])
    pattern = profile.get('dated_pattern')
    dates = []
    details = {}

    if fmt in ('json', 'gzip_jsonl'):
        if fmt == 'json':
            root = json.loads(path.read_bytes())
            records = nested(root, profile.get('path', []))
            records = list(records.values()) if profile.get('dict_records') and isinstance(records, dict) else records
            if isinstance(records, dict):
                records = [records]
            if profile.get('json_header') and isinstance(records,list):
                records = records[1:]
        else:
            root = {}
            with gzip.open(path, 'rb') as rows:
                records = [json.loads(line) for line in itertools.islice(rows, 30)]
                for _ in iter(lambda: rows.read(1024*1024), b''):
                    pass  # gzip verifies stream completion and CRC
        if not isinstance(records, list):
            raise ValueError('unexpected_provider_json_envelope')
        if not records:
            if profile.get('empty_ok'):
                return None
            raise ValueError('empty_provider_records')
        fields = profile.get('fields', [])
        if not all(isinstance(item, dict) and all(nested(item, k.split('.')) is not None for k in fields) for item in records[:30]):
            raise ValueError('unexpected_provider_record_fields')
        dates = [date_value(nested(item, key.split('.'))) for item in records for key in profile.get('dated', [])]
        if profile.get('date_from_url'):
            dates.append(date_value(urlsplit(url).path.rsplit('/', 1)[-1].split('.')[0]))
        details['records_in_response'] = len(records) if fmt == 'json' else None
        next_page = bool(root.get(profile.get('pagination_flag'))) if isinstance(root, dict) else False
        total = root.get(profile.get('page_total')) if isinstance(root, dict) else None
        details['pagination_incomplete'] = next_page or (str(total).isdigit() and int(total)>len(records))
    elif fmt == 'gdelt':
        with ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) != 1 or members[0].file_size > 128*1024**2:
                raise ValueError('unexpected_gdelt_archive')
            with archive.open(members[0]) as file:
                row = file.readline(131072).decode('utf-8').rstrip('\r\n').split('\t')
                date_columns = {'events': (1, 8), 'mentions': (1, 14), 'knowledge_graph': (1, 14)}
                column,width = date_columns[profile['dataset']]
                if len(row)!=profile['columns'] or not re.fullmatch(r'\d{'+str(width)+'}',row[column]):
                    raise ValueError('unexpected_gdelt_columns')
                for _ in iter(lambda: file.read(1024*1024), b''):
                    pass
            details['provider_file_interval'] = members[0].filename[:14]
    elif fmt in ('zip', 'xlsx', 'document') and head.startswith(b'PK\x03\x04'):
        with ZipFile(path) as archive:
            members = [member for member in archive.infolist() if not member.is_dir()]
            if not members or len(members) > 2000 or sum(m.file_size for m in members)>profile.get('max_expanded_mb',512)*1024**2:
                raise ValueError('archive_expansion_limit')
            names = [member.filename for member in members]
            lookup = '\n'.join(names)
            if fmt in ('xlsx', 'document'):
                if 'xl/workbook.xml' not in names:
                    raise ValueError('workbook_structure_missing')
                workbook = archive.read('xl/workbook.xml').decode('utf-8', 'replace')
                lookup += '\n'+workbook
            if any(not re.search(token, lookup, re.I) for token in tokens):
                raise ValueError('expected_archive_members_missing')
            if archive.testzip():
                raise ValueError('archive_checksum_invalid')
            details['native_members'] = names[:30]
    elif fmt in ('pdf', 'document') and head.startswith(b'%PDF-'):
        with path.open('rb') as file:
            file.seek(-min(4096, path.stat().st_size), 2)
            if b'%%EOF' not in file.read():
                raise ValueError('incomplete_pdf')
    elif fmt == 'xpt':
        if not head.startswith(b'HEADER RECORD*******LIBRARY HEADER RECORD') or b'MEMBER  HEADER RECORD' not in head or path.stat().st_size < 800:
            raise ValueError('invalid_sas_transport')
    elif fmt in ('html', 'text', 'csv', 'xml'):
        body = path.read_bytes().decode(profile.get('encoding','utf-8-sig'), 'replace')
        if not all(re.search(token, body[:262144], re.I) for token in tokens):
            raise ValueError('expected_content_fields_missing')
        if fmt == 'csv' and (len(body.splitlines())<2 or not re.search(r'[,;\t|]',body.splitlines()[0])):
            raise ValueError('invalid_delimited_rows')
        if fmt == 'xml':
            ElementTree.fromstring(body)
        if fmt == 'html' and (not html or len(body)<1000):
            raise ValueError('invalid_document_html')
        if pattern:
            flags = re.M if profile.get('multiline_dates') else 0
            dates.extend(date_value(match[0] if isinstance(match, tuple) else match) for match in re.findall(pattern,body,flags))
            if not any(dates):
                raise ValueError('dated_source_rows_missing')
    else:
        raise ValueError('unexpected_original_file_format')
    dates = sorted(set(v for v in dates if v))
    details.update(format=fmt, observed_from=dates[0] if dates else None, observed_through=dates[-1] if dates else None)
    return details


class Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        href = dict(attrs).get('href')
        if tag == 'a' and href:
            self.hrefs.append(href)


def allowed(profile, url):
    parsed = urlsplit(url)
    return (parsed.scheme == 'https' and parsed.hostname in profile['hosts']
            and not parsed.username and not parsed.password and parsed.port in (None,443))


def get(session, profile, url, headers=None):
    headers = {**(headers or {}), 'User-Agent': USER_AGENT, 'Accept': profile.get('accept', '*/*')}
    for _ in range(5):
        if not allowed(profile,url):
            raise ValueError('destination_outside_reviewed_provider_hosts')
        from constellation.shared_limits import admit
        admit(url)
        response = session.get(url, headers=headers, timeout=(6,25), stream=True, allow_redirects=False)
        if response.is_redirect:
            target = urljoin(url, response.headers['Location'])
            response.close()
            url = target
            continue
        if response.status_code in (200,304):
            return response
        status = response.status_code
        response.close()
        raise ValueError(f'provider_http_{status}')
    raise ValueError('provider_redirect_limit')


def documents(session, profile, seeds, mode, today):
    if not profile.get('link'):
        if profile.get('pointer') == 'hn' and mode == 'daily':
            with get(session,profile,seeds[0]) as response:
                top = response.json()
            if not isinstance(top, int):
                raise ValueError('invalid_hacker_news_high_watermark')
            return [seeds[0].replace('maxitem',f'item/{offset}') for offset in range(top, top-10, -1)]
        return seeds
    if mode == 'historical' and profile.get('seed_is_document_history'):
        return seeds
    matches = []
    for url in seeds:
        if profile.get('direct_document_ext') and urlsplit(url).path.endswith(profile['direct_document_ext']):
            matches.append(url)
            continue
        with get(session, profile, url) as response:
            raw = b''.join(itertools.islice(response.iter_content(65536), 33))
            if len(raw) > 2*1024**2 or CHALLENGE.search(raw[:32768]):
                raise ValueError('provider_index_limit_or_challenge')
            parser = Anchors()
            parser.feed(raw.decode('utf-8','replace'))
            for href in parser.hrefs:
                target = urljoin(response.url,href).split('#',1)[0].replace(' ','%20')
                if allowed(profile,target) and re.search(profile['link'],urlsplit(target).path,re.I):
                    if profile.get('exclude_current_year') and str(today.year) in urlsplit(target).path.rsplit('/',1)[-1]:
                        continue
                    matches.append(target)
    def year(url):
        found = re.findall(r'(?<!\d)20(?:1[6-9]|2\d)(?!\d)', urlsplit(url).path)
        return int(found[-1]) if found else 0
    if mode == 'historical':
        return sorted(set(matches),key=lambda u:(year(u)==0,year(u),u))
    return sorted(dict.fromkeys(matches),key=year,reverse=True)[:profile.get('current_items',4)]


def immutable_put(s3, bucket, key, body, digest, media, *, verify=False):
    checksum = base64.b64encode(bytes.fromhex(digest)).decode()
    try:
        s3.put_object(Bucket=bucket,Key=key,Body=body,ServerSideEncryption='AES256',
                      ContentType=media,IfNoneMatch='*',ChecksumSHA256=checksum)
    except ClientError as exc:
        if exc.response['Error']['Code'] not in ('412','PreconditionFailed','ConditionalRequestConflict'):
            raise
        verify = True
    if verify:
        stream = s3.get_object(Bucket=bucket,Key=key)['Body']
        actual = hashlib.sha256()
        try:
            for chunk in stream.iter_chunks(128*1024):
                actual.update(chunk)
        finally:
            stream.close()
        if actual.hexdigest()!=digest:
            raise ValueError('retained_original_checksum_mismatch')


def json_bytes(value):
    return (json.dumps(value,ensure_ascii=False,sort_keys=True)+'\n').encode()


def retain_json(s3,bucket,key,value):
    body = json_bytes(value)
    immutable_put(s3,bucket,key,body,hashlib.sha256(body).hexdigest(),'application/x-ndjson')


def save_state(s3, bucket, key, state, etag):
    condition = {'IfMatch':etag} if etag else {'IfNoneMatch':'*'}
    response = s3.put_object(Bucket=bucket,Key=key,Body=json_bytes(state),
                             ServerSideEncryption='AES256',ContentType='application/json',**condition)
    return response['ETag']


def metadata_key(receipt):
    return f"{PREFIX}/athena/market-{receipt['source']}-{receipt['dataset']}-{receipt['sha256']}.jsonl"


def capture(session, s3, bucket, profile, mode, url, partition, previous=None, *, verify=False):
    conditional = {}
    if previous:
        if previous.get('etag'):
            conditional['If-None-Match'] = previous['etag']
        if previous.get('last_modified'):
            conditional['If-Modified-Since'] = previous['last_modified']
    with get(session,profile,url,conditional) as response:
        if response.status_code==304:
            return previous, False
        max_bytes = profile.get('max_mb',16)*1024**2
        if response.headers.get('Content-Length','').isdigit() and int(response.headers['Content-Length'])>max_bytes:
            raise ValueError('original_exceeds_configured_byte_limit')
        scratch = Path('/dev/shm')
        with tempfile.NamedTemporaryFile(dir=scratch) as file:
            digest = hashlib.sha256()
            size = 0
            deadline = time.monotonic()+120
            for chunk in response.iter_content(128*1024):
                size += len(chunk)
                if size > max_bytes or time.monotonic()>deadline:
                    raise ValueError('original_exceeds_capture_budget')
                file.write(chunk)
                digest.update(chunk)
            file.flush()
            details = validated(Path(file.name),profile,response.url)
            if details is None:
                return {'status':'checked_no_data', 'checked_at':utcnow().isoformat()}, False
            publication = publication_from_path(profile['source'], Path(file.name), profile['format'])
            sha = digest.hexdigest()
            if previous and previous.get('sha256')==sha:
                return previous, False
            media = response.headers.get('Content-Type','application/octet-stream')
            key = f"{MARKET}/objects/{profile['source']}/{sha}"
            file.seek(0)
            immutable_put(s3,bucket,key,file,sha,media,verify=verify)
            receipt = {
                'source':profile['source'],'catalog_entry':profile['catalog_entry'],'dataset':profile['dataset'],
                'resource_url':url,'source_url':response.url,'retrieved_at':utcnow().isoformat(),
                'artifact_uri':f's3://{bucket}/{key}','sha256':sha,'bytes':size,'media_type':media,'mode':mode,
                'artifact_kind':'public_document','market_original':True,'validation':details,'partition':partition,
                'scope_note':profile['scope'],'historical_target_start':'2016-01-01','available_at':None,
                'etag':response.headers.get('ETag'),'last_modified':response.headers.get('Last-Modified'),
                'previous_sha256':previous.get('sha256') if previous else None,
            }
            if publication:
                receipt['publication_evidence'] = publication
            receipt_identity = hashlib.sha256(url.encode()).hexdigest()
            validator_identity = hashlib.sha256(json_bytes(details)).hexdigest()[:16]
            receipt_key = f"{MARKET}/receipts/{mode}/{profile['source']}/{profile['dataset']}/{receipt_identity}/{sha}-{validator_identity}.jsonl"
            receipt['evidence_receipt_key'] = receipt_key
            # Identical versions may appear in overlapping windows. Preserve
            # the first immutable receipt, and verify the original independently.
            from public_source_capture import read_json
            existing, _ = read_json(s3,receipt_key)
            if existing:
                return existing,False
            retain_json(s3,bucket,receipt_key,receipt)
            return receipt,True


def pilot_one(args):
    profile,mode,cutoff,today,bucket=args
    import boto3
    s3=boto3.client('s3',region_name='us-east-1')
    errors=[]
    with requests.Session() as session:
        for partition,seeds in itertools.islice(plan(profile,mode,cutoff,today), 12 if profile.get('history_step')=='day' else 2):
            try:
                urls = documents(session,profile,seeds,mode,today)
                if not urls:
                    errors.append({'url':seeds[0],'reason':'reviewed_document_links_not_found'})
                for url in urls[:4]:
                    try:
                        record,_ = capture(session,s3,bucket,profile,mode,url,partition,verify=True)
                        if record.get('sha256'):
                            return {'receipt':record,'attempts':errors}
                        errors.append({'url':url,'reason':'checked_no_data'})
                    except (ValueError, OSError, requests.RequestException, ClientError, BadZipFile, ElementTree.ParseError) as exc:
                        errors.append({'url':url,'reason':str(exc)[:160] if isinstance(exc,ValueError) else type(exc).__name__})
                        if str(exc) in ('provider_http_429','original_exceeds_configured_byte_limit'):
                            break
            except (ValueError, OSError, requests.RequestException, ClientError) as exc:
                errors.append({'url':seeds[0],'reason':str(exc)[:160] if isinstance(exc,ValueError) else type(exc).__name__})
    return {'attempts':errors}


def run(source, mode, limit, s3, *, now=None):
    from public_source_capture import BUCKET, read_json
    conf = configuration()
    active = active_routes().get(source, {})
    today = (now or utcnow()).date()
    cutoff = date.fromisoformat(conf['historical_cutoff_exclusive'])
    profiles = [profile for profile in conf['routes'] if profile['source']==source and
                mode in active.get(profile['dataset'],{}).get('modes',[])]
    results = []
    drained = bool(profiles)
    with requests.Session() as session:
        for profile in profiles:
            dataset = profile['dataset']
            revision = profile.get('capture_revision')
            checkpoint = f'{dataset}-{revision}' if revision else dataset
            key = f'{MARKET}/state/{mode}/{source}/{checkpoint}.json'
            state,etag = read_json(s3,key)
            state = state or {'cursor':0,'frontier':[],'resources':{}}
            if mode=='daily' and not state.get('plan_day'):
                if state.get('next_check','')>str(today):
                    continue
                state.update(plan_day=str(today),cursor=0)
            budget = min(limit, profile.get('batch_size', 3))
            interval = profile['check_days']
            plan_day = date.fromisoformat(state['plan_day']) if mode=='daily' else today
            depth = state['cursor'] + bool(state['frontier'])
            partitions = itertools.islice(plan(profile,mode,cutoff,plan_day),depth,None)
            for _ in range(budget):
                if not state['frontier']:
                    try:
                        partition,seeds=next(partitions)
                    except StopIteration:
                        if mode=='daily':
                            state.update(plan_day=None,next_check=str(today+timedelta(days=interval)))
                        break
                    try:
                        urls=documents(session,profile,seeds,mode,plan_day)
                    except (ValueError,requests.RequestException) as exc:
                        results.append({'dataset':dataset,'partition':partition,'reason':str(exc)[:160]})
                        drained=False
                        break
                    state['frontier']=[(partition,url) for url in urls]
                    state['active_partition']=partition
                    if not urls:
                        drained=False
                        results.append({'dataset':dataset,'partition':partition,'reason':'reviewed_document_links_not_found'})
                        break
                partition,url=state['frontier'].pop(0)
                prior=state['resources'].get(url)
                try:
                    receipt,changed=capture(session,s3,BUCKET,profile,mode,url,partition,prior)
                    if mode=='daily':
                        state['resources'][url]=receipt
                    if receipt.get('sha256') and active[dataset].get('metadata'):
                        from public_source_capture import read_json
                        if not read_json(s3,metadata_key(receipt))[0]:
                            retain_json(s3,BUCKET,metadata_key(receipt),receipt)
                    if receipt.get('validation',{}).get('pagination_incomplete'):
                        state.setdefault('gaps',{})[partition]='additional_provider_pages_required'
                    results.append({'dataset':dataset,'partition':partition,'status':'captured' if changed else receipt.get('status','checked_no_change'),'sha256':receipt.get('sha256')})
                except (ValueError,OSError,requests.RequestException,ClientError,BadZipFile,ElementTree.ParseError) as exc:
                    reason=str(exc)[:160] if isinstance(exc,ValueError) else type(exc).__name__
                    state.setdefault('gaps',{})[partition+' '+url]=reason
                    results.append({'dataset':dataset,'partition':partition,'reason':reason})
                if not state['frontier']:
                    state['cursor']+=1
                etag=save_state(s3,BUCKET,key,state,etag)
            else:
                drained=False
            if state['frontier']:
                drained=False
            if mode=='daily':
                if len(state['resources'])>128:
                    ordered = sorted(state['resources'],key=lambda url:state['resources'][url].get('retrieved_at',''))
                    state['resources']={url:state['resources'][url] for url in ordered[-128:]}
                save_state(s3,BUCKET,key,state,etag)
    collected=sum(row.get('status')=='captured' for row in results)
    failed=sum('reason' in row for row in results)
    report={'collector':'public_document_capture','source':source,'mode':mode,'at':utcnow().isoformat(),
            'outcomes':results,'captured_urls':collected,'remaining_urls':int(not drained),'failed_urls':failed,
            'route_drained':drained,'historical_complete':False}
    import os,uuid
    from public_source_capture import put
    base=os.environ.get('CONSTELLATION_OPERATION_RECEIPT_PREFIX','constellation-backfill/public-capture/daily-receipts')
    report_key=f'research-data/{base}/{uuid.uuid4().hex}.json'
    put(s3,report_key,json_bytes(report))
    print(json.dumps({'report_key':report_key.removeprefix('research-data/'),'public_capture_summary':{k:report[k] for k in ('source','mode','captured_urls','remaining_urls','failed_urls')}}),flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['pilot','plan','collect'])
    parser.add_argument('--source',type=int,action='append')
    parser.add_argument('--mode',choices=['daily','historical'])
    parser.add_argument('--limit',type=int,default=3)
    parser.add_argument('--output',type=Path,default=ROOT/'config/market-source-pilots.v1.json')
    parser.add_argument('--workers',type=int,default=6)
    args=parser.parse_args()
    if args.action=='collect':
        if len(args.source or [])!=1 or not args.mode or not 1<=args.limit<=12:
            parser.error('collect requires one --source, --mode, and a limit from 1 to 12')
        import os
        import boto3
        expected = 'worker' if args.mode=='historical' else 'controller'
        if os.environ.get('CONSTELLATION_ROLE','controller')!=expected:
            parser.error('collect is assigned to the '+expected+' host')
        run(f'market_source_{args.source[0]}',args.mode,args.limit,boto3.client('s3',region_name='us-east-1'))
        return
    config=configuration()
    profiles=[p for p in config['routes'] if not args.source or p['catalog_entry'] in args.source]
    cutoff=date.fromisoformat(config['historical_cutoff_exclusive'])
    from public_source_capture import BUCKET
    today=cutoff  # fixed first implementation review cutoff, including pilot semantics
    tasks=[(p,mode,cutoff,today,BUCKET) for p in profiles for mode in ('historical','daily') if p['history' if mode=='historical' else 'current']]
    if args.action=='plan':
        for profile,mode,cutoff,today,_ in tasks:
            print(json.dumps({'source':profile['source'],'dataset':profile['dataset'],'mode':mode,'first':list(itertools.islice(plan(profile,mode,cutoff,today),1))}))
        return
    output=json.loads(args.output.read_text()) if args.output.exists() else {}
    with ThreadPoolExecutor(max_workers=min(max(1,args.workers),10)) as pool:
        for task, result in zip(tasks,pool.map(pilot_one,tasks)):
            profile,mode,*_=task
            outcomes = output.setdefault(profile['source'],{}).setdefault(profile['dataset'],{})
            if 'receipt' in result or not outcomes.get(mode,{}).get('receipt'):
                outcomes[mode]=result
            else:
                outcomes[mode]['latest_retry_attempts']=result['attempts']
            temporary=args.output.with_suffix('.tmp')
            temporary.write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n')
            temporary.replace(args.output)
            print(profile['source'],profile['dataset'],mode, 'verified' if result.get('receipt') else 'no evidence',flush=True)


if __name__=='__main__':
    main()
