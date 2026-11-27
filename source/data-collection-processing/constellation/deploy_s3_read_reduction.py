"""Install the scoped S3 read reduction in live runtime copies at normal wake."""
import base64
import contextlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DONE = ROOT/'state'/'s3-read-reduction-m7-complete.json'
TIMER = 'optima-s3-read-reduction-on-wake.timer'
META = '/opt/constellation/metadata-engine-runtime'
PUBLIC = '/opt/constellation/source'
AUX = '/opt/constellation/auxiliary-publication/source'


def section(file, beginning, end):
    text = (ROOT/file).read_text()
    start = text.index(beginning)
    return text[start:text.index(end,start)]


def package(mode):
    parts = {
        'cache':section('metadata_engine/evidence.py','MAX_BODY=', 'def s3_key('),
        'upload':section('constellation/worker.py','def put_verified(', 'def collect('),
        'public':section('public_source_capture.py','            if size < SINGLE_PART_LIMIT:', '            fmt = '),
        'helper':(ROOT/'constellation/s3_integrity.py').read_text(),
    }
    return 'MODE='+repr(mode)+'\nPARTS='+repr(parts)+'\n'+ PROGRAM


PROGRAM = r"""
from pathlib import Path
from hashlib import sha256
import json
import os
import stat
import tempfile
import traceback

base = Path('/opt/constellation')
meta = base/'metadata-engine-runtime'
if MODE == 'arm':
    roots = [meta]
elif MODE == 'm7':
    roots = [meta, base/'source', base/'auxiliary-publication/source']
    # Native constellation-backfill@ services import from the base directory.
    roots.append(base)
    roots.extend(p for p in (base/'legacy').glob('constellation-public-*.service') if p.is_dir())
    if not all(p.is_dir() for p in roots[:3]):
        raise RuntimeError('missing required M7 runtime root')
elif MODE == 'daily':
    roots = sorted(Path('constellation/daily-workspaces').glob('*/'))
else:
    raise ValueError(MODE)
backup = (Path('state/s3-read-reduction-backups') if MODE=='daily'
          else Path('/var/tmp/optima-s3-read-reduction-20261124'))
edits = {}
counts = dict(metadata=0,native=0,public=0)
issues = []

def replace(text, old, new):
    if text.count(old)!=1:
        raise ValueError('no unique required edit marker')
    return text.replace(old,new,1)

def region(text, start, end, new):
    a=text.index(start); b=text.index(end,a)
    return text[:a]+new+text[b:]

def stage(path,text):
    compile(text,str(path),'exec')
    if path.is_file() and path.read_text()==text:return
    edits[path]=text

for root in roots:
    get=(root/'metadata_engine/evidence.py')
    worker=(root/'metadata_engine/worker.py')
    if MODE!='daily' and get.is_file() and worker.is_file():
        try:
            orig=get.read_text()
            if 'def job_evidence_cache(' not in orig:
                orig=replace(orig,'import re\n','import re\nfrom collections import Counter\nfrom contextlib import contextmanager\nfrom contextvars import ContextVar\nfrom pathlib import Path\nimport tempfile\n')
                orig=region(orig,'MAX_BODY=', 'def s3_key(', PARTS['cache'])
            stage(get,orig)
            orig=worker.read_text()
            if 'with job_evidence_cache(rows)' not in orig:
                orig=replace(orig,'import RawFailure,Uncommitted,object_bytes,evidence_for',
                                  'import RawFailure,Uncommitted,object_bytes,evidence_for,job_evidence_cache')
                a=orig.index('        for original in rows:\n')
                b=orig.index('        if document_exclusions:\n',a)
                orig=orig[:a]+'        with job_evidence_cache(rows) as evidence_cache_stats:\n'+''.join(
                    '    '+line if line.strip() else line for line in orig[a:b].splitlines(keepends=True)
                )+"        report['evidence_cache'] = dict(evidence_cache_stats)\n"+orig[b:]
            stage(worker,orig)
            counts['metadata']+=1
        except ValueError as ex:
            edits.pop(get,None);edits.pop(worker,None)
            issues.append((str(root),'metadata',str(ex)[:180]))
    native=root/'constellation/worker.py'
    public=root/'public_source_capture.py'
    if MODE!='daily' and native.is_file():
        try:
            orig=region(native.read_text(),'def put_verified(', 'def collect(', PARTS['upload'])
            stage(root/'constellation/s3_integrity.py',PARTS['helper'])
            stage(native,orig)
            counts['native']+=1
        except ValueError as ex:
            issues.append((str(root),'native',str(ex)[:180]))
    if public.is_file() and MODE!='arm':
        try:
            orig=public.read_text()
            if 'from constellation.s3_integrity import' not in orig:
                orig=replace(orig,'from constellation.shared_limits import admit\n',
                    'from constellation.shared_limits import admit\nfrom constellation.s3_integrity import put_immutable_checked, verify_readback\n')
                orig=replace(orig,'MAX_BYTES = 128 * 1024**2\n','MAX_BYTES = 128 * 1024**2\nSINGLE_PART_LIMIT = 8 * 1024**2\n')
                old_read="        native_body=s3.get_object(Bucket=BUCKET,Key=key)['Body'].read(4*1024*1024+1)\n"
                block=PARTS['public']
                if '            file.flush(); s3.upload_file(' in orig:
                    end="            if actual.hexdigest() != checksum.hexdigest(): raise ValueError('public_readback_checksum_mismatch')\n"
                    a=orig.index('            file.flush(); s3.upload_file(')
                    b=orig.index(end,a)+len(end)
                    upload=block[:block.index("            if html and source['source'] in REGIONAL_KEYS:")]
                    orig=orig[:a]+'            file.flush()\n'+upload+orig[b:]
                elif old_read in orig:
                    orig=replace(orig,old_read,'')
                    orig=region(orig,'            s3.upload_file(file.name, BUCKET, key,','            fmt = ',block)
                else:
                    block=block[:block.index("            if html and source['source'] in REGIONAL_KEYS:")]
                    orig=region(orig,'            s3.upload_file(file.name, BUCKET, key,','            fmt = ',block)
            stage(root/'constellation/s3_integrity.py',PARTS['helper'])
            stage(public,orig)
            counts['public']+=1
        except ValueError as ex:
            issues.append((str(root),'public',str(ex)[:180]))
if MODE in ('arm','m7') and not (counts['metadata'] and counts['native']):
    raise RuntimeError('missing runtime changes '+json.dumps(counts))
# Keep an individual older copy intact if its layout diverges. The main
# worker and the publisher's primary source tree must still be safe to update.
required={str(meta),str(base),str(base/'source')}
if issues and (MODE!='m7' or any(root in required for root,kind,error in issues)):
    raise RuntimeError('unexpected required runtime layouts '+json.dumps(issues[:12]))
backup.mkdir(mode=0o750,exist_ok=True)
for path,text in sorted(edits.items(),key=lambda item:(item[0].name!='s3_integrity.py',str(item[0]))):
    if path.is_file():
        info=path.stat()
        copy=backup/(sha256(str(path.resolve()).encode()).hexdigest()[:16]+'-'+path.name)
        if not copy.exists():copy.write_bytes(path.read_bytes())
    else:
        info=path.parent.stat()
    with tempfile.NamedTemporaryFile('w',dir=path.parent,delete=False) as f:
        tmp=Path(f.name); f.write(text)
    os.chmod(tmp,0o644 if not path.exists() else stat.S_IMODE(info.st_mode))
    if os.geteuid()==0:os.chown(tmp,info.st_uid,info.st_gid)
    tmp.replace(path)
    assert path.read_text()==text
print(json.dumps({'target':MODE,'runtime_copies':counts,'files_changed':len(edits),'skipped_layouts':issues}),flush=True)
"""


def install_on_normal_wake():
    import boto3
    from constellation import finish_aux_migration as runtime
    if DONE.is_file():
        return
    session = boto3.Session(region_name='us-east-1')
    runtime.session=session
    runtime.ssm=session.client('ssm')
    instances=session.client('ec2').describe_instances(InstanceIds=[runtime.M7])['Reservations'][0]['Instances']
    state=instances[0]['State']['Name']
    if state!='running':
        print(json.dumps({'target':'m7','activation':'awaiting_normal_wake','instance_state':state}))
        return
    online=runtime.ssm.describe_instance_information(Filters=[{'Key':'InstanceIds','Values':[runtime.M7]}]).get('InstanceInformationList',[])
    if not online or online[0]['PingStatus']!='Online':
        return
    output=io.StringIO()
    with contextlib.redirect_stdout(output):
        try:runtime.remote(runtime.M7,package('m7'))
        except Exception as error:raise RuntimeError(output.getvalue()[-5000:]) from error
    result=json.loads(output.getvalue())
    assert result['status']=='Success'
    receipt=json.loads(result['out'])
    DONE.write_text(json.dumps({'target':'m7','status':'installed_and_verified',**receipt})+'\n')
    print(json.dumps(receipt))
    subprocess.run(['systemctl','disable','--now',TIMER],check=True)


def main():
    mode=sys.argv[1]
    if mode=='m7-on-wake':
        install_on_normal_wake()
    elif mode=='arm':
        body=base64.b64encode(package(mode).encode()).decode()
        print('/opt/constellation/legacy-venv/bin/python -B -c '+shlex.quote('import base64;exec(base64.b64decode('+repr(body)+'))'))
    elif mode=='daily':
        exec(package(mode),{})
    else:
        raise ValueError(mode)


if __name__=='__main__':
    main()
