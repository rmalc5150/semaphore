"""Resumable OpenDART index coverage, deliberately separate from original ZIP capture."""
import argparse
from datetime import date,datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import re
import time
from zoneinfo import ZoneInfo

import requests

SOURCE='south_korea_fss_opendart'
URL='https://opendart.fss.or.kr/api/list.json'
SEOUL=ZoneInfo('Asia/Seoul')
PAGE_SIZE=100
MAX_RESPONSE=1024**2


class StopCapture(RuntimeError):
    pass


def windows(start,through,today):
    end=through+timedelta(days=1)
    while start<end:
        new_month=date(start.year+(start.month==12),(start.month%12)+1,1)
        next_date=min(new_month,end,today if start<today else end)
        yield start,next_date
        start=next_date


def parse_page(body,page,start,end,expected=None):
    data=json.loads(body)
    code=data.get('status')
    if code=='013' and page==1 and expected is None:
        return 0,1,[]
    if code!='000':
        raise StopCapture('opendart_provider_'+(code if isinstance(code,str) and re.fullmatch(r'\d{3}',code) else 'invalid_status'))
    total,pages,which=(int(data[k]) for k in ('total_count','total_page','page_no'))
    if (total<=0 or total>400000 or pages!=(total+PAGE_SIZE-1)//PAGE_SIZE or not 1<=page<=pages
            or which!=page or expected is not None and expected!=total):
        raise StopCapture('opendart_pagination_totals_changed')
    rows=data.get('list')
    if not isinstance(rows,list) or len(rows)!=min(PAGE_SIZE,total-(page-1)*PAGE_SIZE):
        raise StopCapture('opendart_incomplete_index_page')
    lo,hi=start.strftime('%Y%m%d'),end.strftime('%Y%m%d')
    ids=[]
    for r in rows:
        rid,day=r.get('rcept_no',''),r.get('rcept_dt','')
        if not re.fullmatch(r'\d{14}',rid) or not re.fullmatch(r'\d{8}',day) or not lo<=day<hi:
            raise StopCapture('opendart_row_outside_requested_scope')
        ids.append(rid)
    if len(ids)!=len(set(ids)):raise StopCapture('opendart_duplicate_receipt')
    return total,pages,ids


def request(session,key,page,start,end):
    from constellation.shared_limits import admit
    params={'bgn_de':start.strftime('%Y%m%d'),'end_de':(end-timedelta(days=1)).strftime('%Y%m%d'),
            'sort':'date','sort_mth':'asc','last_reprt_at':'N','page_count':PAGE_SIZE,'page_no':page}
    admit(URL)
    try:
        with session.get(URL,params={**params,'crtfc_key':key},stream=True,allow_redirects=False,timeout=(8,20)) as res:
            if res.status_code!=200:raise StopCapture('opendart_http_'+str(res.status_code))
            body=bytearray()
            for chunk in res.iter_content(65536):
                body.extend(chunk)
                if len(body)>MAX_RESPONSE:raise StopCapture('opendart_index_body_limit')
    except requests.RequestException as exc:
        raise StopCapture('opendart_transport_'+type(exc).__name__) from None
    if key.encode() in body:raise StopCapture('opendart_secret_in_unexpected_response')
    return bytes(body),params


def collect(evidence,session,key,lo,hi,today,budget,enabled):
    from constellation.worker import put_verified
    today_snapshot=hi>today
    window=f'{lo}_{hi}'
    cp=f'opendart-index/v1/windows/{window}/checkpoint.json'
    state,etag=evidence.state(cp)
    if state and state.get('status') in ('complete','captured_so_far'):
        return state
    state=state or {'scope_start':str(lo),'scope_end_exclusive':str(hi),'pages':[],
                    'status':'partial','history_includes_corrections':True}
    seen=set()
    fields=('total_records','provider_pages')
    for i,saved in enumerate(state['pages'],1):
        with evidence.s3.get_object(Bucket=evidence.bucket,Key=saved['key'])['Body'] as stream:
            raw=stream.read(MAX_RESPONSE+1)
        if len(raw)!=saved['bytes'] or hashlib.sha256(raw).hexdigest()!=saved['sha256']:
            raise StopCapture('opendart_archived_page_checksum_mismatch')
        _,_,ids=parse_page(raw,i,lo,hi,state[fields[0]]) if state[fields[0]] else parse_page(raw,i,lo,hi)
        if seen.intersection(ids):raise StopCapture('opendart_duplicate_receipt_across_pages')
        seen.update(ids)
    while budget['requests'] and enabled() and len(state['pages'])<state.get(fields[1],1):
        page=len(state['pages'])+1;budget['requests']-=1
        body,params=request(session,key,page,lo,hi)
        total,pages,ids=parse_page(body,page,lo,hi,state.get(fields[0]))
        if seen.intersection(ids):raise StopCapture('opendart_duplicate_receipt_across_pages')
        sha=hashlib.sha256(body).hexdigest()
        path=f'research-data/source_documents/{SOURCE}/{sha}'
        archived=put_verified(evidence.control,path,body,'application/json')
        seen.update(ids)
        state[fields[0]]=total;state[fields[1]]=pages
        state['record_count']=len(seen)
        state['pages'].append({'page':page,'key':path,'sha256':sha,'bytes':archived['bytes'],
                               'request':params,'retrieved_at':datetime.now(timezone.utc).isoformat(),'records':len(ids)})
        etag=evidence.save(cp,state,etag)
        if page%25==0 or page==pages:
            print(json.dumps({'scope':window,'pages':page,'provider_pages':pages,'archived_records':len(seen)}),flush=True)
    if len(state['pages'])==state.get(fields[1],1):
        if len(seen)!=state[fields[0]]:raise StopCapture('opendart_index_count_does_not_reconcile')
        state.update(status='captured_so_far' if today_snapshot else 'complete',
                     complete_as_of=datetime.now(timezone.utc).isoformat(),
                     original_documents_verified=False,metadata_published=False)
        proof=f'opendart-index/v1/windows/{window}/receipts/{hashlib.sha256(json.dumps(state,sort_keys=True).encode()).hexdigest()}.json'
        evidence.immutable(proof,json.dumps(state,sort_keys=True).encode(),'application/json')
        state['receipt']=evidence.uri(proof)
        evidence.save(cp,state,etag)
    return state


def main():
    from additional_source_apis import credentials
    from constellation.control import Control
    from constellation.research_feeds import Evidence

    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--start',required=True,type=date.fromisoformat)
    p.add_argument('--through',required=True,type=date.fromisoformat)
    p.add_argument('--requests',type=int,default=300)
    a=p.parse_args();today=datetime.now(SEOUL).date()
    if not date(2016,1,1)<=a.start<=a.through<=today or not 1<=a.requests<=500:p.error('invalid capture window or budget')
    control=Control();e=Evidence(control); scopes=[]
    gate={'checked':0,'allowed':False}
    def enabled():
        if Path('/opt/constellation/batch-paused').exists():return False
        if time.monotonic()-gate['checked']>=10:
            gate.update(checked=time.monotonic(),allowed=control.allowed())
        return gate['allowed']
    key=credentials().get('dart','').strip()
    if not key:raise StopCapture('opendart_credential_missing')
    budget={'requests':a.requests}
    with control.db() as tx,requests.Session() as session:
        tx.execute("SELECT GET_LOCK('constellation:opendart:index-coverage',0) AS acquired")
        if tx.fetchone()['acquired']!=1:raise StopCapture('opendart_index_another_writer')
        try:
            for lo,hi in windows(a.start,a.through,today):
                def permit():
                    tx.execute("SELECT IS_USED_LOCK('constellation:opendart:index-coverage')=CONNECTION_ID() AS owned")
                    return tx.fetchone()['owned']==1 and enabled()
                if not permit():raise StopCapture('opendart_historical_window_inactive')
                receipt=collect(e,session,key,lo,hi,today,budget,permit)
                scopes.append({k:receipt.get(k) for k in ('scope_start','scope_end_exclusive','status','record_count','receipt')})
                if receipt['status']=='partial':break
        finally:tx.execute("SELECT RELEASE_LOCK('constellation:opendart:index-coverage')")
    print(json.dumps({'scope':'filing_index_only','requests_used':a.requests-budget['requests'],'windows':scopes}),flush=True)


if __name__=='__main__':
    try:main()
    except StopCapture as exc:
        print(json.dumps({'status':'stopped_safely','reason':str(exc)}),flush=True)
        raise SystemExit(2)
