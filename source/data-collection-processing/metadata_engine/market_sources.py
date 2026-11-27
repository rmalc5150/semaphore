"""Metadata contracts and evidence verification for reviewed market originals."""
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.parse import urlsplit

from market_source_capture import MARKET, allowed, validated
from metadata_engine.evidence import RawFailure


VERSION = '2.0.3-market-v1'


def contracts(root):
    config = root/'config'
    activation = json.loads((config/'market-source-activation.v1.json').read_text())
    routes = json.loads((config/'market-source-routes.v1.json').read_text())['routes']
    result = {}
    for source, datasets in activation.items():
        selected = [route for route in routes if route['source']==source and
                    datasets.get(route['dataset'],{}).get('metadata')]
        if not selected:
            continue
        result[source] = {
            'source_key':source, 'catalog_entries':[selected[0]['catalog_entry']],
            'datasets':sorted(route['dataset'] for route in selected),
            'market_routes':{route['dataset']:route for route in selected},
            'state':'enabled', 'contract_version':VERSION, 'adapter':'market_workbook_original',
            'adapter_version':VERSION, 'record_kind':'provider_release_file',
            'license_policy_id':'source-rights-review-required',
            'allowed_hosts':sorted({host for route in selected for host in route['hosts']}),
            'completeness_scope':'Verified original file or bounded provider response, with the declared resource scope and first-seen timestamp.',
            'raw_requirements':{'version':VERSION,'minimum_completeness':'complete',
                                'required_artifact_kinds':['provider_record'],
                                'forbidden_shortcuts':['documentation_as_data','discovery_page','unchecked_original']},
        }
    return result


def from_receipt(receipt):
    return {
        'source':receipt['source'], 'dataset':receipt['dataset'],
        'source_record_id':receipt['sha256'], 'source_record_id_basis':'provider_content_sha256',
        'source_document_id':receipt['resource_url'], 'ingested_at':receipt['retrieved_at'],
        'source_url':receipt['source_url'], 'available_at':None,
        'parser_version':VERSION,
        'payload':{'data':{'validation':receipt['validation'], 'partition':receipt['partition'],
                           'scope':receipt['scope_note'], 'resource_url':receipt['resource_url'],
                           'previous_sha256':receipt.get('previous_sha256')},
                   'source_evidence':[{'s3_uri':receipt['artifact_uri'],'sha256':receipt['sha256'],
                                       'source_url':receipt['source_url'],'size':receipt['bytes'],
                                       'retrieved_at':receipt['retrieved_at']}]},
    }


def evidence(record, contract, s3, bucket):
    profile = contract['market_routes'].get(record['dataset'])
    if not profile:
        raise RawFailure('market_dataset_not_enabled')
    ref, = record['payload']['source_evidence']
    url = ref['source_url']
    uri = urlsplit(ref['s3_uri'])
    digest = ref['sha256']
    if not allowed(profile,url) or uri.scheme!='s3' or uri.netloc!=bucket:
        raise RawFailure('market_provider_or_storage_scope_mismatch')
    if uri.path != f"/{MARKET}/objects/{profile['source']}/{digest}":
        raise RawFailure('market_raw_identity_mismatch')
    cap = profile.get('max_mb',16)*1024**2
    response = s3.get_object(Bucket=bucket,Key=uri.path.lstrip('/'))
    stream = response['Body']
    sha = hashlib.sha256()
    size = 0
    try:
        with tempfile.NamedTemporaryFile() as file:
            for chunk in stream.iter_chunks(128*1024):
                size += len(chunk)
                if size > cap:
                    raise RawFailure('market_validation_byte_limit')
                file.write(chunk)
                sha.update(chunk)
            if sha.hexdigest()!=digest or size!=ref['size']:
                raise RawFailure('market_original_checksum_or_size_mismatch')
            file.flush()
            try:
                details = validated(Path(file.name),profile,url)
            except Exception as exc:
                raise RawFailure('market_original_content_invalid: '+type(exc).__name__) from exc
    finally:
        stream.close()
    if not details or details!=record['payload']['data']['validation']:
        raise RawFailure('market_original_validation_mismatch')
    return [{'artifact_kind':'provider_record','s3_uri':ref['s3_uri'],'sha256':digest,'origin':'first_party_source',
             'source_url':url,'validation':details}]
