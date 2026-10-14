#!/usr/bin/env python3
"""Quota-bounded EODHD history and daily refresh across the pinned listing universe."""
import argparse
from datetime import date,datetime,timedelta,timezone
import fcntl
import json
from pathlib import Path

from collection_operations import load_stored
from collection_storage import StorageSettings,now,write_json
from eodhd_universe import EODHDClient
from market_collection import collect_eodhd,enqueue
from market_coverage_exclusions import Exclusions, SUCCESS, excluded_window, reconcile_state, unresolved, report as coverage_report
from regulatory_collection import SourceIssue,require
from research_contract import ROOT,digest,load_json


def symbols(universe):
    listings={l['listing_id']:l for l in universe['listings'] if l['review_status']!='rejected'}
    result={}
    for item in universe['external_identifiers']:
        if item['system']=='eodhd_symbol' and item['entity_id'] in listings and item['review_status']!='rejected':
            result.setdefault(item['value'],[]).append(item['entity_id'])
    return {s:sorted(set(ids)) for s,ids in sorted(result.items())}


class Budget:
    def __init__(self,store,config,remaining,opener):
        self.store,self.config,self.remaining,self.opener=store,config,remaining,opener
    def __call__(self,*args,**kwargs):
        if self.remaining<=0:raise SourceIssue('market_run_request_budget_reached',True)
        key='operations/market/budgets/'+now()[:10]+'.json'
        state,token=load_stored(self.store,key);state=state or {'reserved':0}
        if state['reserved']>=self.config['max_requests_per_day']:raise SourceIssue('market_daily_request_budget_reached',True)
        state.update(reserved=state['reserved']+1,updated_at=now());write_json(self.store,key,state,token)
        self.remaining-=1
        return self.opener(*args,**kwargs)


def next_month(day):return date(day.year+(day.month==12),day.month%12+1,1)


class MarketOperations:
    def __init__(self,store,settings,config,universe,taxonomy):
        self.store,self.settings,self.config,self.universe,self.taxonomy=store,settings,config,universe,taxonomy
        self.symbols=symbols(universe)
        self.identity=digest({'version':'market-operations-1.0','config':config,'universe':digest(universe),'taxonomy':digest(taxonomy)})
        self.prefix='operations/market/automation/'+self.identity
    def reconcile_exclusions(self, registry=None, persist=True):
        registry = registry or Exclusions(self.store, self.prefix, self.symbols)
        states = {}
        for lane in ('daily', 'historical'):
            key = self.prefix + '/' + lane + '.json'
            state, token = load_stored(self.store, key)
            states[lane] = reconcile_state(state, lane, registry) if state else None
            if persist and state is not None and states[lane] != state:
                write_json(self.store, key, states[lane], token)
        return states
    def run(self,client,today=None):
        today=today or datetime.now(timezone.utc).date();outcomes=[]
        registry = Exclusions(self.store, self.prefix, self.symbols)
        self.reconcile_exclusions(registry)
        for lane in ('daily','historical'):
            if lane == 'historical':
                daily, _ = load_stored(self.store, self.prefix+'/daily.json')
                daily = (daily or {}).get('symbols', {})
                due = [s for s in self.symbols if daily.get(s, {}).get('retry_after', '') <= str(today)
                       and daily.get(s, {}).get('scan_next_date', daily.get(s, {}).get('next_date', self.config['daily_origin'])) < str(today)]
                if due:
                    continue  # Reserve capacity for current data before backfill.
            key=self.prefix+'/'+lane+'.json';state,token=load_stored(self.store,key);state=state or {'symbols':{}}
            ordered=sorted(self.symbols,key=lambda s:(state['symbols'].get(s,{}).get('last_attempt',''),s))
            attempted=0
            for symbol in ordered:
                item=state['symbols'].get(symbol,{})
                diagnosing_empty = item.get('last_result', {}).get('reason') == 'market_empty_price_window_unverified' and not item.get('empty_window_diagnosed')
                advancing_empty_month = (lane == 'daily' and not item.get('scan_next_date') and
                    item.get('last_result', {}).get('reason') == 'market_empty_price_window_unverified' and
                    item.get('window_end_exclusive', str(today)) <= str(today.replace(day=1)))
                if item.get('retry_after','')>str(today) and not (diagnosing_empty or advancing_empty_month):continue
                cursor=date.fromisoformat(item.get('scan_next_date', item.get('next_date', self.config['historical_start'])) if lane=='historical'
                    else item.get('scan_next_date', item.get('next_date',self.config['daily_origin'])))
                limit=today if lane=='daily' else date.fromisoformat(self.config['daily_origin'])
                retry_gap = None
                if cursor >= limit and item.get('gaps'):
                    retry_gap = min(item['gaps'], key=lambda value:
                        (item['gaps'][value].get('last_attempt', ''), value))
                    cursor = date.fromisoformat(retry_gap)
                if cursor>=limit:continue
                start=cursor.replace(day=1) if lane=='daily' else cursor
                end=min(next_month(start) if lane=='daily' else date(start.year+1,1,1),limit)
                if retry_gap:
                    end = min(date.fromisoformat(item['gaps'][retry_gap].get('end_exclusive', str(end))), limit)
                if attempted>=getattr(self,'window_limit',self.config['windows_per_lane']):break
                decision = registry.match(symbol, str(start), str(end))
                if decision:
                    result = excluded_window(registry, decision, str(start), str(end))
                    item.setdefault('excluded_windows', {})[str(start)] = result
                else:
                    result=collect_eodhd(self.store,self.settings,self.universe,self.taxonomy,symbol,start,end,
                        'daily' if lane=='daily' else 'historical',client,self.symbols[symbol])
                if retry_gap:
                    item['gaps'][retry_gap]['last_attempt'] = now()
                if result['status'] in SUCCESS:
                    # Daily month partitions are replaced as the month fills in;
                    # older observations remain immutable in raw evidence/releases.
                    logical_end=next_month(start) if lane=='daily' else end
                    if result['status'] == 'complete':
                        item['last_complete'] = result
                        enqueue(self.store,result,'eodhd_market',start,logical_end,lane,{'symbol':symbol,'universe':digest(self.universe)})
                    if lane == 'historical' or item.get('scan_next_date') or item.get('gaps'):
                        item.setdefault('gaps', {}).pop(str(start), None)
                        if not retry_gap:
                            item['scan_next_date'] = str(end)
                        item['next_date'] = min(item['gaps']) if item['gaps'] else item.get('scan_next_date', str(end))
                    else:
                        item['next_date']=str(end)
                    item.pop('retry_after',None)
                else:
                    item['retry_after']=str(today+timedelta(days=1))
                    if result.get('reason') == 'market_empty_price_window_unverified':
                        item['empty_window_diagnosed'] = True
                        # Keep unverified closed months in the gap ledger while
                        # allowing current prices to proceed. An open month is
                        # retried as it fills in, without declaring it covered.
                        if lane == 'historical' or end == next_month(start):
                            item.setdefault('gaps', {})[str(start)] = {'end_exclusive': str(end), 'manifest': result.get('manifest'), 'reason': result['reason'], 'last_attempt': now()}
                            if not retry_gap:
                                item['scan_next_date'] = str(end)
                                item.pop('retry_after', None)
                            item['next_date'] = min(item['gaps'])
                item.update(last_attempt=now(),last_result=result,window_start=str(start),window_end_exclusive=str(end))
                state['symbols'][symbol]=item;token=write_json(self.store,key,state,token)
                outcomes.append({'symbol':symbol,'lane':lane,**result});attempted+=1
                if result.get('reason') in {'market_run_request_budget_reached','market_daily_request_budget_reached','eodhd_authentication_denied','eodhd_endpoint_access_denied','eodhd_shared_quota_reached','eodhd_quota_refresh_required'}:
                    # Quota exhaustion is shared: don't mark every symbol failed.
                    return {'status':'partial','stream_id':self.identity,'results':outcomes}
        unresolved_counts = {}; excluded_counts = {}
        for lane in ('daily', 'historical'):
            saved, _ = load_stored(self.store, self.prefix+'/'+lane+'.json')
            unresolved_counts[lane] = sum(unresolved(v) for v in (saved or {}).get('symbols', {}).values())
            excluded_counts[lane] = sum(len(v.get('excluded_windows', {})) for v in (saved or {}).get('symbols', {}).values())
        return {'status':'partial' if any(unresolved_counts.values()) or any(r['status'] not in SUCCESS for r in outcomes) else 'complete',
            'stream_id':self.identity,'listing_symbols':len(self.symbols),'results':outcomes,
            'symbols_with_unresolved_windows': unresolved_counts, 'excluded_windows': excluded_counts,
            'coverage':'Invocation status only; complete historical coverage requires every symbol cursor and gap review.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--status',action='store_true');p.add_argument('--dry-run',action='store_true');a=p.parse_args()
    config=load_json(ROOT/'config/market-operations.json');u=load_json(ROOT/config['universe']);t=load_json(ROOT/config['taxonomy'])
    if a.dry_run:print(json.dumps({'historical_start':config['historical_start'],'daily_origin':config['daily_origin'],'symbols':len(symbols(u)),**config,'runtime_quota':load_json(ROOT/'config/eodhd-quota.json')}));return 0
    with (ROOT/'.market-collection.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return 2
        settings=StorageSettings.load(ROOT/config['storage_config']);store=settings.store();runner=MarketOperations(store,settings,config,u,t)
        if a.status:
            registry = Exclusions(store, runner.prefix, runner.symbols)
            status = runner.reconcile_exclusions(registry, persist=False)
            print(json.dumps({'stream_id':runner.identity,'states':status,'coverage_review':coverage_report(status,registry)}));return 0
        runner.reconcile_exclusions()
        limits=load_json(ROOT/'config/eodhd-quota.json');runner.window_limit=limits['market_windows_per_lane']
        source_config=load_json(ROOT/'config/eodhd-universe.json');client=EODHDClient.configured(source_config);account=client.account()
        limit,used=account.get('dailyRateLimit'),account.get('apiRequests')
        require(type(limit)==int and type(used)==int and isinstance(account.get('apiRequestsDate'),str) and account['apiRequestsDate']<=now()[:10],'market_account_quota_unverified')
        if account['apiRequestsDate']<now()[:10]:used=0
        allowance=min(limits['market_requests_per_run'],max(0,limit-used-source_config['daily_api_call_reserve']))
        if allowance<3:print(json.dumps({'status':'partial','reason':'shared_eodhd_quota_reserve'}));return 2
        client.opener=Budget(store,{**config,'max_requests_per_day':limits['daily_group_caps']['market']},allowance,client.opener)
        result=runner.run(client);write_json(store,runner.prefix+'/attempts/'+digest(result)+'.json',result)
        print(json.dumps(result),flush=True);return 0 if result['status']=='complete' else 2

if __name__=='__main__':raise SystemExit(main())
