#!/usr/bin/env python3
"""EODHD listing inventory and auditable current profiles for universe review.

This creates evidence-backed classification candidates; it never silently
replaces the shared company universe or claims a global inventory is complete.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

from collection_storage import AlreadyComplete, CollectionRun, StorageSettings, now, task_spec
from disclosure_collection import finish_error, midnight
from regulatory_collection import CompanyMatcher, EvidenceClient, SourceIssue, require
from research_contract import ROOT, digest, load_json, seal_record, validate_record


def parse_token(value):
    try:
        data=json.loads(value)
    except ValueError:
        data=value
    if isinstance(data,dict):
        keys=('eodhd','eodhd_api_key','api_key','api_token','apikey','token')
        values=[v for k,v in data.items() if k.lower().replace('-','_') in keys and isinstance(v,str)]
        if not values and len(data)==1:values=list(data.values())
        require(len(values)==1,'eodhd_secret_format_invalid')
        data=values[0]
    require(isinstance(data,str) and data.strip(),'eodhd_secret_format_invalid')
    return data.strip()


class EODHDClient:
    def __init__(self, token, opener=urlopen, sleeper=time.sleep):
        self.token,self.opener,self.sleep=token,opener,sleeper

    @classmethod
    def configured(cls,config):
        import boto3
        secret=boto3.client('secretsmanager',region_name=config['region']).get_secret_value(SecretId=config['secret_id'])
        client=cls(parse_token(secret['SecretString']))
        from eodhd_quota import SharedQuota
        client.quota=SharedQuota(ROOT/'.eodhd-quota.sqlite3',load_json(ROOT/'config/eodhd-quota.json'))
        client.account()  # Initialize/synchronize the shared weighted counter.
        return client

    def get(self,path,params=None):
        public='https://eodhd.com/api/'+path
        params={'fmt':'json',**(params or {})}
        require('api_token' not in params,'credential_in_public_parameters')
        public+='?'+urlencode(params)
        private=public+'&'+urlencode({'api_token':self.token})
        for attempt in range(4):
            self.sleep(0.3 if not attempt else 2**attempt)
            try:
                if hasattr(self,'quota'): self.quota.reserve(path)
                with self.opener(Request(private,headers={'User-Agent':'Optima Holdings support@optima-holdings.com','Accept-Encoding':'identity'}),timeout=60) as response:
                    raw=response.read(16*1024*1024+1)
                require(len(raw)<=16*1024*1024,'eodhd_response_too_large')
                require(self.token.encode() not in raw,'eodhd_response_contains_credential')
                try:data=json.loads(raw)
                except ValueError:raise SourceIssue('eodhd_invalid_json') from None
                return data,raw,public
            except HTTPError as exc:
                if exc.code in (401,403):
                    raise SourceIssue('eodhd_authentication_denied' if exc.code==401 else 'eodhd_endpoint_access_denied',True) from None
                if exc.code not in (429,500,502,503,504):
                    raw=exc.read(1024*1024+1)
                    require(len(raw)<=1024*1024,'eodhd_error_response_too_large')
                    require(self.token.encode() not in raw,'eodhd_response_contains_credential')
                    error=SourceIssue('eodhd_http_'+str(exc.code))
                    error.raw,error.public_url,error.http_status=raw,public,exc.code
                    raise error from None
                retry=exc.headers.get('Retry-After') if exc.headers else None
                if retry:
                    try:delay=float(retry)
                    except ValueError:raise SourceIssue('eodhd_retry_deferred',True) from None
                    if delay>30:raise SourceIssue('eodhd_retry_deferred',True) from None
                    self.sleep(max(0,delay))
            except (URLError,TimeoutError):pass
        raise SourceIssue('eodhd_retries_exhausted',True)

    def account(self):
        # User responses may include account details or keys; never persist raw.
        # Request using a dedicated path that does not pass through evidence storage.
        url='https://eodhd.com/api/user?'+urlencode({'api_token':self.token,'fmt':'json'})
        try:
            if hasattr(self,'quota'): self.quota.reserve('user')
            with self.opener(Request(url),timeout=45) as response:data=json.load(response)
        except (HTTPError,URLError,TimeoutError):raise SourceIssue('eodhd_account_check_failed',True) from None
        result={key:data.get(key) for key in ('subscriptionType','subscriptionMode','dailyRateLimit','apiRequests','apiRequestsDate')}
        if hasattr(self,'quota'): self.quota.sync(result)
        return result


def sector_candidates(general,config):
    evidence=[]
    for sector,pattern in config['sector_patterns'].items():
        matches=[]
        for field in ('Industry','GicIndustry','GicSubIndustry','Description'):
            value=general.get(field)
            if not isinstance(value,str):continue
            match=re.search(pattern,value,re.I)
            if match:matches.append({'field':field,'matched_text':match.group(0),
                                     'excerpt':value[max(0,match.start()-60):match.end()+100]})
        if matches:evidence.append({'sector_id':sector,'review_status':'pending','matches':matches})
    return evidence


def valid_symbol(value):
    if not isinstance(value,str) or not 3<=len(value)<=200 or '.' not in value:
        return False
    code,exchange=value.rsplit('.',1)
    return bool(code and re.fullmatch(r'[A-Za-z0-9]+',exchange) and
        all(character.isprintable() and not character.isspace() for character in code))


def exchange_directory(client,config,requested=()):
    rows,raw,url=client.get('exchanges-list')
    require(isinstance(rows,list) and rows,'eodhd_exchange_directory_invalid')
    directory={}
    for row in rows:
        require(isinstance(row,dict) and re.fullmatch(r'[A-Z0-9]+',str(row.get('Code',''))),'eodhd_exchange_directory_invalid')
        require(row['Code'] not in directory,'eodhd_exchange_directory_duplicate')
        directory[row['Code']]=row
    for row in config.get('supplemental_exchanges',[]):
        require(isinstance(row,dict) and re.fullmatch(r'[A-Z0-9]+',str(row.get('Code',''))),'eodhd_supplemental_exchange_invalid')
        directory.setdefault(row['Code'],row)
    selected=sorted(set(requested)) if requested else sorted(code for code,row in directory.items()
        if row.get('CountryISO2') and row.get('OperatingMIC'))
    require(selected and all(code in directory for code in selected),'eodhd_exchange_not_in_directory')
    return [directory[code] for code in selected],raw,url


def inventory_record(run,row,status,evidence,matcher):
    code=str(row.get('Code','')).strip();name=str(row.get('Name','')).strip()
    require(code and name and str(row.get('Type','')).casefold() in {'common stock','common_stock'},'eodhd_listing_identity_invalid')
    exchange=str(row['_requested_exchange'])
    provider_symbol=f'{code}.{exchange}'
    candidates,sectors=matcher.match([name])
    payload={'provider_symbol':provider_symbol,'provider_code':code,'requested_exchange':exchange,
        'provider_exchange':row.get('Exchange'),'name':name,'country':row.get('Country'),
        'currency':row.get('Currency'),'instrument_type':row.get('Type'),'isin':row.get('Isin'),
        'listing_status':status,'candidate_company_ids':candidates,'candidate_sector_ids':sectors,
        'source_evidence':list(evidence),
        'coverage_note':'A provider listing is an identity candidate, not a verified legal-company match.'}
    return seal_record({'document_type':'collected_record','schema_version':'1.0','source':'eodhd',
        'dataset':'listing_inventory','source_record_id':provider_symbol,'source_record_id_basis':'provider',
        'source_url':evidence[0]['source_url'],'universe_version':run.universe['universe_version'],
        'company_ids':[],'listing_ids':[],'product_ids':[],'person_ids':[],'entity_match_status':'unresolved',
        'event_at':None,'available_at':None,'source_updated_at':None,'ingested_at':now(),
        'availability_basis':'unknown','availability_evidence':[],'run_id':run.run_id,'payload':payload})


def collect_inventory(store,settings,universe,taxonomy,config,exchanges,directory_raw,directory_url,
                      statuses=('active','delisted'),client=None,refresh=False,max_exchanges=None):
    require(client is not None,'eodhd_client_required')
    require(statuses and set(statuses)<= {'active','delisted'},'invalid_inventory_status')
    codes=[row['Code'] for row in exchanges]
    require(len(codes)==len(set(codes)) and codes,'invalid_exchange_scope')
    today=datetime.now(timezone.utc).date()
    scope={'exchanges':exchanges,'statuses':list(statuses),'instrument_type':config['instrument_type'],
        'exchange_directory_sha256':hashlib.sha256(directory_raw).hexdigest(),
        'coverage':'Exact active/delisted common-stock snapshots for the listed provider exchange codes; private companies are outside this source.'}
    spec=task_spec('eodhd','listing_inventory','daily',midnight(today),midnight(today+timedelta(days=1)),scope,
                   'eodhd-listing-inventory-1.0',universe,taxonomy)
    try:run=CollectionRun.start(store,spec,universe,taxonomy,settings,resume=not refresh,refresh=refresh)
    except AlreadyComplete as exc:return {'status':'complete','already_complete':True,'manifest':str(exc)}
    evidence_client=EvidenceClient(store,'eodhd');matcher=CompanyMatcher(universe)
    try:
        evidence_client.save(directory_raw,directory_url)
        jobs=[(row,status) for row in exchanges for status in statuses]
        offset=int(run.cursor or 0);processed_exchanges=0;last_exchange=None
        while not run.exhausted and offset<len(jobs):
            row,status=jobs[offset]
            if max_exchanges is not None and row['Code']!=last_exchange and processed_exchanges>=max_exchanges:
                return {'status':'partial','reason':'exchange_limit','records':run.state['record_count'],
                    'manifest':run.finish('partial','exchange_limit')}
            if row['Code']!=last_exchange:
                processed_exchanges+=1;last_exchange=row['Code']
            params={'type':config['instrument_type']}
            if status=='delisted':params['delisted']=1
            data,raw,url=client.get('exchange-symbol-list/'+quote(row['Code'],safe=''),params)
            require(isinstance(data,list),'eodhd_listing_inventory_invalid')
            codes_in_page=[];records=[]
            evidence_client.evidence=[];evidence_client.save(raw,url)
            for item in data:
                require(isinstance(item,dict),'eodhd_listing_inventory_invalid')
                codes_in_page.append(str(item.get('Code','')))
                records.append(inventory_record(run,{**item,'_requested_exchange':row['Code']},status,evidence_client.evidence,matcher))
            require(len(codes_in_page)==len(set(codes_in_page)),'eodhd_listing_inventory_duplicate')
            offset+=1
            run.commit_page(records,next_cursor=str(offset) if offset<len(jobs) else None,exhausted=offset==len(jobs))
            print(json.dumps({'stage':'inventory_progress','exchange':row['Code'],'listing_status':status,
                'listings':len(records),'completed_requests':offset,'total_requests':len(jobs)}),flush=True)
        return {'status':'complete','records':run.state['record_count'],'exchanges':len(exchanges),
            'manifest':run.finish('complete',expected_records=run.state['record_count'])}
    except (Exception,KeyboardInterrupt) as exc:return finish_error(run,exc,evidence_client.evidence)


def read_inventory(store,key,universe,taxonomy,include_delisted=False):
    obj=store.get(key);require(obj is not None,'inventory_manifest_missing')
    manifest=json.loads(obj.body);task=manifest.get('task',{})
    require(manifest.get('status')=='complete' and manifest.get('exhausted'),'inventory_manifest_not_complete')
    require((task.get('source'),task.get('dataset'))==('eodhd','listing_inventory'),'inventory_manifest_wrong_dataset')
    require(task.get('universe_hash')==digest(universe) and task.get('taxonomy_hash')==digest(taxonomy),'inventory_configuration_mismatch')
    task_id='task_'+digest(task);head_obj=store.get(f'checkpoints/{task_id}/head.json')
    require(head_obj is not None and key in json.loads(head_obj.body).get('terminal_history',[]),'inventory_manifest_not_committed')
    symbols=[];count=0;verified_evidence=set()
    for page in manifest['pages']:
        for batch in page['batches']:
            batch_obj=store.get(batch['key']);require(batch_obj is not None,'inventory_batch_missing')
            require(hashlib.sha256(batch_obj.body).hexdigest()==batch['sha256'],'inventory_batch_checksum_mismatch')
            rows=[json.loads(line) for line in batch_obj.body.splitlines()]
            require(len(rows)==batch['records'],'inventory_batch_count_mismatch')
            for record in rows:
                require(not validate_record(record,universe),'inventory_record_invalid')
                require(record['source']=='eodhd' and record['dataset']=='listing_inventory','inventory_record_scope_mismatch')
                for ref in record['payload']['source_evidence']:
                    identity=(ref['key'],ref['sha256'])
                    if identity not in verified_evidence:
                        evidence=store.get(ref['key'])
                        require(evidence is not None and hashlib.sha256(evidence.body).hexdigest()==ref['sha256'],'inventory_evidence_missing')
                        verified_evidence.add(identity)
                if include_delisted or record['payload']['listing_status']=='active':symbols.append(record['payload']['provider_symbol'])
            count+=len(rows)
    require(count==manifest['record_count']==manifest['expected_records'],'inventory_manifest_count_mismatch')
    symbols=sorted(set(symbols))
    return symbols,{'key':key,'sha256':hashlib.sha256(obj.body).hexdigest(),'records':count}


def profile_record(run,symbol,general,status,evidence,config,matcher):
    names=[general.get('Name')] if isinstance(general,dict) and general.get('Name') else []
    candidates,sectors=matcher.match(names)
    payload={'provider_symbol':symbol,'profile_status':status,'general':general,
        'sector_candidates':sector_candidates(general,config) if isinstance(general,dict) else [],
        'candidate_company_ids':candidates,'candidate_sector_ids':sectors,
        'source_evidence':list(evidence),'coverage_note':config['coverage_note']}
    return seal_record({'document_type':'collected_record','schema_version':'1.0','source':'eodhd','dataset':'company_profiles',
        'source_record_id':symbol,'source_record_id_basis':'provider','source_url':evidence[0]['source_url'],
        'universe_version':run.universe['universe_version'],'company_ids':[],'listing_ids':[],'product_ids':[],
        'person_ids':[],'entity_match_status':'unresolved','event_at':None,'available_at':None,'source_updated_at':None,
        'ingested_at':now(),'availability_basis':'unknown','availability_evidence':[],'run_id':run.run_id,'payload':payload})


def resume_spec(store,key,spec):
    obj=store.get(key);require(obj is not None,'resume_manifest_missing')
    manifest=json.loads(obj.body);previous=manifest['task']
    require(manifest['status'] in {'partial','failed'},'resume_manifest_not_incomplete')
    require(all(previous.get(k)==v for k,v in spec.items() if k!='window'),'resume_scope_mismatch')
    require(manifest['task_id']=='task_'+digest(previous),'resume_task_mismatch')
    head_obj=store.get('checkpoints/'+manifest['task_id']+'/head.json')
    require(head_obj is not None,'resume_checkpoint_missing')
    head=json.loads(head_obj.body)
    require(head['task']==previous and head['terminal_manifest']==key and
            head['status'] in {'partial','failed'},'resume_checkpoint_changed')
    return previous


def collect_profile_scope(store,settings,universe,taxonomy,config,symbols,client,scope,refresh=False,max_records=None,
                          resume_manifest=None):
    symbols=sorted(set(symbols))
    require(symbols and all(valid_symbol(symbol) for symbol in symbols),'invalid_eodhd_symbol')
    today=datetime.now(timezone.utc).date()
    spec=task_spec('eodhd','company_profiles','daily',midnight(today),midnight(today+timedelta(days=1)),scope,
                   'eodhd-profiles-1.1',universe,taxonomy)
    if resume_manifest:
        require(not refresh,'resume_refresh_conflict')
        spec=resume_spec(store,resume_manifest,spec)
    try:run=CollectionRun.start(store,spec,universe,taxonomy,settings,resume=not refresh,refresh=refresh)
    except AlreadyComplete as exc:return {'status':'complete','already_complete':True,'manifest':str(exc)}
    evidence_client=EvidenceClient(store,'eodhd');matcher=CompanyMatcher(universe)
    try:
        offset=int(run.cursor or 0);processed=0;missing=0
        while not run.exhausted and offset<len(symbols):
            if max_records is not None and processed>=max_records:
                return {'status':'partial','reason':'record_limit','records':run.state['record_count'],
                    'manifest':run.finish('partial','record_limit')}
            symbol=symbols[offset];evidence_client.evidence=[]
            try:
                general,raw,url=client.get('fundamentals/'+quote(symbol,safe=''),{'filter':'General'})
                require(isinstance(general,dict) and general.get('Code')==symbol.rsplit('.',1)[0] and general.get('Name'),'eodhd_profile_identity_mismatch')
                evidence_client.save(raw,url);status='available'
            except SourceIssue as exc:
                if exc.code!='eodhd_http_404' or not hasattr(exc,'raw'):raise
                evidence_client.save(exc.raw,exc.public_url);general=None;status='not_found';missing+=1
            record=profile_record(run,symbol,general,status,evidence_client.evidence,config,matcher)
            offset+=1;processed+=1
            run.commit_page([record],next_cursor=str(offset) if offset<len(symbols) else None,exhausted=offset==len(symbols))
            if processed%100==0:
                print(json.dumps({'stage':'profile_progress','records':run.state['record_count'],
                    'total_symbols':len(symbols),'run_id':run.run_id}),flush=True)
        return {'status':'complete','records':run.state['record_count'],'profiles_not_found_this_attempt':missing,
            'manifest':run.finish('complete',expected_records=len(symbols))}
    except (Exception,KeyboardInterrupt) as exc:return finish_error(run,exc,evidence_client.evidence)


def collect_profiles(store,settings,universe,taxonomy,config,symbols,client,refresh=False,max_records=None):
    symbols=sorted(set(symbols))
    scope={'symbols':symbols,'classification_rules':config['sector_patterns'],'rules_version':config['sector_rules_version'],
           'coverage':'Explicit listing-symbol cohort, current profiles only; not complete global or private-company coverage.'}
    return collect_profile_scope(store,settings,universe,taxonomy,config,symbols,client,scope,refresh,max_records)


def collect_inventory_profiles(store,settings,universe,taxonomy,config,manifest_key,client,
                               include_delisted=False,refresh=False,max_records=None,resume_manifest=None):
    symbols,input_manifest=read_inventory(store,manifest_key,universe,taxonomy,include_delisted)
    scope={'input_manifest':input_manifest,'symbol_count':len(symbols),'symbols_sha256':digest(symbols),
        'include_delisted':include_delisted,'classification_rules':config['sector_patterns'],
        'rules_version':config['sector_rules_version'],
        'coverage':'Every distinct listing symbol in the pinned complete inventory is attempted; current profiles and labels are not historical facts.'}
    return collect_profile_scope(store,settings,universe,taxonomy,config,symbols,client,scope,refresh,max_records,resume_manifest)


def quota_batch_size(client,config,requested=None):
    account=client.account()
    limit,used=account.get('dailyRateLimit'),account.get('apiRequests')
    require(isinstance(limit,int) and isinstance(used,int),'eodhd_usage_unavailable')
    cost=config['fundamentals_general_api_calls'];reserve=config['daily_api_call_reserve']
    require(isinstance(cost,int) and cost>0 and isinstance(reserve,int) and reserve>=0,'eodhd_quota_config_invalid')
    available=max(0,(limit-used-reserve)//cost)
    desired=requested if requested is not None else config['default_profile_batch_size']
    require(isinstance(desired,int) and desired>0,'eodhd_profile_batch_invalid')
    return min(desired,available),account


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('check','inventory','profiles','inventory-profiles'))
    parser.add_argument('--config',type=Path,default=ROOT/'config/eodhd-universe.json')
    parser.add_argument('--storage-config',type=Path,default=ROOT/'config/collection-storage.s3.json')
    parser.add_argument('--universe',type=Path,default=ROOT/'config/company-universe.v0.1.json')
    parser.add_argument('--taxonomy',type=Path,default=ROOT/'config/sectors.v1.json')
    parser.add_argument('--symbol',action='append',default=[])
    parser.add_argument('--exchange',action='append',default=[])
    parser.add_argument('--inventory-status',action='append',choices=('active','delisted'),default=[])
    parser.add_argument('--inventory-manifest')
    parser.add_argument('--resume-manifest',help='Resume the latest incomplete profile manifest, preserving its task across UTC dates')
    parser.add_argument('--include-delisted',action='store_true')
    parser.add_argument('--max-exchanges',type=int)
    parser.add_argument('--max-records',type=int)
    parser.add_argument('--refresh',action='store_true')
    args=parser.parse_args()
    if args.stage=='profiles' and not args.symbol:parser.error('profiles requires explicit --symbol values')
    if args.stage=='inventory-profiles' and not args.inventory_manifest:parser.error('inventory-profiles requires --inventory-manifest')
    if args.resume_manifest and (args.stage!='inventory-profiles' or args.refresh):parser.error('--resume-manifest requires inventory-profiles without --refresh')
    if args.max_records is not None and args.max_records<1:parser.error('--max-records must be positive')
    if args.max_exchanges is not None and args.max_exchanges<1:parser.error('--max-exchanges must be positive')
    try:
        config=load_json(args.config);client=EODHDClient.configured(config)
        if args.stage=='check':result=client.account()
        else:
            settings=StorageSettings.load(args.storage_config)
            store=settings.store();universe=load_json(args.universe);taxonomy=load_json(args.taxonomy)
            if args.stage=='inventory':
                exchanges,raw,url=exchange_directory(client,config,args.exchange)
                statuses=tuple(args.inventory_status or ('active','delisted'))
                result=collect_inventory(store,settings,universe,taxonomy,config,exchanges,raw,url,statuses,client,
                    args.refresh,args.max_exchanges)
            elif args.stage=='profiles':
                result=collect_profiles(store,settings,universe,taxonomy,config,args.symbol,client,args.refresh,args.max_records)
            else:
                batch,account=quota_batch_size(client,config,args.max_records)
                if batch<1:
                    result={'status':'partial','reason':'daily_quota_reserve','account':account}
                else:
                    result=collect_inventory_profiles(store,settings,universe,taxonomy,config,args.inventory_manifest,
                        client,args.include_delisted,args.refresh,batch,args.resume_manifest)
                    result['quota_at_start']=account;result['batch_limit']=batch
        print(json.dumps(result),flush=True)
        return 0 if result.get('status','complete')=='complete' else 2
    except Exception as exc:
        print(json.dumps({'status':'failed','reason':exc.code if isinstance(exc,SourceIssue) else 'eodhd_configuration_error','error_type':type(exc).__name__}))
        return 2


if __name__=='__main__':raise SystemExit(main())
