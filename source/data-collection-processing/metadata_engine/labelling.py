"""Pure, deterministic common-envelope labelling.

Source adapters supply only source-specific identity and field mappings.  This
module deliberately performs no network, database, or S3 operation, making its
results testable and safe to replay for historical data.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


REQUIRED = ("source", "dataset", "source_record_id", "payload", "ingested_at")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def require_timestamp(value: str, field: str) -> None:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(field + " must include a UTC offset")


def label_observation(record: dict[str, Any], contract: dict[str, Any], *, labelled_at: str | None = None) -> dict[str, Any]:
    """Return a labelled source observation without modifying ``record``.

    The source record may already use the existing collected-record envelope.
    ``raw_s3_uri`` and ``raw_sha256`` are mandatory evidence links; adapters do
    not invent them.  Unknown availability remains explicit.
    """
    for key in REQUIRED:
        if key not in record:
            raise ValueError("missing collected-record field: " + key)
    if record["source"] != contract["source_key"]:
        raise ValueError("source does not match contract")
    if not record.get("raw_s3_uri") or not record.get("raw_sha256"):
        raise ValueError("raw S3 URI and SHA-256 are required")
    raw_artifacts = record.get("raw_artifacts")
    requirements = contract.get("raw_requirements", {})
    if record.get("raw_completeness_status") != "complete":
        raise ValueError("raw source evidence is not complete")
    if not isinstance(raw_artifacts, list) or not raw_artifacts:
        raise ValueError("complete raw source evidence requires raw_artifacts")
    kinds = set()
    for artifact in raw_artifacts:
        if not isinstance(artifact, dict) or not artifact.get("artifact_kind") or not artifact.get("s3_uri") or not artifact.get("sha256"):
            raise ValueError("each raw artifact requires kind, S3 URI, and SHA-256")
        if artifact.get("origin") != "first_party_source":
            raise ValueError("raw artifact must originate from the first-party source")
        kinds.add(artifact["artifact_kind"])
    missing_kinds = set(requirements.get("required_artifact_kinds", ())) - kinds
    if missing_kinds:
        raise ValueError("required raw artifact kinds missing: " + ", ".join(sorted(missing_kinds)))
    forbidden = set(requirements.get("forbidden_shortcuts", ()))
    if forbidden & set(record.get("raw_limitations", ())):
        raise ValueError("source record relies on forbidden raw-data shortcut")
    require_timestamp(record["ingested_at"], "ingested_at")
    if labelled_at is None:
        labelled_at = datetime.now(timezone.utc).isoformat()
    require_timestamp(labelled_at, "labelled_at")
    payload = deepcopy(record["payload"])
    # Preserve the existing research-contract namespace across labelling.
    identity = ["record-v1", record["source"], record["dataset"], str(record["source_record_id"])]
    record_id = "rec_" + digest(identity)
    if record.get("record_id", record_id) != record_id:
        raise ValueError("collected-record identity mismatch")
    availability = record.get("available_at")
    if availability is not None and not isinstance(availability, dict):
        raise ValueError("available_at must be a structured temporal value or null")
    base = {
        "record_id": record_id,
        "source_key": record["source"],
        "dataset": record["dataset"],
        "record_kind": contract["record_kind"],
        "source_record_id": str(record["source_record_id"]),
        "source_record_id_basis": record.get("source_record_id_basis", contract.get("source_record_id_basis", "provider")),
        "raw_s3_uri": record["raw_s3_uri"],
        "raw_sha256": record["raw_sha256"],
        "raw_artifacts": deepcopy(raw_artifacts),
        "raw_completeness_status": "complete",
        "raw_requirements_version": requirements.get("version"),
        "original_url": record.get("source_url"),
        "source_document_id": record.get("source_document_id"),
        "evidence_locator": record.get("evidence_locator"),
        "event_at": record.get("event_at"),
        "source_published_at": record.get("source_published_at"),
        "available_at": availability,
        "availability_basis": record.get("availability_basis", "unknown"),
        "ingested_at": record["ingested_at"],
        "contract_version": contract["contract_version"],
        "adapter": contract["adapter"],
        "adapter_version": contract["adapter_version"],
        "parser_version": record.get("parser_version"),
        "license_policy_id": contract["license_policy_id"],
        "entity_match_status": "unresolved",
        "quality_status": "accepted",
        "quality_flags": [],
        "payload": payload,
        "labelled_at": labelled_at,
    }
    from regional_source_review import PUBLIC_KEYS
    if record['source']in PUBLIC_KEYS and record['dataset']=='public_documents':base['quality_flags'].append('original_file_metadata; numerical_extraction_and_full_history_not_asserted')
    if record['source']in ('cninfo_mainland_china_company_disclosures','south_korea_fss_opendart'):base['quality_flags'].append('native_index_and_original_document; XBRL_extraction_not_asserted')
    if record['source']in ('wto_quantitative_restrictions_api','wto_eping_sps_tbt_notifications','epo_ops_patent_legal_events','ember_electricity_demand_and_generation'):
        info=next(a['validation']for a in raw_artifacts if isinstance(a.get('validation'),dict))
        base.update(record_kind=info['record_type'],completeness_scope=info['scope'])
        base['quality_flags'].append('declared_query_scope_not_full_history_or_verified_legal_effect')
    if record['source']in ('imf_portwatch_shipping_activity','unido_iip_and_indstat'):
        info=next(a['validation']for a in raw_artifacts if isinstance(a.get('validation'),dict))
        base.update(record_kind=info['record_type'],completeness_scope=info['scope'])
        base['quality_flags'].append('current_provider_estimates_or_statistics_not_original_historical_vintages')
        if record['source']=='unido_iip_and_indstat' and 'v' not in record['payload']['data']['native_observation']:
            base['quality_flags'].append('provider_footnote_only_cell_no_numeric_value')
    if record['source']in ('arxiv','england_nhsbsa_prescribing_data','ucdp_organized_violence','semi_worldwide_equipment_billings','sia_wsts_public_semiconductor_sales','international_federation_of_robotics_world_robotics','iea_pvps_solar_deployment_reports','germany_g_ba_drug_benefit_assessments','france_has_medicine_assessment_opinions','canada_cda_amc_cadth_reimbursement_reviews','france_assurance_maladie_open_medic'):
        info=next(a['validation']for a in raw_artifacts if isinstance(a.get('validation'),dict))
        base.update(record_kind=info['record_type'],completeness_scope=info['scope'])
        base['quality_flags'].append('declared_record_or_file_scope_not_full_historical_completion')
        if record['source']=='arxiv':base['quality_flags'].append('citation_and_abstract_metadata_only; article_full_text_not_collected')
    if record['source']=='sam_gov_opportunities':
        info=next(a['validation']for a in raw_artifacts if isinstance(a.get('validation'),dict))
        base.update(record_kind=info['record_type'],completeness_scope=info['scope'])
        base['quality_flags'].append('notice_metadata_not_full_description_or_attachments')
    if record['source']=='nmpa_trials' and record['dataset']=='registry_inventory':
        base.update(record_kind='registry_inventory',completeness_scope='original_registry_inventory_row')
        base['quality_flags'].append('registry_inventory_not_trial_detail')
    if record['source']=='nmpa_trials' and payload.get('record_type')=='clinical_trial' and payload.get('data',{}).get('firstPublicDisclosureDate')is None:
        base['quality_flags'].append('provider_first_disclosure_date_not_supplied')
    if record['source'] in ('nih_reporter','usa_spending','uspto_assignment_histories'):
        from metadata_engine.grants_awards import context
        payload['source_context']=context(record)
        base['quality_flags'].append('source_scope_not_full_documents_or_verified_legal_entity')
    if record['source'] in ('uspto_odp','google_patents_bigquery'):
        base['record_kind']={'patent_records':'patent_bibliography','patent_assignment_records':'patent_assignment_chain','patent_office_actions':'office_action_document','patent_petition_decisions':'petition_decision_document'}[record['dataset']]
        if record['dataset'] in ('patent_records','patent_assignment_records'):base['quality_flags'].append('bibliography_or_assignment_metadata_not_patent_full_text')
        base['quality_flags'].append('historical_vintage_and_legal_title_not_established')
    if record['source']=='ted_notices':
        chunk=payload['data'].get('record_type')=='notice_content_chunk'
        base['record_kind']='notice_content_chunk' if chunk else 'procurement_notice'
        if chunk:base['quality_flags'].append('content_chunk_not_additional_notice_or_award')
    if record['source'] in ('nist_robotics_methods','nist_robotics_documents'):
        document=next(a['validation'].pop('parsed_document') for a in base['raw_artifacts'] if 'parsed_document' in a.get('validation',{}))
        if payload['data'].get('document_kind')=='official source discovery page':payload['original_collector_data']=payload['data']
        payload['data']=document
        base['record_kind']='source_discovery' if document['kind']=='discovery' else 'nist_original_document'
        base['quality_flags'].append('document_text_not_inferred_robot_performance_measurements')
    if record['source'] in ('fda_dd_compliance_actions', 'fda_dd_import_refusals', 'fda_dd_inspections_citations', 'fda_ires_recalls', 'fda_product_codes'):
        from metadata_engine.fda_authenticated import context
        payload['fda_context']=context(record)
        base['quality_flags'].append('current_api_records_not_historical_vintages_or_original_documents')
        if record['source']=='fda_product_codes':base['quality_flags'].append('industry_reference_not_full_product_code_hierarchy')
        if record['source']=='fda_ires_recalls' and payload['fda_context']['legacy_selected_columns']:base['quality_flags'].append('legacy_selected_recall_columns')
    if record['source']=='cms_payments_catalog':
        base['quality_flags'].append('catalog_metadata_not_individual_payment_or_spending_rows')
    if record['source']=='un_comtrade' or record['source'].startswith('doe_storage_'):
        info=next(a['validation'] for a in base['raw_artifacts'] if isinstance(a.get('validation'),dict)
                  and a['validation'].get('provider') in ('UN Comtrade','DOE storage originals'))
        document=info.pop('parsed_document',None)
        base.update(record_kind=info['record_type'],completeness_scope=info['scope'])
        if document is not None:
            payload['original_collector_data']=payload['data'];payload['data']=document
        base['quality_flags'].append('configured_source_scope_not_exhaustive_history')
        if record['source'].startswith('doe_storage_'):
            base['quality_flags'].append('source_statement_not_verified_performance_or_award_payment')
            if info['extraction_limits']:base['quality_flags'].append('extraction_limits_preserved')
    if record['source'] in ('federal_register','federal_register_documents'):
        info=next(a['validation']for a in raw_artifacts if isinstance(a.get('validation'),dict)
                  and a['validation'].get('provider')in ('Federal Register API','Federal Register full notice'))
        base.update(record_kind=info['record_type'],completeness_scope=info['scope'])
        payload['federal_register_context']=deepcopy(info)
        base['quality_flags'].append('current_law_and_product_applicability_unreviewed')
        if record['source']=='federal_register':base['quality_flags'].append('listing_metadata_not_full_notice')
        if payload.get('data',{}).get('enrichment',{}).get('extraction_storage'):
            base['quality_flags'].append('full_extraction_in_linked_s3_artifact')
    if record['source'] in ('mlperf_results','cpsc_recalls'):
        info=next(a['validation']for a in raw_artifacts if isinstance(a.get('validation'),dict)
                  and a['validation'].get('provider')in ('MLCommons MLPerf','CPSC recalls'))
        base.update(record_kind=info['record_type'],completeness_scope=info['scope'])
        if info['record_type']=='benchmark_artifact_inventory':
            base['quality_flags'].append('artifact_inventory_not_benchmark_result_or_file_contents')
        elif info['record_type']=='benchmark_supporting_artifact':
            base['quality_flags'].append('supporting_file_not_independent_benchmark_result')
    if record['source']=='cms_coverage':
        base['quality_flags'].append('inventory_row_not_policy_body')
    if record['source']=='cms_coverage_documents':
        from metadata_engine.cms_coverage import enrichment
        payload['cms_context']=enrichment(payload['data'])
        base['quality_flags'].append('effective_date_not_historical_api_vintage')
    if record['source']=='crossref_proceedings':
        base.update(completeness_scope='complete_crossref_doi_metadata_not_full_paper')
        base['quality_flags'].append('proceedings_full_text_not_collected')
        if not payload['data'].get('abstract'):base['quality_flags'].append('abstract_not_deposited_in_returned_metadata')
    if record['source']=='europe_pmc_fulltext':
        from raw_parsers.epmc_fulltext import enrichment
        data=payload['data'];data['enrichment']=enrichment(data['article_xml'],str(record['source_record_id']))
        base.update(completeness_scope=data['enrichment']['completeness_scope'],parser_version=data['enrichment']['version'])
        base['quality_flags'].append('supplements_and_historical_vintages_not_established')
    if contract['adapter'] == 'research_feed':
        base['completeness_scope'] = contract['completeness_scope']
        base['quality_flags'].append('provider_metadata_scope')
    if contract['adapter'] == 'market_archive_original':
        base['completeness_scope'] = contract['completeness_scope']
        base['quality_flags'].append('original_release_publication_date_unverified')
    if contract['adapter'] == 'sedi_issuer_events':
        base['completeness_scope'] = contract['completeness_scope']
        base['quality_flags'].append('public_release_date_unverified')
    if record['source']=='pubmed_abstracts':
        from raw_parsers.pubmed_enrichment import enrich
        data=payload['data']
        if 'enrichment'not in data:
            data['enrichment']=enrich(data['article_xml'],str(record['source_record_id']))
            base['quality_flags'].append('derived_pubmed_context_from_original_xml')
        base.update(completeness_scope='complete_pubmed_citation_not_article_full_text',parser_version=data['enrichment']['version'])
        base['quality_flags'].append('pubmed_record_not_article_full_text')
        if not data['enrichment']['abstract_sections']:base['quality_flags'].append('primary_abstract_not_supplied_or_book_record')
    for field in ('company_ids', 'entity_ids', 'product_ids', 'person_ids'):
        if isinstance(record.get(field), list) and record[field]:
            base[field] = deepcopy(record[field])
    base["payload_hash"] = "sha256:" + digest(payload)
    if contract.get('provider_role'):
        base.update(provider_role=contract['provider_role'],data_purpose=contract['data_purpose'],
                    completeness_scope=contract['completeness_scope'])
        base['quality_flags']=['vendor_data_not_primary_document','original_historical_availability_unverified']
        if payload.get('profile_status')=='not_found':
            base['quality_status']='provider_unavailable'
            base['quality_flags'].append('provider_profile_not_found; complete_response_not_complete_profile')
        if payload.get('kind')=='prices':base['quality_flags'].append('adjusted_prices_are_current_provider_vintage')
    base["source_observation_id"] = record.get("observation_id")
    # A replay's processing clock does not create a new evidence observation.
    base["observation_id"] = "obs_" + digest({key: value for key, value in base.items() if key != "labelled_at"})
    return base
