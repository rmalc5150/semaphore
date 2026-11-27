"""Preserve a verified, credential-scanned source snapshot when GitHub is unavailable."""
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
from datetime import datetime, timezone

from backup import BRANCH, REMOTE, ROOT, collect


def main():
    files = collect()  # Keep exactly the production selection and credential checks.
    checked = datetime.now(timezone.utc)
    destination = ROOT / 'code-backup/.pending'
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    archive = destination / ('source-' + checked.strftime('%Y-%m-%dT%H%M%S%fZ') + '.tar.gz')
    partial = archive.with_suffix('.partial')
    manifest = [{'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
                for path, data, _ in files]
    try:
        with partial.open('xb') as output:
            os.chmod(partial, 0o600)
            with tarfile.open(fileobj=output, mode='w:gz') as tar:
                for path, data, executable in files:
                    info = tarfile.TarInfo('source/' + str(path))
                    info.size = len(data)
                    info.mode = 0o755 if executable else 0o644
                    tar.addfile(info, io.BytesIO(data))
                data = (json.dumps(manifest, indent=2) + '\n').encode()
                info = tarfile.TarInfo('manifest.json')
                info.size = len(data)
                info.mode = 0o600
                tar.addfile(info, io.BytesIO(data))
            output.flush()
            os.fsync(output.fileno())
        with tarfile.open(partial, 'r:gz') as tar:
            saved_manifest = json.load(tar.extractfile('manifest.json'))
            assert saved_manifest == manifest, 'Snapshot manifest mismatch'
            assert len(tar.getmembers()) == len(files) + 1, 'Unexpected snapshot members'
            for entry in saved_manifest:
                body = tar.extractfile('source/' + entry['path']).read()
                assert len(body) == entry['bytes'], 'Snapshot size mismatch: ' + entry['path']
                assert hashlib.sha256(body).hexdigest() == entry['sha256'], 'Snapshot checksum mismatch: ' + entry['path']
        partial.replace(archive)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    sha = hashlib.sha256()
    with archive.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            sha.update(block)
    receipt = {'checked_at': checked.isoformat(), 'archive': str(archive),
               'archive_sha256': sha.hexdigest(), 'archive_bytes': archive.stat().st_size,
               'files': len(files), 'source_bytes': sum(len(data) for _, data, _ in files),
               'credential_scan': 'passed', 'all_members_verified': True,
               'remote': REMOTE, 'branch': BRANCH, 'uploaded': False}
    receipt_path = archive.with_suffix('.receipt.json')
    with receipt_path.open('x') as output:
        os.chmod(receipt_path, 0o600)
        json.dump(receipt, output, indent=2)
        output.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
