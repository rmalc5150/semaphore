"""Metadata contracts for checked, user-supplied release archives."""
import base64
import hashlib
import json
import re
from urllib.parse import urlsplit

ADAPTER = 'verified_archive_intake'
DATASET = 'archive_objects'
VERSION = '1.0.0-archive-intake'
EXPORTS = 'research-data/constellation-backfill/public-capture/market-workbook-v1/historical-exports'
HOSTS = {
    123: ('api.globalenergymonitor.org',),
    189: ('ec.europa.eu',),
    235: ('gis.cdc.gov',),
    254: ('data.fca.org.uk',),
    255: ('www.cnmv.es',),
    256: ('www.nbim.no',),
    266: ('www.ferc.gov', 's3.us-west-2.amazonaws.com'),
}


def contracts():
    return {
        f'market_source_{number}': {
            'source_key': f'market_source_{number}', 'catalog_entries': [number], 'datasets': [DATASET],
            'state': 'enabled', 'contract_version': VERSION, 'adapter': ADAPTER, 'adapter_version': VERSION,
            'record_kind': 'provider_release_file', 'license_policy_id': 'source-rights-review-required',
            'allowed_hosts': list(hosts),
            'completeness_scope': 'Verified release object and its native rows for the captured scope.',
            'raw_requirements': {
                'version': VERSION, 'minimum_completeness': 'complete', 'required_artifact_kinds': ['dataset_file'],
                'forbidden_shortcuts': ['discovery_page', 'unchecked_archive', 'index_as_underlying_filing'],
            },
        } for number, hosts in HOSTS.items()
    }


def archive_root(source):
    return f'{EXPORTS}/{source}/temporary-intake/'


def processing_prefix(source, key):
    identity = key.removeprefix(archive_root(source)).split('/', 1)[0]
    if not re.fullmatch(r'[a-f0-9]{64}', identity):
        raise ValueError('archive_evidence_identity_invalid')
    return f'{EXPORTS}/{source}/temporary-intake-processed/{identity}/{VERSION}'


def check_object(s3, bucket, key, sha, size):
    if not re.fullmatch(r'[0-9a-f]{64}', sha) or type(size) is not int or size <= 0:
        raise ValueError('archive_invalid_checksum_or_size')
    response = s3.head_object(Bucket=bucket, Key=key, ChecksumMode='ENABLED')
    if (response['ContentLength'] != size or response.get('ChecksumType') != 'FULL_OBJECT'
            or response.get('ChecksumSHA256') != base64.b64encode(bytes.fromhex(sha)).decode()
            or response.get('ServerSideEncryption') != 'AES256'):
        raise ValueError('archive_s3_checksum_or_size_mismatch')
    return response


def evidence(record, contract, s3, bucket):
    from metadata_engine.evidence import RawFailure, object_bytes, s3_key

    ref, = record['payload']['source_evidence']
    scope = record['payload']['data']
    url = urlsplit(ref['source_url'])
    source = record['source']
    key = s3_key(ref['s3_uri'], bucket)
    checksum = ref['sha256']
    if (source != contract['source_key'] or record['dataset'] != DATASET or url.scheme != 'https'
            or url.hostname not in contract['allowed_hosts']
            or not key.startswith(archive_root(source))
            or not re.fullmatch(r'[a-f0-9]{64}/[^/]+', key.removeprefix(archive_root(source)))):
        raise RawFailure('archive_evidence_scope_mismatch')

    expected_manifest = processing_prefix(source, key) + '/manifest.json'
    manifest_key = s3_key(scope['processing_manifest_s3_uri'], bucket)
    if manifest_key != expected_manifest:
        raise RawFailure('archive_manifest_outside_evidence_path')
    try:
        stored = check_object(s3, bucket, key, checksum, ref['bytes'])
        if 'attachment' in ref:
            attachment = ref['attachment']
            parent = s3_key(attachment['s3_uri'], bucket)
            if parent != f"{EXPORTS}/intake-attachments/{attachment['sha256']}/original.zip":
                raise ValueError('archive_attachment_evidence_path_mismatch')
            check_object(s3, bucket, parent, attachment['sha256'], attachment['bytes'])
        body = object_bytes(s3, bucket, manifest_key, 4 * 1024**2, scope['processing_manifest_sha256'])
        manifest = json.loads(body)
        if (manifest['raw'] != ref or scope['summary'] != manifest['summary']
                or manifest['version'] != VERSION or manifest['source'] != source
                or manifest['summary']['rows'] <= 0 or not manifest['tables']):
            raise ValueError('archive_processing_receipt_mismatch')
        for table in manifest['tables']:
            output = table['object']
            output_key = s3_key(output['s3_uri'], bucket)
            if output_key != key and not output_key.startswith(f"{manifest_key.rsplit('/',1)[0]}/tables/"):
                raise ValueError('archive_processed_object_scope_mismatch')
            if output_key != key:
                check_object(s3, bucket, output_key, output['sha256'], output['bytes'])
    except (KeyError, ValueError) as error:
        raise RawFailure(str(error)) from error
    return [{
        'artifact_kind': 'dataset_file', 'origin': 'first_party_source', 's3_uri': ref['s3_uri'],
        'sha256': checksum, 'bytes': ref['bytes'], 'media_type': stored.get('ContentType'),
        'source_url': ref['source_url'], 'representation': manifest['summary']['representation'],
        'validation': {'processing_manifest_s3_uri': scope['processing_manifest_s3_uri'],
                       'processing_manifest_sha256': hashlib.sha256(body).hexdigest(),
                       'native_rows': manifest['summary']['rows']},
    }]
