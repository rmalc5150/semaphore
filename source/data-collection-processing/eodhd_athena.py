#!/usr/bin/env python3
"""Publish inventory coverage, profiles and review queues without promoting identities."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from collection_storage import StorageSettings
from eodhd_coverage import read_records
from research_contract import ROOT, canonical_json, digest, load_json
import sec_athena_pilot as release

SCHEMAS={
 'listing_inventory':[(k,'string') for k in ('provider_symbol','exchange_code','exchange_mic','listing_status','name','country','currency','isin',
     'profile_status','profile_observed_at','inventory_observed_at','record_id','raw_manifest','source_evidence_json')],
 'company_profiles':[(k,'string') for k in ('provider_symbol','profile_status','name','provider_exchange','primary_ticker','isin',
     'lei','cik','country','sector','industry','gics_industry','gics_subindustry','description','source_url',
     'ingested_at','record_id','observation_id','raw_manifest','source_evidence_json','general_json')],
 'sector_candidates':[(k,'string') for k in ('provider_symbol','name','sector_id','review_status','review_reason','matches_json',
     'profile_observation_id','observed_at','raw_manifest')],
 'company_identity_review':[(k,'string') for k in ('provider_symbol','name','primary_ticker','isin','lei','cik','identity_status',
     'inventory_name','inventory_isin','review_flags_json','candidate_company_ids_json','profile_observation_id')],
 'exchange_coverage':[('exchange_code','string'),('listing_status','string'),('inventory_records','bigint'),
     ('profiles_attempted','bigint'),('profiles_available','bigint'),('profiles_unavailable','bigint'),
     ('profiles_not_collected','bigint'),('sector_candidate_listings','bigint')],
 'collection_runs':[(k,'string') for k in ('manifest','source','dataset','run_status','reason','task_id','window_start','window_end')]+
     [('records','bigint')]
}


def curate(store,config):
    tables={name:[] for name in SCHEMAS};profiles={};inputs=[];base_task=None
    def accept_manifest(key,manifest):
        nonlocal base_task
        task=manifest['task']
        if base_task is None:base_task=task
        release.require(all(task[k]==base_task[k] for k in ('universe_hash','taxonomy_hash')),'Input configuration mismatch')
        inputs.append({'key':key,'sha256':hashlib.sha256(store.get(key).body).hexdigest(),
            'records':manifest['record_count'],'status':manifest['status']})
        tables['collection_runs'].append({'manifest':key,'source':task['source'],'dataset':task['dataset'],
            'run_status':manifest['status'],'reason':manifest['reason_code'],'task_id':manifest['task_id'],
            'window_start':task['window']['start'],'window_end':task['window']['end'],'records':manifest['record_count']})
    for key in sorted(set(config['profile_manifests'])):
        manifest,rows=read_records(store,key,'company_profiles');accept_manifest(key,manifest)
        for row in rows:
            symbol=row['payload']['provider_symbol'];previous=profiles.get(symbol)
            if previous is None or (row['ingested_at'],row['observation_id'])>(previous[0]['ingested_at'],previous[0]['observation_id']):
                profiles[symbol]=(row,key)
    identifiers=defaultdict(set)
    for symbol,(row,_) in profiles.items():
        g=row['payload'].get('general') or {}
        for field in ('ISIN','LEI','CIK','PrimaryTicker'):
            if g.get(field):identifiers[(field,str(g[field]).strip())].add(symbol)
    for symbol,(row,key) in sorted(profiles.items()):
        p=row['payload'];g=p.get('general') or {};status=p.get('profile_status','available')
        value=lambda field:str(g[field]) if g.get(field) is not None else None
        tables['company_profiles'].append({'provider_symbol':symbol,'profile_status':status,'name':value('Name'),
            'provider_exchange':value('Exchange'),'primary_ticker':value('PrimaryTicker'),'isin':value('ISIN'),
            'lei':value('LEI'),'cik':value('CIK'),'country':value('CountryName'),'sector':value('Sector'),
            'industry':value('Industry'),'gics_industry':value('GicIndustry'),'gics_subindustry':value('GicSubIndustry'),
            'description':value('Description'),'source_url':row['source_url'],'ingested_at':row['ingested_at'],
            'record_id':row['record_id'],'observation_id':row['observation_id'],'raw_manifest':key,
            'source_evidence_json':release.json_text(p['source_evidence']),'general_json':release.json_text(g)})
        flags=[]
        if status!='available':flags.append('profile_'+status)
        if not g.get('Description'):flags.append('missing_description')
        if not g.get('LEI') and not g.get('CIK'):flags.append('no_legal_identifier')
        if g.get('PrimaryTicker') and g['PrimaryTicker']!=symbol:flags.append('non_primary_listing')
        for field in ('ISIN','LEI','CIK','PrimaryTicker'):
            if g.get(field) and len(identifiers[(field,str(g[field]).strip())])>1:flags.append('shared_'+field.lower())
        tables['company_identity_review'].append({'provider_symbol':symbol,'name':value('Name'),'primary_ticker':value('PrimaryTicker'),
            'isin':value('ISIN'),'lei':value('LEI'),'cik':value('CIK'),'identity_status':'pending',
            'inventory_name':None,'inventory_isin':None,
            'review_flags_json':release.json_text(flags),'candidate_company_ids_json':release.json_text(p.get('candidate_company_ids',[])),
            'profile_observation_id':row['observation_id']})
        for candidate in p.get('sector_candidates',[]):
            tables['sector_candidates'].append({'provider_symbol':symbol,'name':value('Name'),'sector_id':candidate['sector_id'],
                'review_status':'pending','review_reason':'Textual candidate requires business-activity review.',
                'matches_json':release.json_text(candidate['matches']),'profile_observation_id':row['observation_id'],
                'observed_at':row['ingested_at'],'raw_manifest':key})
    groups={};seen_inventory=set()
    identity_rows={r['provider_symbol']:r for r in tables['company_identity_review']}
    candidate_symbols={r['provider_symbol'] for r in tables['sector_candidates']}
    exchange_mics={}
    def inventory_row(record):
        p=record['payload'];symbol=p['provider_symbol']
        release.require(symbol not in seen_inventory,'Duplicate inventory symbol');seen_inventory.add(symbol)
        profile=profiles.get(symbol);status=profile[0]['payload'].get('profile_status','available') if profile else 'not_collected'
        if symbol in identity_rows:
            identity=identity_rows[symbol];identity['inventory_name']=p['name'];identity['inventory_isin']=p.get('isin')
            flags=json.loads(identity['review_flags_json'])
            if identity['isin'] and p.get('isin') and identity['isin']!=p['isin']:flags.append('inventory_isin_mismatch')
            if identity['name'] and identity['name'].casefold()!=p['name'].casefold():flags.append('inventory_name_differs')
            identity['review_flags_json']=release.json_text(flags)
        tables['listing_inventory'].append({'provider_symbol':symbol,'exchange_code':p['requested_exchange'],
            'exchange_mic':exchange_mics.get(p['requested_exchange']),
            'listing_status':p['listing_status'],'name':p['name'],'country':p.get('country'),'currency':p.get('currency'),
            'isin':p.get('isin'),'profile_status':status,'profile_observed_at':profile[0]['ingested_at'] if profile else None,
            'inventory_observed_at':record['ingested_at'],'record_id':record['record_id'],
            'raw_manifest':config['inventory_manifest'],'source_evidence_json':release.json_text(p['source_evidence'])})
        group=(p['requested_exchange'],p['listing_status'])
        counts=groups.setdefault(group,Counter());counts['inventory_records']+=1
        counts['profiles_attempted']+=status!='not_collected';counts['profiles_available']+=status=='available'
        counts['profiles_unavailable']+=status not in {'not_collected','available'}
        counts['profiles_not_collected']+=status=='not_collected';counts['sector_candidate_listings']+=symbol in candidate_symbols
    # Read the manifest first so its provider-code to MIC mapping is available
    # while materializing listings. read_records validates it again with rows.
    inventory_obj=store.get(config['inventory_manifest'])
    release.require(inventory_obj is not None,'Inventory manifest missing')
    manifest_scope=json.loads(inventory_obj.body)['task']['scope']
    exchange_mics={row['Code']:row.get('OperatingMIC') for row in manifest_scope['exchanges']}
    manifest,_=read_records(store,config['inventory_manifest'],'listing_inventory',inventory_row)
    release.require(manifest['status']=='complete','Inventory must be complete');accept_manifest(config['inventory_manifest'],manifest)
    for exchange in manifest['task']['scope']['exchanges']:
        for status in manifest['task']['scope']['statuses']:groups.setdefault((exchange['Code'],status),Counter())
    for (code,status),counts in sorted(groups.items()):
        tables['exchange_coverage'].append({'exchange_code':code,'listing_status':status,
            **{k:counts[k] for k,_ in SCHEMAS['exchange_coverage'][2:]}})
    return tables,inputs,base_task['universe_hash']


def prepare(store,settings,config,output_root):
    release.validate_config(config)
    tables,inputs,universe_hash=curate(store,config)
    decisions=[]
    if config.get('review_file'):
        decisions=load_json(Path(config['review_file']))
        indexed={(r['provider_symbol'],r['sector_id'],r['profile_observation_id']):r for r in tables['sector_candidates']}
        seen=set()
        for d in decisions:
            key=(d['provider_symbol'],d['sector_id'],d['profile_observation_id'])
            release.require(key in indexed and key not in seen,'Invalid or duplicate sector review target')
            release.require(d['review_status'] in {'supported','rejected','needs_more_evidence'} and d['reason'].strip(),'Invalid review decision')
            seen.add(key);indexed[key]['review_status']=d['review_status'];indexed[key]['review_reason']=d['reason']
    release_id=digest({'version':'eodhd-curation-1.0','arrow':pa.__version__,'config':config,'inputs':inputs,
        'schemas':SCHEMAS,'decisions':decisions,'bucket':settings.s3_bucket,'prefix':settings.s3_prefix})
    root=Path(output_root)/release_id;root.mkdir(parents=True,exist_ok=True);prefix=config['curated_prefix']+'/'+release_id
    files={};ddl=[]
    for name,rows in tables.items():
        table=pa.Table.from_pylist(rows,schema=pa.schema([(field,release.ARROW_TYPES[kind]) for field,kind in SCHEMAS[name]]))
        relative=f'tables/{name}/part-00000.parquet';path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
        pq.write_table(table,path,compression='snappy',version='1.0')
        release.require(pq.ParquetFile(path).read().equals(table),'Parquet round-trip mismatch')
        body=path.read_bytes();location=f's3://{settings.s3_bucket}/{settings.s3_prefix}/{prefix}/tables/{name}/'
        files[name]={'path':relative,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'rows':len(rows),
            'location':location,'columns':SCHEMAS[name]}
        ddl.append(f"CREATE EXTERNAL TABLE {config['database']}.{name} ({', '.join(f'{field} {kind}' for field,kind in SCHEMAS[name])}) STORED AS PARQUET LOCATION '{location}';")
    db=config['database'];counts=Counter((r['sector_id'],r['review_status']) for r in tables['sector_candidates'])
    queries={'table_counts':' UNION ALL '.join(f"SELECT '{name}' AS table_name, count(*) AS records FROM {db}.{name}" for name in SCHEMAS)+' ORDER BY table_name',
        'sector_counts':f'SELECT sector_id, review_status, count(*) FROM {db}.sector_candidates GROUP BY sector_id, review_status ORDER BY sector_id, review_status',
        'profile_outcomes':f'SELECT profile_status, count(*) FROM {db}.company_profiles GROUP BY profile_status ORDER BY profile_status',
        'coverage':f'SELECT sum(inventory_records), sum(profiles_attempted), sum(profiles_not_collected) FROM {db}.exchange_coverage',
        'preview':f'SELECT provider_symbol, name, sector_id, review_status FROM {db}.sector_candidates ORDER BY provider_symbol, sector_id LIMIT 20'}
    outcomes=Counter(r['profile_status'] for r in tables['company_profiles'])
    expected={'table_counts':[[name,str(len(rows))] for name,rows in sorted(tables.items())],
        'sector_counts':[[sector,status,str(count)] for (sector,status),count in sorted(counts.items())],
        'profile_outcomes':[[status,str(count)] for status,count in sorted(outcomes.items())],
        'coverage':[[str(sum(r[k] for r in tables['exchange_coverage'])) for k in ('inventory_records','profiles_attempted','profiles_not_collected')]]}
    report={'curator_version':'eodhd-curation-1.0','catalog_owner':'eodhd','workgroup_description':'Optima EODHD research and review',
        'release_id':release_id,'release_prefix':prefix,'bucket':settings.s3_bucket,'s3_prefix':settings.s3_prefix,'config':config,
        'inputs':inputs,'universe_hash':universe_hash,'files':files,'expected_results':expected,'queries':queries,
        'status':'locally_validated','schema_version':'1.0',
        'semantics':'Current observed profiles; partial collection is explicit. Sector support is distinct from legal identity verification. No shared-universe promotion.'}
    (root/'release.json').write_bytes(canonical_json(report)+b'\n');(root/'tables.sql').write_text('\n\n'.join(ddl)+'\n')
    (root/'queries.sql').write_text('\n\n'.join(f'-- {name}\n{sql};' for name,sql in queries.items())+'\n')
    for name in ('sector_candidates','company_identity_review','exchange_coverage'):
        with (root/(name+'.csv')).open('w',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=[field for field,_ in SCHEMAS[name]])
            writer.writeheader();writer.writerows(tables[name])
    candidate_symbols={r['provider_symbol'] for r in tables['sector_candidates']}
    review_profiles=[r for r in tables['company_profiles'] if r['provider_symbol'] in candidate_symbols or
        r['provider_symbol'] in {'ISRG.US','MRNA.US','NVDA.US','QS.US'}]
    (root/'review_profiles.json').write_text(json.dumps(review_profiles,indent=2)+'\n')
    (root/'sector-review.json').write_text(json.dumps(decisions,indent=2)+'\n')
    print(json.dumps({'stage':'prepared','directory':str(root),'expected_results':expected}),flush=True)
    return root


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=('prepare','publish','deploy'))
    p.add_argument('--config',type=Path,default=ROOT/'config/eodhd-athena.json')
    p.add_argument('--storage-config',type=Path,default=ROOT/'config/collection-storage.s3.json')
    p.add_argument('--output-root',type=Path,default=ROOT/'eodhd-athena-build');p.add_argument('--release-dir',type=Path)
    p.add_argument('--update-existing',action='store_true',help='advance owned Glue tables to this immutable release')
    a=p.parse_args();settings=StorageSettings.load(a.storage_config);store=settings.store()
    if a.stage=='prepare':prepare(store,settings,load_json(a.config),a.output_root)
    else:
        release.require(a.release_dir is not None,'--release-dir required')
        if a.stage=='publish':release.publish(store,settings,a.release_dir)
        else:release.deploy(store,settings,a.release_dir,a.update_existing)


if __name__=='__main__':main()
