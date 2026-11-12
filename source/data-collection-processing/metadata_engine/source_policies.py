"""Catalog-to-contract policy; raw checks run on actual artifacts, never counts."""
import json
from pathlib import Path
from urllib.parse import urlsplit

# A new version forces the controller to register the expanded first-party
# artifact hosts instead of continuing to use the previous metadata-only
# publication contract already stored in the runtime database.
VERSION='2.0.2'
PAUSED={'marketaux','github_sdk','reddit','bluesky_search','bluesky_company_accounts','bluesky_company_posts','bluesky_company_events','nice_technology_appraisals'}
PUBLICATIONS={'pubmed_abstracts','europe_pmc','europe_pmc_fulltext','crossref_proceedings','arxiv','openalex_scholarly_graph','datacite_dissertations_datasets_software_and_usage','biorxiv_medrxiv_preprints','openaire_graph_projects_and_research_products','semantic_scholar_citation_context','france_theses_fr_doctoral_theses','brazil_capes_theses_and_dissertations'}
FILINGS={'sec_edgar','hkex_news','edinet_filings','cninfo_mainland_china_company_disclosures','south_korea_fss_opendart','taiwan_twse_mops_issuer_and_revenue_archives'}
PATENTS={'google_patents_bigquery','uspto_odp'}
EODHD={'eodhd','eodhd_market'}
EODHD_VERSION='2.0.3'
SERIES={'eodhd_market','hkex_prices','bls_wages','eia_retail_prices','caiso_prices','caiso_ancillary_prices','caiso_price_intervals','un_comtrade','fred_alfred_series_and_vintages','bis_sdmx_api','nasa_power_weather_and_solar_resource','us_census_international_trade_api','eurostat_comext_goods_trade','wto_timeseries_api'}


def urls(value):
    if isinstance(value,str) and value.startswith('https://'):yield value
    elif isinstance(value,dict):
        for item in value.values():yield from urls(item)
    elif isinstance(value,list):
        for item in value:yield from urls(item)


def build(root):
    registry=json.loads((root/'config/constellation-source-registry.json').read_text())['sources']
    hosts={}
    for name in ('constellation-specialist-historical.json','constellation-public-sources.json'):
        data=json.loads((root/'config'/name).read_text())
        for row in data.get('sources',[]):
            key=row.get('source'); hosts.setdefault(key,set()).update(urlsplit(u).hostname for u in urls(row))
            hosts[key].update(row.get('hosts',[]))
            hosts[key].update(row.get('full_text_hosts',[]))
    hosts.setdefault('sec_edgar',set()).add('www.sec.gov')
    for key in EODHD:hosts.setdefault(key,set()).add('eodhd.com')
    for key,host in [('usgs_earthquakes','earthquake.usgs.gov'),('nsf_awards','api.nsf.gov'),('arxiv','export.arxiv.org')]:hosts.setdefault(key,set()).add(host)
    policies={}
    for entry in registry:
        key=entry['source_key']
        family='publications' if key in PUBLICATIONS else 'filings_xbrl' if key in FILINGS else 'patents' if key in PATENTS else 'time_series' if key in SERIES else 'api_records'
        required=['provider_record']
        if family in ('publications','filings_xbrl','patents'):required.append({'publications':'full_text','filings_xbrl':'primary_document','patents':'patent_document'}[family])
        layer=entry.get('evidence_role')=='access_or_processing_route' or key=='decodo_shared_web_retrieval_access_layer'
        state='owner_paused' if key in PAUSED else 'access_layer' if layer else 'enabled'
        if key not in policies:
            policies[key]={'source_key':key,'catalog_entries':[],'datasets':[],'state':state,'contract_version':VERSION,
                'adapter':family,'adapter_version':VERSION,'record_kind':'measurement' if family=='time_series' else 'source_record',
                'license_policy_id':'source-rights-review-required','allowed_hosts':sorted(h for h in hosts.get(key,[]) if h),
                'raw_requirements':{'version':VERSION,'minimum_completeness':'complete','required_artifact_kinds':required,
                    'forbidden_shortcuts':['abstract_only','index_only','title_date_only','third_party_metadata_only']}}
        policies[key]['catalog_entries'].append(entry['catalog_entry'])
        policies[key]['datasets']=sorted(set(policies[key]['datasets']+entry.get('datasets',[])))
    for key in EODHD:
        policy=policies[key]
        policy.update(contract_version=EODHD_VERSION,adapter='eodhd_provider_data',adapter_version=EODHD_VERSION,
                      record_kind='market_observation' if key=='eodhd_market' else 'company_reference',
                      provider_role='third_party_data_vendor',data_purpose='market_data' if key=='eodhd_market' else 'company_reference',
                      completeness_scope='declared_provider_dataset',
                      dataset_contracts=({'market_records':{'kinds':['prices','dividends','splits'],'symbol_identity':'exchange_qualified',
                                                           'price_fields':['date','open','high','low','close','adjusted_close','volume'],
                                                           'dividend_fields':['date','value'],'split_fields':['date','split'],
                                                           'adjusted_prices':'current_provider_vintage_not_point_in_time'}} if key=='eodhd_market' else
                                         {'company_profiles':{'scope':'General','required_identity_fields':['Code','Name'],
                                                              'retain_all_returned_fields':True,'full_fundamentals_required':False},
                                          'listing_inventory':{'scope':'exchange_and_active_or_delisted_status',
                                                               'required_identity_fields':['Code','Name'],'retain_all_returned_fields':True}}))
        policy['raw_requirements']={'version':EODHD_VERSION,'minimum_completeness':'complete',
            'required_artifact_kinds':['provider_record','provider_data'],
            'forbidden_shortcuts':['unverified_provider_response','identity_mismatch','corrupt_provider_response']}
    policy=policies['finlight']
    policy.update(contract_version='2.0.3',adapter_version='2.0.3',allowed_hosts=['api.finlight.me'])
    policy['raw_requirements']={**policy['raw_requirements'],'version':'2.0.3',
        'forbidden_shortcuts':['unverified_provider_response','identity_mismatch','request_receipt_only']}
    policy['completeness_scope']='provider_article_record; publisher_fulltext_is_separate'
    policies['people_rss'].update(contract_version='2.0.3',adapter_version='2.0.3',
        completeness_scope='publisher_article_body; unavailable articles remain explicit gaps')
    policies['people_rss']['raw_requirements']={
        'version':'2.0.3','minimum_completeness':'complete',
        'required_artifact_kinds':['provider_record','full_text'],
        'forbidden_shortcuts':['rss_summary_only','article_url_only','access_block_page']}
    policies['personnel_archive'].update(contract_version='2.0.3',adapter_version='2.0.3',
        completeness_scope='committed upstream source candidate and original content; not a verified personnel event')
    policies['personnel_archive']['raw_requirements']={
        'version':'2.0.3','minimum_completeness':'complete',
        'required_artifact_kinds':['provider_record','parent_record','source_content'],
        'forbidden_shortcuts':['unverified_parent_identity','uncommitted_parent','source_url_only']}
    policy=policies['clinicaltrials_gov']
    policy.update(contract_version='2.0.3',adapter_version='2.0.3',allowed_hosts=['clinicaltrials.gov'],
        completeness_scope='complete provider study record; current registry version, not historical vintages')
    policy['raw_requirements']={**policy['raw_requirements'],'version':'2.0.3',
        'forbidden_shortcuts':['field_projection','missing_protocol','identity_mismatch','request_receipt_only']}
    policy=policies['ema_ctis']
    policy.update(contract_version='2.0.3',adapter_version='2.0.3',allowed_hosts=['euclinicaltrials.eu'],
        completeness_scope='current public CTIS trial detail and matched application/decision events; not document archive or historical vintages')
    policy['raw_requirements']={**policy['raw_requirements'],'version':'2.0.3',
        'forbidden_shortcuts':['discovery_page','search_summary_only','unmatched_trial_or_event','request_receipt_only']}
    policy=policies['fda_openfda']
    policy.update(contract_version='2.0.3',adapter_version='2.0.3',allowed_hosts=['api.fda.gov'],
        completeness_scope='complete current openFDA application or CRL and matched approval event; not all linked documents or historical vintages')
    policy['raw_requirements']={**policy['raw_requirements'],'version':'2.0.3',
        'forbidden_shortcuts':['field_projection','aggregate_only','unmatched_application_or_submission','request_receipt_only']}
    policy=policies['drugsfda_applications']
    policy.update(contract_version='2.0.3',adapter_version='2.0.3',allowed_hosts=['api.fda.gov'],
        completeness_scope='entire current provider application and all returned products/submissions; all-provider inventory plus date-scoped refresh, not all worldwide drugs or historical vintages')
    policy['raw_requirements']={**policy['raw_requirements'],'version':'2.0.3',
        'forbidden_shortcuts':['field_projection','aggregate_only','unmatched_application','request_receipt_only']}
    policy=policies['ema_medicines']
    policy.update(contract_version='2.0.3',adapter_version='2.0.3',allowed_hosts=['www.ema.europa.eu'],
        completeness_scope='entire current EMA bulk medicine row, all categories/statuses; linked EPAR documents and historical vintages separate')
    policy['raw_requirements']={**policy['raw_requirements'],'version':'2.0.3',
        'forbidden_shortcuts':['unmatched_medicine','field_projection','index_only','request_receipt_only']}
    policy=policies['uk_mhra']
    policy.update(contract_version='2.0.3',adapter_version='2.0.3',allowed_hosts=['assets.publishing.service.gov.uk','mhraproducts4853.search.windows.net','mhraproducts4853.blob.core.windows.net'],
        completeness_scope='official designation rows and public medicine documents with original catalogue/PDF linkage; no all-licence or historical-vintage inference')
    policy['raw_requirements']={**policy['raw_requirements'],'version':'2.0.3',
        'forbidden_shortcuts':['unmatched_register_row','discovery_page','request_receipt_only']}
    policy=policies['japan_pmda']
    policy.update(contract_version='2.0.3',adapter_version='2.0.3',allowed_hosts=['www.pmda.go.jp'],
        completeness_scope='original SAKIGAKE designation PDF and matched table rows; all-drug package-insert coverage remains separate')
    policy['raw_requirements']={**policy['raw_requirements'],'version':'2.0.3',
        'forbidden_shortcuts':['unmatched_designation','role_inference_from_flattened_text','index_only','request_receipt_only']}
    policy=policies['canada_noc']
    policy.update(contract_version='2.0.3',adapter_version='2.0.3',allowed_hosts=['health-products.canada.ca'],completeness_scope='entire current official NOC record, all provider drugs and dates; not all marketed drugs or historical vintages')
    policy['raw_requirements']={**policy['raw_requirements'],'version':'2.0.3','forbidden_shortcuts':['unmatched_noc','field_projection','index_only','request_receipt_only']}
    policy=policies['chictr']
    policy.update(contract_version='2.0.3',adapter_version='2.0.3',allowed_hosts=['www.chictr.org.cn','chictr.org.cn'],completeness_scope='original public ChiCTR trial detail HTML and complete matching parsed fields; historical vintages and protocol attachments separate')
    policy['raw_requirements']={**policy['raw_requirements'],'version':'2.0.3','forbidden_shortcuts':['search_listing_only','unmatched_trial','partial_field_list','request_receipt_only']}
    policy=policies['nmpa_trials']
    policy.update(contract_version='2.0.3',adapter_version='2.0.3',allowed_hosts=['www.chinadrugtrials.org.cn','chinadrugtrials.org.cn'],completeness_scope='inventory rows matched to original listing; research records require original full detail; inventory is not full trial coverage')
    policy['raw_requirements']={**policy['raw_requirements'],'version':'2.0.3','forbidden_shortcuts':['inventory_as_trial_detail','unmatched_registration','partial_detail_fields','request_receipt_only']}
    policy=policies['pubmed_abstracts']
    policy.update(contract_version='2.0.3',adapter='api_records',adapter_version='2.0.3',record_kind='publication_abstract_record',allowed_hosts=['eutils.ncbi.nlm.nih.gov'],completeness_scope='complete original PubMed citation XML and abstract when provided; not article full text, all PubMed or historical vintages')
    policy['raw_requirements']={'version':'2.0.3','minimum_completeness':'complete','required_artifact_kinds':['provider_record'],'forbidden_shortcuts':['search_ids_only','title_only','partial_citation_xml','unmatched_primary_pmid','abstract_as_article_full_text']}
    policy=policies['europe_pmc_fulltext']
    policy.update(contract_version='2.0.3',adapter_version='2.0.3',record_kind='publication_fulltext',allowed_hosts=['www.ebi.ac.uk','eutils.ncbi.nlm.nih.gov'],completeness_scope='entire original matched JATS article; external supplements and historical vintages separate')
    policy['raw_requirements']={**policy['raw_requirements'],'version':'2.0.3','forbidden_shortcuts':['abstract_only','index_only','title_date_only','unmatched_pmcid','partial_article_xml','discovery_page_as_fulltext']}
    policy=policies['crossref_proceedings']
    policy.update(contract_version='2.0.3',adapter='api_records',adapter_version='2.0.3',record_kind='conference_metadata',allowed_hosts=['api.crossref.org'],completeness_scope='complete current Crossref proceedings-article metadata and deposited abstract when supplied; publisher full text and historical vintages separate')
    policy['raw_requirements']={'version':'2.0.3','minimum_completeness':'complete','required_artifact_kinds':['provider_record'],'forbidden_shortcuts':['field_projection','unmatched_doi','index_only','metadata_as_full_paper','request_receipt_only']}
    for key,kind,scope in (
        ('cms_coverage','coverage_inventory','complete national coverage inventory rows; policy body is collected separately'),
        ('cms_coverage_documents','coverage_document','complete returned NCD version with coverage criteria; not local policies, all payers or historical API vintages')):
        policy=policies[key]
        policy.update(contract_version='2.0.3',adapter_version='2.0.3',record_kind=kind,allowed_hosts=['api.coverage.cms.gov'],completeness_scope=scope)
        policy['raw_requirements']={'version':'2.0.3','minimum_completeness':'complete','required_artifact_kinds':['provider_record'],'forbidden_shortcuts':['unmatched_document_version','field_projection','inventory_as_policy_body','request_receipt_only']}
    policy=policies['cms_payments_catalog']
    policy.update(contract_version='2.0.3',adapter_version='2.0.3',record_kind='financial_dataset_catalog',allowed_hosts=['openpaymentsdata.cms.gov'],completeness_scope='complete original Open Payments dataset descriptor; underlying payment/spending records are in dedicated financial tables')
    policy['raw_requirements']={'version':'2.0.3','minimum_completeness':'complete','required_artifact_kinds':['provider_record'],'forbidden_shortcuts':['unmatched_dataset','partial_descriptor','catalog_as_payment_rows','request_receipt_only']}
    for key in ('fda_dd_compliance_actions','fda_dd_import_refusals','fda_dd_inspections_citations','fda_ires_recalls','fda_product_codes'):
        policy=policies[key]
        scope=('current industry-code reference, not complete product-code hierarchy or historical vintages' if key=='fda_product_codes' else 'entire returned recall row; legacy selected columns flagged; selected by event modification date, not recall-initiation history or historical vintages' if key=='fda_ires_recalls' else 'entire returned dashboard row and citation/compliance/refusal fields; original documents and historical vintages separate')
        policy.update(contract_version='2.0.3',adapter_version='2.0.3',record_kind='industry_reference' if key=='fda_product_codes' else 'recall_record' if key=='fda_ires_recalls' else 'regulatory_dashboard_record',allowed_hosts=['api-datadashboard.fda.gov' if key.startswith('fda_dd_') else 'www.accessdata.fda.gov'],completeness_scope=scope)
        policy['raw_requirements']={'version':'2.0.3','minimum_completeness':'complete','required_artifact_kinds':['provider_record'],'forbidden_shortcuts':['unmatched_provider_row','dropped_returned_fields','industry_reference_as_full_product_taxonomy','projected_recall_as_full_detail','request_receipt_only']}
    for key in ('nih_reporter','usa_spending','uspto_assignment_histories','ted_notices','google_patents_bigquery','uspto_odp','nist_robotics_methods'):
        policy=policies[key]
        allowed={'nih_reporter':['api.reporter.nih.gov'],'usa_spending':['api.usaspending.gov'],'uspto_assignment_histories':['api.uspto.gov'],'uspto_odp':['api.uspto.gov'],'google_patents_bigquery':['bigquery.googleapis.com'],'ted_notices':['api.ted.europa.eu','ted.europa.eu'],'nist_robotics_methods':['www.nist.gov','nist.gov','nvlpubs.nist.gov','data.nist.gov']}[key]
        policy.update(contract_version='2.0.3',adapter='api_records',adapter_version='2.0.3',record_kind='patent_bibliography' if key=='google_patents_bigquery' else 'source_record',allowed_hosts=allowed,completeness_scope='declared source dataset with original identity/content validation; dataset-specific document requirements apply; not exhaustive coverage or historical vintages')
        policy['raw_requirements']={'version':'2.0.3','minimum_completeness':'complete','required_artifact_kinds':['provider_record'],'forbidden_shortcuts':['unmatched_original','unverified_mapping','bibliography_as_patent_text','discovery_as_measurements','content_chunks_as_additional_awards']}
    policies['uspto_odp']['dataset_contracts']={'patent_records':{'scope':'mapped application bibliography; full original API record archived'},'patent_assignment_records':{'scope':'mapped application and returned assignment chain; not established current title'},'patent_office_actions':{'required_artifact_kinds':['provider_record','primary_document']},'patent_petition_decisions':{'required_artifact_kinds':['provider_record','primary_document']}}
    policies['nist_robotics_documents']={**policies['nist_robotics_methods'],'source_key':'nist_robotics_documents','record_kind':'nist_original_document','catalog_entries':[45]}
    return policies
