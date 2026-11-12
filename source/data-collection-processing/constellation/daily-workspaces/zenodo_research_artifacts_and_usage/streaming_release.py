"""Bounded-memory immutable Parquet upload and full checksum read-back."""
import hashlib
import os
from pathlib import Path
import shutil
import tempfile

from collection_storage import checked_key, write_checked


def stream_digest(handle):
    checksum = hashlib.sha256(); size = 0
    while True:
        chunk = handle.read(1024 * 1024)
        if not chunk:
            break
        checksum.update(chunk); size += len(chunk)
    return checksum.hexdigest(), size


def file_digest(path):
    with Path(path).open('rb') as handle:
        return stream_digest(handle)


def remote_digest(store, key):
    if hasattr(store, 'root'):
        return file_digest(store.root / checked_key(key))
    response = store.client.get_object(**store._args(key))
    handle = response['Body']
    try:
        return stream_digest(handle)
    finally:
        handle.close()


def upload(store, key, path, expected):
    try:
        if hasattr(store, 'root'):
            target = store.root / checked_key(key); target.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(dir=target.parent)
            os.close(fd)
            try:
                shutil.copyfile(path, temporary)
                os.link(temporary, target)  # immutable create; never replace
            finally:
                os.unlink(temporary)
        else:
            with Path(path).open('rb') as handle:
                store.put(key, handle, content_type='application/vnd.apache.parquet')
    except Exception:
        # Resolve retries and ambiguous writes only after checking every byte.
        try:
            if remote_digest(store, key) == expected:
                return
        except Exception:
            pass
        raise
    if remote_digest(store, key) != expected:
        raise ValueError('Uploaded Parquet checksum mismatch')


def publish(store, root, report):
    root = Path(root)
    for info in report['files'].values():
        if file_digest(root / checked_key(info['path'])) != (info['sha256'], info['bytes']):
            raise ValueError('Local release changed after validation')
    for info in report['files'].values():
        upload(store, report['release_prefix'] + '/' + info['path'], root / info['path'],
               (info['sha256'], info['bytes']))
    for name in ('tables.sql', 'queries.sql', 'release.json'):
        write_checked(store, report['release_prefix'] + '/' + name, (root / name).read_bytes())
