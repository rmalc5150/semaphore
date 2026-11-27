"""Deploy evidence-gated market sources to the existing Constellation services."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import shlex
import time

from constellation.control import Control
from market_source_capture import ACTIVATION, ROUTES, metadata_key, retain_json
from market_source_register import MANIFEST, OWNER_REMOVED, PAID_EXCLUSIONS, catalog_rows, write
from metadata_engine.controller import register_contract
from metadata_engine.market_sources import contracts
from metadata_engine.runtime_db import Database
from source_pauses import is_paused


ROOT = Path(__file__).resolve().parents[2]
PILOTS = ROOT/'config/market-source-pilots.v1.json'
CUTOFF = '2026-11-21'
MAX_HISTORY_BATCH = 3


def activation():
    pilots = json.loads(PILOTS.read_text())
    result = {}
    for profile in json.loads(ROUTES.read_text())['routes']:
        if profile['catalog_entry'] in OWNER_REMOVED or profile['catalog_entry'] in PAID_EXCLUSIONS:
            continue
        source, dataset = profile['source'], profile['dataset']
        if is_paused(source):
            continue
        outcomes = pilots.get(source,{}).get(dataset,{})
        verified = [mode for mode,value in outcomes.items() if value.get('receipt')]
        if not verified:
            continue
        modes = [] if profile.get('throughput_hold') else verified
        result.setdefault(source,{})[dataset]={'modes':sorted(modes),'metadata':profile['metadata_eligible']}
    return result


def public_specs(active, catalogue):
    names = {row['source_key']:row for row in catalogue}
    return [
        {'source':source,'catalog_entry':names[source]['catalog_entry'],
         'name':names[source]['catalog_name'],'market_workbook':True,
         'daily_execution':'controller','seeds':[],'scope_note':'Evidence-gated provider capture from the market workbook.'}
        for source,datasets in active.items() if any('daily' in v['modes'] for v in datasets.values())
    ]


def historical_specs(active, catalogue):
    names = {row['source_key']:row for row in catalogue}
    return [
        {'unit':f'constellation-public-{source}.service','catalog_entry':names[source]['catalog_entry'],
         'market_workbook_source':source,'route_kind':'independent_public_historical',
         'argv':['market_source_capture.py','collect','--source',str(names[source]['catalog_entry']),
                 '--mode','historical','--limit',str(MAX_HISTORY_BATCH)],
         'start_target':'2016-01-01','end_exclusive':CUTOFF,'cadence_seconds':900,
         'timeout_seconds':480,'execution_enabled':True,'activation_staged':False,'remaining_requirements':[],
         'validation_basis':'Bounded provider original read back and checksum verified in S3.'}
        for source,datasets in active.items() if any('historical' in v['modes'] for v in datasets.values())
    ]


REMOTE = r"""
import hashlib,json,os,shutil
from pathlib import Path

def atomic(path, body):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.suffix=='.py':
        compile(body,str(path),'exec')
    if path.exists() and path.read_bytes()==body:return
    if path.exists():
        backup=path.with_name(path.name+'.before-market-v1')
        if not backup.exists():
            shutil.copy2(path,backup)
    tmp=path.with_name(path.name+'.market-new')
    tmp.write_bytes(body);os.chown(tmp,1000,1000);os.chmod(tmp,0o644);tmp.replace(path)
    if path.read_bytes()!=body:raise ValueError('deployed file checksum mismatch: '+str(path))

def save_json(path,value):
    atomic(path,(json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode())

def merge(path,field,key,additions):
    data=json.loads(path.read_text())
    rows={row[key]:row for row in data[field]}
    rows.update({row[key]:row for row in additions})
    data[field]=list(rows.values())
    if path.name=='constellation-source-registry.json':data['catalog_entries']=len(data[field])
    save_json(path,data)

def patch(root,name,old,new):
    path=root/name
    body=path.read_text()
    if new in body:return
    if body.count(old)!=1:raise ValueError('unexpected patch context: '+str(path))
    atomic(path,body.replace(old,new,1).encode())

def install_files(root,names):
    for name in names:atomic(root/name,files[name].encode())

def install_metadata(root):
    if not (root/'config/metadata-engine.json').is_file():
        raise ValueError('metadata runtime not found: '+str(root))
    install_files(root,['provider_publication.py','market_source_capture.py','metadata_engine/market_sources.py'])
    for name,old,new in bundle['metadata_patches']:
        patch(root,name,old,new)
    path=root/'config/metadata-engine.json'
    cfg=json.loads(path.read_text())
    cfg['contracts'].update(bundle['contracts'])
    save_json(path,cfg)

files=bundle['files']
config_names=['config/market-source-routes.v1.json','config/market-source-activation.v1.json']
if role=='worker':
    root=Path('/opt/constellation')
    install_metadata(root/'metadata-engine-runtime')
    source=root/'source'
    install_files(source,['provider_publication.py','market_source_capture.py',*config_names])
    for row in bundle['historical']:
        workspace=root/'legacy'/row['unit']
        if not workspace.exists():
            workspace.mkdir()
        for name in ('s3_runtime.py','public_source_capture.py','public_source_scope.py',
                     'provider_tls.py','trade_mining_sources.py','constellation'):
            target=workspace/name
            original=source/name
            if not original.exists() and name=='constellation':original=root/name
            if not original.exists():raise ValueError('required runtime file missing: '+str(original))
            if not target.exists():target.symlink_to(original,target_is_directory=original.is_dir())
        install_files(workspace,['provider_publication.py','market_source_capture.py',*config_names])
        python=workspace/'.venv'
        if not python.exists():
            python.symlink_to(root/'legacy-venv',target_is_directory=True)
        ram=Path('/dev/shm/constellation-legacy')/row['unit']
        (ram/'locks').mkdir(parents=True,exist_ok=True)
        for item in ('reports','mlperf-evidence-cache','ted-package-cache','collection-output'):
            path=workspace/item
            if not path.exists() and not path.is_symlink():path.symlink_to(ram/'work'/item,target_is_directory=True)
        for folder,dirs,filenames in os.walk(workspace):
            os.chown(folder,1000,1000)
            for name in dirs+filenames:os.lchown(Path(folder)/name,1000,1000)
        os.chown(ram,1000,1000);os.chown(ram/'locks',1000,1000)
    merge(root/'config/constellation-legacy-routes.json','routes','unit',bundle['historical'])
else:
    root=Path('/home/ec2-user/data-collection-processing')
    install_metadata(root)
    install_files(root,[*config_names,'config/market-source-register.v1.json'])
    for name,old,new in bundle['controller_patches']:
        patch(root,name,old,new)
    merge(root/'config/constellation-source-registry.json','sources','catalog_entry',bundle['catalogue'])
    merge(root/'config/constellation-public-sources.json','sources','source',bundle['daily'])
    merge(root/'config/constellation-legacy-routes.json','routes','unit',bundle['historical'])
print(json.dumps({'role':role,'daily':len(bundle['daily']),'historical':len(bundle['historical']),'metadata':len(bundle['contracts'])}))
"""


def patches(local_file, name, old_start, new_end):
    body = (ROOT/local_file).read_text()
    start = body.index(old_start)
    stop = body.index(new_end,start)
    return [name,old_start,body[start:stop]]


def deployment_bundle(active, catalogue):
    evidence = patches('metadata_engine/evidence.py','metadata_engine/evidence.py',
        "    source=record.get('source') or record.get('source_key')\n", "    if source == 'us_census_international_trade_api'")
    worker = patches('metadata_engine/worker.py','metadata_engine/worker.py',
        "        for r in rows:\n", "            from metadata_engine.trade_mining")
    collector = patches('public_source_capture.py','public_source_capture.py',
        "    s3 = s3 or boto3.client('s3', region_name='us-east-1')\n", '    # A raw-content revision')
    controller = patches('metadata_engine/controller.py','metadata_engine/controller.py',
        '        if not source:continue\n', '        from metadata_engine.source_policies import PAUSED')
    files=['provider_publication.py','market_source_capture.py','metadata_engine/market_sources.py',str(ROUTES.relative_to(ROOT)),
           str(ACTIVATION.relative_to(ROOT)),str(MANIFEST.relative_to(ROOT))]
    return {'files':{name:(ROOT/name).read_text() for name in files},'catalogue':catalogue,
            'contracts':contracts(ROOT),'daily':public_specs(active,catalogue),
            'historical':historical_specs(active,catalogue),
            'metadata_patches':[evidence,worker],'controller_patches':[collector,controller]}


def wait_ssm(ssm, identity, node):
    for _ in range(190):
        time.sleep(3)
        try:
            result=ssm.get_command_invocation(CommandId=identity,InstanceId=node)
        except ssm.exceptions.InvocationDoesNotExist:
            continue
        if result['Status'] in ('Pending','InProgress','Delayed'):
            continue
        if result['Status'] != 'Success':
            raise RuntimeError(result['Status']+' '+result.get('StandardErrorContent','')[-2000:])
        print(result['StandardOutputContent'],flush=True)
        return
    raise TimeoutError('SSM deployment readback timed out: '+identity)


def deploy(control, bundle, role):
    data = json.dumps(bundle,ensure_ascii=False,sort_keys=True).encode()
    sha = hashlib.sha256(data).hexdigest()
    bucket = control.config['bucket']
    key = control.config['prefix']+'/deployments/market-sources-'+sha+'.json'
    control.s3.put_object(Bucket=bucket,Key=key,Body=data,ServerSideEncryption='AES256')
    boilerplate=f"""
import boto3,json,hashlib
response=boto3.client('s3',region_name='us-east-1').get_object(Bucket={bucket!r},Key={key!r})
body=response['Body'].read()
response['Body'].close()
assert hashlib.sha256(body).hexdigest()=={sha!r}
bundle=json.loads(body)
role={role!r}
"""
    runtime = ('/opt/constellation/.venv/bin/python' if role=='worker' else
               str(ROOT/'.venv-athena/bin/python'))
    encoded = base64.b64encode((boilerplate+REMOTE).encode()).decode()
    command = runtime+' -c '+shlex.quote('import base64;exec(base64.b64decode('+repr(encoded)+'))')
    node = control.config[f'{role}_instance_id']
    ssm = control.session.client('ssm')
    identity = ssm.send_command(InstanceIds=[node],DocumentName='AWS-RunShellScript',
                                Parameters={'commands':[command]},TimeoutSeconds=600)['Command']['CommandId']
    print(json.dumps({'role':role,'command_id':identity}),flush=True)
    wait_ssm(ssm,identity,node)


def seed_catalogue(control, rows):
    with control.db() as cursor:
        cursor.executemany('INSERT IGNORE INTO backfill_sources(catalog_entry,source_key,registry_json) VALUES(%s,%s,%s)',
            [(r['catalog_entry'],r['source_key'],json.dumps(r,ensure_ascii=False)) for r in rows])
        cursor.execute("""SELECT catalog_entry,source_key FROM backfill_sources
            WHERE catalog_entry BETWEEN 159 AND 272
            AND COALESCE(JSON_UNQUOTE(JSON_EXTRACT(registry_json,'$.collector_status')),'') <> 'excluded_owner_removed'""")
        identities = {r['catalog_entry']:r['source_key'] for r in cursor.fetchall()}
        if identities != {r['catalog_entry']:r['source_key'] for r in rows}:
            raise ValueError('catalogue identity mismatch after install')
        cursor.executemany("""UPDATE backfill_sources SET registry_json=JSON_SET(
            registry_json,'$.lineage',%s,'$.related_catalog_entries',CAST(%s AS JSON))
            WHERE catalog_entry=%s AND source_key=%s""",
            [(r['lineage'],json.dumps(r['related_catalog_entries']),r['catalog_entry'],r['source_key']) for r in rows])
        excluded = [r for r in rows if r['catalog_entry'] in PAID_EXCLUSIONS]
        if excluded:
            cursor.executemany("""UPDATE backfill_sources SET registry_json=JSON_SET(
                registry_json,'$.readiness',%s,'$.collector_status',%s,'$.missing_reason',%s)
                WHERE catalog_entry=%s AND source_key=%s""",
                [(r['readiness'],r['collector_status'],r['missing_reason'],r['catalog_entry'],r['source_key'])
                 for r in excluded])


def start_metadata(control, proposed):
    config=json.loads((ROOT/'config/metadata-engine.json').read_text())
    config['contracts'].update(proposed)
    db=Database(config,control.session)
    pilots=json.loads(PILOTS.read_text())
    queued=0
    with db.tx() as cursor:
        for policy in proposed.values():
            register_contract(db,policy,cursor)
    bucket=control.config['bucket']
    for source,policy in proposed.items():
        for dataset in policy['datasets']:
            for outcome in pilots[source][dataset].values():
                receipt=outcome.get('receipt')
                if not receipt:
                    continue
                if not receipt.get('sha256') or not receipt.get('evidence_receipt_key'):
                    raise ValueError('pilot original lacks immutable verification data')
                key=metadata_key(receipt)
                from public_source_capture import read_json
                existing,etag=read_json(control.s3,key)
                if not existing:
                    retain_json(control.s3,bucket,key,receipt)
                    _,etag=read_json(control.s3,key)
                queued+=int(db.enqueue(source,key,etag,'public_receipt',15))
    return queued


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','deploy','verify'])
    parser.add_argument('--output', type=Path)
    args=parser.parse_args()
    if args.action=='verify':
        control=Control()
        db=Database(json.loads((ROOT/'config/metadata-engine.json').read_text()),control.session)
        with db.tx() as cursor:
            cursor.execute("SELECT s.source_key,s.state,j.state AS job_state,COUNT(j.job_id) AS jobs FROM engine_sources s LEFT JOIN engine_jobs j ON j.source_key=s.source_key WHERE s.source_key LIKE 'market\\_source\\_%' GROUP BY s.source_key,s.state,j.state")
            meta=cursor.fetchall()
        with control.db() as cursor:
            cursor.execute("SELECT source_key,status,COUNT(*) AS jobs FROM backfill_jobs WHERE source_key LIKE 'legacy:constellation-public-market%' GROUP BY source_key,status")
            historical=cursor.fetchall()
            cursor.execute("""SELECT COUNT(*) AS sources FROM backfill_sources
                WHERE catalog_entry BETWEEN 159 AND 272
                AND COALESCE(JSON_UNQUOTE(JSON_EXTRACT(registry_json,'$.collector_status')),'') <> 'excluded_owner_removed'""")
            sources=cursor.fetchone()
        from market_source_capture import MARKET
        prefix=f'{MARKET}/state/daily/'
        listing=control.s3.list_objects_v2(Bucket=control.config['bucket'],Prefix=prefix,Delimiter='/')
        daily=[item['Prefix'].removeprefix(prefix).rstrip('/') for item in listing.get('CommonPrefixes',[])]
        expected_sources = sum(1 for _ in catalog_rows(json.loads(MANIFEST.read_text())))
        result={'catalogue':sources,'metadata':meta,'historical':historical,'daily_state_sources':daily,
                'deployed':sources['sources']==expected_sources and bool(meta) and bool(historical)}
        if args.output:
            write(args.output,result)
        print(json.dumps(result,indent=2,default=str))
        return
    active=activation()
    catalogue=list(catalog_rows(json.loads(MANIFEST.read_text())))
    write(ACTIVATION,active)
    bundle=deployment_bundle(active,catalogue)
    if args.action=='prepare':
        print(json.dumps({key:len(bundle[key]) for key in ('catalogue','daily','historical','contracts')}))
        return
    control=Control()
    if not control.allowed() or not control.daily_allowed():
        raise RuntimeError('The existing live collection controls do not currently allow daily and historical dispatch')
    deploy(control,bundle,'worker')
    seed_catalogue(control,catalogue)
    queued=start_metadata(control,bundle['contracts'])
    deploy(control,bundle,'controller')
    from constellation.legacy_dispatch import dispatch
    historical=[dispatch(control,row) for row in bundle['historical']]
    result={'catalog_entries_added':len(catalogue),'daily_sources':len(bundle['daily']),
            'historical_sources':len(bundle['historical']),'metadata_sources':len(bundle['contracts']),
            'metadata_jobs_enqueued':queued,'historical_dispatch':historical}
    write(ROOT/'config/market-source-deployment.v1.json',result)
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    main()
