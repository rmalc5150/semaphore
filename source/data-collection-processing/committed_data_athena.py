"""Expose only checkpoint-committed JSONL batches, including partial windows, in Athena.

An independent bounded-memory catalog job. No collection or curated-table mutation.
Checkpoint history preserves earlier observations; physical batches are indexed once.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

ROOT=Path(__file__).resolve().parent
BUCKET='data-collection-059416028963-us-east-1-an'
PREFIX='research-data/'
BASE=PREFIX+'athena-committed/'
DB='optima_collected_data'
WG='optima-collected-data'
OWNER='optima-committed-batches-v1'


def batches(document):
    task=document['task']; source=task['source']; dataset=task['dataset']
    if not all(re.fullmatch(r'[a-zA-Z0-9_-]+',s) for s in (source,dataset)):
        raise ValueError('Invalid source/dataset')
    canonical=json.dumps(task,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    if document['task_id']!='task_'+hashlib.sha256(canonical).hexdigest():
        raise ValueError('Task identity mismatch')
    total=0; result={}
    for page in document['pages']:
        count=0
        for batch in page['batches']:
            key=batch['key']; checksum=batch['sha256']
            if (not key.startswith(f'raw/source={source}/dataset={dataset}/') or
                not key.endswith('-'+checksum+'.jsonl') or not re.fullmatch('[a-f0-9]{64}',checksum)
                or any(c in key for c in ('\n','\r','..'))):
                raise ValueError('Batch scope mismatch')
            if batch['records']<0 or batch['bytes']<0:raise ValueError('Invalid batch counts')
            count+=batch['records']
            row=(key,source,dataset,batch['records'],batch['bytes'],checksum)
            if key in result:raise ValueError('Duplicate batch within checkpoint')
            result[key]=row
        if count!=page['record_count']:raise ValueError('Page count mismatch')
        total+=count
    if total!=document['record_count']:raise ValueError('Checkpoint count mismatch')
    return list(result.values())


def query(athena,sql):
    q=athena.start_query_execution(QueryString=sql,WorkGroup=WG,
        ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId']
    for _ in range(3600):
        r=athena.get_query_execution(QueryExecutionId=q)['QueryExecution']
        status=r['Status']['State']
        if status=='SUCCEEDED':
            rows=[]
            for page in athena.get_paginator('get_query_results').paginate(QueryExecutionId=q):
                rows.extend([[v.get('VarCharValue') for v in row['Data']] for row in page['ResultSet']['Rows']])
            return {'query_id':q,'rows':rows[1:],'bytes_scanned':r['Statistics'].get('DataScannedInBytes',0)}
        if status in ('FAILED','CANCELLED'):
            raise RuntimeError(json.dumps({'query_id':q,'status':status,'reason':r['Status'].get('StateChangeReason')}))
        time.sleep(1)
    athena.stop_query_execution(QueryExecutionId=q)
    raise RuntimeError('Athena verification timeout '+q)


def catalog(glue,athena):
    try:
        d=glue.get_database(Name=DB)['Database']
        if d.get('Parameters',{}).get('optima_owner')!=OWNER:raise ValueError('Database ownership mismatch')
    except glue.exceptions.EntityNotFoundException:
        glue.create_database(DatabaseInput={'Name':DB,'Parameters':{'optima_owner':OWNER}})
    output='s3://'+BUCKET+'/'+BASE+'query-results/'
    try:
        w=athena.get_work_group(WorkGroup=WG)['WorkGroup']
        if w['Configuration']['ResultConfiguration']['OutputLocation']!=output:raise ValueError('Workgroup ownership mismatch')
    except ClientError as exc:
        if exc.response['Error']['Code']!='InvalidRequestException':raise
        athena.create_work_group(Name=WG,Description=OWNER,Configuration={
            'EnforceWorkGroupConfiguration':True,'BytesScannedCutoffPerQuery':100*1024**3,
            'ResultConfiguration':{'OutputLocation':output,'EncryptionConfiguration':{'EncryptionOption':'SSE_S3'}},
            'EngineVersion':{'SelectedEngineVersion':'Athena engine version 3'}})
    sd={'Columns':[{'Name':'record_json','Type':'string'}],
        'Location':'s3://'+BUCKET+'/'+BASE+'empty/',
        'InputFormat':'org.apache.hadoop.hive.ql.io.SymlinkTextInputFormat',
        'OutputFormat':'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
        'SerdeInfo':{'SerializationLibrary':'org.apache.hadoop.hive.serde2.RegexSerDe','Parameters':{'input.regex':'(.*)'}}}
    definition={'Name':'committed_records','TableType':'EXTERNAL_TABLE','Parameters':{'optima_owner':OWNER},
        'PartitionKeys':[{'Name':'source','Type':'string'},{'Name':'dataset','Type':'string'}],'StorageDescriptor':sd}
    try:
        old=glue.get_table(DatabaseName=DB,Name='committed_records')['Table']
        if old.get('Parameters',{}).get('optima_owner')!=OWNER:raise ValueError('Table ownership mismatch')
        if old['StorageDescriptor']['Columns']!=sd['Columns']:raise ValueError('Table schema mismatch')
    except glue.exceptions.EntityNotFoundException:glue.create_table(DatabaseName=DB,TableInput=definition)
    return sd


def manifest_body(index,source,dataset,pending=False):
    clause=' AND NOT EXISTS (SELECT 1 FROM verified_batches v WHERE v.key=b.key)' if pending else ''
    rows=index.execute('SELECT key FROM batches b WHERE source=? AND dataset=?'+clause+' ORDER BY key',(source,dataset))
    return ''.join('s3://'+BUCKET+'/'+PREFIX+k+'\n' for (k,) in rows).encode()


def bootstrap_verified(index):
    # Upgrade an earlier full-verification index only when its exact manifest
    # still matches the verified receipt. Unknown/new files must be queried.
    if index.execute('SELECT 1 FROM verified_batches LIMIT 1').fetchone():return
    for source,dataset,checksum,qid in index.execute('SELECT source,dataset,manifest_sha256,query_id FROM verified_partitions').fetchall():
        if hashlib.sha256(manifest_body(index,source,dataset)).hexdigest()==checksum:
            index.execute('INSERT OR IGNORE INTO verified_batches SELECT key,? FROM batches WHERE source=? AND dataset=?',(qid,source,dataset))
    index.commit()


def verify_batches(index,s3,glue,athena,sd,selected,full=False):
    """Bound each query to 1,000 files / 1 GiB; retain each successful receipt."""
    name='batch_verification_records'
    partition_keys=[{'Name':n,'Type':'string'} for n in ('source','dataset','batch_group')]
    definition={'Name':name,'Description':'Internal bounded verification; use observations for collected data.',
        'TableType':'EXTERNAL_TABLE','Parameters':{'optima_owner':OWNER},
        'PartitionKeys':partition_keys,'StorageDescriptor':sd}
    try:
        old=glue.get_table(DatabaseName=DB,Name=name)['Table']
        if old.get('Parameters',{}).get('optima_owner')!=OWNER or old['PartitionKeys']!=partition_keys:raise ValueError('Verification table contract mismatch')
    except glue.exceptions.EntityNotFoundException:glue.create_table(DatabaseName=DB,TableInput=definition)
    chunks=[]
    def stage(source,dataset,rows):
        body=''.join('s3://'+BUCKET+'/'+PREFIX+r[0]+'\n' for r in rows).encode()
        identity=hashlib.sha256(body).hexdigest()
        location=BASE+'verification-manifests/'+source+'/'+dataset+'/'+identity+'/'
        s3.put_object(Bucket=BUCKET,Key=location+'files.txt',Body=body,ServerSideEncryption='AES256')
        part={'Values':[source,dataset,identity],'StorageDescriptor':{**sd,'Location':'s3://'+BUCKET+'/'+location},'Parameters':{'optima_owner':OWNER}}
        try:
            old=glue.get_partition(DatabaseName=DB,TableName=name,PartitionValues=part['Values'])['Partition']
            if old.get('Parameters',{}).get('optima_owner')!=OWNER or old['StorageDescriptor']['Location']!=part['StorageDescriptor']['Location']:raise ValueError('Verification partition mismatch')
        except glue.exceptions.EntityNotFoundException:glue.create_partition(DatabaseName=DB,TableName=name,PartitionInput=part)
        chunks.append({'source':source,'dataset':dataset,'batch_group':identity,'records':sum(r[1] for r in rows),'keys':[r[0] for r in rows]})
    for item in selected:
        source,dataset=item['source'],item['dataset']
        clause='' if full else ' AND NOT EXISTS (SELECT 1 FROM verified_batches v WHERE v.key=b.key)'
        pending=[];size=0
        for row in index.execute('SELECT key,records,bytes FROM batches b WHERE source=? AND dataset=?'+clause+' ORDER BY key',(source,dataset)):
            if pending and (len(pending)>=1000 or size+row[2]>1024**3):
                stage(source,dataset,pending);pending=[];size=0
            pending.append(row);size+=row[2]
        if pending:stage(source,dataset,pending)
    def check(chunk):
        where=' AND '.join(k+"='"+chunk[k]+"'" for k in ('source','dataset','batch_group'))
        sql=f"SELECT count(*),count_if(try(json_extract_scalar(record_json,'$.observation_id')) IS NULL OR try(json_extract_scalar(record_json,'$.source')) IS DISTINCT FROM source OR try(json_extract_scalar(record_json,'$.dataset')) IS DISTINCT FROM dataset) FROM {DB}.{name} WHERE {where}"
        result=query(athena,sql)
        if result['rows']!=[[str(chunk['records']),'0']]:raise ValueError('Athena batch count/schema mismatch '+chunk['batch_group'])
        return chunk,result
    results=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for offset in range(0,len(chunks),4):
            for chunk,result in pool.map(check,chunks[offset:offset+4]):
                proof={**{k:v for k,v in chunk.items() if k!='keys'},**result,'status':'verified','checked_at':datetime.now(timezone.utc).isoformat()}
                s3.put_object(Bucket=BUCKET,Key=BASE+'batch-verifications/'+result['query_id']+'.json',Body=json.dumps(proof).encode(),ServerSideEncryption='AES256')
                index.executemany('INSERT OR REPLACE INTO verified_batches VALUES (?,?)',[(k,result['query_id']) for k in chunk['keys']]);index.commit()
                results.append(proof)
                print(json.dumps({'stage':'verified_batch_group','source':chunk['source'],'records':chunk['records'],'query_id':result['query_id']}),flush=True)
    for row in selected:
        unknown=index.execute('SELECT count(*) FROM batches b WHERE source=? AND dataset=? AND NOT EXISTS (SELECT 1 FROM verified_batches v WHERE v.key=b.key)',(row['source'],row['dataset'])).fetchone()[0]
        if unknown:raise ValueError('Unverified batches remain')
        qid=index.execute('SELECT query_id FROM verified_batches v JOIN batches b ON b.key=v.key WHERE source=? AND dataset=? ORDER BY b.key DESC LIMIT 1',(row['source'],row['dataset'])).fetchone()[0]
        index.execute('INSERT OR REPLACE INTO verified_partitions VALUES (?,?,?,?)',(row['source'],row['dataset'],row['manifest_sha256'],qid))
    index.commit()
    return {'queries':results,'records_verified':sum(r['records'] for r in results),'bytes_scanned':sum(r['bytes_scanned'] for r in results)}


VIEW_SQL=f"CREATE OR REPLACE VIEW {DB}.observations AS SELECT source,dataset,json_extract_scalar(record_json,'$.record_id') AS record_id,json_extract_scalar(record_json,'$.observation_id') AS observation_id,json_extract_scalar(record_json,'$.source_record_id') AS provider_id,json_extract_scalar(record_json,'$.ingested_at') AS ingested_at,json_extract_scalar(record_json,'$.source_url') AS source_url,json_format(json_extract(record_json,'$.event_at')) AS event_at_json,json_format(json_extract(record_json,'$.payload')) AS payload_json,record_json FROM {DB}.committed_records"


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify-all',action='store_true');args=parser.parse_args()
    with (ROOT/'.committed-athena.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return 0
        session=boto3.Session(region_name='us-east-1')
        s3=session.client('s3',config=Config(max_pool_connections=12));glue=session.client('glue');athena=session.client('athena')
        index=sqlite3.connect(ROOT/'committed-athena-index.sqlite3')
        index.executescript('CREATE TABLE IF NOT EXISTS documents (key TEXT PRIMARY KEY, etag TEXT); CREATE TABLE IF NOT EXISTS batches (key TEXT PRIMARY KEY, source TEXT, dataset TEXT, records INTEGER, bytes INTEGER, sha256 TEXT); CREATE TABLE IF NOT EXISTS verified_partitions (source TEXT, dataset TEXT, manifest_sha256 TEXT, query_id TEXT, PRIMARY KEY(source,dataset)); CREATE TABLE IF NOT EXISTS verified_batches (key TEXT PRIMARY KEY, query_id TEXT);')
        bootstrap_verified(index)
        report={'started_at':datetime.now(timezone.utc).isoformat(),'status':'running','changed_documents':0}
        def fetch(item):
            key,etag=item
            obj=s3.get_object(Bucket=BUCKET,Key=key)
            return key,obj['ETag'],json.loads(obj['Body'].read())
        def add(doc):
            for row in batches(doc):
                prior=index.execute('SELECT source,dataset,records,bytes,sha256 FROM batches WHERE key=?',(row[0],)).fetchone()
                if prior and prior!=row[1:]:raise ValueError('Immutable batch changed')
                index.execute('INSERT OR IGNORE INTO batches VALUES (?,?,?,?,?,?)',row)
        def unchanged(key,etag):
            row=index.execute('SELECT etag FROM documents WHERE key=?',(key,)).fetchone()
            return row and row[0]==etag
        changed=[]
        for page in s3.get_paginator('list_objects_v2').paginate(Bucket=BUCKET,Prefix=PREFIX+'checkpoints/task_'):
            changed.extend((o['Key'],o['ETag']) for o in page.get('Contents',[]) if o['Key'].endswith('/head.json') and not unchanged(o['Key'],o['ETag']))
        print(json.dumps({'stage':'discover','changed_heads':len(changed)}),flush=True)
        with ThreadPoolExecutor(max_workers=8) as pool:
            for start in range(0,len(changed),32):
                heads=list(pool.map(fetch,changed[start:start+32]))
                history={}
                for key,etag,head in heads:
                    if key!=PREFIX+'checkpoints/'+head['task_id']+'/head.json':raise ValueError('Checkpoint identity mismatch')
                    add(head)
                    for path in head.get('terminal_history',[]):
                        full=PREFIX+path
                        if not path.startswith('manifests/collection_runs/') or not path.endswith('/final.json'):raise ValueError('Invalid terminal history')
                        if not index.execute('SELECT 1 FROM documents WHERE key=?',(full,)).fetchone():history[full]=head['task']
                for offset in range(0,len(history),32):
                    subset=list(history)[offset:offset+32]
                    for mk,me,manifest in pool.map(fetch,[(k,None) for k in subset]):
                        if manifest['task']!=history[mk]:raise ValueError('History task mismatch')
                        add(manifest);index.execute('INSERT OR REPLACE INTO documents VALUES (?,?)',(mk,me))
                for key,etag,head in heads:
                    index.execute('INSERT OR REPLACE INTO documents VALUES (?,?)',(key,etag));report['changed_documents']+=1
                index.commit()
                if start%320==0:print(json.dumps({'stage':'indexed','heads':start+len(changed[start:start+32])}),flush=True)
        sd=catalog(glue,athena);expected=[];changed_partitions=[]
        for source,dataset,count,size in index.execute('SELECT source,dataset,sum(records),sum(bytes) FROM batches GROUP BY source,dataset ORDER BY source,dataset').fetchall():
            body=manifest_body(index,source,dataset)
            digest=hashlib.sha256(body).hexdigest();location=BASE+'manifests/'+source+'/'+dataset+'/'+digest+'/'
            definition={'Values':[source,dataset],'StorageDescriptor':{**sd,'Location':'s3://'+BUCKET+'/'+location},'Parameters':{'optima_owner':OWNER,'manifest_sha256':digest}}
            try:
                old=glue.get_partition(DatabaseName=DB,TableName='committed_records',PartitionValues=[source,dataset])['Partition']
                if old.get('Parameters',{}).get('optima_owner')!=OWNER:raise ValueError('Partition ownership mismatch')
            except glue.exceptions.EntityNotFoundException:old=None
            if not old or old['StorageDescriptor']['Location']!=definition['StorageDescriptor']['Location']:
                s3.put_object(Bucket=BUCKET,Key=location+'files.txt',Body=body,ServerSideEncryption='AES256')
                if old:glue.update_partition(DatabaseName=DB,TableName='committed_records',PartitionValueList=[source,dataset],PartitionInput=definition)
                else:glue.create_partition(DatabaseName=DB,TableName='committed_records',PartitionInput=definition)
                changed_partitions.append((source,dataset))
            verified=index.execute('SELECT manifest_sha256 FROM verified_partitions WHERE source=? AND dataset=?',(source,dataset)).fetchone()
            if not verified or verified[0]!=digest:
                if (source,dataset) not in changed_partitions:changed_partitions.append((source,dataset))
            expected.append({'source':source,'dataset':dataset,'records':count,'bytes':size,'manifest_sha256':digest})
        print(json.dumps({'stage':'cataloged','partitions':len(expected),'records':sum(r['records'] for r in expected),'bytes':sum(r['bytes'] for r in expected)}),flush=True)
        selected=expected if args.verify_all else [r for r in expected if (r['source'],r['dataset']) in changed_partitions]
        report['verification_mode']='full_bounded' if args.verify_all else 'new_batches'
        if selected:report['verification']=verify_batches(index,s3,glue,athena,sd,selected,full=args.verify_all)
        query(athena,VIEW_SQL)
        report['batch_verification_query_ids']=[r[0] for r in index.execute('SELECT DISTINCT query_id FROM verified_batches ORDER BY query_id')]
        report['partition_verifications']=[dict(zip(('source','dataset','manifest_sha256','query_id'),row)) for row in index.execute('SELECT source,dataset,manifest_sha256,query_id FROM verified_partitions ORDER BY source,dataset')]
        report.update(status='verified',finished_at=datetime.now(timezone.utc).isoformat(),sources=expected,verified_partitions=len(selected),note='Committed observations, including incomplete windows and prior versions; not exhaustive coverage or deduplicated entities. Reddit remains in optima_social_research.reddit_records.')
        previous_path=ROOT/'reports/committed-athena-latest.json'
        if previous_path.exists():
            prior_body=previous_path.read_bytes();prior_hash=hashlib.sha256(prior_body).hexdigest()
            prior_key='athena-committed/verifications/'+prior_hash+'.json'
            s3.put_object(Bucket=BUCKET,Key=PREFIX+prior_key,Body=prior_body,ServerSideEncryption='AES256')
            report['prior_verification']={'key':prior_key,'sha256':prior_hash}
        evidence=(json.dumps(report,sort_keys=True)+'\n').encode()
        checksum=hashlib.sha256(evidence).hexdigest()
        evidence_key='athena-committed/verifications/'+checksum+'.json'
        s3.put_object(Bucket=BUCKET,Key=PREFIX+evidence_key,Body=evidence,ServerSideEncryption='AES256')
        report.update(verification_key=evidence_key,verification_sha256=checksum,checked_at=report['finished_at'])
        output=json.dumps(report,indent=2)+'\n'
        (ROOT/'reports/committed-athena-latest.json').write_text(output)
        s3.put_object(Bucket=BUCKET,Key=BASE+'latest-report.json',Body=output.encode(),ServerSideEncryption='AES256')
        print(json.dumps({'status':'verified','partitions':len(expected),'records':sum(r['records'] for r in expected)}),flush=True)
        return 0

if __name__=='__main__':raise SystemExit(main())
