"""Atomically deploy the controller-side M7 lifecycle policy."""
import base64
import hashlib
from pathlib import Path

from constellation.finish_aux_migration import ROOT, T3, remote


def main():
    body = (ROOT / 'constellation/m7_lifecycle.py').read_bytes()
    encoded = base64.b64encode(body).decode()
    checksum = hashlib.sha256(body).hexdigest()
    remote(T3, """import base64, hashlib, os, stat, tempfile
from pathlib import Path
p = Path('/home/ec2-user/data-collection-processing/constellation/m7_lifecycle.py')
body = base64.b64decode(BODY)
assert hashlib.sha256(body).hexdigest() == SHA
compile(body, str(p), 'exec')
fd, temporary = tempfile.mkstemp(prefix=p.name + '.', dir=p.parent)
try:
    with os.fdopen(fd, 'wb') as out:
        out.write(body)
        out.flush()
        os.fsync(out.fileno())
    os.chmod(temporary, stat.S_IMODE(p.stat().st_mode))
    os.chown(temporary, 1000, 1000)
    os.replace(temporary, p)
finally:
    if os.path.exists(temporary):
        os.unlink(temporary)
print('deployed_sha256=' + SHA)
""".replace('BODY', repr(encoded)).replace('SHA', repr(checksum)))


if __name__ == '__main__':
    main()
