"""Strict receipt-scoped recovery of OpenDART XML originals."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from botocore.exceptions import ClientError
import requests

from metadata_engine.dart_originals import PREFIX
from metadata_engine.evidence import RawFailure, object_bytes

URL = 'https://opendart.fss.or.kr/api/document.xml'
LIMIT = 16 * 1024**2


def registry(receipt, anchor_sha, anchor):
    if (not re.fullmatch(r'\d{14}',receipt) or not re.fullmatch(r'[a-f0-9]{64}',anchor_sha)
            or anchor not in ('old_archive','archived_index')):
        raise RawFailure('dart_xml_repair_invalid_identity')
    return f'{PREFIX}/xml-receipts/{receipt}/{anchor}-{anchor_sha}.json'


def repaired(s3,bucket,receipt,anchor_sha,anchor):
    from metadata_engine.regional_filings import dart_zip_validation
    from metadata_engine.streaming import download
    try:
        entry=json.loads(object_bytes(s3,bucket,registry(receipt,anchor_sha,anchor),65536))
    except ClientError as exc:
        if exc.response['Error']['Code'] in ('NoSuchKey','404','NotFound'):
            return None
        raise
    sha=entry.get('sha256','')
    if (entry.get('receipt')!=receipt or entry.get('anchor')!=anchor or entry.get('anchor_sha256')!=anchor_sha
            or not re.fullmatch('[a-f0-9]{64}',sha) or entry.get('key')!=f'{PREFIX}/xml-originals/{sha}.zip'):
        raise RawFailure('dart_xml_repair_registry_mismatch')
    data=download(s3,bucket,entry['key'],sha)
    proof=dart_zip_validation(data,receipt)
    return {'artifact_kind':'primary_document','s3_uri':f's3://{bucket}/{entry["key"]}',
            'sha256':sha,'bytes':data['bytes'],'origin':'first_party_source',
            'source_url':URL+'?rcept_no='+receipt,'retrieved_at':entry['retrieved_at'],
            'validation':{**proof,'provider':'south_korea_fss_opendart','receipt':receipt,
                          'record_type':'original_filing_document','repair_anchor_sha256':anchor_sha}}


def recover(s3,bucket,client,receipt,anchor_sha,anchor,request_budget):
    from additional_source_apis import credentials
    from constellation.shared_limits import admit
    from metadata_engine.regional_filings import dart_zip_validation
    from metadata_engine.worker import put

    key=registry(receipt,anchor_sha,anchor)
    if repaired(s3,bucket,receipt,anchor_sha,anchor):return
    if request_budget['remaining']<=0:raise RawFailure('dart_xml_repair_budget_exhausted')
    token=credentials().get('dart','').strip()
    if not token:raise RawFailure('dart_xml_repair_credential_unavailable')
    request_budget['remaining']-=1
    admit(URL)
    try:
        with client.get(URL,params={'crtfc_key':token,'rcept_no':receipt},stream=True,
                        timeout=(8,20),allow_redirects=False) as response:
            if response.status_code!=200:raise RawFailure(f'dart_xml_repair_http_{response.status_code}')
            body=bytearray()
            for chunk in response.iter_content(65536):
                body.extend(chunk)
                if len(body)>LIMIT:raise RawFailure('dart_xml_repair_size_limit')
    except requests.RequestException as exc:
        raise RawFailure('dart_xml_repair_transport_'+type(exc).__name__) from None
    if not bytes(body[:4])==b'PK\x03\x04':
        # Preserve only recognized error classes and never expose the signed URL.
        status=None
        try:status=json.loads(body).get('status')
        except (ValueError,AttributeError):pass
        if status in ('020','800'):raise RawFailure('dart_xml_repair_provider_cooldown')
        raise RawFailure('dart_xml_repair_original_unavailable')
    sha=hashlib.sha256(body).hexdigest();object_key=f'{PREFIX}/xml-originals/{sha}.zip'
    with TemporaryDirectory(prefix='dart-xml-repair-') as tmp:
        staged=Path(tmp)/'original.zip';staged.write_bytes(body)
        dart_zip_validation({'path':staged,'bytes':len(body),'sha256':sha},receipt)
    put(s3,bucket,object_key,bytes(body),'application/zip')
    record={'receipt':receipt,'anchor':anchor,'anchor_sha256':anchor_sha,'sha256':sha,
            'key':object_key,'retrieved_at':datetime.now(timezone.utc).isoformat()}
    try:
        s3.put_object(Bucket=bucket,Key=key,Body=json.dumps(record,sort_keys=True).encode(),
                      ContentType='application/json',ServerSideEncryption='AES256',IfNoneMatch='*')
    except ClientError as exc:
        if exc.response['Error']['Code'] not in ('412','PreconditionFailed'):raise
