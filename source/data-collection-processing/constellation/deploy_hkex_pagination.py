"""Deploy the tested bounded HKEX index-snapshot fetch to the auxiliary worker."""
import base64
import hashlib
from pathlib import Path

from constellation.finish_aux_migration import M7, ROOT, remote


def main():
    body = (ROOT / 'disclosure_collection.py').read_bytes()
    encoded = base64.b64encode(body).decode()
    checksum = hashlib.sha256(body).hexdigest()
    remote(M7, """import base64, hashlib, os, stat, subprocess, tempfile
from pathlib import Path
p = Path('/opt/constellation/auxiliary-publication/source/disclosure_collection.py')
old = p.read_text()
assert 'rows, _, done = hkex_page(client, day, {}, 100000, stock_id)' in old, 'unexpected_remote_version'
body = base64.b64decode(BODY)
assert hashlib.sha256(body).hexdigest() == SHA
compile(body, str(p), 'exec')
fd, temporary = tempfile.mkstemp(prefix=p.name + '.', dir=p.parent)
try:
    with os.fdopen(fd, 'wb') as out:
        out.write(body)
        out.flush()
        os.fsync(out.fileno())
    mode = stat.S_IMODE(p.stat().st_mode)
    os.chmod(temporary, mode)
    os.chown(temporary, 1000, 1000)
    os.replace(temporary, p)
finally:
    if os.path.exists(temporary):
        os.unlink(temporary)
subprocess.run(['systemctl', 'reset-failed', 'optima-m7-aux-collection-daily.service'], check=True)
subprocess.run(['systemctl', 'start', '--no-block', 'optima-m7-aux-collection-daily.service'], check=True)
print('deployed_sha256=' + SHA)
""".replace('BODY', repr(encoded)).replace('SHA', repr(checksum)))


if __name__ == '__main__':
    main()
