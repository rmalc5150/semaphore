"""Checksum-confirmed immutable writes, retaining readback on older objects."""
import base64
import hashlib
from botocore.exceptions import ClientError


def verify_readback(s3, bucket, key, sha256, *, mismatch='S3 readback checksum mismatch'):
    response = s3.get_object(Bucket=bucket, Key=key)
    try:
        actual = hashlib.sha256()
        for chunk in response['Body'].iter_chunks(1024 * 1024):
            actual.update(chunk)
        if actual.hexdigest() != sha256:
            raise ValueError(mismatch)
    finally:
        response['Body'].close()


def put_immutable_checked(s3, bucket, key, body, content_type, sha256, *, size=None,
                          mismatch='S3 readback checksum mismatch'):
    """Verify a new single-part object on PUT, or verify existing bytes on collision."""
    checksum = base64.b64encode(bytes.fromhex(sha256)).decode('ascii')
    length = {} if size is None else {'ContentLength': size}
    try:
        result = s3.put_object(Bucket=bucket, Key=key, Body=body,
            ContentType=content_type, ServerSideEncryption='AES256', IfNoneMatch='*',
            Metadata={'sha256': sha256}, ChecksumSHA256=checksum, **length)
    except ClientError as error:
        if error.response['Error']['Code'] not in {'412', 'PreconditionFailed'}:
            raise
    else:
        confirmed = result.get('ChecksumSHA256')
        if confirmed == checksum:
            return 'put_checksum'
        if isinstance(confirmed, str) and confirmed:
            raise ValueError(mismatch)
    # A response without the checksum or a pre-existing key still needs proof.
    verify_readback(s3, bucket, key, sha256, mismatch=mismatch)
    return 'readback'
