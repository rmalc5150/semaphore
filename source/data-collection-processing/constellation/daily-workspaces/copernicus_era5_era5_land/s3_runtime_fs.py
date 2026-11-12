"""Lazy, checksum-verified S3 hydration into the pipeline's RAM workspace.

Enabled only for supervised capture processes. The service sandbox makes the
EC2 disk read-only; this module never supplies a disk fallback.
"""
import builtins
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import sqlite3
import threading
from urllib.parse import unquote

ROOT = Path(os.environ.get('OPTIMA_S3_RUNTIME_ROOT', '/home/ec2-user/data-collection-processing/constellation/daily-workspaces/copernicus_era5_era5_land'))
BASE = Path(os.environ.get('OPTIMA_S3_RUNTIME_BASE', '/dev/shm/optima-s3'))
WORK = BASE / 'work'
BUCKET = 'data-collection-059416028963-us-east-1-an'
DATA_DIRS = {'reports', 'mlperf-evidence-cache', 'ted-package-cache', 'collection-output', 'tmp'}
SOURCE_SUFFIXES = {'.py', '.sh', '.sql', '.pem', '.crt', '.key', '.service', '.timer', '.conf', '.slice'}
_OPEN = builtins.open
_IO_OPEN = io.open
_EXISTS = Path.exists
_STAT = Path.stat
_GLOB = Path.glob
_RGLOB = Path.rglob
_CONNECT = sqlite3.connect
_UNLINK = Path.unlink
_INDEX = None
_CLIENT = None
_GUARD = threading.local()


def index():
    global _INDEX
    if _INDEX is None:
        with _OPEN(BASE / 'index.json', 'r') as handle:
            _INDEX = json.load(handle)['paths']
    return _INDEX


def relative(path):
    try:
        value = Path(os.path.abspath(os.fspath(path)))
    except (TypeError, ValueError):
        return None
    for parent in (WORK, ROOT):
        try:
            return value.relative_to(parent).as_posix()
        except ValueError:
            pass
    return None


def target(path, writing=False):
    rel = relative(path)
    if rel is None:
        return None
    parts = PurePosixPath(rel).parts
    if not parts or '..' in parts:
        return None
    first = parts[0]
    is_data = (first in DATA_DIRS or first.endswith('-build') or
               rel in index() or (len(parts) == 1 and Path(rel).suffix in
               {'.sqlite3', '.db', '.json', '.jsonl', '.csv', '.parquet', '.log', '.lock'}) or
               (first == 'config' and Path(rel).name.startswith(
                   ('company-universe.v', 'company-id-registry.', 'company-admission-ledger.'))))
    if not is_data:
        if writing:
            raise PermissionError('Pipeline write outside S3-managed data paths: ' + rel)
        return None
    return WORK / rel


def hydrate(path):
    mapped = target(path)
    if mapped is None:
        return None
    if os.path.exists(mapped):
        return mapped
    rel = mapped.relative_to(WORK).as_posix()
    if os.path.exists(deletion_marker(rel)):
        return mapped
    item = index().get(rel)
    if item is None:
        return mapped
    global _CLIENT
    if _CLIENT is None:
        import boto3
        _CLIENT = boto3.client('s3', region_name='us-east-1')
    lock_name = hashlib.sha256(rel.encode()).hexdigest() + '.lock'
    with _OPEN(BASE / 'locks' / lock_name, 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if os.path.exists(mapped):
            return mapped
        free = os.statvfs(WORK)
        if item['bytes'] + 32 * 1024**2 > free.f_bavail * free.f_frsize:
            raise OSError('RAM workspace budget exceeded; refusing any EC2-disk fallback')
        mapped.parent.mkdir(parents=True, exist_ok=True)
        temporary = mapped.with_name(mapped.name + '.hydrate-' + str(os.getpid()))
        response = _CLIENT.get_object(Bucket=BUCKET, Key=item['key'])
        checksum = hashlib.sha256()
        count = 0
        try:
            with _OPEN(temporary, 'wb') as handle:
                for chunk in response['Body'].iter_chunks(chunk_size=1024 * 1024):
                    handle.write(chunk)
                    checksum.update(chunk)
                    count += len(chunk)
            if count != item['bytes'] or checksum.hexdigest() != item['sha256']:
                raise ValueError('S3 runtime hydration checksum mismatch: ' + rel)
            os.replace(temporary, mapped)
        finally:
            response['Body'].close()
            if os.path.exists(temporary):
                os.unlink(temporary)
    return mapped


def mapped_open(original, file, *args, **kwargs):
    if getattr(_GUARD, 'active', False) or isinstance(file, int):
        return original(file, *args, **kwargs)
    mode = args[0] if args else kwargs.get('mode', 'r')
    writing = any(c in mode for c in 'wax+')
    _GUARD.active = True
    try:
        mapped = target(file, writing=writing)
        if mapped is not None:
            # Appends/read-write operations must preserve the previous version.
            if 'a' in mode or '+' in mode or not writing:
                hydrate(file)
            if writing:
                marker = deletion_marker(mapped.relative_to(WORK).as_posix())
                if os.path.exists(marker):
                    os.unlink(marker)
                mapped.parent.mkdir(parents=True, exist_ok=True)
            file = mapped
        return original(file, *args, **kwargs)
    finally:
        _GUARD.active = False


def stat(path, *args, **kwargs):
    if getattr(_GUARD, 'active', False):
        return _STAT(path, *args, **kwargs)
    _GUARD.active = True
    try:
        mapped = hydrate(path)
        return _STAT(mapped if mapped is not None else path, *args, **kwargs)
    finally:
        _GUARD.active = False


def glob(path, pattern, recursive=False, **kwargs):
    original = _RGLOB if recursive else _GLOB
    seen = set()
    for value in original(path, pattern, **kwargs):
        seen.add(os.fspath(value))
        yield value
    rel = relative(path)
    if rel is None:
        return
    for name in index():
        if os.path.exists(deletion_marker(name)):
            continue
        try:
            child = PurePosixPath(name).relative_to(PurePosixPath(rel))
        except ValueError:
            continue
        if (child.match(pattern) and (recursive or '/' in pattern or len(child.parts) == 1)):
            value = path / str(child)
            if os.fspath(value) not in seen:
                seen.add(os.fspath(value))
                yield value


def connect(database, *args, **kwargs):
    value = os.fspath(database) if not isinstance(database, str) else database
    if value == ':memory:':
        return _CONNECT(database, *args, **kwargs)
    uri = value.startswith('file:')
    name, separator, query = value[5:].partition('?') if uri else (value, '', '')
    name = unquote(name)
    if relative(name) is not None:
        mapped = hydrate(name)
        if mapped is None:
            mapped = target(name, writing=True)
        mapped.parent.mkdir(parents=True, exist_ok=True)
        database = mapped.as_uri() + (separator + query if separator else '') if uri else str(mapped)
    return _CONNECT(database, *args, **kwargs)


def deletion_marker(rel):
    return BASE / 'deletions' / (hashlib.sha256(rel.encode()).hexdigest() + '.json')


def unlink(path, missing_ok=False):
    mapped = target(path, writing=True)
    if mapped is None:
        return _UNLINK(path, missing_ok=missing_ok)
    rel = mapped.relative_to(WORK).as_posix()
    marker = deletion_marker(rel)
    known = rel in index() and not os.path.exists(marker)
    if not os.path.exists(mapped) and not known and not missing_ok:
        raise FileNotFoundError(str(path))
    if os.path.lexists(mapped):
        os.unlink(mapped)
    with _OPEN(marker, 'w') as handle:
        json.dump({'path': rel}, handle)


def install():
    builtins.open = lambda file, *a, **kw: mapped_open(_OPEN, file, *a, **kw)
    io.open = lambda file, *a, **kw: mapped_open(_IO_OPEN, file, *a, **kw)
    Path.stat = stat
    Path.unlink = unlink
    Path.glob = lambda path, pattern, **kw: glob(path, pattern, **kw)
    Path.rglob = lambda path, pattern, **kw: glob(path, pattern, recursive=True, **kw)
    sqlite3.connect = connect
