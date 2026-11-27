"""Stage the reviewed temporary S3 exports without granting the worker bucket access."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import PurePosixPath
import re

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

INBOX = 'temporary-059416028963-us-east-1-an'
BUCKET = 'data-collection-059416028963-us-east-1-an'
ACCOUNT = '059416028963'
REGION = 'us-east-1'
EXPORTS = 'research-data/constellation-backfill/public-capture/market-workbook-v1/historical-exports'
CONTROL = 'research-data/constellation-backfill/deployments/temporary-archive-intake'
INPUTS = {
    'Safety-Gate-Monthly-XML.zip': 189,
    'Safety-Gate-Weekly-Originals.zip': 189,
    'CDC-FluView-Official-Exports.zip': 235,
    'CNMV-Date-Only-Capture.zip': 255,
    'NBIM-Holdings-Exports.zip': 256,
    'FERC-Contracts-2016Q1-to-2026Q3.zip': 266,
    'FERC-Official-Submissions-2016-to-2026.zip': 266,
    'FERC-Q1-2016-Filing-Dates.csv': 266,
    'FERC-Transactions-Download-Index.csv': 266,
    'FERC-Verified-Local-Files.csv': 266,
    'FERC/datapackage.json': 266,
    'Safety-Gate-Weekly-Recapture.zip': 189,
    'CDC-FluView-Recapture.zip': 235,
    'NBIM-Holdings-API-Snapshots.zip': 256,
    'GEM-Current-Assets.zip': 123,
    'GEM-Current-Entities.zip': 123,
    'FCA-PDMR-Notice-Index.zip': 254,
    'CNMV-Legacy-2016.zip': 255,
    'CNMV-Modern-Register-Snapshot.zip': 255,
    'NBIM-Opening-2015.zip': 256,
    'FERC-Official-Q1-2016-Filings.zip': 266,
}
FERC_PARQUET = re.compile(r'FERC/(20\d{2}q[1-4])-(contracts|transactions)\.parquet')


def source_id(key):
    if FERC_PARQUET.fullmatch(key):
        return 266
    return INPUTS.get(key)


def staged_key(key, etag, size):
    number = source_id(key)
    if not number:
        raise ValueError('unrecognized_archive_object')
    identity = hashlib.sha256(json.dumps([key, etag, size]).encode()).hexdigest()
    return f'{EXPORTS}/market_source_{number}/temporary-intake/{identity}/{PurePosixPath(key).name}'


def stage_one(s3, item):
    key, etag, size = (item[name] for name in ('Key', 'ETag', 'Size'))
    target = staged_key(key, etag, size)

    def head():
        return s3.head_object(Bucket=BUCKET, Key=target, ChecksumMode='ENABLED',
                              ExpectedBucketOwner=ACCOUNT)

    try:
        stored = head()
    except ClientError as error:
        if error.response['Error']['Code'] not in ('404', 'NotFound', 'NoSuchKey'):
            raise
        try:
            s3.copy_object(
                Bucket=BUCKET, Key=target, CopySource={'Bucket': INBOX, 'Key': key},
                CopySourceIfMatch=etag, IfNoneMatch='*', ChecksumAlgorithm='SHA256',
                ServerSideEncryption='AES256', ExpectedBucketOwner=ACCOUNT,
                ExpectedSourceBucketOwner=ACCOUNT, MetadataDirective='REPLACE',
                Metadata={'inbox-key': key, 'inbox-etag': etag},
            )
        except ClientError as copy_error:
            if copy_error.response['Error']['Code'] not in ('PreconditionFailed', '412'):
                raise
        stored = head()
    if (stored['ContentLength'] != size or not stored.get('ChecksumSHA256')
            or stored.get('ChecksumType') != 'FULL_OBJECT'
            or stored.get('Metadata') != {'inbox-key': key, 'inbox-etag': etag}
            or stored.get('ServerSideEncryption') != 'AES256'):
        raise ValueError('staged_archive_identity_mismatch')
    return {
        'inbox_key': key, 'inbox_etag': etag, 'bytes': size, 'source': source_id(key),
        'key': target, 'etag': stored['ETag'], 'sha256_base64': stored['ChecksumSHA256'],
        'staged_at': stored['LastModified'].isoformat(),
    }


def write_inventory(s3, items, ignored):
    body = (json.dumps({'version': 1, 'objects': sorted(items, key=lambda item: item['inbox_key']),
                        'ignored': sorted(ignored)}, sort_keys=True) + '\n').encode()
    sha = hashlib.sha256(body).hexdigest()
    key = f'{CONTROL}/inventories/{sha}.json'
    try:
        s3.put_object(Bucket=BUCKET, Key=key, Body=body, IfNoneMatch='*', ContentType='application/json',
                      ServerSideEncryption='AES256', ChecksumAlgorithm='SHA256', ExpectedBucketOwner=ACCOUNT)
    except ClientError as error:
        if error.response['Error']['Code'] not in ('PreconditionFailed', '412'):
            raise
    return key, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--key', action='append', help='Stage only these inbox object keys')
    args = parser.parse_args()
    s3 = boto3.client('s3', region_name=REGION, config=Config(read_timeout=240, retries={'mode': 'standard'}))
    items = [item for page in s3.get_paginator('list_objects_v2').paginate(Bucket=INBOX, ExpectedBucketOwner=ACCOUNT)
             for item in page.get('Contents', [])]
    if args.key:
        requested = set(args.key)
        items = [item for item in items if item['Key'] in requested]
        if requested != {item['Key'] for item in items} or not all(source_id(item['Key']) for item in items):
            parser.error('one or more requested objects are absent or unrecognized')
    recognized = [item for item in items if source_id(item['Key'])]
    ignored = [item['Key'] for item in items if not source_id(item['Key'])]
    if not recognized:
        parser.error('no reviewed input objects were found')
    staged = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        for item in executor.map(lambda item: stage_one(s3, item), recognized):
            staged.append(item)
            print(json.dumps({'staged': item['inbox_key'], 'bytes': item['bytes']}), flush=True)
    key, sha = write_inventory(s3, staged, ignored)
    print(json.dumps({'inventory': key, 'sha256': sha, 'objects': len(staged),
                      'bytes': sum(item['bytes'] for item in staged), 'ignored': ignored}), flush=True)


if __name__ == '__main__':
    main()
