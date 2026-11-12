"""Daily S65 product attention from an explicitly configured product directory."""
import argparse
import base64
import copy
import fcntl
import json
import time
from collections import Counter,defaultdict
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit

from collection_storage import AlreadyComplete,CollectionRun,StorageSettings,now,task_spec,write_json
from research_contract import ROOT,digest,load_json
from specialist_inputs import item,normalized
from regulatory_collection import require

VERSION='product-search-v1'
API='https://api.dataforseo.com/v3/'
SERP='serp/google/organic/live/advanced'
TRENDS='keywords_data/dataforseo_trends/merged_data/live'
VOLUME='keywords_data/google_ads/search_volume/live'


def product_queries(directory,query_basis="Configured product directory name"):
    """One literal product-name query per nonarchived/nonrejected registry product."""
    result=[];counts=Counter(p['canonical_name'].strip().casefold() for p in directory['products'] if not p.get('archived_at') and p.get('review_status')!='rejected')
    for p in directory['products']:
        if p.get('archived_at') or p.get('review_status')=='rejected':continue
        name=p['canonical_name'].strip()
        require(bool(name) and len(name)<=200,'product_query_invalid_length')
        result.append({'product_id':p['product_id'],'product_name':name,'query':name,
            'sector_id':p['sector_id'],'row_version':p.get('row_version'),
            'registry_review_status':p.get('review_status'),'query_basis':query_basis,
            'query_ambiguity':'duplicate_registry_name' if counts[name.casefold()]>1 else 'search_results_require_product_relevance_review'})
    return sorted(result,key=lambda x:x['product_id'])


def response_results(receipt):
    data=receipt.get('data') or {};tasks=data.get('tasks') or []
    require(receipt['http_status']==200 and data.get('status_code')==20000 and len(tasks)==1 and tasks[0].get('status_code')==20000,'dataforseo_task_failed_no_paid_retry')
    require(isinstance(tasks[0].get('result'),list),'dataforseo_result_shape')
    return tasks[0]['result']


def evidence(receipt):
    key=receipt['raw_s3_key']
    require(key.startswith('research-data/'),'unexpected_search_evidence_prefix')
    return {'key':key[len('research-data/'):],'sha256':receipt['sha256'],
        'source_url':receipt['url'],'retrieved_at':receipt['observed_at']}


class PaidCapture:
    def __init__(self,day,config):
        import weekly_readiness as capture
        self.capture=capture;self.day=day;self.config=config;self.auth=None
        self.folder=ROOT/'reports'/('product-search-'+day)
        self.monthly=ROOT/'reports'/('product-search-monthly-'+day[:7])
    def spent(self):
        receipts={}
        for folder in [self.folder,self.monthly]:
            for path in (folder/'captures').glob('*.json'):
                r=json.loads(path.read_text())
                if r.get('observed_at','')[:10]==self.day and 'sha256' in r:
                    receipts[r['sha256']]=Decimal(str((r.get('data') or {}).get('cost',0)))
        return sum(receipts.values(),Decimal(0))
    def __call__(self,endpoint,payload,monthly=False):
        folder=self.monthly if monthly else self.folder
        name=digest([endpoint,payload]);path=folder/'captures'/(name+'.json')
        if not path.exists():
            # Do not continue spending after an ambiguous request in either daily or monthly scope.
            require(not any(list((f/'captures').glob('*.pending')) for f in [self.folder,self.monthly]),'ambiguous_paid_request_requires_receipt_review')
            reserve=Decimal(str(self.config['request_reservation_usd']['volume' if endpoint==VOLUME else 'snapshot']))
            require(self.spent()+reserve<=Decimal(str(self.config['daily_budget_usd'])),'product_search_daily_budget_exhausted')
        if self.auth is None and not path.exists():
            secret=json.loads(self.capture.client('secretsmanager').get_secret_value(SecretId=self.capture.SECRET)['SecretString'])
            token=secret['base64'].strip();token=token[6:] if token.lower().startswith('basic ') else token
            require(':' in base64.b64decode(token).decode(),'invalid_dataforseo_credential')
            self.auth='Basic '+token
        if endpoint==VOLUME and not path.exists():
            time.sleep(max(0,5.1-(time.monotonic()-getattr(self,'last_volume_request',0))))
            self.last_volume_request=time.monotonic()
        self.capture.OUT=folder;self.capture.PREFIX='research-data/'+folder.name
        receipt=self.capture.capture(name,'S65',API+endpoint,[payload],self.auth)
        response_results(receipt)
        return receipt


def volumes(store,paid,queries,locale,day):
    """Monthly per-query cache, batching only queries without a saved observation."""
    saved={};missing=[]
    for query in sorted({p['query'] for p in queries}):
        key='operations/product-search/keyword-cache/'+day[:7]+'/'+digest([query,locale])+'.json'
        old=store.get(key)
        if old:saved[query]=json.loads(old.body)
        else:missing.append((query,key))
    for start in range(0,len(missing),1000):
        group=missing[start:start+1000]
        receipt=paid(VOLUME,{'keywords':[q for q,_ in group],'location_code':locale['location_code'],'language_code':locale['language_code']},monthly=True)
        rows=response_results(receipt)
        by_query={r['keyword'].casefold():r for r in rows if isinstance(r,dict) and r.get('keyword')}
        for query,key in group:
            raw=by_query.get(query.casefold())
            value={'status':'available' if raw and raw.get('search_volume') is not None else 'insufficient_or_unavailable_data',
                'query':query,'provider_observation':raw,'observed_at':receipt['observed_at'],'evidence':evidence(receipt),
                'frequency':'provider monthly estimates; cached for calendar month','refreshed_on_this_day':receipt['observed_at'][:10]==day}
            write_json(store,key,value);saved[query]=value
    return saved


def summarize(serp_receipt,trend_receipt,query):
    serp=response_results(serp_receipt);trends=response_results(trend_receipt)
    require(len(serp)==1 and len(trends)==1,'product_search_response_count')
    results=serp[0].get('items') or []
    domains=defaultdict(lambda:{'result_count':0,'best_organic_rank':None,'result_types':set(),'urls':set()})
    def visit(row):
        url=row.get('url');host=urlsplit(url).hostname if url else None
        if host:
            d=domains[host.lower()];d['result_count']+=1;d['result_types'].add(row.get('type'));d['urls'].add(url)
            if row.get('type')=='organic' and isinstance(row.get('rank_group'),int):
                d['best_organic_rank']=min(d['best_organic_rank'] or row['rank_group'],row['rank_group'])
        for child in row.get('items') or []:
            if isinstance(child,dict):visit(child)
    for r in results:visit(r)
    graph=[];geography=[]
    for block in trends[0].get('items') or []:
        if block.get('type')=='dataforseo_trends_graph':
            require(block.get('keywords',[query])==[query],'product_trend_query_mismatch')
            graph=block.get('data') or []
        if block.get('type')=='subregion_interests':
            for interest in block.get('interests') or []:
                if interest.get('keyword')==query:geography=interest.get('values') or []
    return {'search_results':results,'result_datetime':serp[0].get('datetime'),
        'visible_domains':[{'domain':host,**{k:v for k,v in d.items() if k not in {'urls','result_types'}},'urls':sorted(d['urls']),'result_types':sorted(t for t in d['result_types'] if t)} for host,d in sorted(domains.items())],
        'relative_interest':{'status':'available' if graph else 'insufficient_or_unavailable_data','observations':graph,
            'unit':'provider normalized relative interest, not search counts','normalization_note':'Query and rolling-window dependent; snapshots cannot be stitched as absolute counts. Zero may mean insufficient data.'},
        'geographic_interest':{'status':'available' if geography else 'insufficient_or_unavailable_data','regions':geography,
            'unit':'relative regional interest, not visitor counts or traffic shares','scope':'worldwide; provider country/region labels retained'},
        'raw_trend_items':trends[0].get('items') or []}


def collect_product(store,settings,universe,taxonomy,paid,p,locale,day,volume,snapshot):
    start=date.fromisoformat(day);end=start+timedelta(days=1)
    scope={'source_id':'S65','product':p,'locale':locale,'trend_window_days':90,
        'query_version':VERSION,'coverage_note':'Product search attention, relative geographic interest and visible domains; actual referrals and visits are not measured.'}
    scope['parameters']={k:v for k,v in scope.items() if k not in {'source_id','coverage_note'}}
    spec=task_spec('dataforseo_products','specialist_inputs','daily',day+'T00:00:00Z',end.isoformat()+'T00:00:00Z',scope,VERSION,universe,taxonomy)
    try:run=CollectionRun.start(store,spec,universe,taxonomy,settings,resume=True)
    except AlreadyComplete as exc:return {'status':'complete','manifest':str(exc),'replayed':True}
    try:
        if run.exhausted:return {'status':'complete','manifest':run.finish('complete',expected_records=1),'replayed':True}
        serp=paid(SERP,{'keyword':p['query'],'location_code':locale['location_code'],'language_code':locale['language_code'],'device':'desktop','depth':10})
        window={'date_from':(start-timedelta(days=90)).isoformat(),'date_to':(start-timedelta(days=1)).isoformat()}
        trend=paid(TRENDS,{'keywords':[p['query']],**window,'type':'web'})
        data={'product':p,'capture_date':day,'query':p['query'],'serp_locale':locale,'device':'desktop','engine':'google',
            **summarize(serp,trend,p['query']),'interest_window':window,'keyword_metrics':{**volume,'refreshed_on_this_day':volume['observed_at'][:10]==day},
            'actual_visits':None,'actual_referral_sources':None,'product_relevance':'unreviewed search matches; registry query association is known',
            'registry_snapshot':snapshot,'specialist_use':{'status':'input_observation; routing integration pending',
                'layers':['product_commercial','financial_market'],'event_emitted':False},
            'training_rights':'not_accepted; source-specific review required'}
        e=[snapshot,evidence(serp),evidence(trend),volume['evidence']]
        record=normalized(item(p['product_id']+':'+day+':'+digest(locale),data,API+SERP,None,'derived'),run,e)
        record['payload']['record_type']='product_search_attention_observation'
        record['payload']['entity_link_status']='RDS product query association; result relevance unreviewed'
        # RDS IDs live in the payload until admitted to the model-universe contract.
        record=__import__('research_contract').seal_record(record)
        run.commit_page([record],exhausted=True)
        return {'status':'complete','manifest':run.finish('complete',expected_records=1),'replayed':False}
    except BaseException:
        run.finish('partial','product_search_retry_requires_saved_receipts');raise


def product_directory(config,store):
    source=config.get('directory',{'mode':'metadata_engine'})
    if source['mode']=='pending_registry':return None,source
    if source['mode']=='metadata_engine':
        from product_search_directory import read_products
        return read_products(),{'source_url':'rds://metadata_engine/entities?entity_type=product'}
    raise ValueError('unknown_product_directory_mode')


def execute(config,day=None,write_local_report=True):
    day=day or datetime.now(timezone.utc).date().isoformat()
    settings=StorageSettings.load(ROOT/config['storage_config']);store=settings.store()
    directory,directory_source=product_directory(config,store)
    if directory is None:
        report={'day':day,'version':VERSION,'status':'pending_dependency','reason':'product_directory_required',
            'action':('Populate Constellation product entities; all named products are included automatically.' if directory_source.get('upstream')=='metadata_engine.entities' else 'Configure a current product directory before enabling paid capture.'),
            'directory_source':directory_source,'capture_ready':False,'coverage_status':'unknown',
            'registry_product_count':None,'expected_observations':None,'pending_observations':None,
            'completed_observations':0,'requests_made':0,'actual_provider_cost_usd':'0','updated_at':now()}
        key='operations/product-search/daily/'+day+'/state.json';old=store.get(key);write_json(store,key,report,old.token if old else None)
        if write_local_report:
            folder=ROOT/'reports'/('product-search-'+day);folder.mkdir(parents=True,exist_ok=True);(folder/'state.json').write_text(json.dumps(report,indent=2)+'\n')
        return report
    if config.get('directory',{'mode':'metadata_engine'}).get('mode')=='metadata_engine' and not directory['products']:
        pending={**config,'directory':{'mode':'pending_registry','reason':'No named product entities exist in the Constellation metadata registry yet. All product entities will be eligible automatically.','upstream':'metadata_engine.entities'}}
        return execute(pending,day,write_local_report)
    queries=product_queries(directory,'Constellation product entity name' if config.get('directory',{}).get('mode')=='metadata_engine' else 'Configured product directory name')
    snapshot_raw=json.dumps(directory,sort_keys=True).encode();snapshot_sha=__import__('hashlib').sha256(snapshot_raw).hexdigest()
    from collection_storage import write_checked
    snapshot_key='operations/product-search/directories/'+snapshot_sha+'.json'
    write_checked(store,snapshot_key,snapshot_raw,content_type='application/json')
    snapshot={'key':snapshot_key,'sha256':snapshot_sha,'source_url':directory_source['source_url'],'retrieved_at':now()}
    paid=PaidCapture(day,config)
    report={'day':day,'version':VERSION,'started_at':now(),'status':'running','registry_product_count':len(directory['products']),
        'eligible_product_count':len(queries),'expected_observations':len(queries)*len(config['locales']),'completed_observations':0,'pending_observations':len(queries)*len(config['locales']),
        'directory_snapshot':snapshot,'outcomes':[],'daily_budget_usd':config['daily_budget_usd']}
    def save():
        report['actual_provider_cost_usd']=str(paid.spent());report['updated_at']=now()
        state_key='operations/product-search/daily/'+day+'/state.json'
        prior=store.get(state_key)
        write_json(store,state_key,report,prior.token if prior else None)
        path=ROOT/'reports'/('product-search-'+day);path.mkdir(parents=True,exist_ok=True)
        (path/'state.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    universe=load_json(ROOT/config['universe']);taxonomy=load_json(ROOT/config['taxonomy'])
    for locale in config['locales']:
        try:panel=volumes(store,paid,queries,locale,day)
        except Exception as exc:
            report.update(status='pending',reason=str(exc)[:180],error_type=type(exc).__name__);save();return report
        # Rotate the start each day so a capped universe does not always favor the same IDs.
        rotated=sorted(queries,key=lambda p:digest([day,p['product_id']]))
        for p in rotated:
            try:result=collect_product(store,settings,universe,taxonomy,paid,p,locale,day,panel[p['query']],snapshot)
            except Exception as exc:result={'status':'pending','reason':str(exc)[:180],'error_type':type(exc).__name__}
            report['outcomes'].append({'product_id':p['product_id'],'locale':locale,**result});save()
            if result['status']=='pending':break
        if any(o['status']=='pending' for o in report['outcomes']):break
    complete=sum(o['status']=='complete' for o in report['outcomes'])
    report.update(status='no_products' if not queries else ('complete' if complete==report['expected_observations'] else 'partial'),completed_observations=complete,
        pending_observations=report['expected_observations']-complete,finished_at=now())
    save();return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',default='config/product-search-daily.json');args=parser.parse_args()
    with (ROOT/'.product-search.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return 2
        report=execute(load_json(ROOT/args.config));print(json.dumps(report),flush=True)
        return 0 if report['status'] in {'complete','no_products','pending_dependency'} else 1

if __name__=='__main__':raise SystemExit(main())
