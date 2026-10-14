#!/usr/bin/env python3
"""Create an additive reviewed universe release, preserving prior files and IDs."""
import json,copy,hashlib
from pathlib import Path
from datetime import datetime,timezone
from uuid import uuid4
from collections import Counter
from research_contract import validate_universe,digest
ROOT=Path(__file__).resolve().parent

def main():
 out=ROOT/'config/company-universe.v0.4.json'
 if out.exists():raise SystemExit('Version 0.4 exists; do not overwrite a versioned universe')
 parent=ROOT/'config/company-universe.v0.3.json';before=hashlib.sha256(parent.read_bytes()).hexdigest();u=json.loads(parent.read_text());u=copy.deepcopy(u);stamp=datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
 captures={x['name']:x for x in json.loads((ROOT/'reports/company-source-review/captures.json').read_text()) if x['status']=='captured' and x['kind']=='official'}
 updates=[]
 def ev(name,note):
  c=captures[name]
  return {'source':'official_business_review','reference':c['url'],'note':note+'; observed source sha256:'+c['sha256']}
 display_ids={'9884004ARY4RODDUCT12':'Samsung Display','988400P37K91W0SABO95':'LG Display'}
 for ext in u['external_identifiers']:
  if ext['system']=='lei' and ext['value'] in display_ids:
   name=display_ids[ext['value']];c=next(x for x in u['companies'] if x['company_id']==ext['entity_id'])
   for sector in c['sectors']:
    if sector['sector_id']=='semiconductors':
     sector.update(review_status='rejected',classification_basis='display_panels_alone_outside_chip_taxonomy',observed_at=stamp)
     sector['evidence'].append(ev(name,'Display-panel business alone does not establish chip-sector activity under taxonomy 1.0; separate supported chip activity can be reconsidered'))
   updates.append({'company_id':c['company_id'],'name':name,'decision':'display-only semiconductor membership rejected; legal identity retained'})
 specs=[('insitro','biotech','therapeutics','Drug discovery platform supports biotech membership'),('Agility Robotics','robotics','industrial_robotics','Digit humanoid robot business supports robotics membership'),('Lightmatter','semiconductors','chip_design','Photonic chips/interconnect platform supports semiconductor membership'),('Antora Energy','energy_storage','thermal_storage','Thermal battery business supports energy-storage membership')]
 registry=json.loads((ROOT/'config/company-id-registry.v1.json').read_text())
 for name,sector,subsector,note in specs:
  c=captures[name];cid='cmp_'+str(uuid4());e=ev(name,note)
  u['companies'].append({'company_id':cid,'canonical_name':name,'entity_type':'unresolved_organization','ownership_status':'unknown','domicile_country':None,'collection_enabled':True,'sectors':[{'sector_id':sector,'subsector_ids':[subsector],'classification_basis':'reviewed_official_current_business','valid_from':None,'valid_to':None,'observed_at':stamp,'review_status':'verified','evidence':[e]}],'observed_at':stamp,'review_status':'pending','evidence':[ev(name,'Discovery from official company material; legal identity and ownership require registry corroboration. Collection is discovery, not detailed-tracking admission.')]})
  registry['company_keys']['official_domain:'+c['url'].split('/')[2]]=cid
  updates.append({'company_id':cid,'name':name,'decision':'new sector-supported discovery candidate; legal identity/ownership unresolved','sector':sector})
 form=next(c for c in u['companies'] if c['canonical_name']=='Form Energy')
 for sector in form['sectors']:
  if sector['sector_id']=='energy_storage':sector.update(review_status='verified',subsector_ids=['batteries'],classification_basis='reviewed_official_current_business',observed_at=stamp,evidence=sector['evidence']+[ev('Form Energy','Iron-air battery business supports energy-storage membership; product claims are not independent validation')])
 updates.append({'company_id':form['company_id'],'name':'Form Energy','decision':'energy-storage membership verified; legal identity unresolved'})
 u.update(universe_version='0.4.0',created_at=stamp)
 errors,warnings=validate_universe(u,json.loads((ROOT/'config/sectors.v1.json').read_text()))
 if errors:raise ValueError(errors)
 assert {x['company_id'] for x in json.loads(parent.read_text())['companies']}<={x['company_id'] for x in u['companies']}
 assert before==hashlib.sha256(parent.read_bytes()).hexdigest()
 out.write_text(json.dumps(u,indent=2,ensure_ascii=False)+'\n')
 (ROOT/'config/company-id-registry.v0.4.json').write_text(json.dumps(registry,indent=2)+'\n')
 private=json.loads((ROOT/'reports/private-company-candidates-2026-09-22.json').read_text())
 private['generated_at']=stamp;private['version']='private-company-discovery-1.1';private['coverage']='Prior bounded regulatory discovery plus official company candidates across all four sectors. Ownership remains unknown; absence of listing is not proof of private status.'
 for name,sector,subsector,note in specs:
  private['candidates'].append({'name':name,'normalized_name':name.lower(),'sources':['official_company'],'references':[{'source_url':captures[name]['url'],'sha256':captures[name]['sha256']}],'reference_count':1,'listed_symbol_candidates':[],'discovery_status':'unlisted_company_candidate','ownership_status':'unknown','candidate_sector_ids':[sector],'review_status':'pending','note':'Official business supports sector relevance; legal identity and private/listed status not verified.'})
 private['counts']=dict(Counter(x['discovery_status'] for x in private['candidates']))
 (ROOT/'reports/private-company-candidates-2026-09-25.json').write_text(json.dumps(private,indent=2)+'\n')
 coverage=json.loads((ROOT/'reports/company-universe-v0.2-coverage.json').read_text())
 coverage.update(generated_at=stamp,universe_version='0.4.0',universe_company_entities=len(u['companies']),universe_listings=len(u['listings']),universe_aliases=len(u['company_aliases']),universe_external_identifiers=len(u['external_identifiers']),verified_company_entities=sum(c['review_status']=='verified' for c in u['companies']),pending_company_entities=sum(c['review_status']=='pending' for c in u['companies']),new_company_entities=4,new_listings=0,private_discovery_counts=private['counts'],limitations=['Parent EODHD review cohort statistics retained as dated lineage; not all current profile inventory.','Four new official-business candidates; no unsupported legal-identity promotion.','Display-only semiconductor memberships rejected under existing taxonomy.','Historical windows retain original universe versions.'])
 (ROOT/'reports/company-universe-v0.4-coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
 review=json.loads((ROOT/'reports/company-admission-review.json').read_text());activations=[]
 for d in review['decisions']:
  if d['eligibility']=='eligible_for_activation':activations.append({'company_id':d['company_id'],'decision':'activate_detailed_tracking','decision_at':stamp,'activation_at':stamp,'policy_version':'1.0','reviewer':'Codex under user-authorized company review','basis_universe_version':'0.3.0','basis_universe_hash':review['universe_hash'],'source_references':d['discovery_sources'],'historical_activation_at':None,'note':'New explicit policy activation; does not backdate prior legacy discovery collection.'})
 ledger={'version':'1.0','created_at':stamp,'policy_hash':digest(json.loads((ROOT/'config/company-admission-policy.json').read_text())),'decisions':activations}
 lp=ROOT/'config/company-admission-ledger.v1.json'
 if lp.exists():raise ValueError('Admission ledger already exists; append changes instead of overwriting')
 lp.write_text(json.dumps(ledger,indent=2)+'\n')
 (ROOT/'reports/company-universe-v0.4-review.json').write_text(json.dumps({'reviewed_at':stamp,'parent_sha256':before,'new_universe_hash':digest(u),'updates':updates,'admissions':len(activations),'validation_warnings':warnings},indent=2)+'\n')
 print(json.dumps({'companies':len(u['companies']),'updates':updates,'new_admission_records':len(activations)}))
if __name__=='__main__':main()
