"""Deploy bounded large/light capture lanes to the resized M7 worker."""
import base64
import hashlib

from constellation.finish_aux_migration import M7, ROOT, remote


def main():
    body = (ROOT / 'm7_capture_worker.py').read_bytes()
    encoded = base64.b64encode(body).decode()
    checksum = hashlib.sha256(body).hexdigest()
    remote(M7, """import base64, hashlib, os, stat, subprocess, tempfile
from pathlib import Path
p = Path('/opt/constellation/capture-workers/source/m7_capture_worker.py')
body = base64.b64decode(BODY)
assert hashlib.sha256(body).hexdigest() == SHA
compile(body, str(p), 'exec')
fd, temporary = tempfile.mkstemp(prefix=p.name + '.', dir=p.parent)
try:
    with os.fdopen(fd, 'wb') as out:
        out.write(body); out.flush(); os.fsync(out.fileno())
    os.chmod(temporary, stat.S_IMODE(p.stat().st_mode)); os.chown(temporary, 1000, 1000)
    os.replace(temporary, p)
finally:
    if os.path.exists(temporary): os.unlink(temporary)
dropin = Path('/etc/systemd/system/constellation-workers-capture.slice.d/90-concurrent-lanes.conf')
dropin.parent.mkdir(parents=True, exist_ok=True)
dropin.write_text('[Slice]\\nCPUQuota=500%\\nMemoryHigh=17G\\nMemoryMax=20G\\nMemorySwapMax=0\\n')
subprocess.run(['systemctl','daemon-reload'], check=True)
subprocess.run(['systemd-analyze','verify','constellation-workers-capture.slice'], check=True)
print('deployed_sha256=' + SHA)
""".replace('BODY', repr(encoded)).replace('SHA', repr(checksum)))


if __name__ == '__main__':
    main()
