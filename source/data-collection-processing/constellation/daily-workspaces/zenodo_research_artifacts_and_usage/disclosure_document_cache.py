"""Reuse checksummed original reports across disclosure runs; never treat cache loss as source loss."""
import json
from pathlib import Path
import sqlite3

from research_contract import ROOT, digest


def connect(store):
    local = getattr(store, 'root', None)
    path = Path(local) / '.disclosure-document-cache.sqlite3' if local else ROOT / 'disclosure-document-cache.sqlite3'
    namespace = digest({'root': str(local), 'bucket': getattr(store, 'bucket', None), 'prefix': getattr(store, 'prefix', None)})
    db = sqlite3.connect(path, timeout=30)
    db.execute('CREATE TABLE IF NOT EXISTS originals (namespace TEXT, url TEXT, reference TEXT, PRIMARY KEY(namespace,url))')
    db.execute('CREATE TABLE IF NOT EXISTS indexed_batches (namespace TEXT, key TEXT, PRIMARY KEY(namespace,key))')
    return db, namespace


def remember(store, reference):
    db, namespace = connect(store)
    try:
        with db:
            db.execute('INSERT OR REPLACE INTO originals VALUES (?,?,?)',
                (namespace, reference['source_url'], json.dumps(reference)))
    finally:
        db.close()


def lookup(store, url):
    db, namespace = connect(store)
    try:
        row = db.execute('SELECT reference FROM originals WHERE namespace=? AND url=?', (namespace, url)).fetchone()
        if not row:
            return None
        reference = json.loads(row[0])
    finally:
        db.close()
    from disclosure_collection import get_bytes
    # A corrupt or missing referenced original must fail visibly, not be silently replaced.
    return get_bytes(store, reference['key'], reference['sha256']), reference


def seed_batch(store, batch):
    db, namespace = connect(store)
    try:
        if db.execute('SELECT 1 FROM indexed_batches WHERE namespace=? AND key=?', (namespace, batch['key'])).fetchone():
            return 0
        from disclosure_collection import get_bytes
        raw = get_bytes(store, batch['key'], batch['sha256'])
        references = []
        for line in raw.splitlines():
            record = json.loads(line)
            if record['source'] != 'disclosure_documents':
                continue
            for ref in record['payload'].get('source_evidence', []):
                if ref['key'].startswith('source_documents/disclosure_documents/') and ref['source_url'] == record['source_url']:
                    references.append(ref)
        with db:
            for ref in references:
                db.execute('INSERT OR IGNORE INTO originals VALUES (?,?,?)', (namespace, ref['source_url'], json.dumps(ref)))
            db.execute('INSERT INTO indexed_batches VALUES (?,?)', (namespace, batch['key']))
        return len(references)
    finally:
        db.close()
