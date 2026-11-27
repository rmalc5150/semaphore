"""Deploy queue claims and metrics after the ready-job index is installed."""
import base64
import argparse
from constellation.finish_aux_migration import ROOT,M7,T3,remote


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before-index',action='store_true',help='Deploy retries and shutdown counting while the index builds')
    args=parser.parse_args()
    text=(ROOT/'metadata_engine/runtime_db.py').read_text()
    method=text[text.index('    def claim(self):'):text.index('    def finish(')]
    worker=(ROOT/'metadata_engine/worker.py').read_text()
    main=worker[worker.index('def main():'):worker.index("if __name__=='__main__':")]
    remote(M7,"""import base64,os,stat,time,json,sys
from pathlib import Path
root=Path('/opt/constellation/metadata-engine-runtime')
def replace_section(p, start_marker, end_marker, encoded, suffix):
    old=p.read_text()
    start=old.index(start_marker);end=old.index(end_marker,start)
    replacement=base64.b64decode(encoded).decode()
    body=old[:start]+replacement+old[end:]
    if body==old: return
    compile(body,str(p),'exec')
    backup=p.with_name(p.name+suffix+str(int(time.time())))
    backup.write_text(old)
    tmp=p.with_suffix('.queue-new');tmp.write_text(body)
    info=p.stat()
    os.chmod(tmp,stat.S_IMODE(info.st_mode));os.chown(tmp,info.st_uid,info.st_gid);os.replace(tmp,p)
    print('Updated '+p.name+'; backup='+str(backup))
if not BEFORE_INDEX:
    sys.path.insert(0,str(root))
    from metadata_engine.runtime_db import Database
    db=Database(json.loads((root/'config/metadata-engine.json').read_text()))
    with db.tx() as cursor:
        cursor.execute("SHOW INDEX FROM engine_jobs WHERE Key_name='source_state_priority'")
        if not cursor.fetchone(): raise RuntimeError('Claim index must be installed before deployment')
    replace_section(root/'metadata_engine/runtime_db.py','    def claim(self):','    def finish(',PAYLOAD,'.before-claim-')
replace_section(root/'metadata_engine/worker.py','def main():',"if __name__=='__main__':",MAIN_BODY,'.before-claim-retry-')
""".replace('PAYLOAD',repr(base64.b64encode(method.encode()).decode())).replace('MAIN_BODY',repr(base64.b64encode(main.encode()).decode())).replace('BEFORE_INDEX',repr(args.before_index)))
    batch=(ROOT/'constellation/m7_batch.py').read_text()
    sections=[(start,end,batch[batch.index(start):batch.index(end,batch.index(start)) if end else None]) for start,end in (
        ('METADATA_PENDING_COUNT = ','def read():'),
        ('def count_pending_metadata(', 'def wake_reason('),
        ('def tick():', '\nif __name__') if '\nif __name__' in batch else ('def tick():', None),
    )]
    remote(T3,"""import base64,fcntl,os,stat,time
from pathlib import Path
p=Path('constellation/m7_batch.py')
with (p.parent/'autostop/m7-lifecycle.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    old=p.read_text()
    body=old
    for marker, boundary, replacement in SECTIONS:
        start=body.index('def metrics(' if marker=='def count_pending_metadata(' and marker not in body else marker)
        end=body.index(boundary,start) if boundary else len(body)
        body=body[:start]+replacement+body[end:]
    if body==old: raise SystemExit(0)
    compile(body,str(p),'exec')
    backup=p.with_name(p.name+'.before-count-'+str(int(time.time())))
    backup.write_text(old)
    tmp=p.with_suffix('.count-new');tmp.write_text(body)
    info=p.stat()
    os.chmod(tmp,stat.S_IMODE(info.st_mode));os.chown(tmp,info.st_uid,info.st_gid);os.replace(tmp,p)
    print('Shutdown queue count updated; backup='+str(backup))
""".replace('SECTIONS',repr(sections)))


if __name__=='__main__':main()
