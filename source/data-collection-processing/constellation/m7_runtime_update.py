"""Stage the reviewed EDINET and historical worker changes for M7's next wake."""
import fcntl
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PENDING = ROOT / 'constellation/autostop/m7-edinet-runtime.pending.json'

INSTALL = '''
import json, os, shutil
from pathlib import Path

def install_runtime_update(edits):
    root = Path('/opt/constellation')
    if not (root / 'batch-paused').exists():
        return {'status': 'waiting_for_pause'}
    config = json.loads((root / 'metadata-engine-runtime/config/metadata-engine.json').read_text())
    if config.get('verified_source_failure_handling', {}).get('edinet_filings') != 'queue_by_source_date':
        raise RuntimeError('EDINET must use its reviewed source-date failure policy')
    changes = []
    for name, sections in edits.items():
        path = root / name
        original = path.read_text()
        updated = original
        for start, end, replacement in sections:
            left = updated.index(start)
            right = updated.index(end, left)
            updated = updated[:left] + replacement + updated[right:]
        compile(updated, str(path), 'exec')
        if updated != original:
            changes.append((path, updated, path.stat()))
    for path, data, info in changes:
        backup = path.with_name(path.name + '.before-edinet-concurrency')
        if not backup.exists():
            shutil.copy2(path, backup)
        temporary = path.with_suffix('.edinet-new')
        temporary.write_text(data)
        os.chown(temporary, info.st_uid, info.st_gid)
        os.chmod(temporary, info.st_mode & 0o777)
        temporary.replace(path)
        if path.read_text() != data:
            raise RuntimeError('Staged runtime readback mismatch: ' + str(path))
    return {'status': 'applied', 'files_changed': len(changes)}

try:
    runtime_update = install_runtime_update(EDITS)
except (OSError, ValueError, SyntaxError, RuntimeError) as error:
    runtime_update = {'status': 'failed', 'error': str(error)[:500]}
'''


def program(plan):
    return INSTALL.replace('EDITS', repr(plan))


def stage():
    targets = (
        ('metadata-engine-runtime/metadata_engine/runtime_db.py', 'metadata_engine/runtime_db.py', (
            ('    def enqueue(', '    def stats('),
        )),
        ('constellation/control.py', 'constellation/control.py', (
            ('    def defer(', '    def reconcile('),
        )),
        ('constellation/legacy_worker.py', 'constellation/legacy_worker.py', (
            ('STOP=', 'def main():'),
        )),
        ('summary-worker/constellation/database_diagnostic.py', 'constellation/database_diagnostic.py', (
            ("        elif phase.endswith('_failures'):", "        else:raise ValueError('Unknown database diagnostic phase: "),
        )),
    )
    plan = {}
    for destination, source, markers in targets:
        text = (ROOT / source).read_text()
        sections = []
        for start, end in markers:
            left = text.index(start)
            sections.append((start, end, text[left:text.index(end, left)]))
        plan[destination] = sections
    compile(program(plan), str(PENDING), 'exec')
    with PENDING.with_name('m7-lifecycle.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        temporary = PENDING.with_suffix('.new')
        temporary.write_text(json.dumps(plan) + '\n')
        temporary.replace(PENDING)
    print(PENDING)


if __name__ == '__main__':
    stage()
