#!/usr/bin/env python3
"""Publish separate sector decisions and company identity screening results."""
import argparse
from collections import Counter
import csv
import hashlib
import json
import re
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from collection_storage import StorageSettings
from research_contract import ROOT, canonical_json, digest, load_json
import sec_athena_pilot as release

SCHEMAS={
 'sector_reviews':[(k,'string') for k in ('provider_symbol','name','sector_id','review_status','reason',
     'review_basis','reviewed_at','profile_observation_id','profile_observed_at','parent_release_id')]+[('evidence_urls','array<string>')],
 'company_reviews':[(k,'string') for k in ('provider_symbol','name','identity_assessment','reason','review_flags_json',
     'candidate_company_ids_json','reviewed_at','profile_observation_id','parent_release_id')]
}


def assess_identity(row,profile=None):
    flags=json.loads(row['review_flags_json'])
    if any(f.startswith('profile_') for f in flags):
        return 'profile_unavailable','Resolve provider profile availability before assigning a legal company.'
    if 'inventory_isin_mismatch' in flags:
        return 'identifier_conflict','Inventory and profile ISIN disagree; do not merge or promote this listing.'
    if re.search(r'\b(?:REIT|ETF|warrant|pref|pfd)\b|C/W',row['name'] or '',re.I):
        return 'instrument_type_review','Name indicates a fund, warrant or preferred security despite the common-stock inventory filter. Verify instrument and issuer before promotion.'
    if re.search(r'\b(?:ADR|CDR|CEDEAR)\b',row['name'] or '',re.I):
        return 'security_wrapper_review','Name indicates a depositary receipt; resolve the underlying issuer and listing separately.'
    if profile is not None and (not (profile.get('description') or '').strip() or
            'no profile data available' in profile['description'].lower()):
        return 'profile_content_missing','Profile response exists but lacks a substantive business description; sector and identity validation need additional evidence.'
    if any(f.startswith('shared_') for f in flags) or 'non_primary_listing' in flags:
        return 'cross_listing_review','Shared identifiers or a different primary ticker require listing/ADR and legal-entity reconciliation.'
    if 'no_legal_identifier' in flags:
        return 'legal_identifier_missing','No CIK or LEI supplied. Names and security identifiers alone do not verify a legal-company identity.'
    return 'provider_identifier_unverified','Provider legal identifier is present but has not been corroborated against the issuing registry.'


def prepare(parent_dir,decisions_path,output_root):
    parent_dir=Path(parent_dir);parent=load_json(parent_dir/'release.json')
    for info in parent['files'].values():
        body=(parent_dir/info['path']).read_bytes()
        release.require(hashlib.sha256(body).hexdigest()==info['sha256'],'Parent release changed')
    profiles={r['provider_symbol']:r for r in pq.read_table(parent_dir/parent['files']['company_profiles']['path']).to_pylist()}
    candidates=pq.read_table(parent_dir/parent['files']['sector_candidates']['path']).to_pylist()
    identities=pq.read_table(parent_dir/parent['files']['company_identity_review']['path']).to_pylist()
    raw_decisions=load_json(decisions_path)
    if isinstance(raw_decisions,dict):
        release.require(raw_decisions.get('parent_release_id')==parent['release_id'],'Review parent release mismatch')
    decisions=raw_decisions['sector_decisions'] if isinstance(raw_decisions,dict) else raw_decisions
    company_decisions=raw_decisions.get('company_decisions',[]) if isinstance(raw_decisions,dict) else []
    reviewed_at=raw_decisions.get('reviewed_at') if isinstance(raw_decisions,dict) else None
    decision_map={};tables={name:[] for name in SCHEMAS}
    for d in decisions:
        key=(d['provider_symbol'],d['sector_id'])
        release.require(key not in decision_map and d['provider_symbol'] in profiles,'Duplicate or unknown review symbol')
        release.require(d['sector_id'] in {'biotech','robotics','semiconductors','energy_storage'},'Invalid reviewed sector')
        release.require(d['profile_observation_id']==profiles[d['provider_symbol']]['observation_id'],'Stale review observation')
        release.require(d['review_status'] in {'supported','rejected','needs_more_evidence'} and d['reason'].strip() and d['review_basis'].strip(),'Incomplete review decision')
        decision_map[key]=d
    release.require(all((r['provider_symbol'],r['sector_id']) in decision_map for r in candidates),'Every candidate requires an explicit decision')
    for (symbol,sector),d in sorted(decision_map.items()):
        row=profiles[symbol]
        tables['sector_reviews'].append({'provider_symbol':symbol,'name':row['name'],'sector_id':sector,
            'review_status':d['review_status'],'reason':d['reason'],'review_basis':d['review_basis'],
            'reviewed_at':reviewed_at,
            'profile_observation_id':d['profile_observation_id'],'profile_observed_at':row['ingested_at'],
            'parent_release_id':parent['release_id'],'evidence_urls':d.get('evidence_urls',[])})
    overrides={}
    for d in company_decisions:
        symbol=d['provider_symbol']
        release.require(symbol in profiles and symbol not in overrides and d['profile_observation_id']==profiles[symbol]['observation_id'],
            'Unknown, duplicate or stale company review')
        release.require(d['identity_assessment'] in {'identity_conflict','instrument_type_review','needs_registry_verification'} and d['reason'].strip(),
            'Invalid company review')
        overrides[symbol]=d
    for row in identities:
        status,reason=assess_identity(row,profiles[row['provider_symbol']])
        if row['provider_symbol'] in overrides:
            decision=overrides[row['provider_symbol']];status,reason=decision['identity_assessment'],decision['reason']
        tables['company_reviews'].append({'provider_symbol':row['provider_symbol'],'name':row['name'],
            'identity_assessment':status,'reason':reason,'review_flags_json':row['review_flags_json'],
            'reviewed_at':reviewed_at,
            'candidate_company_ids_json':row['candidate_company_ids_json'],
            'profile_observation_id':row['profile_observation_id'],'parent_release_id':parent['release_id']})
    config={**parent['config'],'curated_prefix':'curated/eodhd_reviews/releases'}
    review_id=digest({'version':'eodhd-review-1.0','parent':parent['release_id'],'decisions':raw_decisions,'schemas':SCHEMAS})
    root=Path(output_root)/review_id;root.mkdir(parents=True,exist_ok=True);prefix=config['curated_prefix']+'/'+review_id
    files={};ddl=[]
    for name,rows in tables.items():
        table=pa.Table.from_pylist(rows,schema=pa.schema([(f,release.ARROW_TYPES[k]) for f,k in SCHEMAS[name]]))
        relative=f'tables/{name}/part-00000.parquet';path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
        pq.write_table(table,path,compression='snappy',version='1.0')
        release.require(pq.read_table(path).equals(table),'Review Parquet round-trip mismatch')
        body=path.read_bytes();location=f"s3://{parent['bucket']}/{parent['s3_prefix']}/{prefix}/tables/{name}/"
        files[name]={'path':relative,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'rows':len(rows),
            'location':location,'columns':SCHEMAS[name]}
        ddl.append(f"CREATE EXTERNAL TABLE {config['database']}.{name} ({', '.join(f'{f} {k}' for f,k in SCHEMAS[name])}) STORED AS PARQUET LOCATION '{location}';")
        with (root/(name+'.csv')).open('w',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=[f for f,_ in SCHEMAS[name]]);writer.writeheader();writer.writerows(rows)
    db=config['database'];sector_counts=Counter((r['sector_id'],r['review_status']) for r in tables['sector_reviews'])
    identity_counts=Counter(r['identity_assessment'] for r in tables['company_reviews'])
    queries={'table_counts':' UNION ALL '.join(f"SELECT '{n}' AS table_name, count(*) AS records FROM {db}.{n}" for n in SCHEMAS)+' ORDER BY table_name',
        'sector_review_counts':f'SELECT sector_id, review_status, count(*) FROM {db}.sector_reviews GROUP BY sector_id, review_status ORDER BY sector_id, review_status',
        'identity_review_counts':f'SELECT identity_assessment, count(*) FROM {db}.company_reviews GROUP BY identity_assessment ORDER BY identity_assessment',
        'review_join':f'SELECT count(*) FROM {db}.sector_reviews r JOIN {db}.company_profiles p ON r.provider_symbol=p.provider_symbol AND r.profile_observation_id=p.observation_id'}
    expected={'table_counts':[[n,str(len(rows))] for n,rows in sorted(tables.items())],
        'sector_review_counts':[[s,status,str(c)] for (s,status),c in sorted(sector_counts.items())],
        'identity_review_counts':[[s,str(c)] for s,c in sorted(identity_counts.items())],
        'review_join':[[str(len(tables['sector_reviews']))]]}
    report={'curator_version':'eodhd-review-1.0','catalog_owner':'eodhd','workgroup_description':parent['workgroup_description'],
        'release_id':review_id,'release_prefix':prefix,'bucket':parent['bucket'],'s3_prefix':parent['s3_prefix'],'config':config,
        'files':files,'inputs':[{'parent_release_id':parent['release_id']}],'universe_hash':parent['universe_hash'],
        'expected_results':expected,'queries':queries,'status':'locally_validated','schema_version':'1.0',
        'sector_decisions':decisions,'company_decisions':company_decisions,
        'semantics':'Sector review of observed business descriptions and cited sources; automated identity screening does not verify legal entities or approve universe promotion.'}
    (root/'release.json').write_bytes(canonical_json(report)+b'\n');(root/'tables.sql').write_text('\n\n'.join(ddl)+'\n')
    (root/'queries.sql').write_text('\n\n'.join(f'-- {n}\n{sql};' for n,sql in queries.items())+'\n')
    print(json.dumps({'stage':'review_prepared','directory':str(root),'expected_results':expected}),flush=True)
    return root


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=('prepare','publish','deploy'))
    p.add_argument('--parent-dir',type=Path);p.add_argument('--decisions',type=Path)
    p.add_argument('--release-dir',type=Path);p.add_argument('--output-root',type=Path,default=ROOT/'eodhd-review-build')
    p.add_argument('--update-existing',action='store_true',help='advance owned Glue tables to this immutable release')
    p.add_argument('--storage-config',type=Path,default=ROOT/'config/collection-storage.s3.json')
    a=p.parse_args()
    if a.stage=='prepare':
        release.require(a.parent_dir and a.decisions,'--parent-dir and --decisions required')
        prepare(a.parent_dir,a.decisions,a.output_root)
    else:
        release.require(a.release_dir is not None,'--release-dir required')
        settings=StorageSettings.load(a.storage_config)
        if a.stage=='publish':release.publish(settings.store(),settings,a.release_dir)
        else:release.deploy(settings.store(),settings,a.release_dir,a.update_existing)


if __name__=='__main__':main()
