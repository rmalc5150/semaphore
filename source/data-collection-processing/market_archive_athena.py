"""Verify this archive batch using the established Athena committed-records table."""
import argparse
from collections import defaultdict
import hashlib
import json
import re
from pathlib import Path

import boto3

from committed_data_athena import BASE, BUCKET, DB, OWNER, PREFIX, batches, catalog, query, validate_terminal_manifest
from market_archive_import import RESULTS
from market_source_capture import immutable_put, utcnow
from market_source_register import ROOT, write

VERIFICATION = ROOT/'config/market-archive-athena.v1.json'


def read(s3,key):
    response=s3.get_object(Bucket=BUCKET,Key=key)
    with response['Body'] as body:
        return body.read()


def native_batches(s3,results):
    found=defaultdict(dict)
    for result in results:
        path=result['manifest']
        manifest=json.loads(read(s3,PREFIX+path))
        task=manifest['task']
        validate_terminal_manifest(path,manifest,task)
        head=json.loads(read(s3,PREFIX+'checkpoints/'+manifest['task_id']+'/head.json'))
        if path not in head['terminal_history'] or manifest['status']!='complete':
            raise ValueError('archive_native_manifest_not_committed')
        group=(result['source'],result['dataset'])
        if result['records']!=manifest['record_count'] or (task['source'],task['dataset'])!=group:
            raise ValueError('archive_record_manifest_scope_mismatch')
        for key,source,dataset,count,size,digest in batches(manifest):
            found[group][key]=(count,size,digest)
    return found


def partition(s3,glue,sd,source,dataset,entries):
    if not re.fullmatch(r'market_source_\d+',source) or not re.fullmatch(r'[a-z][a-z0-9_]*',dataset):
        raise ValueError('invalid_archive_partition_identity')
    try:
        old=glue.get_partition(DatabaseName=DB,TableName='committed_records',PartitionValues=[source,dataset])['Partition']
    except glue.exceptions.EntityNotFoundException:
        old=None
    urls={f's3://{BUCKET}/{PREFIX}{key}' for key in entries}
    if old:
        if old.get('Parameters',{}).get('optima_owner')!=OWNER:
            raise ValueError('unexpected_athena_partition_owner')
        location=old['StorageDescriptor']['Location']
        approved='s3://'+BUCKET+'/'+BASE+'manifests/'+source+'/'+dataset+'/'
        if not location.startswith(approved):
            raise ValueError('unexpected_athena_manifest_location')
        oldbody=read(s3,location.split('/',3)[3]+'files.txt')
        if hashlib.sha256(oldbody).hexdigest()!=old['Parameters'].get('manifest_sha256'):
            raise ValueError('athena_manifest_checksum_mismatch')
        urls.update(oldbody.decode().splitlines())
    body=('\n'.join(sorted(urls))+'\n').encode()
    sha=hashlib.sha256(body).hexdigest()
    key=BASE+'manifests/'+source+'/'+dataset+'/'+sha+'/'
    immutable_put(s3,BUCKET,key+'files.txt',body,sha,'text/plain')
    loc=f's3://{BUCKET}/{key}'
    definition={'Values':[source,dataset],'StorageDescriptor':{**sd,'Location':loc},
                'Parameters':{'optima_owner':OWNER,'manifest_sha256':sha}}
    if old:
        if old['StorageDescriptor']['Location']!=loc:
            glue.update_partition(DatabaseName=DB,TableName='committed_records',
                                  PartitionValueList=[source,dataset],PartitionInput=definition)
    else:
        try:
            glue.create_partition(DatabaseName=DB,TableName='committed_records',PartitionInput=definition)
        except glue.exceptions.AlreadyExistsException:
            existing=glue.get_partition(DatabaseName=DB,TableName='committed_records',PartitionValues=[source,dataset])['Partition']
            if existing['StorageDescriptor']['Location']!=loc:
                raise
    return sha


def publish(s3,glue,athena,results):
    selected=native_batches(s3,results)
    sd=catalog(glue,athena)
    expectations={}
    for (source,dataset),entries in selected.items():
        sha=partition(s3,glue,sd,source,dataset,entries)
        expectations[(source,dataset)]={'expected_records':sum(r[0] for r in entries.values()),
                                        'manifest_sha256':sha,'native_batches':len(entries)}
    clauses=[f"(source='{s}' AND dataset='{d}')" for s,d in selected]
    sql=(f"SELECT source,dataset,count(*),count(DISTINCT json_extract_scalar(record_json,'$.observation_id')),"
         f"count_if(json_extract_scalar(record_json,'$.payload.source_evidence[0].sha256') IS NOT NULL) "
         f"FROM {DB}.committed_records WHERE "+' OR '.join(clauses)+" GROUP BY source,dataset")
    result=query(athena,sql)
    checked={(source,dataset):(int(records),int(unique),int(linked)) for source,dataset,records,unique,linked in result['rows']}
    rows=[]
    for (source,dataset),expectation in sorted(expectations.items()):
        count=expectation['expected_records']
        actual=checked.get((source,dataset))
        if actual!=(count,count,count):
            raise RuntimeError(f'Athena row or provenance count mismatch for {source}/{dataset}: expected {count}, got {actual}')
        rows.append({'source':source,'dataset':dataset,'records':count,**expectation})
    report={'table':f'{DB}.committed_records','observations_view':f'{DB}.observations','query_id':result['query_id'],
            'bytes_scanned':result['bytes_scanned'],'verified_at':utcnow().isoformat(),'partitions':rows}
    body=(json.dumps(report,indent=2,sort_keys=True)+'\n').encode()
    sha=hashlib.sha256(body).hexdigest()
    key=BASE+'verifications/market-archive-'+sha+'.json'
    immutable_put(s3,BUCKET,key,body,sha,'application/json')
    return {**report,'receipt':f's3://{BUCKET}/{key}'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=int,action='append')
    args=parser.parse_args(argv)
    captured=json.loads(RESULTS.read_text())
    selected={key:r for key,r in captured.items() if r.get('manifest') and (not args.source or r['id'] in args.source)}
    if not selected:
        parser.error('no successful captures to publish')
    session=boto3.Session(region_name='us-east-1')
    s3=session.client('s3')
    status=publish(s3,session.client('glue'),session.client('athena'),list(selected.values()))
    from metadata_engine.market_archive import TRENDS, retain_receipt, trends_receipt
    from market_archive_import import profiles
    selected_trends = {key: value for key, value in selected.items() if value['source'] == TRENDS}
    if selected_trends:
        specs = {row['key']: row for row in profiles() if row['id'] == 166}
        for key, result in selected_trends.items():
            retain_receipt(s3, BUCKET, trends_receipt(specs[key], result))
    if args.source and VERIFICATION.exists():
        previous=json.loads(VERIFICATION.read_text())
        replacement={(p['source'],p['dataset']) for p in status['partitions']}
        for item in status['partitions']:
            item['query_id']=status['query_id']
        keep=[{**p,'query_id':p.get('query_id',previous['query_id'])}
              for p in previous['partitions'] if (p['source'],p['dataset']) not in replacement]
        status['partitions']=keep+status['partitions']
    write(VERIFICATION,status)
    print(json.dumps(status,indent=2))


if __name__=='__main__':
    main()
