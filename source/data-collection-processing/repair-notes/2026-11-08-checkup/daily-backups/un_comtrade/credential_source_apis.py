"""Credential-backed official APIs; bounded requests and explicit coverage scopes."""
import json
from datetime import date,timedelta
from additional_source_apis import get_json,row,unique
from regulatory_collection import require
from research_contract import digest

_CONTROL=None
def reserve_comtrade():
    """Conservative shared allowance across historical and daily requests."""
    global _CONTROL
    if _CONTROL is None:
        from constellation.control import Control
        _CONTROL=Control()
    from datetime import datetime,timezone
    day=datetime.now(timezone.utc).date()
    with _CONTROL.db() as q:
        q.execute('INSERT INTO backfill_quotas(source_key,quota_day) VALUES(%s,%s) ON DUPLICATE KEY UPDATE source_key=VALUES(source_key)',('comtrade_keyed',day))
        q.execute('SELECT used_requests FROM backfill_quotas WHERE source_key=%s AND quota_day=%s FOR UPDATE',('comtrade_keyed',day));require(q.fetchone()['used_requests']<400,'comtrade_daily_request_budget')
        q.execute('UPDATE backfill_quotas SET used_requests=used_requests+1 WHERE source_key=%s AND quota_day=%s',('comtrade_keyed',day))

def fetch(client,job,cursor,item):
    kind=job['adapter'].removeprefix('additional_');p=job['parameters'];state=json.loads(cursor) if cursor else {}
    start=p.get('data_start',job['start']);end=p.get('data_end',job['end']);last=(date.fromisoformat(end)-timedelta(days=1)).isoformat();url=p['url'];rows=[]
    if kind=='copernicus':
        from copernicus_capture import fetch as capture
        return capture(client,job,cursor,item)
    if kind=='ember':
        d,_=get_json(client,url,{'start_date':start[:7],'end_date':last[:7]},'Ember');records=d.get('data');total=d.get('stats',{}).get('number_of_records')
        require(isinstance(records,list) and len(records)==total,'ember_count_mismatch')
        for r in records:
            require(start[:7]<=r['date'][:7]<=last[:7],'ember_date_outside_scope')
            identity=digest({'dataset':p['dataset'],**{k:r.get(k) for k in ('entity','entity_code','date','series','is_aggregate_entity','is_aggregate_series')}})
            rows.append(row(item,identity,{**r,'dataset':p['dataset'],'attribution':'Ember, CC-BY-4.0'},url,r['date'][:7],'month'))
        client.expected_records=total
    elif kind=='wto_timeseries':
        offset=state.get('offset',0);query={'i':p['indicator'],'r':'all','p':'default','ps':'default' if p.get('no_time_dimension') else str(p['year']),'pc':'default','fmt':'json','mode':'codes','max':500,'off':offset,'head':'M','lang':1,'meta':'true'}
        d,_=get_json(client,url,query,'WTO-primary',key_header='Ocp-Apim-Subscription-Key',allow_empty=True)
        if d is None:
            require(not state and offset == 0, 'wto_empty_during_pagination')
            client.expected_records = 0
            return [], None
        records=d.get('Dataset');require(isinstance(records,list),'wto_timeseries_shape')
        summaries=d.get('Summary',[]);counts=summaries[0].get('DataSet',[]) if summaries else []
        total=next((r.get('TotalCount') for r in counts if r.get('Name')=='Data'),None)
        require(isinstance(total,int),'wto_total_missing')
        if state:require(state['total']==total,'source_changed_refresh_required')
        if state:require(state.get('page_hash')!=digest(records) or not records,'wto_repeated_page')
        for r in records:
            lowered={k.lower():v for k,v in r.items()};year=None if p.get('no_time_dimension') else int(lowered['year'])
            if year is not None:require(year==p['year'],'wto_year_outside_scope')
            identity=digest({k:v for k,v in lowered.items() if k.endswith('code') or k in ('year','period')})
            rows.append(row(item,identity,r,url,str(year) if year is not None else None,'year' if year is not None else 'day'))
        unique(rows)
        following=offset+len(records);require(following<=total and (rows or following==total),'wto_truncated_page');client.expected_records=total
        if following<total:return rows,json.dumps({'offset':following,'total':total,'page_hash':digest(records)})
    elif kind=='wto_qr':
        page=state.get('page',1);query={'page':page,p['year_parameter']:p['year']}
        d,_=get_json(client,url,query,'WTO-primary',key_header='Ocp-Apim-Subscription-Key');records=d.get('data');meta=d.get('meta',{});require(isinstance(records,list) and isinstance(meta.get('total'),int),'wto_qr_shape');total=meta['total']
        if state:require(state['total']==total,'source_changed_refresh_required')
        require(meta.get('current_page')==page,'wto_qr_wrong_page')
        for r in records:
            stamp=r.get('notification_dt') if p['resource']=='notifications' else r.get('in_force_from')
            require(stamp and int(stamp[:4])==p['year'],'wto_qr_year_outside_scope')
            identity=str(r.get('id') or r.get('document_symbol') or '')
            require(bool(identity),'wto_qr_identity_missing')
            rows.append(row(item,p['resource']+':'+identity,r,r.get('document_url') or url,stamp[:10]))
        seen=state.get('seen',0)+len(rows);require(seen<=total and (rows or seen==total),'wto_qr_truncated_page');unique(rows);client.expected_records=total
        if seen<total:
            require(page<meta['last_page'],'wto_qr_missing_page');return rows,json.dumps({'page':page+1,'seen':seen,'total':total})
    elif kind=='wto_eping':
        page=state.get('page',1)
        d,_=get_json(client,url,{'language':1,'distributionDateFrom':start,'distributionDateTo':last,'page':page,'pageSize':100},'WTO-primary',key_header='Ocp-Apim-Subscription-Key');records=d.get('items');total=d.get('totalCount');require(isinstance(records,list) and isinstance(total,int),'wto_eping_shape')
        if state:require(state['total']==total,'source_changed_refresh_required')
        require(d.get('currentPage')==page,'wto_eping_wrong_page')
        for r in records:
            stamp=r['distributionDate'][:10];require(start<=stamp<end,'wto_eping_date_outside_scope');rows.append(row(item,str(r['id']),r,url,stamp))
        seen=state.get('seen',0)+len(rows);require(seen<=total and (rows or seen==total),'wto_eping_truncated_page');unique(rows);client.expected_records=total
        if seen<total:return rows,json.dumps({'page':page+1,'seen':seen,'total':total})
    elif kind=='census':
        direction=p['direction'];commodity='I_COMMODITY' if direction=='imports' else 'E_COMMODITY';value='GEN_VAL_MO' if direction=='imports' else 'ALL_VAL_MO'
        d,_=get_json(client,url,{'get':f'CTY_CODE,CTY_NAME,{commodity},{value}',commodity:p['commodity'],'CTY_CODE':'*','YEAR':start[:4],'MONTH':start[5:7]},'US-census','key')
        require(isinstance(d,list) and d and isinstance(d[0],list),'census_response_shape');require(len(d)<50000,'census_row_cap_split_required')
        for values in d[1:]:
            require(len(values)==len(d[0]),'census_row_length');r=dict(zip(d[0],values));require(r.get('YEAR',start[:4])==start[:4] and r.get('MONTH',start[5:7])==start[5:7],'census_date_outside_scope')
            identity=':'.join((direction,start[:7],r['CTY_CODE'],r[commodity]));rows.append(row(item,identity,r,url,start[:7],'month'))
        unique(rows)
    elif kind=='usda':
        url=url.format(commodity=p['commodity'],year=p['year'])
        # Preserve saved scopes while routing legacy requests to the official gateway.
        legacy='https://apps.fas.usda.gov/OpenData/api/psd/'
        if url.startswith(legacy):url='https://api.fas.usda.gov/api/psd/'+url[len(legacy):]
        records,_=get_json(client,url,None,'usda-fas',key_parameter='api_key');require(isinstance(records,list),'usda_response_shape')
        for r in records:
            require(int(r['marketYear'])==p['year'],'usda_year_outside_scope')
            identity=':'.join(str(r[k]) for k in ('commodityCode','countryCode','marketYear','attributeId'))
            rows.append(row(item,identity,{**r,'vintage_basis':'current PSD estimate retrieved now; market year is not release time'},url,str(p['year']),'year'))
        unique(rows)
    elif kind=='comtrade':
        reserve_comtrade()
        query={**p['query'],'period':str(p['year']),'maxRecords':500};d,_=get_json(client,url,query,'UN-primary',key_parameter='subscription-key');records=d.get('data');require(isinstance(records,list) and d.get('error') in (None,'',False),'comtrade_response_shape');require(len(records)<500,'comtrade_cap_split_scope_required')
        for r in records:
            identity=digest({k:r.get(k) for k in ('typeCode','freqCode','period','reporterCode','cmdCode','flowCode','partnerCode','partner2Code','customsCode','motCode','classificationCode')})
            require(int(r['period'])==p['year'],'comtrade_date_outside_scope');rows.append(row(item,identity,r,url,str(p['year']),'year'))
        unique(rows)
    else:raise ValueError('Unknown credential adapter')
    return rows,None
