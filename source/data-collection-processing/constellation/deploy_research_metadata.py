"""Install the research feed intake adapter and register its two contracts."""

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shlex

from constellation.control import Control
from constellation.deploy_research_feeds import execute
from constellation.worker import put_verified
from metadata_engine.controller import register_contract
from metadata_engine.research_feeds import DATASETS, FORM, PREFIX, discover
from metadata_engine.runtime_db import Database

ROOT = Path(__file__).resolve().parents[1]
MODULE = 'metadata_engine/research_feeds.py'
WORKER_EDITS = {
    'worker.py': [
        ("    job={**job,'input_format':input_form.split(':')[0]}\n",
         "    job={**job,'input_format':input_form.split(':')[0]}\n"
         "    if job['input_format'] == 'research_feed':\n"
         "        from metadata_engine.research_feeds import load_batch\n"
         "        return load_batch(s3, bucket, job)\n"),
        ("        total=len(rows);rows=rows[offset:offset+32]\n",
         "        batch_size = 128 if job['input_format'].split('@')[0] == 'research_feed' else 32\n"
         "        total=len(rows);rows=rows[offset:offset+batch_size]\n"
         "        input_sha256 = hashlib.sha256(raw).hexdigest()\n"),
        ("'sha256':hashlib.sha256(raw).hexdigest(),'origin':'first_party_source',",
         "'sha256':input_sha256,'origin':'first_party_source',"),
    ],
    'evidence.py': [
        ("def evidence_for(record,contract,s3,bucket):\n    source=record.get('source') or record.get('source_key')\n",
         "def evidence_for(record,contract,s3,bucket):\n    source=record.get('source') or record.get('source_key')\n"
         "    if contract.get('adapter') == 'research_feed':\n"
         "        from metadata_engine.research_feeds import evidence\n"
         "        return evidence(record, s3, bucket)\n"),
    ],
    'labelling.py': [
        ("    base[\"payload_hash\"] = \"sha256:\" + digest(payload)\n",
         "    if contract['adapter'] == 'research_feed':\n"
         "        base['completeness_scope'] = contract['completeness_scope']\n"
         "        base['quality_flags'].append('provider_metadata_scope')\n"
         "    base[\"payload_hash\"] = \"sha256:\" + digest(payload)\n"),
    ],
}
CONTROLLER_EDITS = {
    'controller.py': [
        ("        if not source:continue\n",
         "        if not source:continue\n"
         "        if db.config['contracts'].get(source, {}).get('adapter') == 'research_feed':continue\n"),
        ("        if policy['state'] in ('owner_paused','access_layer'):continue\n",
         "        if policy['state'] in ('owner_paused','access_layer') or policy.get('adapter') == 'research_feed':continue\n"),
        ("            result=json.loads(row['result_json']) if row['result_json'] else {}\n",
         "            if db.config['contracts'].get(row['source_key'], {}).get('adapter') == 'research_feed':continue\n"
         "            result=json.loads(row['result_json']) if row['result_json'] else {}\n"),
        ("def main():\n", "def main():\n    from metadata_engine.research_feeds import discover as research_feed_discovery\n"),
        ("('daily_intake',lambda:committed_daily_intake(db,s3)),",
         "('research_feed_discovery',lambda:research_feed_discovery(db,s3,include_daily=not args.no_daily)),"
         "('daily_intake',lambda:committed_daily_intake(db,s3)),"),
    ],
}

INSTALL = '''
import hashlib, json, os, stat, tempfile
from pathlib import Path
import boto3

root = Path(SETTINGS['root'])
s3 = boto3.client('s3', region_name='us-east-1')
source = SETTINGS['object']
bucket, key = source['uri'].removeprefix('s3://').split('/', 1)
with s3.get_object(Bucket=bucket, Key=key)['Body'] as stream:
    module = stream.read()
assert hashlib.sha256(module).hexdigest() == source['sha256']
changes = {root / 'metadata_engine/research_feeds.py': module}
for name, replacements in SETTINGS['edits'].items():
    path = root / 'metadata_engine' / name
    before = path.read_text()
    after = before
    for old, new in replacements:
        if new in after:
            continue
        if after.count(old) != 1:
            raise RuntimeError(f'Cannot locate exact edit in {path}: {old[:72]}')
        after = after.replace(old, new, 1)
    if before != after:
        changes[path] = after.encode()
cfg_path = root / 'config/metadata-engine.json'
cfg = json.loads(cfg_path.read_text())
for source, contract in SETTINGS['contracts'].items():
    cfg['contracts'][source] = contract
    cfg['verified_source_failure_handling'][source] = 'queue_by_source_date'
changes[cfg_path] = (json.dumps(cfg, indent=2) + '\\n').encode()
for path, body in changes.items():
    if path.suffix == '.py':
        compile(body, str(path), 'exec')
for path, body in changes.items():
    if path.exists() and path.read_bytes() == body:
        continue
    info = path.stat() if path.exists() else (path.parent / '__init__.py').stat()
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name+'.', delete=False) as out:
        out.write(body)
    os.chown(out.name, info.st_uid, info.st_gid)
    os.chmod(out.name, stat.S_IMODE(info.st_mode))
    Path(out.name).replace(path)
    print(f'Installed and verified {path}')
'''


def install_command(root, python, artifact, edits, contracts):
    settings = {'root': root, 'object': artifact, 'edits': edits, 'contracts': contracts}
    code = 'SETTINGS = ' + repr(settings) + '\n' + INSTALL
    wire = base64.b64encode(code.encode()).decode()
    return f"{python} -B -c " + shlex.quote(f"import base64;exec(base64.b64decode({wire!r}))")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=('install', 'queue', 'recover'))
    args = parser.parse_args()
    control = Control()
    config = json.loads((ROOT / 'config/metadata-engine.json').read_text())
    contracts = {source: config['contracts'][source] for source in DATASETS}
    if args.step in ('queue', 'recover'):
        db = Database(config, control.session)
        if args.step == 'queue':
            with db.tx() as cursor:
                for contract in contracts.values():
                    register_contract(db, contract, cursor)
            print(json.dumps(discover(db, control.s3)), flush=True)
        else:
            results = {}
            for source, contract in contracts.items():
                with db.tx() as cursor:
                    params = (source, contract['contract_version'], FORM + '%', f'{PREFIX}/records/{source}/%')
                    cursor.execute("""UPDATE engine_jobs SET state='queued',reason=NULL,available_after=UTC_TIMESTAMP(6)
                        WHERE source_key=%s AND contract_version=%s AND input_format LIKE %s AND input_key LIKE %s
                          AND state='uncommitted' AND reason='unknown_input_format'""", params)
                    recovered = cursor.rowcount
                    cursor.execute("""UPDATE engine_jobs SET priority=20
                        WHERE source_key=%s AND contract_version=%s AND input_format LIKE %s AND input_key LIKE %s
                          AND state='queued' AND priority<20""", params)
                    results[source] = {'requeued': recovered, 'priorities_aligned': cursor.rowcount}
                    history = (*params[:3], f'{PREFIX}/records/{source}/historical/%')
                    cursor.execute("""SELECT 1 FROM engine_jobs
                        WHERE source_key=%s AND contract_version=%s AND input_format LIKE %s AND input_key LIKE %s
                          AND (state IN ('accepted','running') OR (state='queued' AND priority=21)) LIMIT 1""", history)
                    if not cursor.fetchone():
                        cursor.execute("""UPDATE engine_jobs SET priority=21
                            WHERE source_key=%s AND contract_version=%s AND input_format LIKE %s AND input_key LIKE %s
                              AND state='queued' ORDER BY created_at,job_id LIMIT 1""", history)
                        results[source]['historical_verification_job'] = cursor.rowcount
            print(json.dumps(results), flush=True)
        return
    module = (ROOT / MODULE).read_bytes()
    sha = hashlib.sha256(module).hexdigest()
    artifact = put_verified(control, f"{control.config['prefix']}/deployments/research-metadata/{sha}.py",
                            module, 'application/octet-stream')
    changes = [
        ('worker_instance_id', '/opt/constellation/metadata-engine-runtime',
         '/opt/constellation/legacy-venv/bin/python', WORKER_EDITS),
        ('controller_instance_id', '/home/ec2-user/data-collection-processing',
         '/home/ec2-user/data-collection-processing/.venv-athena/bin/python', CONTROLLER_EDITS),
    ]
    ssm = control.session.client('ssm')
    with ThreadPoolExecutor(max_workers=2) as pool:
        calls = [pool.submit(execute, ssm, control.config[target],
                             [install_command(root, python, artifact, edits, contracts)], 120)
                 for target, root, python, edits in changes]
        for call in calls:
            call.result()


if __name__ == '__main__':
    main()
