#!/usr/bin/env python3
"""Evaluate admission eligibility without changing collection or inventing activation."""
import json,re,argparse
from collections import defaultdict,Counter
from pathlib import Path
from datetime import datetime,timezone
from research_contract import digest
ROOT=Path(__file__).resolve().parent

def evaluate(company,identifiers,conflicts=()):
 reasons=[]
 sector_ids=[s['sector_id'] for s in company.get('sectors',[]) if s.get('sector_id') in {'biotech','robotics','semiconductors','energy_storage'} and s.get('review_status')=='verified' and s.get('evidence')]
 if not sector_ids:reasons.append('sector_not_verified')
 entity_ids=[x for x in identifiers if x.get('review_status')=='verified' and x['system'] in {'lei','cik','sec_cik'}]
 identity=company.get('review_status')=='verified' and company.get('entity_type')=='legal_entity' and bool(company.get('evidence')) and bool(entity_ids)
 if not identity:reasons.append('legal_identity_not_verified')
 if conflicts:reasons.append('identifier_conflict')
 if company.get('review_status')=='rejected':reasons.append('rejected_identity')
 return {'eligibility':'eligible_for_activation' if not reasons else 'review_required','eligible_sector_ids':sector_ids,'reasons':reasons,'activation_at':None,'activation_status':'not_established_by_eligibility_evaluation'}

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--universe',default='config/company-universe.v0.5.json');args=parser.parse_args()
 path=ROOT/args.universe;u=json.loads(path.read_text());ids=defaultdict(list);tokens=defaultdict(set);aliases=defaultdict(set)
 for x in u['external_identifiers']:
  ids[x['entity_id']].append(x)
  if x['system'] in {'lei','cik','sec_cik'} and x.get('review_status')!='rejected':tokens[(x['system'].replace('sec_cik','cik'),x['value'].lstrip('0') if x['system'] in {'cik','sec_cik'} else x['value'])].add(x['entity_id'])
 conflicts=[{'system':k[0],'value':k[1],'entity_ids':sorted(v)} for k,v in tokens.items() if len(v)>1]
 for a in u['company_aliases']:
  aliases[re.sub(r'\W+',' ',a['alias'].casefold()).strip()].add(a['company_id'])
 collisions=[{'alias':a,'company_ids':sorted(v)} for a,v in aliases.items() if len(v)>1]
 decisions=[]
 for c in u['companies']:
  cf=[x for x in conflicts if c['company_id'] in x['entity_ids']]
  decisions.append({'company_id':c['company_id'],'name':c['canonical_name'],**evaluate(c,ids[c['company_id']],cf),'first_supported_observation_at':c.get('observed_at'),'observation_basis':'earliest known universe entry observation; not certified first external mention','discovery_sources':c.get('evidence',[]),'supporting_source_dates':None,'legacy_collection_enabled':c.get('collection_enabled'),'universe_version':u['universe_version'],'policy_version':'1.0'})
 state_path=ROOT/'config/company-admission-state.json'
 if state_path.exists():
  state=json.loads(state_path.read_text());ledger=json.loads((ROOT/state['ledger']).read_text())
  latest={d['company_id']:d for d in ledger['decisions']}
  for d in decisions:
   activation=latest.get(d['company_id'])
   if activation:
    d['activation_at']=activation['activation_at'];d['activation_status']='recorded_in_versioned_ledger'
    d['activation_ledger']=state['ledger']
 report={'generated_at':datetime.now(timezone.utc).isoformat(),'universe_file':str(path.relative_to(ROOT)),'universe_hash':digest(u),'policy':'config/company-admission-policy.json','counts':dict(Counter(x['eligibility'] for x in decisions)),'decisions':decisions,'identifier_collisions':conflicts,'alias_collisions':collisions,'note':'Full structural review of current universe. Eligibility does not activate or suspend collectors. Unresolved identities need registry/source review.'}
 (ROOT/'reports/company-admission-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'counts':report['counts'],'identifier_collisions':len(conflicts),'alias_collisions':len(collisions)}))
if __name__=='__main__':main()
