"""One host-wide request gate for USPTO collectors; credentials never enter state."""
import fcntl
import json
import os
from pathlib import Path
import time

PATH = Path(__file__).resolve().parent / '.uspto-request-gate.json'


def pace(path=PATH, interval=2.0, clock=time.time, sleeper=time.sleep):
    if os.environ.get('CONSTELLATION_SHARED_HTTP_LIMITS') == '1':
        from constellation.shared_limits import admit
        admit('https://api.uspto.gov/')
        return
    # A separate lock inode survives atomic state replacement. Waiting reserves
    # a slot across processes; the network request itself does not hold the lock.
    path = Path(path)
    if os.environ.get('OPTIMA_S3_RUNTIME') == '1':
        # Atomic replacement must target RAM, not overwrite the read-only root symlink.
        from s3_runtime_fs import hydrate
        path = hydrate(path) or path
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        prior = json.loads(path.read_text()) if path.exists() else {}
        current = clock()
        slot = max(current, prior.get('next_request_at', 0))
        temporary = path.with_name(path.stem + '.pending.json') if os.environ.get('OPTIMA_S3_RUNTIME') == '1' else path.with_suffix('.tmp')
        with temporary.open('w') as handle:
            json.dump({'next_request_at': slot + interval}, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    sleeper(max(0, slot - clock()))
