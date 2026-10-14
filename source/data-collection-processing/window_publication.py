"""Publish bounded immutable releases as owned, verified Athena partitions."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from pathlib import Path

from botocore.exceptions import ClientError
from collection_operations import load_stored
from collection_storage import now, write_json, write_checked
from research_contract import canonical_json, digest, load_json
import sec_athena_pilot as release


def list_keys(store, settings, prefix):
    if hasattr(store, 'root'):
        return sorted(str(p.relative_to(store.root)) for p in (store.root/prefix).rglob('*.json'))
    base = settings.s3_prefix.rstrip('/')+'/' if settings.s3_prefix else ''
    return sorted(o['Key'][len(base):] for page in store.client.get_paginator('list_objects_v2').paginate(
        Bucket=settings.s3_bucket,Prefix=base+prefix) for o in page.get('Contents',[]) if o['Key'].endswith('.json'))


def descriptor(info):
    return {'Columns':[{'Name':n,'Type':t} for n,t in info['columns']], 'Location':info['location'],
        'InputFormat':'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat',
        'OutputFormat':'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat',
        'SerdeInfo':{'SerializationLibrary':'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'}}


def ensure_catalog(glue, athena, report, owner):
    config=report['config']; db=config['database']; release.validate_config(config)
    try:
        existing=glue.get_database(Name=db)['Database']
        release.require(existing.get('Parameters',{}).get('optima_pilot')==owner,'Database ownership mismatch')
    except ClientError as exc:
        if exc.response['Error']['Code']!='EntityNotFoundException': raise
        glue.create_database(DatabaseInput={'Name':db,'Parameters':{'optima_pilot':owner}})
    output=f"s3://{report['bucket']}/{report['s3_prefix']}/{config['query_results_prefix']}/"
    description=report.get('workgroup_description', 'Optima '+owner+' pilot')
    try:
        wg=athena.get_work_group(WorkGroup=config['workgroup'])['WorkGroup']; wc=wg['Configuration']
        release.require(wg['State']=='ENABLED' and wc.get('EnforceWorkGroupConfiguration') and
            wc['ResultConfiguration']['OutputLocation'].rstrip('/')==output.rstrip('/') and
            wc.get('BytesScannedCutoffPerQuery')==104857600,'Workgroup configuration mismatch')
    except ClientError as exc:
        if exc.response['Error']['Code']!='InvalidRequestException' or 'not found' not in exc.response['Error']['Message'].lower(): raise
        athena.create_work_group(Name=config['workgroup'],Description=description,Configuration={
            'ResultConfiguration':{'OutputLocation':output,'EncryptionConfiguration':{'EncryptionOption':'SSE_S3'}},
            'EnforceWorkGroupConfiguration':True,'BytesScannedCutoffPerQuery':104857600,
            'EngineVersion':{'SelectedEngineVersion':'Athena engine version 3'}})


def deploy_window(store, settings, root, window_id, owner, glue=None, athena=None):
    release.require(bool(re.fullmatch('[0-9a-f]{64}',window_id)), 'Invalid window identity')
    report=load_json(Path(root)/'release.json')
    release.require(report['bucket']==settings.s3_bucket and report['s3_prefix']==settings.s3_prefix,'Destination mismatch')
    release.require(release.get_bytes(store,report['release_prefix']+'/release.json')==(Path(root)/'release.json').read_bytes(),'Release not published')
    if glue is None:
        import boto3
        session=boto3.Session(region_name=report['config']['region']); glue=session.client('glue'); athena=session.client('athena')
    ensure_catalog(glue,athena,report,owner)
    db=report['config']['database']; previous={}; definitions={}
    for name,info in report['files'].items():
        table=name+'_windows'
        sd=descriptor(info)
        definition={'Name':table,'TableType':'EXTERNAL_TABLE','Parameters':{'classification':'parquet','optima_owner':owner},
            'PartitionKeys':[{'Name':'window_id','Type':'string'}],
            'StorageDescriptor':{**sd,'Location':f"s3://{settings.s3_bucket}/{settings.s3_prefix}/curated/{owner}/empty/{table}/"}}
        try:
            old=glue.get_table(DatabaseName=db,Name=table)['Table']
            release.require(old.get('Parameters',{}).get('optima_owner')==owner and
                old['StorageDescriptor']['Columns']==sd['Columns'] and old['PartitionKeys']==definition['PartitionKeys'],'Table contract mismatch')
        except ClientError as exc:
            if exc.response['Error']['Code']!='EntityNotFoundException': raise
            glue.create_table(DatabaseName=db,TableInput=definition)
        try:
            part=glue.get_partition(DatabaseName=db,TableName=table,PartitionValues=[window_id])['Partition']
            release.require(part.get('Parameters',{}).get('optima_owner')==owner,'Partition ownership mismatch')
            previous[table]={k:deepcopy(part[k]) for k in ('Values','StorageDescriptor','Parameters')}
        except ClientError as exc:
            if exc.response['Error']['Code']!='EntityNotFoundException': raise
            previous[table]=None
        definitions[table]={'Values':[window_id],'StorageDescriptor':sd,
                            'Parameters':{'optima_owner':owner,'release_id':report['release_id']}}
    attempted=[]
    try:
        for table,definition in definitions.items():
            attempted.append(table)  # An ambiguous write is also rolled back.
            if previous[table]: glue.update_partition(DatabaseName=db,TableName=table,PartitionValueList=[window_id],PartitionInput=definition)
            else: glue.create_partition(DatabaseName=db,TableName=table,PartitionInput=definition)
        sql=' UNION ALL '.join(f"SELECT '{n}' AS table_name, count(*) AS records FROM {db}.{n}_windows WHERE window_id='{window_id}'" for n in sorted(report['files']))+' ORDER BY table_name'
        result=release.run_query(athena,report,sql)
        expected=[[n,str(report['files'][n]['rows'])] for n in sorted(report['files'])]
        release.require(result['rows']==expected,'Window Athena counts mismatch')
        verification={'status':'verified','window_id':window_id,'release_id':report['release_id'],'checked_at':now(),'query':result}
        body=canonical_json(verification)+b'\n'; key=report['release_prefix']+'/verifications/'+hashlib.sha256(body).hexdigest()+'.json'
        write_checked(store,key,body)
        (Path(root)/'window-verification.json').write_bytes(body)
        return {**verification,'verification_key':key,'verification_sha256':hashlib.sha256(body).hexdigest()}
    except BaseException:
        for table in reversed(attempted):
            if previous[table]: glue.update_partition(DatabaseName=db,TableName=table,PartitionValueList=[window_id],PartitionInput=previous[table])
            else:
                try: glue.delete_partition(DatabaseName=db,TableName=table,PartitionValues=[window_id])
                except ClientError as exc:
                    if exc.response['Error']['Code']!='EntityNotFoundException': raise
        raise


def publish_pending(store,settings,owner,config,prepare,output_root,max_windows=2,window_ids=None):
    outcomes=[]
    blocked_commits = 0
    # Queue inventories grow with every historical window. Read the small
    # metadata objects concurrently so discovery does not monopolize the shared
    # heavy-job lock; preparation, publication and receipt writes stay serial.
    keys = list_keys(store,settings,'operations/'+owner+'/publication-queue/')
    with ThreadPoolExecutor(max_workers=8) as pool:
        queued=list(pool.map(lambda key: load_stored(store,key)[0], keys))
    if owner == 'specialists':
        canonical = {tuple(sorted(q['manifests'])) for q in queued if not q.get('repair_evidence')}
        aliases = [q for q in queued if q.get('repair_evidence') and tuple(sorted(q['manifests'])) in canonical]
        alias_ids = {q['window_id'] for q in aliases}
        queued = [q for q in queued if q['window_id'] not in alias_ids]
        # Retain every object for review, but never publish the same repaired
        # manifest under a second window identity. Existing aliases need review.
        outcomes.extend({'window_id':q['window_id'],'status':'failed',
                         'reason':'duplicate_queue_alias_requires_review'} for q in aliases)
        blocked_commits = len(aliases)
    if window_ids is not None:
        queued = [q for q in queued if q['window_id'] in window_ids]
    def inspect(item):
        receipt_key='operations/'+owner+'/publication-receipts/'+item['window_id']+'.json'
        receipt,token=load_stored(store,receipt_key)
        source_hash=digest({'manifests':item['manifests'],'config':config,'curation_version':'window-publication-1.0'})
        done = bool(receipt and receipt['source_hash']==source_hash)
        if done:
            obj=store.get(receipt['verification_key'])
            release.require(obj is not None and hashlib.sha256(obj.body).hexdigest()==receipt['verification_sha256'],'Missing publication receipt evidence')
        return item, receipt_key, receipt, token, source_hash, done

    def candidates():
        ordered = sorted(queued,key=lambda row:(row.get('queued_at',''),row['window_id']))
        with ThreadPoolExecutor(max_workers=8) as pool:
            for offset in range(0, len(ordered), 32):
                # Bound look-ahead; never fan out expensive publication work.
                yield from pool.map(inspect, ordered[offset:offset+32])

    with closing(candidates()) as pending:
        for item, receipt_key, receipt, token, source_hash, done in pending:
            if done:
                continue
            retry_key='operations/'+owner+'/publication-retries/'+item['window_id']+'.json'
            retry,retry_token=load_stored(store,retry_key)
            if retry and retry.get('source_hash')==source_hash and retry['retry_after']>now():
                continue
            # Invalid legacy queue entries remain failures, but must not starve
            # valid committed windows on every scheduled specialist run.
            if len(outcomes)-blocked_commits>=max_windows or blocked_commits>=64: break
            try:
                print(json.dumps({'stage':'preparing_window','owner':owner,
                    'window_id':item['window_id'],'manifests':item['manifests']}), flush=True)
                root=prepare(store,settings,config,item['manifests'],output_root)
                release.publish(store,settings,root)
                verification=deploy_window(store,settings,root,item['window_id'],owner)
                write_json(store,receipt_key,{**verification,'source_hash':source_hash,'manifests':item['manifests']},token)
                outcomes.append({'window_id':item['window_id'],'status':'verified','release_id':verification['release_id']})
            except Exception as exc:
                failure={'window_id':item['window_id'],'status':'failed','error_type':type(exc).__name__,'message':str(exc)[:500],'at':now()}
                uncommitted = owner == 'specialists' and isinstance(exc, ValueError) and (
                    str(exc) == 'Uncommitted manifest' or
                    str(exc).startswith('Missing required object: checkpoints/task_'))
                if uncommitted:
                    blocked_commits += 1
                    failure['reason_code'] = 'uncommitted_publication_input'
                write_json(store,'operations/'+owner+'/publication-failures/'+digest(failure)+'.json',failure)
                write_json(store,retry_key,{'source_hash':source_hash,
                    'retry_after':(datetime.now(timezone.utc)+timedelta(minutes=1440 if uncommitted else 30)).isoformat().replace('+00:00','Z')},retry_token)
                outcomes.append(failure)
    return {'status':'failed' if any(r['status']=='failed' for r in outcomes) else 'complete','results':outcomes}
