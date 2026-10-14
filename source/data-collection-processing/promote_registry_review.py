#!/usr/bin/env python3
import json,copy,hashlib
from pathlib import Path
from datetime import datetime,timezone
from uuid import uuid4
from research_contract import validate_universe,digest
ROOT=Path(__file__).resolve().parent
p=ROOT/'config/company-universe.v0.5.json'
if p.exists():raise SystemExit('Refusing to overwrite universe version 0.5')
u=json.loads((ROOT/'config/company-universe.v0.4.json').read_text());stamp=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
rows=json.loads((ROOT/'reports/pending-company-registry-refresh.json').read_text())
selected={'HORIBA Ltd','Moderna','BioNTech','ASML','Lakefront Biotherapeutics NV'};updates=[]
for row in rows:
 if row['candidate_name'] not in selected or row['system']!='lei':continue
 assert row['status']=='source_verified_identity_adjudication_required' and row['entity_status']=='ACTIVE'
 c=next(c for c in u['companies'] if c['company_id']==row['company_id']);old=c['canonical_name']
 evidence={'source':'gleif','reference':row['source_url'],'note':'Reviewed current registry legal identity and known company name/alternative-language name; source sha256:'+row['sha256']+'. LEI registration status '+row['registration_status']+' is distinct from entity status ACTIVE.'}
 c.update(canonical_name=row['registry_name'],entity_type='legal_entity',review_status='verified',domicile_country=row['country']);c['evidence'].append(evidence)
 if not any(a['company_id']==c['company_id'] and a['alias']==old for a in u['company_aliases']):
  u['company_aliases'].append({'alias_id':'als_'+str(uuid4()),'company_id':c['company_id'],'alias':old,'language':None,'alias_type':'unclassified','valid_from':None,'valid_to':None,'observed_at':stamp,'review_status':'verified','evidence':[evidence]})
 for e in u['external_identifiers']:
  if e['entity_id']==c['company_id'] and e['system']=='lei' and e['value']==row['identifier']:e['review_status']='verified';e['evidence'].append(evidence)
 updates.append({'company_id':c['company_id'],'old_name':old,'registry_name':row['registry_name'],'decision':'verified legal identity; stable company and listing IDs retained'})
u.update(universe_version='0.5.0',created_at=stamp)
errors,warnings=validate_universe(u,json.loads((ROOT/'config/sectors.v1.json').read_text()));assert not errors,errors
p.write_text(json.dumps(u,indent=2,ensure_ascii=False)+'\n')
ledger=json.loads((ROOT/'config/company-admission-ledger.v1.json').read_text());ledger['version']='1.1';ledger['updated_at']=stamp
from company_admission import evaluate
for x in updates:
 c=next(c for c in u['companies'] if c['company_id']==x['company_id']);ids=[e for e in u['external_identifiers'] if e['entity_id']==c['company_id']]
 if evaluate(c,ids)['eligibility']=='eligible_for_activation':
  ledger['decisions'].append({'company_id':c['company_id'],'decision':'activate_detailed_tracking','decision_at':stamp,'activation_at':stamp,'policy_version':'1.0','reviewer':'Codex under user-authorized registry review','basis_universe_version':'0.5.0','basis_universe_hash':digest(u),'source_references':c['evidence'],'historical_activation_at':None,'note':'Registry-corroborated legal identity; activation is current, not retrospective.'})
(ROOT/'config/company-admission-ledger.v2.json').write_text(json.dumps(ledger,indent=2)+'\n')
coverage=json.loads((ROOT/'reports/company-universe-v0.4-coverage.json').read_text());coverage.update(generated_at=stamp,universe_version='0.5.0',universe_aliases=len(u['company_aliases']),verified_company_entities=sum(c['review_status']=='verified' for c in u['companies']),pending_company_entities=sum(c['review_status']=='pending' for c in u['companies']),new_company_entities=0)
(ROOT/'reports/company-universe-v0.5-coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
(ROOT/'reports/company-universe-v0.5-review.json').write_text(json.dumps({'reviewed_at':stamp,'updates':updates,'admission_count':len(ledger['decisions']),'warnings':warnings},indent=2)+'\n')
# Adjudicate the remainder rather than treating successful HTTP as verified identity.
for row in rows:
 name=row['candidate_name']
 if name in selected:row['adjudication']='identity_corroborated'
 elif name=='Nio Inc Class A ADR':row['adjudication']='receipt_underlying_mapping_required'
 elif name in {'Catalent Inc','Merck & Co. Inc'}:row['adjudication']='parent_subsidiary_identifier_mismatch'
 elif name=='COLOSSUS MINERALS':row['adjudication']='identifier_name_conflict'
 elif row.get('other_names') or row.get('former_names'):row['adjudication']='rename_or_entity_transition_requires_dated_sector_and_listing_review'
 else:row['adjudication']='further_identity_or_current_status_review_required'
(ROOT/'reports/company-registry-adjudications.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps({'promoted':len(updates),'admissions':len(ledger['decisions']),'verified':coverage['verified_company_entities'],'pending':coverage['pending_company_entities']}))
