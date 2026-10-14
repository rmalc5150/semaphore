#!/usr/bin/env python3
"""Build a stable-ID reviewed universe and a separate unlisted-company queue."""
import argparse
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from uuid import uuid4

import pyarrow.parquet as pq

from research_contract import ROOT, load_json, validate_universe


def timestamp():return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def normalized(value):
    value=re.sub(r'[^\w]+',' ',(value or '').casefold(),flags=re.UNICODE)
    return ' '.join(value.split())
def new_id(prefix):return prefix+'_'+str(uuid4())


def load_table(root,release,name):
    return pq.read_table(Path(root)/release['files'][name]['path']).to_pylist()


def discover_private(regulatory_dir,eodhd_dir):
    regulatory_dir=Path(regulatory_dir);eodhd_dir=Path(eodhd_dir)
    reg=load_json(regulatory_dir/'release.json');market=load_json(eodhd_dir/'release.json')
    profiles=load_table(eodhd_dir,market,'company_profiles')
    listed=defaultdict(set)
    for row in profiles:
        for name in (row.get('name'),):
            if name:listed[normalized(name)].add(row['provider_symbol'])
    records=load_table(regulatory_dir,reg,'research_records');found={}
    noncompany=re.compile(r'\b(university|hospital|institute|foundation|association|government|ministry|council|medical center|health system|nhs|academy)\b',re.I)
    company_form=re.compile(r'\b(inc|incorporated|corp|corporation|llc|ltd|limited|plc|gmbh|ag|sa|s a|bv|nv|pharma|therapeutics|biosciences|biotech|laboratories|medicines)\b',re.I)
    for row in records:
        for name in row.get('company_names') or []:
            name=' '.join(name.split());key=normalized(name)
            if not key:continue
            item=found.setdefault(key,{'name':name,'normalized_name':key,'sources':set(),'references':[],
                'listed_symbol_candidates':set()})
            item['sources'].add(row['source']);item['references'].append({'record_id':row['record_id'],'source_url':row['source_url']})
            item['listed_symbol_candidates'].update(listed.get(key,set()))
    rows=[]
    for key,item in sorted(found.items()):
        name=item['name']
        if item['listed_symbol_candidates']:status='listed_name_match'
        elif noncompany.search(name):status='institutional_or_noncompany'
        elif company_form.search(name) or item['sources'] & {'fda_openfda','ema_ctis','uk_mhra'}:status='unlisted_company_candidate'
        else:status='ambiguous_organization_or_person'
        rows.append({**item,'sources':sorted(item['sources']),'references':item['references'][:20],
            'reference_count':len(item['references']),'listed_symbol_candidates':sorted(item['listed_symbol_candidates']),
            'discovery_status':status,'ownership_status':'unknown','candidate_sector_ids':['biotech'],
            'review_status':'pending','note':'Absence from the partial EODHD profile cohort does not prove private ownership. Legal identity, ownership and sector activity require review.'})
    counts={}
    for row in rows:counts[row['discovery_status']]=counts.get(row['discovery_status'],0)+1
    return {'version':'private-company-discovery-1.0','generated_at':timestamp(),
        'inputs':{'regulatory_release_id':reg['release_id'],'eodhd_release_id':market['release_id']},
        'coverage':'Organization names observed in the bounded regulatory Athena release, compared with the partial EODHD profile release. This is a discovery queue, not a complete private-company directory.',
        'counts':counts,'candidates':rows}


def subsectors(sector,text):
    text=(text or '').casefold();values=[]
    patterns={
      'biotech':[('therapeutics',r'therap|drug|medicine|vaccine|antibod'),('diagnostics',r'diagnostic|assay|test kit|sequenc'),('research_tools',r'research tool|laboratory|reagent'),('industrial_biotechnology',r'industrial biotech|agricultural biotech|fermentation')],
      'robotics':[('medical_robotics',r'surg|medical robot'),('industrial_robotics',r'industrial robot|cobot|factory automation'),('service_robotics',r'service robot|warehouse robot'),('autonomy_and_components',r'autonomous|machine vision|robotic component')],
      'semiconductors':[('chip_design',r'chip design|designs? (?:semiconductor|integrated circuit)'),('chip_manufacturing',r'fabricat|foundry|manufactur.{0,50}(?:semiconductor|chip|wafer)'),('semiconductor_equipment',r'photolith|semiconductor equipment'),('materials_and_packaging',r'packaging|wafer|semiconductor material')],
      'energy_storage':[('batteries',r'batter'),('supercapacitors',r'supercapacitor|ultracapacitor'),('thermal_storage',r'thermal storage|heat storage|molten salt storage'),('mechanical_storage',r'pumped hydro|flywheel storage|compressed air energy'),('hydrogen_storage',r'hydrogen storage|hydrogen tank')]
    }
    for value,pattern in patterns[sector]:
        if re.search(pattern,text):values.append(value)
    return values


def former_names(description):
    values=[]
    for pattern in (r'formerly known as ([A-Z][^.;]{2,100}?)(?: and changed|;|\.)',r'changed its name from ([A-Z][^.;]{2,100}?) to '):
        for match in re.finditer(pattern,description or ''):
            value=' '.join(match.group(1).split()).strip(' ,')
            if value:values.append(value)
    return sorted(set(values))


def listing_mic(inventory,profile):
    value=(inventory.get('exchange_mic') or '').strip()
    if re.fullmatch(r'[A-Z0-9]{4}',value):return value
    exchange=(profile.get('provider_exchange') or '').upper().strip()
    if exchange=='NASDAQ':return 'XNAS'
    if exchange=='NYSE':return 'XNYS'
    if exchange in {'PINK','OTCGREY','OTCQB','OTCQX'}:return 'OTCM'
    if exchange.startswith('CBOE'):return 'XCBO'
    return None


class UnionFind:
    def __init__(self,values):self.parent={v:v for v in values}
    def find(self,x):
        while self.parent[x]!=x:self.parent[x]=self.parent[self.parent[x]];x=self.parent[x]
        return x
    def union(self,a,b):
        a,b=self.find(a),self.find(b)
        if a!=b:self.parent[max(a,b)]=min(a,b)


def build_universe(parent_path,eodhd_dir,review_dir,registry_path,private_path,verification_path,version,taxonomy_path):
    parent=load_json(Path(parent_path));taxonomy=load_json(Path(taxonomy_path));registry_path=Path(registry_path)
    registry=load_json(registry_path) if registry_path.exists() else {'version':'1.0','company_keys':{},'listing_keys':{},'alias_keys':{},'identifier_keys':{}}
    eodhd_dir=Path(eodhd_dir);review_dir=Path(review_dir);market=load_json(eodhd_dir/'release.json');review=load_json(review_dir/'release.json')
    if review['inputs'][0]['parent_release_id']!=market['release_id']:raise ValueError('review release does not match EODHD release')
    profiles={r['provider_symbol']:r for r in load_table(eodhd_dir,market,'company_profiles')}
    listings={r['provider_symbol']:r for r in load_table(eodhd_dir,market,'listing_inventory')}
    company_reviews={r['provider_symbol']:r for r in load_table(review_dir,review,'company_reviews')}
    sector_rows=[r for r in load_table(review_dir,review,'sector_reviews') if r['review_status']=='supported']
    verification=load_json(Path(verification_path)) if verification_path else {'records':[]}
    if verification_path and (verification.get('eodhd_release_id')!=market['release_id'] or verification.get('review_release_id')!=review['release_id']):
        raise ValueError('registry verification does not match the reviewed release')
    registry_checks={r['provider_symbol']:r for r in verification['records']}
    selected=sorted({r['provider_symbol'] for r in sector_rows});uf=UnionFind(selected);tokens=defaultdict(list)
    for symbol in selected:
        row=profiles[symbol]
        for system in ('lei','cik'):
            value=(row.get(system) or '').strip()
            if value:tokens[(system,value)].append(symbol)
    for values in tokens.values():
        for other in values[1:]:uf.union(values[0],other)
    groups=defaultdict(list)
    for symbol in selected:groups[uf.find(symbol)].append(symbol)
    universe=deepcopy(parent);universe['universe_version']=version;universe['created_at']=timestamp();universe['purpose']='research'
    company_index={r['company_id']:r for r in universe['companies']}
    for row in universe['external_identifiers']:
        if row['entity_id'] in company_index and row['system'] in {'lei','cik'}:
            registry['company_keys'].setdefault(row['system']+':'+row['value'],row['entity_id'])
    alias_keys={(r['company_id'],normalized(r['alias']),r['alias_type']) for r in universe['company_aliases']}
    ext_keys={(r['entity_id'],r['system'],r['value']) for r in universe['external_identifiers']}
    listing_symbols=set()
    for row in universe['external_identifiers']:
        if row['system']=='eodhd_symbol':listing_symbols.add(row['value'])
    observed=universe['created_at'];new_companies=0;new_listings=0
    for root,symbols in sorted(groups.items()):
        keyset=set('symbol:'+s for s in symbols)
        for symbol in symbols:
            p=profiles[symbol]
            for system in ('lei','cik'):
                if p.get(system):keyset.add(system+':'+p[system].strip())
            try:candidates=json.loads(company_reviews[symbol].get('candidate_company_ids_json') or '[]')
            except ValueError:candidates=[]
            keyset.update('existing:'+c for c in candidates if c in company_index)
        ids={registry['company_keys'][k] for k in keyset if k in registry['company_keys']}
        ids.update(k.split(':',1)[1] for k in keyset if k.startswith('existing:'))
        if len(ids)>1:raise ValueError('conflicting stable company IDs for '+','.join(symbols))
        company_id=next(iter(ids),new_id('cmp'))
        for key in keyset:registry['company_keys'][key]=company_id
        primary=next((profiles[s] for s in symbols if profiles[s].get('primary_ticker')==s),profiles[sorted(symbols)[0]])
        verified_checks=[check for s in symbols for check in registry_checks.get(s,{}).get('checks',[]) if check['status']=='verified']
        registry_conflict=any(registry_checks.get(s,{}).get('identity_status') in {'conflict','name_mismatch'} for s in symbols)
        registry_name=next((check['registry_name'] for check in verified_checks if check.get('registry_name')),None)
        if verified_checks and not registry_conflict:
            first_check=verified_checks[0]
            evidence={'source':first_check['registry'],'reference':first_check['source_url'],'note':'Issuing registry corroborates the identifier and legal name.'}
        else:evidence={'source':'eodhd','reference':primary['source_url'],'note':'Current provider profile; legal identity remains subject to registry corroboration.'}
        conflicts=registry_conflict or any(company_reviews[s]['identity_assessment'] in {'identifier_conflict','identity_conflict','needs_registry_verification'} for s in symbols)
        has_legal=any(profiles[s].get('lei') or profiles[s].get('cik') for s in symbols)
        identity_verified=bool(verified_checks) and not conflicts
        company=company_index.get(company_id)
        if company is None:
            company={'company_id':company_id,'canonical_name':registry_name or primary['name'],'entity_type':'legal_entity' if (identity_verified or has_legal and not conflicts) else 'unresolved_organization',
                'ownership_status':'public','domicile_country':None,'collection_enabled':True,'sectors':[],
                'observed_at':observed,'review_status':'verified' if identity_verified else 'pending','evidence':[evidence]}
            universe['companies'].append(company);company_index[company_id]=company;new_companies+=1
        by_sector=defaultdict(list)
        for row in sector_rows:
            if row['provider_symbol'] in symbols:by_sector[row['sector_id']].append(row)
        for sector,rows in sorted(by_sector.items()):
            descriptions=' '.join(profiles[r['provider_symbol']].get('description') or '' for r in rows)
            membership={'sector_id':sector,'subsector_ids':subsectors(sector,descriptions),'classification_basis':'reviewed_current_business_description',
                'valid_from':None,'valid_to':None,'observed_at':observed,'review_status':'verified',
                'evidence':[{'source':'eodhd_review','reference':r['profile_observation_id'],'note':r['reason']} for r in rows]}
            current=next((x for x in company['sectors'] if x['sector_id']==sector and x['valid_to'] is None),None)
            if current:
                current.update(membership)
            else:company['sectors'].append(membership)
        names=set()
        for symbol in symbols:
            p=profiles[symbol];names.add(p['name']);names.update(former_names(p.get('description')))
        for name in sorted(names):
            alias_type='former_name' if any(name in former_names(profiles[s].get('description')) for s in symbols) else 'source_name'
            key=(company_id,normalized(name),alias_type)
            if key in alias_keys:continue
            regkey='|'.join(key);alias_id=registry['alias_keys'].setdefault(regkey,new_id('als'))
            universe['company_aliases'].append({'alias_id':alias_id,'company_id':company_id,'alias':name,'language':None,
                'alias_type':alias_type,'valid_from':None,'valid_to':None,'observed_at':observed,'review_status':'pending','evidence':[evidence]})
            alias_keys.add(key)
        for system in ('lei','cik'):
            for value in sorted({profiles[s].get(system) for s in symbols if profiles[s].get(system)}):
                key=(company_id,system,value)
                if key in ext_keys:continue
                idkey='|'.join(key);identifier_id=registry['identifier_keys'].setdefault(idkey,new_id('xid'))
                check=next((c for s in symbols for c in registry_checks.get(s,{}).get('checks',[]) if c['system']==system and c['value'].lstrip('0')==value.lstrip('0') and c['status']=='verified'),None)
                id_evidence={'source':check['registry'],'reference':check['source_url'],'note':'Issuing registry corroborates this identifier and legal name.'} if check else evidence
                universe['external_identifiers'].append({'identifier_id':identifier_id,'entity_id':company_id,'system':system,'value':value,
                    'valid_from':None,'valid_to':None,'observed_at':observed,'review_status':'verified' if check else 'pending','evidence':[id_evidence]});ext_keys.add(key)
        for symbol in symbols:
            if symbol in listing_symbols:continue
            row=listings.get(symbol);profile=profiles[symbol]
            mic=listing_mic(row or {},profile)
            if not row or not mic:continue
            listing_id=registry['listing_keys'].setdefault('eodhd:'+symbol,new_id('lst'))
            assessment=company_reviews[symbol]['identity_assessment'];name=(profile.get('name') or '')
            security='adr' if re.search(r'\bADR\b',name,re.I) else 'gdr' if re.search(r'\bGDR\b',name,re.I) else 'other' if assessment in {'security_wrapper_review','instrument_type_review'} else 'ordinary_share'
            ticker=symbol.rsplit('.',1)[0];currency=row.get('currency') or 'XXX'
            if not re.fullmatch(r'[A-Z]{3}',currency):currency='XXX'
            universe['listings'].append({'listing_id':listing_id,'company_id':company_id,'exchange_mic':mic,'ticker':ticker,
                'security_type':security,'share_class':None,'currency':currency,'valid_from':None,
                'valid_to':None,
                'observed_at':observed,'review_status':'pending','evidence':[evidence]});new_listings+=1
            for system,value in (('eodhd_symbol',symbol),('isin',profile.get('isin') or row.get('isin'))):
                if not value or (listing_id,system,value) in ext_keys:continue
                key=(listing_id,system,value);idkey='|'.join(key);identifier_id=registry['identifier_keys'].setdefault(idkey,new_id('xid'))
                universe['external_identifiers'].append({'identifier_id':identifier_id,'entity_id':listing_id,'system':system,'value':value,
                    'valid_from':None,'valid_to':None,'observed_at':observed,'review_status':'pending','evidence':[evidence]});ext_keys.add(key)
            listing_symbols.add(symbol)
    errors,warnings=validate_universe(universe,taxonomy)
    if errors:raise ValueError('invalid universe: '+'; '.join(errors[:20]))
    private=load_json(Path(private_path)) if private_path else None
    coverage={'version':'company-universe-coverage-1.0','generated_at':observed,'universe_version':version,
        'eodhd_release_id':market['release_id'],'review_release_id':review['release_id'],
        'supported_memberships':len(sector_rows),'supported_listing_symbols':len(selected),
        'modeled_company_entities':len({registry['company_keys']['symbol:'+s] for s in selected}),
        'new_company_entities':new_companies,'new_listings':new_listings,
        'universe_company_entities':len(universe['companies']),'universe_listings':len(universe['listings']),
        'universe_aliases':len(universe['company_aliases']),'universe_external_identifiers':len(universe['external_identifiers']),
        'verified_company_entities':sum(c['review_status']=='verified' for c in universe['companies']),
        'pending_company_entities':sum(c['review_status']=='pending' for c in universe['companies']),
        'promoted_sector_memberships':sum(s['review_status']=='verified' for c in universe['companies'] for s in c['sectors']),
        'profile_records':market['files']['company_profiles']['rows'],
        'inventory_records':market['files']['listing_inventory']['rows'],
        'profiles_not_collected':market['files']['listing_inventory']['rows']-sum(1 for r in listings.values() if r['profile_status']!='not_collected'),
        'identity_assessment_counts':{},'universe_validation_warnings':warnings,
        'registry_verification_counts':verification.get('counts',{}),
        'private_discovery_counts':private.get('counts') if private else {},
        'limitations':['EODHD covers listed securities and the profile scan remains partial.',
          'Sector review describes currently observed activity and does not establish historical membership dates.',
          'Pending CIK/LEI values require issuing-registry corroboration before identity is verified.',
          'Private discovery is bounded by collected regulatory records and does not prove ownership status or global completeness.']}
    for row in company_reviews.values():
        value=row['identity_assessment'];coverage['identity_assessment_counts'][value]=coverage['identity_assessment_counts'].get(value,0)+1
    registry['updated_at']=observed
    return universe,registry,coverage


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    d=sub.add_parser('discover-private');d.add_argument('--regulatory-release',type=Path,required=True);d.add_argument('--eodhd-release',type=Path,required=True);d.add_argument('--output',type=Path,required=True)
    b=sub.add_parser('build');b.add_argument('--parent-universe',type=Path,default=ROOT/'config/company-universe.v0.1.json');b.add_argument('--eodhd-release',type=Path,required=True);b.add_argument('--review-release',type=Path,required=True);b.add_argument('--registry',type=Path,default=ROOT/'config/company-id-registry.v1.json');b.add_argument('--private-candidates',type=Path);b.add_argument('--registry-verification',type=Path);b.add_argument('--version',default='0.2.0');b.add_argument('--taxonomy',type=Path,default=ROOT/'config/sectors.v1.json');b.add_argument('--output',type=Path,required=True);b.add_argument('--coverage-output',type=Path,required=True)
    a=p.parse_args()
    if a.command=='discover-private':
        value=discover_private(a.regulatory_release,a.eodhd_release);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n');print(json.dumps(value['counts']))
    else:
        universe,registry,coverage=build_universe(a.parent_universe,a.eodhd_release,a.review_release,a.registry,a.private_candidates,a.registry_verification,a.version,a.taxonomy)
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(universe,indent=2,ensure_ascii=False)+'\n')
        a.registry.parent.mkdir(parents=True,exist_ok=True);a.registry.write_text(json.dumps(registry,indent=2,sort_keys=True)+'\n')
        a.coverage_output.parent.mkdir(parents=True,exist_ok=True);a.coverage_output.write_text(json.dumps(coverage,indent=2)+'\n')
        print(json.dumps({k:v for k,v in coverage.items() if k not in {'limitations','universe_validation_warnings'}}))


if __name__=='__main__':main()
