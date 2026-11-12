"""S56 archive provenance and US/ALL retail context; battery capture is separate."""
import copy
import io
import json
import re
import zipfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit, unquote

import openpyxl
from collection_storage import now, write_json, Conflict
from research_contract import digest
from regulatory_collection import require, SourceIssue

VERSION='eia-index-retail-v1'
RETAIL_URL='https://api.eia.gov/v2/electricity/retail-sales/data/'
MONTHS={name.lower():i for i,name in enumerate(['January','February','March','April','May','June','July','August','September','October','November','December'],1)}


def month_shift(period,delta):
    require(re.fullmatch(r'\d{4}-\d{2}',period),'eia_invalid_period')
    year,month=map(int,period.split('-'));require(1<=month<=12,'eia_invalid_month')
    total=year*12+month-1+delta
    return f'{total//12:04d}-{total%12+1:02d}'


def archive_period(url):
    parts=urlsplit(url)
    require(parts.scheme=='https' and parts.hostname in {'www.eia.gov','eia.gov'} and not parts.username
            and not parts.password and parts.port in {None,443} and not parts.query and not parts.fragment
            and parts.path.startswith('/electricity/data/eia860m/') and parts.path.lower().endswith('.xlsx'), 'eia_untrusted_archive_url')
    name=unquote(parts.path.rsplit('/',1)[-1]).lower()
    match=re.fullmatch(r'([a-z]+)_generator(\d{4})\.xlsx',name)
    if match:
        require(match[1] in MONTHS,'eia_unknown_archive_month')
        return f'{match[2]}-{MONTHS[match[1]]:02d}'
    require('code' in name,'eia_unrecognized_archive_name')
    return None


def number(value):
    if value is None or str(value).strip() in {'','--','—','NA','N/A','NM','(s)','W'}:return None
    try:
        result=Decimal(str(value).replace(',',''))
        return result if result.is_finite() else None
    except InvalidOperation:return None


def workbook_summary(raw,url):
    period=archive_period(url)
    require(raw.startswith(b'PK') and len(raw)<=32*1024**2,'eia_invalid_or_oversize_workbook')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        require(sum(i.file_size for i in z.infolist())<=256*1024**2 and len(z.infolist())<20000,'eia_workbook_expansion_limit')
    sheets=[];gaps=[];all_ids=set();code_rows=[]
    book=openpyxl.load_workbook(io.BytesIO(raw),read_only=True,data_only=True)
    try:
        for sheet in book:
            headers=None;header_row=None;rows=0;ids=set();states=Counter();status=Counter();movers=Counter();totals={};bad=0;duplicates=0;intro=[]
            for index,values in enumerate(sheet.iter_rows(values_only=True),1):
                cells=[str(v).strip() if v is not None else '' for v in values]
                normal=[re.sub(r'\s+',' ',v).strip().lower() for v in cells]
                if index<=8:intro.append({'row':index,'cells':cells})
                if 'plant id' in normal and 'generator id' in normal:
                    headers=cells;normal_headers=normal;header_row=index;continue
                if headers is None:
                    if period is None and any(cells):code_rows.append({'sheet':sheet.title,'row':index,'cells':cells})
                    continue
                lookup={h:cells[i] if i<len(cells) else '' for i,h in enumerate(normal_headers) if h}
                plant,gen=lookup.get('plant id'),lookup.get('generator id')
                if not plant and not gen:continue
                if not plant or not gen:bad+=1;continue
                ident=(plant,gen);duplicates+=ident in ids;ids.add(ident);all_ids.add(ident);rows+=1
                for header in ['plant state','state']:
                    if lookup.get(header):states[lookup[header]]+=1;break
                status[lookup.get('status') or lookup.get('status code') or 'not_supplied_in_row']+=1
                movers[lookup.get('prime mover code') or lookup.get('prime mover') or 'not_supplied_in_row']+=1
                for key,val in lookup.items():
                    if 'capacity' in key and re.search(r'\bmw\b',key) and 'mwh' not in key:
                        parsed=number(val)
                        if parsed is not None:totals[key]=totals.get(key,Decimal(0))+parsed
            if duplicates:gaps.append({'sheet':sheet.title,'reason':'duplicate_plant_generator_within_sheet','count':duplicates})
            if bad:gaps.append({'sheet':sheet.title,'reason':'missing_generator_identity','count':bad})
            sheets.append({'name':sheet.title,'header_row':header_row,'headers':headers,'intro_rows':intro,
                'generator_rows':rows,'distinct_generators':len(ids),'state_counts':dict(states),
                'reported_status_code_counts':dict(status),'prime_mover_code_counts':dict(movers),
                'reported_capacity_sums_mw':{k:str(v) for k,v in totals.items()},
                'capacity_note':'Sums of reported nonmissing cells only; sheet statuses remain separate; not firm capacity or commitments.'})
    finally:
        book.close()
    if period and not all_ids:gaps.append({'reason':'no_generator_headers_or_rows'})
    if not period and not code_rows:gaps.append({'reason':'empty_code_reference'})
    import hashlib
    sha=hashlib.sha256(raw).hexdigest()
    return {'version':VERSION,'archive_kind':'monthly_generator_workbook' if period else 'code_reference',
        'report_period':period,'period_basis':'official_archive_filename; not publication_date',
        'workbook_validated':True,'workbook_sha256':sha,'archive_bytes':len(raw),'sheets':sheets,'code_reference_rows':code_rows,
        'distinct_generators_across_sheets':len(all_ids),'gaps':gaps,'status':'review_required' if gaps else 'enriched',
        'battery_dataset_link':{'source':'eia_battery_generators','dataset':'specialist_inputs','archive_url':url,
            'report_period':period,'join_basis':'original workbook URL/report period, then Plant ID + Generator ID',
            'coverage':'existing battery rows remain authoritative; this index does not duplicate or certify that table'},
        'event_candidate':{'type':'macro.statistics_release' if period else None,'key':digest([url,period]),
            'content_version':sha,'review_status':'pending; workbook is provenance, not a separate generator milestone'},
        'limitations':['Preliminary inventory; changes may be corrections, not physical developments.',
            'Workbook month is not publication or commissioning date.', 'No equipment supplier, owner or product relationships inferred.']}


def enrich_archive(url,client,refresh=False):
    period=archive_period(url)
    if period and period>now()[:7]:
        return {'version':VERSION,'status':'not_applicable_future_period','report_period':period,
            'archive_kind':'future_index_link','workbook_validated':False,'event_candidate':None,
            'note':'Index HTML contains future-month template links. No workbook or release inferred; reconsider when the period is reached.'}
    key=historical_metadata_key('operations/eia-enrichment/archive-heads/'+digest(url)+'.json')
    obj=client.store.get(key);saved=json.loads(obj.body) if obj else None
    cutoff=24 if period and period>=month_shift(now()[:7],-4) else 24*30
    if saved and not refresh and datetime.now(timezone.utc)-datetime.fromisoformat(saved['checked_at'].replace('Z','+00:00'))<timedelta(hours=cutoff):
        client.evidence.extend(e for e in saved['evidence'] if e not in client.evidence)
        return copy.deepcopy(saved['summary'])
    start=len(client.evidence);raw=client.get(url)
    require(bool(raw),'eia_empty_workbook_response')
    result=workbook_summary(raw,url)
    previous=saved['summary'] if saved else None
    result['same_period_comparison']={'status':'baseline'} if previous is None else {
        'status':'unchanged' if previous['workbook_sha256']==result['workbook_sha256'] else 'changed_workbook',
        'previous_workbook_sha256':previous['workbook_sha256'],'interpretation':'source revision candidate; inspect data before treating as physical change'}
    saved_value={'checked_at':now(),'summary':result,'evidence':client.evidence[start:]}
    write_json(client.store,historical_metadata_key('operations/eia-enrichment/archive-versions/'+digest(saved_value)+'.json'),saved_value)
    try:write_json(client.store,key,saved_value,obj.token if obj else None)
    except Conflict:pass
    return result


def published_links(raw,url):
    from html.parser import HTMLParser
    from urllib.parse import urljoin
    class Anchors(HTMLParser):
        def __init__(self):super().__init__();self.links=[]
        def handle_starttag(self,tag,attrs):
            if tag.lower()!='a':return
            href=dict(attrs).get('href','')
            if href.lower().endswith('.xlsx'):self.links.append(urljoin(url,href))
    parser=Anchors();parser.feed(raw.decode('utf-8'))
    return sorted(set(parser.links),key=lambda u:(archive_period(u) or '',u),reverse=True)


def historical_metadata_key(key):
    import os
    if os.environ.get('CONSTELLATION_SPECIALIST_SCHEDULER_PREFIX'):
        return 'constellation-backfill/source-metadata/'+key
    return key


def refresh_generator_archives(plan, store):
    """Refresh published links once daily; HTML comments are not releases."""
    from regulatory_collection import EvidenceClient
    sources=[s for s in plan['sources'] if s.get('enabled') and s.get('adapter')=='eia_xlsx']
    if not sources:return None
    url=sources[0]['api']; key=historical_metadata_key('operations/eia/published-generator-archives/'+now()[:10]+'.json')
    saved=store.get(key)
    if saved:
        snapshot=json.loads(saved.body)
    else:
        client=EvidenceClient(store,'eia_generator_index')
        links=published_links(client.get(url),url)
        archives=[{'period':archive_period(link),'url':link} for link in links if archive_period(link)]
        require(bool(archives),'eia_missing_archive_links')
        snapshot={'checked_at':now(),'archives':archives,'source_evidence':client.evidence}
        write_json(store,key,snapshot)
    for source in sources:source['archives']=snapshot['archives']
    return {a['period'] for a in snapshot['archives']}


def index_page(client,job,cursor,item):
    from urllib.parse import urljoin
    p=job['parameters'];url=p['url']
    if cursor:
        state=json.loads(cursor)
        require(state['version']==VERSION,'eia_index_cursor_version')
        for e in state['index_evidence']:
            if e not in client.evidence:client.evidence.append(e)
    else:
        start=len(client.evidence);raw=client.get(url)
        links=published_links(raw,url)
        require(links,'eia_missing_archive_links')
        state={'version':VERSION,'offset':0,'links':links,'index_evidence':client.evidence[start:]}
    out=[]
    for link in state['links'][state['offset']:state['offset']+5]:
        try:
            summary=enrich_archive(link,client)
        except SourceIssue as exc:
            summary={'version':VERSION,'status':'retrieval_gap','error':exc.code,
                'report_period':archive_period(link),'specialist_ready':False,'note':'Discovered link retained; workbook enrichment must be retried.'}
        out.append(item(digest(link),{'archive_url':link,'enrichment':summary},link,basis='derived'))
    end=state['offset']+len(out)
    return out,json.dumps({**state,'offset':end}) if end<len(state['links']) else None


def retail_metadata(client):
    if hasattr(client,'_eia_retail_metadata'):return client._eia_retail_metadata
    from specialist_authenticated import request
    response=request(client,'eia',RETAIL_URL.replace('/data/','/')).get('response',{})
    require(response.get('id')=='retail-sales' and isinstance(response.get('data'),dict),'eia_metadata_shape')
    client._eia_retail_metadata=response
    return response


def retail_history(client,start,end):
    from specialist_authenticated import request
    rows=[];offset=0;total=None
    while True:
        params={'frequency':'monthly','facets[stateid][]':'US','facets[sectorid][]':'ALL','start':start,'end':end,
            'sort[0][column]':'period','sort[0][direction]':'asc','length':100,'offset':offset,
            **{'data['+str(i)+']':k for i,k in enumerate(['price','sales','revenue','customers'])}}
        data=request(client,'eia',RETAIL_URL,params)
        require(not data.get('error'),'eia_api_error');response=data.get('response',{});page=response.get('data');count=int(response.get('total',-1))
        require(isinstance(page,list) and count>=0 and offset+len(page)<=count,'eia_history_count')
        require(total is None or count==total,'eia_history_total_changed');total=count
        require(bool(page) or offset==count,'eia_history_missing_page')
        require(all(r.get('stateid')=='US' and r.get('sectorid')=='ALL' and start<=r.get('period','')<=end for r in page),'eia_history_scope')
        rows+=page;offset+=len(page)
        if offset==total:break
        require(len(page)==100,'eia_history_short_page')
    require(len({r['period'] for r in rows})==len(rows),'eia_history_duplicate_period')
    return rows


def retail_row(row,history,metadata):
    period=row['period'];require(re.fullmatch(r'\d{4}-\d{2}',period),'eia_invalid_period')
    result=copy.deepcopy(row);fields={};gaps=[]
    for key in ['price','sales','revenue','customers']:
        val=number(row.get(key));units=row.get(key+'-units') or metadata.get('data',{}).get(key,{}).get('units')
        fields[key]={'raw':row.get(key),'value':str(val) if val is not None else None,'units':units,
            'status':'reported_numeric' if val is not None else 'missing_or_non_numeric'}
        if val is None or units is None:gaps.append({'field':key,'reason':'missing_value_or_units'})
    typed_price=fields['price'];conversion=None
    if typed_price['units']=='cents per kilowatt-hour' and typed_price['value'] is not None:
        conversion={'value':str(Decimal(typed_price['value'])/100),'unit':'USD/kWh','formula':'reported cents/kWh divided by 100'}
    comparisons=[]
    for label,delta in [('month_over_month',-1),('year_over_year',-12)]:
        baseline=next((r for r in history if r['period']==month_shift(period,delta)),None)
        for metric in ['price','sales','revenue','customers']:
            current=fields[metric];prior=number(baseline.get(metric)) if baseline else None
            base_units=baseline.get(metric+'-units') or metadata.get('data',{}).get(metric,{}).get('units') if baseline else None
            if prior is None or current['value'] is None or base_units!=current['units']:
                comparisons.append({'comparison':label,'metric':metric,'status':'baseline_missing_or_units_differ','baseline_period':month_shift(period,delta)});continue
            value=Decimal(current['value']);change=value-prior
            comparisons.append({'comparison':label,'metric':metric,'status':'computed','baseline_period':baseline['period'],
                'baseline_value':str(prior),'current_value':str(value),'absolute_change':str(change),'units':current['units'],
                'relative_change_percent':str((change/prior*100).quantize(Decimal('.01'))) if prior else None,
                'interpretation':'not seasonally adjusted; current-retrieved series, not historical release surprise'})
    if any(c['status']!='computed' for c in comparisons):gaps.append({'reason':'one_or_more_comparison_baselines_unavailable'})
    reconciliation={'status':'units_or_values_unavailable'}
    if fields['revenue']['units']=='million dollars' and fields['sales']['units']=='million kilowatt hours' and number(fields['sales']['value']) not in {None,Decimal(0)} and number(fields['revenue']['value']) is not None and typed_price['value'] is not None and typed_price['units']=='cents per kilowatt-hour':
        implied=Decimal(fields['revenue']['value'])/Decimal(fields['sales']['value'])*100
        reconciliation={'status':'computed','implied_price_cents_per_kwh':str(implied.quantize(Decimal('.0001'))),
            'reported_price_cents_per_kwh':typed_price['value'],'absolute_difference_cents_per_kwh':str(abs(implied-Decimal(typed_price['value'])).quantize(Decimal('.0001'))),
            'formula':'100 * revenue_million_USD / sales_million_kWh','note':'Rounding and provider methodology require review; this is not an independently measured tariff.'}
    result['enrichment']={'price_revenue_sales_reconciliation':reconciliation,'version':VERSION,'series_key':'US:ALL:monthly','reference_period':period,
        'geography':{'code':'US','name':row.get('stateDescription')},'customer_sector':{'code':'ALL','name':row.get('sectorName')},
        'fields':fields,'price_usd_per_kwh':conversion,'comparisons':comparisons,'metadata':metadata,
        'gaps':gaps,'status':'review_required' if gaps else 'enriched',
        'source_revision_status':'current_retrieval; original publication vintage not established',
        'event_candidate':{'type':'macro.statistics_release','key':'eia_retail_sales:US:ALL:'+period,
            'content_version':digest(row),'review_status':'pending; routine prices are model features, not company events'},
        'limitations':['US all-sector average retail price, not a state/customer tariff or wholesale dispatch price.',
            'Sales, revenue and customer counts share this scope; changes do not establish storage arbitrage or company profitability.',
            'Reference month is not release date; current retrieval cannot be backdated.']}
    return result


def retail_revision(row,client):
    period=row['period'];key=historical_metadata_key('operations/eia-enrichment/retail-heads/'+period+'.json')
    current=client.store.get(key);prior=json.loads(current.body) if current else None
    changed=[]
    if prior:
        for metric in ['price','sales','revenue','customers']:
            old=prior['row'].get(metric);new=row.get(metric)
            a,b=number(old),number(new)
            if (a!=b if a is not None and b is not None else old!=new) or prior['row'].get(metric+'-units')!=row.get(metric+'-units'):
                changed.append({'metric':metric,'previous_value':old,'current_value':new,
                    'previous_units':prior['row'].get(metric+'-units'),'current_units':row.get(metric+'-units')})
    result={'status':'baseline' if prior is None else 'observed_revision' if changed else 'unchanged',
        'changed_fields':changed,'previous_observed_at':prior['observed_at'] if prior else None,
        'interpretation':'Observed series change, not proof of official release timing or a company event.'}
    value={'row':row,'observed_at':now(),'source_evidence':copy.deepcopy(client.evidence)}
    write_json(client.store,historical_metadata_key('operations/eia-enrichment/retail-versions/'+digest(value)+'.json'),value)
    try:write_json(client.store,key,value,current.token if current else None)
    except Conflict:result['head_update']='concurrent_update; retry_on_next_capture'
    return result


def retail_page(client,job,cursor,item):
    require(cursor is None,'eia_retail_unexpected_cursor')
    p=job['parameters'];start=p['start'][:7];end=(datetime.fromisoformat(p['end'])-timedelta(days=1)).strftime('%Y-%m')
    metadata=retail_metadata(client);history=retail_history(client,month_shift(start,-12),end)
    selected=[r for r in history if start<=r['period']<=end]
    out=[]
    for row in selected:
        enriched=retail_row(row,history,metadata)
        enriched['enrichment']['observed_revision']=retail_revision(row,client)
        out.append(item('US:ALL:'+row['period'],enriched,p['url']))
    return out,None
