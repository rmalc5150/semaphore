"""Bounded official API pages with secret-safe evidence and explicit pagination."""
from datetime import date,datetime,timedelta,timezone
from functools import lru_cache
import json
import re
from urllib.parse import urlsplit,urlencode,urlunsplit,parse_qsl
import requests
from regulatory_collection import SourceIssue,require
from research_contract import digest

KINDS={'additional_fred','additional_dart','additional_nasa','additional_biorxiv','additional_datacite','additional_zenodo','additional_huggingface','additional_epo'}
KINDS.update('additional_'+k for k in ('ember','wto_timeseries','wto_qr','wto_eping','census','usda','comtrade','copernicus'))
KINDS.update(('additional_portwatch','additional_unido','additional_nhsbsa','additional_cninfo'))
HOSTS={'api.stlouisfed.org','opendart.fss.or.kr','power.larc.nasa.gov','api.biorxiv.org','www.biorxiv.org','www.medrxiv.org','api.datacite.org','zenodo.org','huggingface.co'}
HOSTS.update({'api.ember-energy.org','api.wto.org','api.census.gov','apps.fas.usda.gov','api.fas.usda.gov','comtradeapi.un.org'})
HOSTS.update(('services9.arcgis.com','stat.unido.org','opendata.nhsbsa.net'))
SECRET='arn:aws:secretsmanager:us-east-1:059416028963:secret:dataSourceAPIkeys-PSTzff'

@lru_cache(maxsize=1)
def credentials():
    import boto3
    try:return json.loads(boto3.client('secretsmanager',region_name='us-east-1').get_secret_value(SecretId=SECRET)['SecretString'])
    except Exception:raise SourceIssue('additional_credentials_unavailable',True) from None

def validated_url(url,host=None):
    u=urlsplit(url)
    require(u.scheme=='https' and u.hostname in HOSTS and not u.username and not u.password and u.port in (None,443),'unreviewed_additional_api_url')
    if host:require(u.hostname==host,'pagination_host_changed')
    return url

def get_json(client,url,params=None,key_field=None,key_parameter='api_key',key_header=None,allow_empty=False):
    validated_url(url)
    public=dict(params or {});query=dict(public);key=None
    if key_field:
        key=credentials().get(key_field);require(isinstance(key,str) and bool(key.strip()),'additional_key_missing')
        if not key_header:query[key_parameter]=key.strip()
    headers={'User-Agent':'ConstellationResearch/1.0 (support@optima-holdings.com)'}
    if key_header:headers[key_header]=key.strip()
    from constellation.shared_limits import admit
    admit(url)
    stage='http_request'
    try:
        with requests.get(url,params=query,headers=headers,timeout=(10,30),stream=True,allow_redirects=False) as r:
            pieces=[];size=0
            for chunk in r.iter_content(65536):
                size+=len(chunk);require(size<=16*1024**2,'additional_response_too_large_split_scope');pieces.append(chunk)
            body=b''.join(pieces)
            if key:
                for value in {key,key.strip(),json.dumps(key)[1:-1]}:body=body.replace(value.encode(),b'[REDACTED]')
            # Evidence includes provider error bodies, with credentials removed.
            public_url=url+('?' +urlencode(public,doseq=True) if public else '')
            stage='archive_response'
            client.save(body,public_url,r.headers.get('Content-Type','application/json'))
            stage='parse_response'
            if r.status_code == 302 and urlsplit(url).hostname == 'api.census.gov':
                location = urlsplit(r.headers.get('Location', ''))
                if location.path == '/data/invalid_key.html' and location.hostname in (None, 'api.census.gov'):
                    raise SourceIssue('census_api_key_rejected')
            if allow_empty and r.status_code == 204 and not body.strip():
                return None, None
            if r.status_code == 400 and urlsplit(url).hostname == 'api.stlouisfed.org':
                try: message = json.loads(body).get('error_message', '')
                except ValueError: message = ''
                if 'series does not exist in ALFRED' in message:
                    raise SourceIssue('fred_vintage_unavailable')
            require(r.status_code==200,'source_http_'+str(r.status_code))
            try:
                try:data=json.loads(body)
                except UnicodeDecodeError:
                    # WTO's legacy time-series service emits Windows-1252 text.
                    if urlsplit(url).hostname!='api.wto.org':raise
                    data=json.loads(body.decode('cp1252'))
            except (ValueError,UnicodeDecodeError):raise SourceIssue('additional_non_json_response') from None
            return data,r.links.get('next',{}).get('url')
    except SourceIssue:raise
    except Exception as exc:
        # Exception strings may include an authenticated URL. Retain only safe
        # failure classification so transport and archive failures are distinct.
        diagnostics={'stage':stage,'host':urlsplit(url).hostname,'exception_type':type(exc).__name__}
        if isinstance(getattr(exc,'response',None),dict):
            diagnostics['aws_error_code']=exc.response.get('Error',{}).get('Code')
        raise SourceIssue('additional_request_failed',True,diagnostics) from None

def datacite_page(client, url, params):
    # Shrink only this request, retaining cursor/filter dimensions. Provider
    # next links carry the reduced size forward; never skip a large record.
    current_url=url
    current_params=dict(params) if params is not None else None
    for size in (100, 10, 1):
        if current_params is not None:
            current_params['page[size]']=size
        else:
            parts=urlsplit(url);query=dict(parse_qsl(parts.query,keep_blank_values=True))
            existing=int(query.get('page[size]',100))
            query['page[size]']=str(min(size,existing))
            current_url=urlunsplit(parts._replace(query=urlencode(query)))
        try:return get_json(client,current_url,current_params)
        except SourceIssue as exc:
            if exc.code!='additional_response_too_large_split_scope' or size==1:raise


def row(item,identity,data,url,day=None,precision='day',derived=False):
    r=item(identity,data,url,day,basis='derived' if derived else 'provider');r['date_precision']=precision;return r

def zenodo_event_date(value):
    """Canonical scalar date only; retain intervals/invalid text in the raw payload."""
    if not isinstance(value, str):
        return None, 'unknown'
    text = value.strip()
    try:
        if len(text) == 4 and text.isdigit():
            date(int(text), 1, 1)
            return text, 'year'
        if len(text) == 7 and text[4] == '-':
            date.fromisoformat(text + '-01')
            return text, 'month'
        if len(text) == 10:
            return date.fromisoformat(text).isoformat(), 'day'
    except ValueError:
        pass
    return None, 'unknown'


def unique(rows):
    require(len({r['id'] for r in rows})==len(rows),'additional_duplicate_provider_ids')

def position(cursor):
    return json.loads(cursor) if cursor else {}

def fetch(client,job,cursor,item):
    if job['adapter']in ('additional_dart','additional_cninfo'):
        from filing_originals_capture import fetch as filing_fetch
        return filing_fetch(client,job,cursor,item)
    if job['adapter']=='additional_nhsbsa':
        from nhsbsa_capture import fetch as nhsbsa_fetch
        return nhsbsa_fetch(client,job,cursor,item)
    if job['adapter']in ('additional_portwatch','additional_unido'):
        from public_statistics_apis import fetch as statistics_fetch
        return statistics_fetch(client,job,cursor,item)
    if job['adapter'] in {'additional_'+k for k in ('ember','wto_timeseries','wto_qr','wto_eping','census','usda','comtrade','copernicus')}:
        from credential_source_apis import fetch as credential_fetch
        return credential_fetch(client,job,cursor,item)
    if job['adapter']=='additional_epo':
        from epo_ops import fetch as epo_fetch
        return epo_fetch(client,job,cursor,item)
    kind=job['adapter'];p=job['parameters'];job={**job,'start':p.get('data_start',job['start']),'end':p.get('data_end',job['end'])};start=date.fromisoformat(job['start']);end=date.fromisoformat(job['end']);last=end-timedelta(days=1);state=position(cursor);rows=[]
    if kind=='additional_fred':
        url='https://api.stlouisfed.org/fred/series/observations';offset=state.get('offset',0)
        meta=state.get('series_metadata')
        if meta is None:
            d,_=get_json(client,'https://api.stlouisfed.org/fred/series',{'series_id':p['series_id'],'file_type':'json'},'FRED')
            require(isinstance(d.get('seriess'),list) and len(d['seriess'])==1,'fred_series_metadata_shape');meta=d['seriess'][0]
        requested_start=date.fromisoformat(p.get('realtime_start','2016-01-01'))
        requested_end=date.fromisoformat(p['realtime_end'])
        segment_start=date.fromisoformat(state.get('segment_start',requested_start.isoformat()))
        segment_end=min(requested_end,date(segment_start.year+3,1,1)-timedelta(days=1))
        if state and 'segment_start' not in state and segment_end<requested_end:
            raise SourceIssue('source_changed_refresh_required')
        d,_=get_json(client,url,{'series_id':p['series_id'],'file_type':'json','observation_start':job['start'],'observation_end':last.isoformat(),'realtime_start':segment_start.isoformat(),'realtime_end':segment_end.isoformat(),'output_type':1,'limit':1000,'offset':offset,'sort_order':'asc'},'FRED')
        require(isinstance(d.get('observations'),list) and isinstance(d.get('count'),int),'fred_response_shape');total=d['count']
        if 'total' in state:require(state['total']==total,'source_changed_refresh_required')
        for r in d['observations']:
            require(job['start']<=r['date']<job['end'],'fred_date_outside_scope')
            identity=':'.join((p['series_id'],r['date'],r['realtime_start'],r['realtime_end']))
            value={**r,'series_id':p['series_id'],'series_metadata':meta,'numeric_value':None if r.get('value')=='.' else r.get('value'),'missing_value':r.get('value')=='.','vintage_basis':'provider realtime interval; no inferred release time'}
            rows.append(row(item,identity,value,'https://fred.stlouisfed.org/series/'+p['series_id'],r['date']))
        following=offset+len(rows);require(following<=total and (bool(rows) or following==total),'fred_truncated_pagination');unique(rows)
        completed=state.get('completed_count',0)
        if following<total:
            return rows,json.dumps({'offset':following,'total':total,'series_metadata':meta,
                'segment_start':segment_start.isoformat(),'completed_count':completed})
        if segment_end<requested_end:
            return rows,json.dumps({'offset':0,'series_metadata':meta,
                'segment_start':(segment_end+timedelta(days=1)).isoformat(),'completed_count':completed+total})
        client.expected_records=completed+total
        return rows,None
    if kind=='additional_nasa':
        require(not cursor,'nasa_unexpected_cursor');url='https://power.larc.nasa.gov/api/temporal/daily/point';parameters=('T2M','PRECTOTCORR','ALLSKY_SFC_SW_DWN')
        d,_=get_json(client,url,{'parameters':','.join(parameters),'community':'RE','longitude':p['longitude'],'latitude':p['latitude'],'start':start.strftime('%Y%m%d'),'end':last.strftime('%Y%m%d'),'format':'JSON','time-standard':'UTC'})
        values=d.get('properties',{}).get('parameter');require(isinstance(values,dict) and all(isinstance(values.get(k),dict) for k in parameters),'nasa_response_shape')
        days=set.union(*(set(values[k]) for k in parameters));require(all(set(values[k])==days for k in parameters),'nasa_parameter_dates_differ');fill=d.get('header',{}).get('fill_value',-999)
        for code in sorted(days):
            day=datetime.strptime(code,'%Y%m%d').date().isoformat();require(job['start']<=day<job['end'],'nasa_date_outside_scope')
            original={k:values[k][code] for k in parameters};missing=[k for k,v in original.items() if v==fill or v is None]
            data={'reference_location':p['location'],'latitude':p['latitude'],'longitude':p['longitude'],'date':day,'values':{k:None if k in missing else v for k,v in original.items()},'provider_values':original,'missing_parameters':missing,'parameters':d.get('parameters'),'header':d.get('header')}
            rows.append(row(item,p['location']+':'+day,data,url,day,derived=True))
        require(len(rows)==(end-start).days,'nasa_missing_calendar_days');return rows,None
    if kind=='additional_biorxiv':
        offset=state.get('offset',0);url=f"https://api.biorxiv.org/details/{p['repository']}/{job['start']}/{last.isoformat()}/{offset}"
        d,_=get_json(client,url);messages=d.get('messages');require(isinstance(messages,list) and messages and isinstance(d.get('collection'),list),'biorxiv_response_shape')
        require(messages[0].get('status') in ('ok','OK'),'biorxiv_provider_error');total=int(messages[0]['total'])
        if state:require(state['total']==total,'source_changed_refresh_required')
        # The listing API is metadata only.  Retain a bounded number of pages
        # per invocation so every emitted record also has its own source PDF.
        # Advancing by emitted rows (rather than the API's 100-row response)
        # makes this resumable without skipping records.
        if offset and 'seen_signatures' not in state:
            raise SourceIssue('biorxiv_cursor_identity_upgrade_required')
        signatures=dict(state.get('seen_signatures',{}));duplicates=state.get('duplicate_rows',0)
        batch=d['collection'][:int(p.get('full_text_per_page',20))]
        consumed=0
        for r in batch:
            consumed+=1
            require(job['start']<=r['date']<job['end'],'biorxiv_date_outside_scope');require(r.get('doi') and r.get('version'),'biorxiv_identity_missing')
            identity=r['doi']+':v'+str(r['version']);signature=digest(r)
            if identity in signatures:
                require(signatures[identity]==signature,'biorxiv_conflicting_duplicate_provider_id')
                duplicates+=1;continue
            require(len(signatures)<20000,'biorxiv_identity_scope_split_required')
            host='www.biorxiv.org' if p['repository']=='biorxiv' else 'www.medrxiv.org'
            pdf=f"https://{host}/content/{r['doi']}v{r['version']}.full.pdf"
            validated_url(pdf,host)
            gateway=None
            paid_before=getattr(client,'_pdf_proxy_requests',0)
            if type(paid_before)is not int:paid_before=0
            raw=client.get(pdf)
            paid_after=getattr(client,'_pdf_proxy_requests',0)
            if type(paid_after)is int and paid_after>paid_before:
                gateway={'transport':'decodo_residential_proxy','last_resort':True}
            require(raw.startswith(b'%PDF-') and b'%%EOF' in raw[-4096:],'biorxiv_full_text_invalid_pdf')
            # EvidenceClient appends this PDF after the listing response.  Do
            # not let another paper's PDF satisfy this record's contract.
            proof=dict(client.evidence[-1])
            data={**r,'full_text_capture':gateway}if gateway else r
            rows.append({**row(item,identity,data,pdf,r['date']), 'source_evidence':[proof]});signatures[identity]=signature
            # One paid fallback per page, then commit immediately; never replay
            # paid successes because a later paper on the page was blocked.
            if gateway:break
        following=offset+consumed;require(following<=total and (bool(batch) or following==total),'biorxiv_truncated_pagination');unique(rows);client.expected_records=total-duplicates
        return rows,json.dumps({'offset':following,'total':total,'seen_signatures':signatures,'duplicate_rows':duplicates}) if following<total else None
    if kind=='additional_datacite':
        url=validated_url(state['url'],'api.datacite.org') if state else 'https://api.datacite.org/dois'
        params=None if state else {'query':f"created:[{job['start']}T00:00:00Z TO {last.isoformat()}T23:59:59.999Z]",'resource-type-id':p['resource'],'page[size]':100,'page[cursor]':'1'}
        d,_=datacite_page(client,url,params);require(isinstance(d.get('data'),list) and isinstance(d.get('meta',{}).get('total'),int),'datacite_response_shape');total=d['meta']['total']
        if state:require(state['total']==total,'source_changed_refresh_required')
        for r in d['data']:
            a=r.get('attributes',{});created=a.get('created');require(isinstance(created,str) and job['start']<=created[:10]<job['end'],'datacite_date_outside_scope')
            rows.append(row(item,r['id'],r,'https://doi.org/'+r['id'],created[:10]))
        next_url=d.get('links',{}).get('next');seen=state.get('seen',0)+len(rows);require(seen<=total and (bool(rows) or seen==total),'datacite_truncated_pagination')
        if seen==total:next_url=None
        elif next_url:validated_url(next_url,'api.datacite.org');require(next_url!=url,'datacite_invalid_next_cursor')
        else:require(seen==total,'datacite_pagination_missing')
        unique(rows);client.expected_records=total
        return rows,json.dumps({'url':next_url,'total':total,'seen':seen}) if next_url else None
    if kind=='additional_zenodo':
        page=state.get('page',1);url='https://zenodo.org/api/records'
        cutoff=state.get('cutoff') or datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
        d,_=get_json(client,url,{'q':f"publication_date:[{job['start']} TO {last.isoformat()}] AND created:[* TO {cutoff}]",'size':25,'page':page,'sort':'mostrecent'})
        hits=d.get('hits',{});require(isinstance(hits.get('hits'),list),'zenodo_response_shape');total=hits.get('total');total=total.get('value') if isinstance(total,dict) else total;require(isinstance(total,int),'zenodo_total_missing')
        if state:require(state['total']==total,'source_changed_refresh_required')
        for r in hits['hits']:
            stamp,precision=zenodo_event_date(r.get('metadata',{}).get('publication_date'))
            emitted=row(item,str(r['id']),r,r.get('links',{}).get('self_html','https://zenodo.org/records/'+str(r['id'])),stamp,precision)
            emitted['date_status']='provider_scalar' if stamp else ('interval_retained_in_raw' if '/' in str(r.get('metadata',{}).get('publication_date','')) else 'invalid_or_missing_retained_in_raw')
            rows.append(emitted)
        seen=state.get('seen',0)+len(rows);require(seen<=total and (bool(rows) or seen==total),'zenodo_truncated_pagination');unique(rows);client.expected_records=total
        if seen<total:require(page*25<10000,'zenodo_query_cap_split_scope_required')
        return rows,json.dumps({'page':page+1,'seen':seen,'total':total,'cutoff':cutoff}) if seen<total else None
    if kind=='additional_huggingface':
        descending=job.get('mode')=='daily'
        url=validated_url(state['url'],'huggingface.co') if state else 'https://huggingface.co/api/'+p['category']
        d,link=get_json(client,url,None if state else {'sort':'createdAt','direction':-1 if descending else 1,'limit':100,'full':'true'})
        require(isinstance(d,list),'huggingface_response_shape');last_date=state.get('last_date');past_end=False
        for r in d:
            require(isinstance(r.get('id'),str),'huggingface_identity_missing');created=r.get('createdAt')
            if created:
                require(last_date is None or (created<=last_date if descending else created>=last_date),'huggingface_creation_sort_changed');last_date=created
                if created[:10]>=job['end']:
                    if not descending:past_end=True
                    continue
                if created[:10]<job['start']:
                    if descending:past_end=True
                    continue
            fraction=re.search(r'\.(\d+)',created or '');digits=len(fraction.group(1)) if fraction else 0
            require(digits<=6,'huggingface_timestamp_precision_unsupported')
            precision='microsecond' if digits>3 else 'millisecond' if digits else 'second'
            rows.append(row(item,p['category']+':'+r['id'],r,'https://huggingface.co/'+('datasets/' if p['category']=='datasets' else '')+r['id'],created,precision if created else 'day'))
        unique(rows)
        if link and not past_end:validated_url(link,'huggingface.co');require(link!=url and bool(d),'huggingface_invalid_next_cursor')
        return rows,json.dumps({'url':link,'last_date':last_date}) if link and not past_end else None
    raise SourceIssue('additional_adapter_not_implemented')
