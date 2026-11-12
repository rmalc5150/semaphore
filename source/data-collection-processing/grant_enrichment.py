"""Evidence-based NIH award lifecycle and ROR identity normalization (S36/S68)."""
import re
import unicodedata
from research_contract import digest

VERSION='grant-lifecycle-evidence-v1'
AWARD_TYPES={'1':'new_application','2':'competing_renewal','3':'supplemental_support',
 '4':'extension_or_fast_track_continuation','4C':'competing_extension','4N':'noncompeting_extension',
 '5':'noncompeting_continuation','6':'successor_in_interest','7':'grantee_institution_change',
 '8':'administering_institute_transfer','9':'competing_awarding_institute_change'}


def norm(value):
    return ' '.join(re.findall(r'\w+',unicodedata.normalize('NFKC',str(value or '')).casefold()))


def institution(r):
    return {k:r.get(k) for k in ('id','names','external_ids','locations','links','domains','relationships','status','types','established','admin')}


def institution_match(org,candidates):
    """Name plus geographic corroboration; ambiguous and conflicting identities stay pending."""
    assessments=[]
    for r in candidates:
        names=[n['value'] for n in r.get('names',[]) if 'acronym' not in n.get('types',[])]
        exact=norm(org.get('org_name')) in [norm(n) for n in names]
        locations=[l.get('geonames_details',{}) for l in r.get('locations',[])]
        country=org.get('country_code') or ('US' if org.get('org_fips')=='US' else None)
        country_name=org.get('org_country') or org.get('country')
        city=org.get('org_city') or org.get('city')
        country_ok=bool(any((country and norm(l.get('country_code'))==norm(country)) or (country_name and norm(l.get('country_name'))==norm(country_name)) for l in locations))
        city_ok=bool(city and any(norm(l.get('name'))==norm(city) for l in locations))
        country_conflict=bool((country or country_name) and locations and not country_ok)
        state=org.get('org_state')
        state_conflict=bool(country=='US' and state and locations and not any(str(l.get('country_subdivision_code') or '').split('-')[-1]==state for l in locations) and country_ok)
        assessments.append({'ror_id':r['id'],'exact_name_or_alias':exact,'country_agrees':country_ok,
          'city_agrees':city_ok,'geographic_conflict':country_conflict or state_conflict,
          'eligible':exact and country_ok and city_ok and not (country_conflict or state_conflict) and r.get('status')=='active'})
    eligible=[a for a in assessments if a['eligible']]
    return {'status':'confirmed_name_and_location' if len(eligible)==1 else 'unresolved_no_candidates' if not candidates else 'review_required',
      'ror_id':eligible[0]['ror_id'] if len(eligible)==1 else None,
      'confidence':'high' if len(eligible)==1 else 'unverified','candidate_assessments':assessments,
      'historical_identity_status':'current_registry_identity_not_historical_affiliation',
      'relationship_rule':'parent_and_related_institutions_are_distinct; no_automatic_grant_rollup'}


def grant_facts(p):
    keys=('appl_id','core_project_num','project_num','fiscal_year','project_title','abstract_text','phr_text',
      'organization','principal_investigators','program_officers','agency_code','agency_ic_admin','agency_ic_fundings',
      'activity_code','funding_mechanism','opportunity_number','award_type','project_num_split','award_notice_date',
      'budget_start','budget_end','project_start_date','project_end_date','award_amount','direct_cost_amt','indirect_cost_amt',
      'subproject_id','is_active','date_added','project_detail_url')
    result={k:p.get(k) for k in keys}
    code=str(p.get('award_type') or (p.get('project_num_split') or {}).get('appl_type_code') or '')
    result['explicit_trial_ids']=sorted(set(re.findall(r'\bNCT\d{8}\b',' '.join(str(p.get(k) or '') for k in ('project_title','abstract_text','phr_text')),re.I)))
    result['trial_link_status']='explicit_text_identifier_requires_registry_validation' if result['explicit_trial_ids'] else 'no_explicit_identifier_in_project_text'
    result.update(lifecycle_stage=AWARD_TYPES.get(code,'unclassified_source_application_type'),
      lifecycle_date=p.get('award_notice_date'),lifecycle_date_basis='award_notice_date' if p.get('award_notice_date') else 'unknown',
      funding_scope='source_reported_application_fiscal_year; not_disbursement_or_lifetime_total',
      aggregation_status='do_not_sum_parent_and_subprojects_or_multiple_snapshot_versions',
      sbir_sttr_candidate=p.get('activity_code') in {'R41','R42','R43','R44','U43','U44','UT1','UT2'},
      funding_instrument='intramural' if str(p.get('activity_code') or '').startswith('Z') else 'research_contract' if str(p.get('activity_code') or '').startswith('N') else 'financial_assistance_or_other_source_mechanism',
      event_eligible=bool(p.get('award_notice_date')) and p.get('subproject_id') is None and code in AWARD_TYPES,
      event_status='candidate_requires_entity_and_temporal_review; no_production_event_emitted')
    return result


def entity_connections(p,match,directory):
    """Confirm identifier bindings only; names/text mentions remain candidates."""
    org=p.get('organization') or {}; evidence_fields=['organization.org_name']
    identifiers={'ror':match.get('ror_id'),'nih_org_ipf':str(org.get('org_ipf_code') or ''),'uei':org.get('primary_uei')}
    candidates=[]
    for company in directory.get('companies',[]):
        if company.get('archived_at') or company.get('review_status')!='verified':continue
        hits=[i for i in directory.get('identifiers',[]) if i['company_id']==company['company_id'] and i.get('review_status')=='verified'
          and identifiers.get(i['namespace']) and i['identifier_value']==identifiers[i['namespace']]]
        if hits or norm(company['canonical_name'])==norm(org.get('org_name')):
            candidates.append({'company_id':company['company_id'],'role':'grant_recipient','status':'confirmed_identifier' if hits else 'name_candidate_review_required',
              'identifiers':hits,'source_fields':evidence_fields})
    if len({c['company_id'] for c in candidates if c['status']=='confirmed_identifier'})>1:
        for c in candidates:c['status']='conflicting_identifiers_review_required'
    people=[]
    for pi in p.get('principal_investigators') or []:
        for person in directory.get('people',[]):
            if person.get('archived_at') or person.get('review_status')!='verified':continue
            hits=[i for i in directory.get('person_identifiers',[]) if i['person_id']==person['person_id'] and i.get('review_status')=='verified'
              and i['namespace']=='nih_pi_profile' and str(i['identifier_value'])==str(pi.get('profile_id'))]
            if hits or norm(person['canonical_name'])==norm(pi.get('full_name')):
                people.append({'person_id':person['person_id'],'profile_id':pi.get('profile_id'),
                  'status':'confirmed_identifier' if hits else 'name_candidate_review_required','role':'principal_investigator',
                  'source_fields':['principal_investigators'],'employment_claim':False})
    products=[];texts={k:p.get(k) or '' for k in ('project_title','abstract_text','phr_text')}
    for product in directory.get('products',[]):
        if product.get('archived_at') or product.get('review_status')!='verified':continue
        names=[product['canonical_name']]+[a['alias'] for a in directory.get('product_aliases',[]) if a['product_id']==product['product_id'] and a.get('review_status')=='verified']
        fields=[k for k,v in texts.items() if any(len(norm(n))>=5 and (' '+norm(n)+' ') in (' '+norm(v)+' ') for n in names)]
        if fields:products.append({'product_id':product['product_id'],'status':'explicit_name_mention_candidate_review_required',
          'source_fields':fields,'funding_allocation_claim':False})
    return {'companies':candidates,'people':people,'products':products,
      'mapping_status':'unmatched_directory_empty' if not any(directory.get(k) for k in ('companies','people','products')) else 'identifier_bindings_and_review_candidates',
      'rule':'no_company_ownership_employment_or_product_funding_inferred_from_affiliation_topic_or_parent_relationship'}


def lifecycle_summary(projects):
    unique={str(p['appl_id'])+':'+str(p.get('fiscal_year'))+':'+str(p.get('subproject_id')):p for p in projects}
    rows=sorted(unique.values(),key=lambda p:(p.get('award_notice_date') or '',str(p['appl_id'])))
    return {'applications':[{'appl_id':p['appl_id'],'fiscal_year':p.get('fiscal_year'),
      'project_num':p.get('project_num'),'subproject_id':p.get('subproject_id'),
      'award_notice_date':p.get('award_notice_date'),'organization':p.get('organization'),
      'stage':grant_facts(p)['lifecycle_stage'],'award_amount':p.get('award_amount')} for p in rows],
      'award_total':None,'note':'No inferred termination, completion, disbursement, or lifetime funding sum. Missing years remain unknown.'}
