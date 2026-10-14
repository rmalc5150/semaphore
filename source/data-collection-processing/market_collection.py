#!/usr/bin/env python3
"""Shared HKEX prices and EODHD prices/splits/dividends with explicit coverage."""
import argparse
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import fcntl
import json
from pathlib import Path
from urllib.parse import quote

from collection_operations import load_stored
from collection_storage import AlreadyComplete, CollectionRun, StorageSettings, now, task_spec, write_json
from disclosure_collection import finish_error
from eodhd_universe import EODHDClient
from historical_policy import historical_start
from regulatory_collection import EvidenceClient, SourceIssue, instant, require
from research_contract import ROOT, digest, load_json, seal_record
import hkex_historical_prices as hkex

VERSION='market-collection-1.0'


def number(value, positive=False):
    if value is None or value=='': return None
    try: n=Decimal(str(value))
    except InvalidOperation: raise SourceIssue('market_invalid_numeric') from None
    require(n.is_finite() and n>=0 and (not positive or n>0),'market_invalid_numeric')
    return str(n)


def normalize(row,kind,start,end):
    require(isinstance(row,dict),'market_invalid_row')
    day=date.fromisoformat(row['date']); require(start<=day<end,'market_date_outside_window')
    data=dict(row)
    if kind=='prices':
        for field in ('open','high','low','close','adjusted_close','volume'):
            require(field in row,'market_price_field_missing')
            data[field]=number(row[field])
        require(all(data[k] is not None for k in ('open','high','low','close','volume')),'market_missing_ohlcv')
        require(Decimal(data['low'])<=min(Decimal(data['open']),Decimal(data['close']))<=
                max(Decimal(data['open']),Decimal(data['close']))<=Decimal(data['high']),'market_ohlc_inconsistent')
    elif kind=='dividends':
        data['value']=number(row.get('value'));require(data['value'] is not None,'market_dividend_value_missing')
        for field in ('declarationDate','recordDate','paymentDate'):
            if row.get(field): date.fromisoformat(row[field])
    elif kind=='splits':
        pieces=str(row.get('split','')).split('/')
        require(len(pieces)==2,'market_split_ratio_invalid')
        data['numerator']=number(pieces[0],True); data['denominator']=number(pieces[1],True)
        require(data['numerator'] is not None and data['denominator'] is not None,'market_split_ratio_invalid')
        data['share_multiplier']=str(Decimal(data['numerator'])/Decimal(data['denominator']))
    else: raise ValueError('unknown market kind')
    return data


def record(run,symbol,kind,data,url,evidence,candidates=()):
    day=data['date']; provider_id=symbol+':'+kind+':'+day
    return seal_record({'document_type':'collected_record','schema_version':'1.0',
        'source':run.spec['source'],'dataset':'market_records','source_record_id':provider_id,
        'source_record_id_basis':'documented_composite','source_url':url,
        'universe_version':run.universe['universe_version'],'company_ids':[],'listing_ids':[],
        'product_ids':[],'person_ids':[],'entity_match_status':'unresolved',
        'event_at':{'value':day,'precision':'day','source_timezone':None},'available_at':None,
        'source_updated_at':None,'ingested_at':now(),'availability_basis':'unknown','availability_evidence':[],
        'run_id':run.run_id,'payload':{'symbol':symbol,'kind':kind,'data':data,
            'candidate_listing_ids':list(candidates),'source_evidence':list(evidence),
            'coverage_note':'Current provider observation. Listing links are candidates. Adjusted prices can incorporate later actions; historical feature availability is not established.'}})


def spec(universe,taxonomy,source,start,end,mode,scope):
    return task_spec(source,'market_records',mode,instant(start),instant(end),scope,VERSION,universe,taxonomy)


def collect_eodhd(store,settings,universe,taxonomy,symbol,start,end,mode,client,candidates=(),refresh=False):
    require(start<end and (end-start).days<=366,'market_window_must_be_bounded_to_one_year')
    scope={'symbol':symbol,'kinds':['prices','dividends','splits'],'candidate_listing_ids':sorted(candidates),'end_policy':'exclusive'}
    try: run=CollectionRun.start(store,spec(universe,taxonomy,'eodhd_market',start,end,mode,scope),universe,taxonomy,settings,resume=not refresh,refresh=refresh)
    except AlreadyComplete as exc: return {'status':'complete','manifest':str(exc),'already_complete':True}
    evidence=EvidenceClient(store,'eodhd_market')
    try:
        jobs=[('prices','eod'),('dividends','div'),('splits','splits')]
        offset=int(run.cursor or 0)
        while not run.exhausted and offset<len(jobs):
            kind,path=jobs[offset]; evidence.evidence=[]
            data,raw,url=client.get(path+'/'+quote(symbol,safe=''),{'from':str(start),'to':str(end-timedelta(days=1)),'order':'a'})
            require(isinstance(data,list),'market_response_not_list'); evidence.save(raw,url)
            rows=[normalize(r,kind,start,end) for r in data]
            dates=[r['date'] for r in rows];require(len(dates)==len(set(dates)),'market_duplicate_date_requires_review')
            # An empty price history is not evidence that a listing had no sessions.
            if kind == 'prices' and not rows:
                # Empty windows may precede listing or follow the last available
                # quote. Preserve a bounded source-history probe for diagnosis,
                # while keeping this window incomplete rather than inventing prices.
                probe_end = datetime.now(timezone.utc).date()
                history, raw_history, history_url = client.get(path+'/'+quote(symbol,safe=''),
                    {'from': str(historical_start()), 'to': str(probe_end-timedelta(days=1)), 'order': 'a'})
                require(isinstance(history, list), 'market_response_not_list')
                evidence.save(raw_history, history_url)
                dates = sorted(date.fromisoformat(r['date']).isoformat() for r in history)
                diagnostics = {'symbol': symbol, 'window_start': str(start), 'window_end_exclusive': str(end),
                    'provider_first_price': dates[0] if dates else None,
                    'provider_last_price': dates[-1] if dates else None,
                    'observed_price_rows': len(dates), 'evidence': evidence.evidence,
                    'coverage': 'Provider availability only; does not prove listing dates or absence of trading.'}
                write_json(store, run.state['manifest_prefix']+'/price-availability.json', diagnostics)
                raise SourceIssue('market_empty_price_window_unverified', True, diagnostics)
            records=[record(run,symbol,kind,r,url,evidence.evidence,candidates) for r in rows]
            offset+=1;run.commit_page(records,next_cursor=str(offset) if offset<len(jobs) else None,exhausted=offset==len(jobs))
        return {'status':'complete','records':run.state['record_count'],'manifest':run.finish('complete',expected_records=run.state['record_count'])}
    except (Exception,KeyboardInterrupt) as exc: return finish_error(run,exc,evidence.evidence)


def collect_hkex(store,settings,universe,taxonomy,day,mode,loader=None,max_boards=2):
    end=day+timedelta(days=1)
    try: run=CollectionRun.start(store,spec(universe,taxonomy,'hkex_prices',day,end,mode,{'boards':['Main Board','GEM'],'selection':'all_quoted_instruments'}),universe,taxonomy,settings,resume=True)
    except AlreadyComplete as exc: return {'status':'complete','manifest':str(exc),'already_complete':True}
    evidence=EvidenceClient(store,'hkex_prices'); loader=loader or hkex.get_sheet
    try:
        offset=int(run.cursor or 0);processed=0
        while not run.exhausted and offset<2:
            if processed>=max_boards: raise SourceIssue('board_limit',True)
            board=('Main Board','GEM')[offset];evidence.evidence=[]
            try: document,url=loader(day,board)
            except FileNotFoundError: raise SourceIssue('hkex_sheet_unavailable_not_verified_holiday',True) from None
            # The sheet must identify the requested date, not just parse as a table.
            import re
            visible=__import__('html').unescape(re.sub('<[^>]+>',' ',document))
            date_tokens=(day.strftime('%d/%m/%Y'),day.strftime('%d/%m/%y'),day.strftime('%d %b %Y').upper(),day.strftime('%d %B %Y').upper(),day.strftime('%Y-%m-%d'))
            require(any(t in visible.upper() for t in date_tokens),'hkex_sheet_date_unverified')
            evidence.save(document.encode(),url)
            quotes=hkex.parse_sheet(document,day,board);require(quotes,'hkex_empty_sheet')
            seen=set();records=[]
            for q in quotes:
                require(q.code not in seen,'hkex_duplicate_code');seen.add(q.code)
                data=asdict(q); data.update(date=str(day),close=number(q.closing_price),high=number(q.high),low=number(q.low),volume=number(q.shares_traded),adjusted_close=None,open=None)
                candidates=[l['listing_id'] for l in universe['listings'] if l['exchange_mic']=='XHKG' and l['ticker'].zfill(5)==q.code.zfill(5) and l['review_status']!='rejected']
                records.append(record(run,q.code.zfill(5)+'.HK','prices',data,url,evidence.evidence,candidates))
            offset+=1;processed+=1
            run.commit_page(records,next_cursor=str(offset) if offset<2 else None,exhausted=offset==2)
        return {'status':'complete','records':run.state['record_count'],'manifest':run.finish('complete',expected_records=run.state['record_count'])}
    except (Exception,KeyboardInterrupt) as exc:return finish_error(run,exc,evidence.evidence)


def enqueue(store,result,source,start,end,mode,scope):
    if result['status']!='complete':return
    wid=digest({'source':source,'start':str(start),'end':str(end),'mode':mode,'scope':scope})
    key='operations/market/publication-queue/'+wid+'.json';old,token=load_stored(store,key)
    item={'window_id':wid,'manifests':[result['manifest']],'start':str(start),'end_exclusive':str(end),'source':source,'queued_at':now()}
    if not old or old['manifests']!=item['manifests']:write_json(store,key,item,token)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',choices=['hkex','eodhd']);p.add_argument('mode',choices=['daily','historical'])
    p.add_argument('--start',type=date.fromisoformat);p.add_argument('--end',type=date.fromisoformat);p.add_argument('--symbol')
    p.add_argument('--dry-run',action='store_true');p.add_argument('--output',type=Path)
    a=p.parse_args(); today=datetime.now(timezone.utc).date()
    start=a.start or (historical_start() if a.mode=='historical' else today-timedelta(days=1));end=a.end or (today if a.mode=='daily' else None)
    if end is None or not start<end<=today:p.error('require completed-day start < exclusive end <= today')
    if a.source=='hkex' and end!=start+timedelta(days=1):p.error('HKEX bounded invocation requires one day; use the runner for ranges')
    if a.source=='eodhd' and not a.symbol:p.error('--symbol required')
    if a.dry_run:print(json.dumps({'source':a.source,'start':str(start),'end_exclusive':str(end)}));return 0
    settings=StorageSettings.load(ROOT/'config/collection-storage.s3.json');store=settings.store()
    u=load_json(ROOT/'config/company-universe.v0.3.json');t=load_json(ROOT/'config/sectors.v1.json')
    with (ROOT/'.market-collection.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if a.source=='hkex':result=collect_hkex(store,settings,u,t,start,a.mode)
        else:
            candidates=[i['entity_id'] for i in u['external_identifiers'] if i['system']=='eodhd_symbol' and i['value']==a.symbol and i['review_status']!='rejected']
            result=collect_eodhd(store,settings,u,t,a.symbol,start,end,a.mode,EODHDClient.configured(load_json(ROOT/'config/eodhd-universe.json')),candidates)
        enqueue(store,result,'eodhd_market' if a.source=='eodhd' else 'hkex_prices',start,end,a.mode,{'symbol':a.symbol,'universe':digest(u)})
        if a.output:a.output.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result));return 0 if result['status']=='complete' else 2 if result['status']=='partial' else 1

if __name__=='__main__':raise SystemExit(main())
