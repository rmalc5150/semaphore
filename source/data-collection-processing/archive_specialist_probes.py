"""Copy bounded validation evidence to AWS and queue only exhausted scopes."""
import hashlib
import json
from collection_storage import StorageSettings, now, write_checked, write_json
from research_contract import digest
from specialist_inputs import OUT, discover_children


def main():
    settings = StorageSettings.load('config/collection-storage.s3.json')
    store = settings.store()
    root = OUT / 'schema-probes'
    files = []
    # Never replace operational checkpoints with local validation checkpoints.
    for prefix in ('source_documents', 'raw', 'manifests'):
        for path in sorted((root / prefix).rglob('*')):
            if not path.is_file(): continue
            key = path.relative_to(root).as_posix()
            raw = path.read_bytes(); checksum = hashlib.sha256(raw).hexdigest()
            write_checked(store, key, raw)
            check = store.get(key)
            if check is None or hashlib.sha256(check.body).hexdigest() != checksum:
                raise RuntimeError('S3 evidence readback mismatch')
            files.append({'key': key, 'sha256': checksum, 'bytes': len(raw)})
    rows = json.loads((OUT / 'schema-probes.json').read_text())
    rows += json.loads((OUT / 'schema-repairs.json').read_text())
    queued = []
    for row in rows:
        if row['status'] in {'complete', 'partial'} and row.get('records', 0):
            discover_children(store, row['manifest'], row['job'])
        if row['status'] != 'complete': continue
        identity = digest({'validation_manifest': row['manifest']})
        key = 'operations/specialists/publication-queue/' + identity + '.json'
        if store.get(key) is None:
            write_json(store, key, {'window_id': identity, 'manifests': [row['manifest']], 'queued_at': now()})
        queued.append({'source': row['source'], 'records': row.get('records', 0), 'window_id': identity})
    receipt = {'at': now(), 'files': files, 'queued_exhausted_scopes': queued,
               'total_queued_records': sum(r['records'] for r in queued),
               'publication_status': 'queued for shared-lock verified publication; not yet query-certified',
               'bucket': settings.s3_bucket, 'prefix': settings.s3_prefix}
    write_json(store, 'operations/specialists/validation-imports/' + digest(receipt) + '.json', receipt)
    (OUT / 's3-probe-archive.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'files'}), flush=True)


if __name__ == '__main__': main()
