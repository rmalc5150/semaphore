#!/usr/bin/env python3
"""Publish a validated company-universe version and its discovery gaps to Athena."""
import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from collection_storage import StorageSettings, write_checked
from research_contract import ROOT, canonical_json, digest, load_json, validate_universe
import sec_athena_pilot as release


SCHEMAS={
 'universe_companies':[(k,'string') for k in ('company_id','canonical_name','entity_type','ownership_status','domicile_country','review_status','observed_at','universe_version')]+[('collection_enabled','boolean')],
 'universe_sectors':[(k,'string') for k in ('company_id','sector_id','classification_basis','review_status','valid_from','valid_to','observed_at','evidence_json')]+[('subsector_ids','array<string>')],
 'universe_listings':[(k,'string') for k in ('listing_id','company_id','exchange_mic','ticker','security_type','share_class','currency','valid_from','valid_to','review_status','observed_at','company_role','depositary_issuer_name','trading_from')],
 'universe_aliases':[(k,'string') for k in ('alias_id','company_id','alias','language','alias_type','valid_from','valid_to','review_status','observed_at','evidence_json')],
 'universe_identifiers':[(k,'string') for k in ('identifier_id','entity_id','system','value','valid_from','valid_to','review_status','observed_at','evidence_json')],
 'private_company_candidates':[(k,'string') for k in ('name','normalized_name','discovery_status','ownership_status','review_status','note','sources_json','references_json','listed_symbols_json','candidate_sectors_json')]+[('reference_count','bigint')],
 'universe_coverage':[(k,'string') for k in ('universe_version','generated_at','eodhd_release_id','review_release_id','coverage_json')]
}


def prepare(settings,config,universe_path,taxonomy_path,coverage_path,private_path,registry_path,verification_path,output_root,extra_artifacts=(),admission_path=None):
    universe=load_json(universe_path);taxonomy=load_json(taxonomy_path);errors,warnings=validate_universe(universe,taxonomy)
    release.require(not errors,'Universe validation failed: '+'; '.join(errors[:10]))
    coverage=load_json(coverage_path);private=load_json(private_path)
    release.require(coverage['universe_version']==universe['universe_version'],'Coverage version mismatch')
    schemas=dict(SCHEMAS)
    if admission_path:
        schemas['universe_admissions']=[(k,'string') for k in ('company_id','decision','decision_at','activation_at','policy_version','reviewer','basis_universe_version','basis_universe_hash','source_references_json','historical_activation_at')]
    tables={name:[] for name in schemas};version=universe['universe_version']
    if admission_path:
        ledger=load_json(admission_path);company_ids={c['company_id'] for c in universe['companies']}
        for item in ledger['decisions']:
            release.require(item['company_id'] in company_ids,'Admission references unknown company')
            release.require(item['activation_at'] and item['activation_at']>=ledger['created_at'],'Admission must not be backdated')
            tables['universe_admissions'].append({k:item.get(k) for k,_ in schemas['universe_admissions'] if k!='source_references_json'}|{'source_references_json':release.json_text(item['source_references'])})
        extra_artifacts=(*extra_artifacts,admission_path)

    for row in universe['companies']:
        tables['universe_companies'].append({k:row[k] for k in ('company_id','canonical_name','entity_type','ownership_status','domicile_country','review_status','observed_at','collection_enabled')}|{'universe_version':version})
        for sector in row['sectors']:
            tables['universe_sectors'].append({'company_id':row['company_id'],'sector_id':sector['sector_id'],'classification_basis':sector['classification_basis'],'review_status':sector['review_status'],'valid_from':sector['valid_from'],'valid_to':sector['valid_to'],'observed_at':sector['observed_at'],'evidence_json':release.json_text(sector['evidence']),'subsector_ids':sector['subsector_ids']})
    for row in universe['listings']:tables['universe_listings'].append({k:row.get(k) for k,_ in schemas['universe_listings']})
    for row in universe['company_aliases']:tables['universe_aliases'].append({k:row[k] for k,_ in schemas['universe_aliases'] if k!='evidence_json'}|{'evidence_json':release.json_text(row['evidence'])})
    for row in universe['external_identifiers']:tables['universe_identifiers'].append({k:row[k] for k,_ in schemas['universe_identifiers'] if k!='evidence_json'}|{'evidence_json':release.json_text(row['evidence'])})
    for row in private['candidates']:
        tables['private_company_candidates'].append({'name':row['name'],'normalized_name':row['normalized_name'],'discovery_status':row['discovery_status'],'ownership_status':row['ownership_status'],'review_status':row['review_status'],'note':row['note'],'sources_json':release.json_text(row['sources']),'references_json':release.json_text(row['references']),'listed_symbols_json':release.json_text(row['listed_symbol_candidates']),'candidate_sectors_json':release.json_text(row['candidate_sector_ids']),'reference_count':row['reference_count']})
    tables['universe_coverage'].append({'universe_version':version,'generated_at':coverage['generated_at'],'eodhd_release_id':coverage['eodhd_release_id'],'review_release_id':coverage['review_release_id'],'coverage_json':release.json_text(coverage)})
    artifacts=[]
    for path in (universe_path,coverage_path,private_path,registry_path,verification_path,*extra_artifacts):
        path=Path(path);body=path.read_bytes();artifacts.append({'name':path.name,'path':str(path),'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)})
    release.require(len({a['name'] for a in artifacts})==len(artifacts),'Duplicate artifact filename')
    release_id=digest({'version':'company-universe-athena-1.0','config':config,'schemas':schemas,'artifacts':[{k:v for k,v in a.items() if k!='path'} for a in artifacts]})
    root=Path(output_root)/release_id;root.mkdir(parents=True,exist_ok=True);prefix=config['curated_prefix']+'/'+release_id;files={};ddl=[]
    for name,rows in tables.items():
        table=pa.Table.from_pylist(rows,schema=pa.schema([(field,release.ARROW_TYPES[kind]) for field,kind in schemas[name]]))
        relative=f'tables/{name}/part-00000.parquet';path=root/relative;path.parent.mkdir(parents=True,exist_ok=True);pq.write_table(table,path,compression='snappy',version='1.0')
        release.require(pq.read_table(path).equals(table),'Parquet round-trip mismatch: '+name);body=path.read_bytes();location=f's3://{settings.s3_bucket}/{settings.s3_prefix}/{prefix}/tables/{name}/'
        files[name]={'path':relative,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'rows':len(rows),'location':location,'columns':schemas[name]}
        ddl.append(f"CREATE EXTERNAL TABLE {config['database']}.{name} ({', '.join(f'{f} {k}' for f,k in schemas[name])}) STORED AS PARQUET LOCATION '{location}';")
    db=config['database'];sector_counts=Counter((r['sector_id'],r['review_status']) for r in tables['universe_sectors']);private_counts=Counter(r['discovery_status'] for r in tables['private_company_candidates'])
    queries={'table_counts':' UNION ALL '.join(f"SELECT '{n}', count(*) FROM {db}.{n}" for n in schemas)+' ORDER BY 1',
      'company_status':f'SELECT review_status, count(*) FROM {db}.universe_companies GROUP BY review_status ORDER BY review_status',
      'sector_counts':f'SELECT sector_id, review_status, count(*) FROM {db}.universe_sectors GROUP BY sector_id, review_status ORDER BY sector_id, review_status',
      'private_counts':f'SELECT discovery_status, count(*) FROM {db}.private_company_candidates GROUP BY discovery_status ORDER BY discovery_status'}
    queries['receipt_links']=f"SELECT exchange_mic,ticker,company_id,security_type,depositary_issuer_name,valid_from,valid_to,trading_from FROM {db}.universe_listings WHERE company_role='underlying_issuer' ORDER BY exchange_mic,ticker"
    queries['listing_integrity']=f"SELECT count(*) FROM {db}.universe_listings l LEFT JOIN {db}.universe_companies c ON l.company_id=c.company_id WHERE c.company_id IS NULL OR (l.company_role='underlying_issuer' AND c.review_status<>'verified')"
    company_counts=Counter(r['review_status'] for r in tables['universe_companies'])
    expected={'table_counts':[[n,str(len(rows))] for n,rows in sorted(tables.items())],
      'company_status':[[k,str(v)] for k,v in sorted(company_counts.items())],
      'sector_counts':[[a,b,str(v)] for (a,b),v in sorted(sector_counts.items())],
      'private_counts':[[k,str(v)] for k,v in sorted(private_counts.items())]}
    expected['receipt_links']=[[r[k] for k in ('exchange_mic','ticker','company_id','security_type','depositary_issuer_name','valid_from','valid_to','trading_from')] for r in sorted(tables['universe_listings'],key=lambda r:(r['exchange_mic'],r['ticker'])) if r.get('company_role')=='underlying_issuer']
    expected['listing_integrity']=[['0']]
    report={'curator_version':'company-universe-athena-1.0','catalog_owner':'eodhd','workgroup_description':'Optima EODHD research and review','release_id':release_id,'release_prefix':prefix,'bucket':settings.s3_bucket,'s3_prefix':settings.s3_prefix,'config':config,'files':files,'artifacts':artifacts,'expected_results':expected,'queries':queries,'status':'locally_validated','schema_version':'1.0','universe_hash':digest(universe),'validation_warnings':warnings}
    (root/'release.json').write_bytes(canonical_json(report)+b'\n');(root/'tables.sql').write_text('\n\n'.join(ddl)+'\n');(root/'queries.sql').write_text('\n\n'.join(f'-- {n}\n{q};' for n,q in queries.items())+'\n')
    print(json.dumps({'stage':'prepared','directory':str(root),'expected_results':expected}));return root


def publish(store,settings,directory):
    root=Path(directory);report=load_json(root/'release.json')
    release.require(report['bucket']==settings.s3_bucket and report['s3_prefix']==settings.s3_prefix,'Release destination mismatch')
    for artifact in report['artifacts']:
        body=Path(artifact['path']).read_bytes();release.require(hashlib.sha256(body).hexdigest()==artifact['sha256'],'Artifact changed')
    for artifact in report['artifacts']:
        body=Path(artifact['path']).read_bytes();release.require(hashlib.sha256(body).hexdigest()==artifact['sha256'],'Artifact changed')
        key=report['release_prefix']+'/artifacts/'+artifact['name'];write_checked(store,key,body)
        release.require(release.get_bytes(store,key)==body,'Artifact read-back mismatch')
    release.publish(store,settings,root)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=('prepare','publish','deploy'));p.add_argument('--config',type=Path,default=ROOT/'config/company-universe-athena.json');p.add_argument('--storage-config',type=Path,default=ROOT/'config/collection-storage.s3.json');p.add_argument('--universe',type=Path,default=ROOT/'config/company-universe.v0.2.json');p.add_argument('--taxonomy',type=Path,default=ROOT/'config/sectors.v1.json');p.add_argument('--coverage',type=Path,default=ROOT/'reports/company-universe-v0.2-coverage.json');p.add_argument('--private-candidates',type=Path,default=ROOT/'reports/private-company-candidates-2026-09-22.json');p.add_argument('--id-registry',type=Path,default=ROOT/'config/company-id-registry.v1.json');p.add_argument('--registry-verification',type=Path,default=ROOT/'reports/company-registry-verification-2026-09-22.json');p.add_argument('--output-root',type=Path,default=ROOT/'company-universe-build');p.add_argument('--release-dir',type=Path);p.add_argument('--update-existing',action='store_true');a=p.parse_args();settings=StorageSettings.load(a.storage_config);store=settings.store();config=load_json(a.config)
    if a.stage=='prepare':prepare(settings,config,a.universe,a.taxonomy,a.coverage,a.private_candidates,a.id_registry,a.registry_verification,a.output_root)
    else:
        release.require(a.release_dir,'--release-dir required')
        if a.stage=='publish':publish(store,settings,a.release_dir)
        else:release.deploy(store,settings,a.release_dir,a.update_existing)


if __name__=='__main__':main()
