"""Verify substantive raw artifacts; missing evidence is an explicit failure."""
import hashlib
import json
import re
from urllib.parse import urlsplit

from metadata_engine.sec_documents import retrieve_submission,archive_submission,DocumentError

MAX_BODY=32*1024*1024


class RawFailure(ValueError):pass
class Uncommitted(ValueError):pass
class OversizedArtifact(RuntimeError):pass


def object_bytes(s3,bucket,key,limit=MAX_BODY,expected=None):
    r=s3.get_object(Bucket=bucket,Key=key)
    try:
        if r.get('ContentLength',0)>limit:raise OversizedArtifact('larger_artifact_requires_streaming_adapter')
        b=r['Body'].read(limit+1)
    finally:r['Body'].close()
    if len(b)>limit:raise OversizedArtifact('larger_artifact_requires_streaming_adapter')
    if expected and hashlib.sha256(b).hexdigest()!=expected.removeprefix('sha256:'):raise RawFailure('raw_artifact_checksum_mismatch')
    return b


def s3_key(uri,bucket):
    p=urlsplit(uri)
    if p.scheme!='s3' or p.netloc!=bucket or not p.path.startswith('/research-data/'):
        raise RawFailure('raw_reference_outside_project')
    return p.path.lstrip('/')


def substantive(body):
    if not body:raise RawFailure('empty_raw_artifact')
    lower=body[:16384].lower()
    if any(s in lower for s in (b'<title>access denied',b'captcha',b'cf-chl-',b'request rate threshold exceeded',b'undeclared automated tool')):
        raise RawFailure('raw_artifact_is_access_block_page')
    if body.startswith(b'%PDF-'):
        if b'%%EOF' not in body[-4096:]:raise RawFailure('truncated_pdf')
        return 'document'
    if body.startswith((b'PK\x03\x04',b'\x1f\x8b',b'CDF',b'\x89HDF')):return 'dataset_file'
    if b'<article' in lower and b'<body' in body.lower():return 'full_text'
    if body.lstrip().startswith((b'{',b'[')):
        try:data=json.loads(body)
        except (ValueError,UnicodeError):raise RawFailure('malformed_native_json') from None
        metadata={'id','ids','doi','pmid','title','name','url','link','links','date','time','timestamp','created','updated','published','summary','abstract','abstracttext','description','total','count','offset','limit','page','cursor','authors','author','source','publisher','type','status','metadata','query','request'}
        found=[]
        def scan(value,depth=0):
            if depth>15:return
            if isinstance(value,dict):
                for key,v in value.items():
                    word=str(key).lower().replace('_','')
                    if word in {'protocolsection','resultssection','claims','specification','fulltext','observations','geometry','series','price','close','open','volume','value','amount','units','measure','reactions','patient','drug','devices','decision','submission','application','project','award','financials','general'} and v not in (None,[],{}):found.append(word)
                    scan(v,depth+1)
            elif isinstance(value,list):
                for v in value[:100]:scan(v,depth+1)
        scan(data)
        if not found:raise RawFailure('raw_response_is_metadata_or_abstract_only')
        return 'native_record'
    if body.lstrip().startswith(b'<'):
        if b'<html' in lower or b'<!doctype html' in lower:
            raise RawFailure('html_requires_source_document_validator')
        if any(s in lower for s in (b'<clinical_study',b'<trial',b'<patent',b'<sdmx',b'<genericdata',b'<structure',b'<featurecollection')):return 'native_record'
        raise RawFailure('xml_requires_substantive_content_validator')
    lines=body.splitlines()
    if len(lines)>2 and (b',' in lines[0] or b'\t' in lines[0]):return 'dataset_file'
    raise RawFailure('raw_content_validator_required')


def evidence_for(record,contract,s3,bucket):
    source=record.get('source') or record.get('source_key')
    if source in ('cninfo_mainland_china_company_disclosures','south_korea_fss_opendart')and contract.get('contract_version')=='2.0.3':
        from metadata_engine.regional_filings import evidence
        return evidence(record,s3,bucket)
    from regional_source_review import PUBLIC_KEYS
    if source in PUBLIC_KEYS and contract.get('contract_version')=='2.0.3':
        from metadata_engine.regional_public import evidence
        return evidence(record,s3,bucket)
    if source in ('arxiv','nasa_power_weather_and_solar_resource'):
        from metadata_engine.raw_catalog_review import evidence
        return evidence(record,s3,bucket)
    if source=='england_nhsbsa_prescribing_data':
        from metadata_engine.nhsbsa import evidence
        return evidence(record,s3,bucket)
    if source in ('ucdp_organized_violence','semi_worldwide_equipment_billings','sia_wsts_public_semiconductor_sales','international_federation_of_robotics_world_robotics','iea_pvps_solar_deployment_reports','germany_g_ba_drug_benefit_assessments','france_has_medicine_assessment_opinions','canada_cda_amc_cadth_reimbursement_reviews','france_assurance_maladie_open_medic'):
        from metadata_engine.public_documents import evidence
        return evidence(record,s3,bucket)
    if source=='sam_gov_opportunities':
        from metadata_engine.sam_opportunities import evidence
        return evidence(record,s3,bucket)
    if source in ('imf_portwatch_shipping_activity','unido_iip_and_indstat'):
        from metadata_engine.public_statistics import evidence
        return evidence(record,s3,bucket)
    if source in ('wto_quantitative_restrictions_api','wto_eping_sps_tbt_notifications','epo_ops_patent_legal_events','ember_electricity_demand_and_generation'):
        from metadata_engine.economic_records import evidence
        return evidence(record,s3,bucket)
    if source=='un_comtrade':
        from metadata_engine.comtrade import evidence
        return evidence(record,s3,bucket)
    if source in ('doe_storage_program','doe_storage_documents','doe_storage_benchmarks','doe_storage_funding'):
        from metadata_engine.doe_storage import evidence
        return evidence(record,s3,bucket)
    if source in ('federal_register','federal_register_documents'):
        from metadata_engine.federal_register import evidence
        return evidence(record,s3,bucket)
    if source in ('mlperf_results', 'cpsc_recalls'):
        from metadata_engine.benchmark_recalls import evidence
        return evidence(record,s3,bucket)
    if source=='trade_screening':
        from metadata_engine.streaming import evidence
        for ref in record.get('payload',{}).get('source_evidence',[]):
            if (ref.get('source_url')or ref.get('url'))=='https://data.trade.gov/downloadable_consolidated_screening_list/v1/consolidated.json':
                return [evidence(record,ref,contract,s3,bucket)]
        raise RawFailure('trade_screening_original_response_missing')
    if source in ('nih_reporter','usa_spending','uspto_assignment_histories'):
        from metadata_engine.grants_awards import evidence
        return evidence(record,s3,bucket)
    if source in ('uspto_odp','google_patents_bigquery'):
        from metadata_engine.patent_sources import evidence
        return evidence(record,s3,bucket)
    if source=='ted_notices':
        from metadata_engine.ted_records import evidence
        return evidence(record,s3,bucket)
    if source in ('nist_robotics_methods','nist_robotics_documents'):
        from metadata_engine.nist_methods import evidence
        return evidence(record,s3,bucket)
    if source in ('fda_dd_compliance_actions', 'fda_dd_import_refusals', 'fda_dd_inspections_citations', 'fda_ires_recalls', 'fda_product_codes'):
        from metadata_engine.fda_authenticated import evidence
        return evidence(record,s3,bucket)
    if source=='cms_payments_catalog':
        from metadata_engine.cms_catalog import evidence
        return evidence(record,s3,bucket)
    if source in ('cms_coverage','cms_coverage_documents'):
        from metadata_engine.cms_coverage import evidence
        return evidence(record,s3,bucket)
    if source == 'crossref_proceedings':
        from metadata_engine.crossref import evidence
        return evidence(record,s3,bucket)
    if source == 'europe_pmc_fulltext':
        from metadata_engine.epmc_fulltext import evidence
        return evidence(record,s3,bucket)
    if source == 'pubmed_abstracts':
        from metadata_engine.pubmed import evidence
        return evidence(record,s3,bucket)
    if source == 'nmpa_trials':
        from metadata_engine.nmpa import evidence
        return evidence(record,s3,bucket)
    if source == 'japan_pmda':
        from metadata_engine.pmda import evidence
        return evidence(record,s3,bucket)
    if source == 'uk_mhra':
        from metadata_engine.mhra import evidence
        return evidence(record,s3,bucket)
    if source == 'personnel_archive':
        from metadata_engine.personnel_archive import evidence
        return evidence(record,s3,bucket)
    if source == 'people_rss':
        from metadata_engine.people_rss import evidence
        return evidence(record,s3,bucket)
    artifacts=[]
    validation_errors=[]
    payload=record.get('payload',{})
    refs=payload.get('source_evidence',[])+record.get('source_evidence',[])
    if record.get('raw_s3_uri') and not refs:
        refs=[{'key':s3_key(record['raw_s3_uri'],bucket),'sha256':record.get('raw_sha256'),'source_url':record.get('original_url')}]
    for ref in refs:
        key=ref.get('key')
        if not key and ref.get('s3_uri'):key=s3_key(ref['s3_uri'],bucket)
        if not key or not ref.get('sha256'):continue
        if not key.startswith('research-data/'):key='research-data/'+key
        # EDINET extraction JSON is derived content, not original provider
        # evidence. It can be much larger than the compressed filing. Keep its
        # linkage in the payload; validate the original PDF/ZIP references here.
        if source == 'edinet_filings' and key.startswith('research-data/source_documents/edinet_filings_extracted/'):
            continue
        host=urlsplit(ref.get('source_url') or record.get('source_url') or record.get('original_url') or '').hostname
        if not host or host not in contract.get('allowed_hosts',[]):continue
        if source=='chictr':
            from metadata_engine.chictr import project_id,ProviderError
            try:
                if project_id(ref.get('source_url')or'')!=project_id(record.get('source_url')or''):continue
            except ProviderError:continue
        try:body=object_bytes(s3,bucket,key,expected=ref['sha256'])
        except OversizedArtifact:
            from metadata_engine.streaming import evidence
            wanted='provider_data' if contract['adapter']=='eodhd_provider_data' else 'full_text' if contract['adapter']=='publications' else 'patent_document' if contract['adapter']=='patents' else 'primary_document' if contract['adapter']=='filings_xbrl' else 'provider_record'
            if contract['adapter']=='eodhd_provider_data':raise
            artifacts.append(evidence(record,ref,contract,s3,bucket,wanted));continue
        validation=None
        try:
            if contract['adapter']=='eodhd_provider_data':
                from metadata_engine.eodhd import validate,ProviderDataError
                try:validation=validate(body,record,ref.get('source_url') or record.get('source_url') or '')
                except ProviderDataError as error:raise RawFailure(str(error)) from None
                kind='provider_data'
            elif source == 'chictr':
                from metadata_engine.chictr import validate, ProviderError
                try: validation=validate(body,record,ref.get('source_url')or'')
                except ProviderError as error:raise RawFailure(str(error))from None
                kind='native_record'
            elif source == 'canada_noc':
                from metadata_engine.canada_noc import validate, ProviderError
                try: validation = validate(body,record,ref.get('source_url') or '')
                except ProviderError as error: raise RawFailure(str(error)) from None
                kind = 'native_record'
            elif source == 'ema_medicines':
                from metadata_engine.ema_medicines import validate, ProviderError
                try: validation = validate(body,record,ref.get('source_url') or '')
                except ProviderError as error: raise RawFailure(str(error)) from None
                kind = 'native_record'
            elif source in ('fda_openfda','drugsfda_applications'):
                from metadata_engine.openfda import validate, ProviderError
                try: validation = validate(body,record,ref.get('source_url') or '')
                except ProviderError as error: raise RawFailure(str(error)) from None
                kind = 'native_record'
            elif source == 'ema_ctis':
                from metadata_engine.ctis import validate, ProviderError
                try: validation = validate(body,record,ref.get('source_url') or '')
                except ProviderError as error: raise RawFailure(str(error)) from None
                kind = 'native_record'
            elif source == 'clinicaltrials_gov':
                from metadata_engine.clinicaltrials import validate, ProviderError
                try: validation = validate(body,record,ref.get('source_url') or '')
                except ProviderError as error: raise RawFailure(str(error)) from None
                kind = 'native_record'
            elif source == 'finlight':
                from metadata_engine.finlight import validate, ProviderError
                try: validation = validate(body,record,ref.get('source_url') or '')
                except ProviderError as error: raise RawFailure(str(error)) from None
                kind = 'native_record'
            elif source == 'hkex_news' and ref.get('source_url') == record.get('source_url'):
                from hkex_originals import validate_original, OriginalError
                try: validation = validate_original(body, record['source_url'])
                except OriginalError as error: raise RawFailure(str(error)) from None
                kind = 'document'
            else:kind=substantive(body)
        except RawFailure as error:
            validation_errors.append(str(error))
            continue
        wanted='provider_data' if contract['adapter']=='eodhd_provider_data' else 'full_text' if contract['adapter']=='publications' else 'patent_document' if contract['adapter']=='patents' else 'primary_document' if contract['adapter']=='filings_xbrl' else 'provider_record'
        if wanted in ('full_text','patent_document','primary_document') and kind not in ('document','full_text'):continue
        artifacts.append({'artifact_kind':wanted,'s3_uri':'s3://'+bucket+'/'+key,'sha256':hashlib.sha256(body).hexdigest(),
                          'bytes':len(body),'origin':'first_party_source','source_url':ref.get('source_url'),'retrieved_at':ref.get('retrieved_at'),
                          'validation':validation or 'original source bytes, SHA-256 and substantive content checked'})
        if validation and contract['adapter']=='eodhd_provider_data':artifacts[-1].update(provider_role='third_party_data_vendor',completeness_scope='declared_provider_dataset')
    if source=='sec_edgar':
        # Reuse the existing verified pilot artifact for this known accession.
        if record['source_record_id']=='0000950170-24-067660':
            sha='ca11cb9b18e68330810e97f392f72c3051eaaa1900117053e9cca7580a927e21'
            key='research-data/constellation-backfill/metadata-engine/source_documents/sec_edgar/'+sha+'.txt'
            from metadata_engine.sec_documents import validate_submission
            body=object_bytes(s3,bucket,key,expected=sha)
            info=validate_submission(body,record['source_record_id'],[r['cik'] for r in payload['issuer_rows']],payload['form'])
            artifacts.append({'artifact_kind':'primary_document','s3_uri':'s3://'+bucket+'/'+key,'sha256':sha,'bytes':len(body),'origin':'first_party_source','validation':info})
        else:
            try:body,receipt=retrieve_submission(record);artifacts.append(archive_submission(s3,bucket,body,receipt))
            except DocumentError as exc:raise RawFailure(str(exc)) from None
    required=set(contract['raw_requirements']['required_artifact_kinds'])-{'provider_record'}
    kinds={a['artifact_kind'] for a in artifacts}
    if (contract['adapter']=='eodhd_provider_data' or source in ('clinicaltrials_gov','ema_ctis','fda_openfda','drugsfda_applications','ema_medicines','canada_noc','chictr')) and not artifacts and validation_errors:
        raise RawFailure(validation_errors[0])
    if not artifacts or required-kinds:raise RawFailure('missing_verified_raw_artifacts:'+','.join(sorted(required-kinds or {'provider_record'})))
    # The envelope is a provenance/index record. Only actual separately verified
    # artifacts establish substantive completeness.
    return artifacts
