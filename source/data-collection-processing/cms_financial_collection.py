"""Stream CMS financial CSV editions to S3, publish resumable Parquet rows, verify and email."""
import argparse
import csv
import fcntl
import hashlib
import io
import json
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import boto3
import requests
import pyarrow as pa
import pyarrow.parquet as pq
from research_contract import ROOT, digest
from collection_storage import StorageSettings, now

VERSION='cms-financial-files-v1'
CATALOGS={'payments':'https://openpaymentsdata.cms.gov/api/1/metastore/schemas/dataset/items',
          'spending':'https://data.cms.gov/data.json'}
SCHEMA=pa.schema([(x,pa.string()) for x in ('dataset_id','record_id','row_json')]+[('row_number',pa.int64())])
TABLES={'cms_open_payments':'cms_open_payments_rows','cms_drug_spending':'cms_drug_spending_rows'}
PART=16*1024*1024


def select_editions(catalogs, first_year=2021):
    result=[]
    for r in catalogs['payments']:
        m=re.fullmatch(r'(20\d\d) (General|Research|Ownership) Payment Data',r.get('title',''))
        if not m or int(m[1])<first_year: continue
        for d in r.get('distribution',[]):
            if d.get('format','').lower()=='csv' and d.get('downloadURL'):
                result.append({'source':'cms_open_payments','dataset_id':r['identifier'],'category':m[2].lower(),
                    'program_year':int(m[1]),'title':r['title'],'modified':r.get('modified'),
                    'url':d['downloadURL'],'dictionary':d.get('describedBy'),'temporal':r.get('temporal')})
    for r in catalogs['spending']['dataset']:
        title=r.get('title','')
        if not re.match(r'^(Medicare (Quarterly )?Part [BD]|Medicaid) Spending by Drug\s*:',title):continue
        files=[d for d in r.get('distribution',[]) if d.get('format','').lower()=='csv' and d.get('downloadURL')]
        for d in files:
            result.append({'source':'cms_drug_spending','dataset_id':r['identifier'],
                'category':'quarterly' if 'Quarterly' in title else 'annual','title':title,
                'modified':d.get('modified',r.get('modified')),'url':d['downloadURL'],
                'dictionary':(d.get('describedBy') or {}).get('downloadURL'),'temporal':d.get('temporal')})
    for r in result:
        if urlsplit(r['url']).hostname not in {'download.cms.gov','data.cms.gov'}:raise ValueError('Unexpected CMS download host')
        r['edition_id']=digest(r)
    return sorted(result,key=lambda r:(r['source']!='cms_drug_spending',r['category']!='ownership',r['url']))


def registry(path):
    db=sqlite3.connect(path)
    db.executescript('''CREATE TABLE IF NOT EXISTS editions(id TEXT PRIMARY KEY, meta TEXT NOT NULL,
       initial INTEGER NOT NULL, state TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',error TEXT);
       CREATE TABLE IF NOT EXISTS control(key TEXT PRIMARY KEY,value TEXT NOT NULL);''')
    return db


def save(db, identity, state, status=None):
    with db:
        db.execute('UPDATE editions SET state=?,status=COALESCE(?,status),error=NULL WHERE id=?',
                   (json.dumps(state),status,identity))


def safe_get(url, **kwargs):
    r=requests.get(url,timeout=(15,90),**kwargs);r.raise_for_status();return r


def discover(db, config, s3, bucket, prefix):
    initial=json.loads((ROOT/config['inventory_file']).read_text())
    if digest(initial)!=config['inventory_digest']:raise ValueError('Pinned inventory changed')
    with db:
        for meta in initial:
            db.execute('INSERT OR IGNORE INTO editions(id,meta,initial,state) VALUES (?,?,1,?)',
                (meta['edition_id'],json.dumps(meta),'{}'))
    old=db.execute("SELECT value FROM control WHERE key='last_discovery'").fetchone()
    if old and time.time()-float(old[0])<86400:return
    catalogs={}
    for kind,url in CATALOGS.items():
        raw=safe_get(url).content;catalogs[kind]=json.loads(raw)
        s3.put_object(Bucket=bucket,Key=prefix+'catalogs/'+hashlib.sha256(raw).hexdigest()+'.json',Body=raw,ServerSideEncryption='AES256',ContentType='application/json')
    selected=select_editions(catalogs,config['first_payment_year'])
    if not selected:raise ValueError('CMS catalog discovery empty')
    with db:
        for meta in selected:
            db.execute('INSERT OR IGNORE INTO editions(id,meta,initial,state) VALUES (?,?,0,?)',
                (meta['edition_id'],json.dumps(meta),'{}'))
        db.execute("INSERT OR REPLACE INTO control VALUES ('last_discovery',?)",(str(time.time()),))


def stream_download(db,meta,state,s3,bucket,key,deadline):
    """Fallback for CMS hosts ignoring Range; skip committed bytes on retry."""
    r=safe_get(meta['url'],headers={'Accept-Encoding':'identity'},stream=True)
    try:
        if (r.headers.get('ETag') or r.headers.get('Last-Modified'))!=state['validator']:
            raise ValueError('CMS streaming source version changed')
        skip=state['offset_download'];buffer=b''
        for chunk in r.iter_content(1024*1024):
            if skip:
                n=min(skip,len(chunk));skip-=n;chunk=chunk[n:]
            buffer+=chunk
            if len(buffer)>=PART:
                data,buffer=buffer[:PART],buffer[PART:]
                number=len(state['parts'])+1
                part=s3.upload_part(Bucket=bucket,Key=key,UploadId=state['upload_id'],PartNumber=number,Body=data)
                state['parts'].append({'PartNumber':number,'ETag':part['ETag']})
                state['offset_download']+=len(data);save(db,meta['edition_id'],state)
                if time.monotonic()>=deadline:return False
        if skip:raise ValueError('CMS streaming source shrank')
        if buffer:
            number=len(state['parts'])+1
            part=s3.upload_part(Bucket=bucket,Key=key,UploadId=state['upload_id'],PartNumber=number,Body=buffer)
            state['parts'].append({'PartNumber':number,'ETag':part['ETag']})
            state['offset_download']+=len(buffer)
        state['total_bytes']=state['offset_download'];save(db,meta['edition_id'],state)
        s3.complete_multipart_upload(Bucket=bucket,Key=key,UploadId=state['upload_id'],MultipartUpload={'Parts':state['parts']})
        state['raw_complete']=True;save(db,meta['edition_id'],state,'hashing');return True
    finally:r.close()


def raw_download(db,meta,state,s3,bucket,prefix,deadline):
    identity=meta['edition_id'];key=prefix+'files/'+identity+'/original.csv'
    if state.get('raw_complete'):return True
    if 'upload_id' not in state:
        r=safe_get(meta['url'],headers={'Range':'bytes=0-0','Accept-Encoding':'identity'},stream=True)
        try:
            match=re.fullmatch(r'bytes 0-0/(\d+)',r.headers.get('Content-Range',''))
            if r.status_code==200:
                mode='stream';size=None
            elif r.status_code==206 and match and r.headers.get('Content-Encoding','identity')=='identity':
                mode='range';size=int(match[1])
            else:raise ValueError('Unsupported CMS range response')
            state.update(total_bytes=size,download_mode=mode,validator=r.headers.get('ETag') or r.headers.get('Last-Modified'),
                         offset_download=0,parts=[],raw_key=key,retrieved_at=now())
            if not state['validator']:raise ValueError('CMS source version validator absent')
        finally:r.close()
        state['upload_id']=s3.create_multipart_upload(Bucket=bucket,Key=key,ServerSideEncryption='AES256',ContentType='text/csv')['UploadId']
        save(db,identity,state,'downloading')
    # Recover a crash after multipart completion but before the local checkpoint.
    try:
        head=s3.head_object(Bucket=bucket,Key=key)
        if head['ContentLength']==state['total_bytes']:
            state['raw_complete']=True;save(db,identity,state,'hashing');return True
    except s3.exceptions.ClientError as exc:
        if exc.response['Error']['Code'] not in {'404','NoSuchKey','NotFound'}:raise
    if state.get('download_mode')=='stream':return stream_download(db,meta,state,s3,bucket,key,deadline)
    while state['offset_download']<state['total_bytes'] and time.monotonic()<deadline:
        start=state['offset_download'];end=min(start+PART,state['total_bytes'])-1
        r=safe_get(meta['url'],headers={'Range':f'bytes={start}-{end}','If-Range':state['validator'],'Accept-Encoding':'identity'})
        expected=f'bytes {start}-{end}/{state["total_bytes"]}'
        validator=r.headers.get('ETag') or r.headers.get('Last-Modified')
        if r.status_code!=206 or r.headers.get('Content-Range')!=expected or validator!=state['validator'] or len(r.content)!=end-start+1:
            raise ValueError('CMS range changed; refusing to mix source versions')
        number=len(state['parts'])+1
        response=s3.upload_part(Bucket=bucket,Key=key,UploadId=state['upload_id'],PartNumber=number,Body=r.content)
        state['parts'].append({'PartNumber':number,'ETag':response['ETag']})
        state['offset_download']=end+1;save(db,identity,state)
    if state['offset_download']!=state['total_bytes']:return False
    s3.complete_multipart_upload(Bucket=bucket,Key=key,UploadId=state['upload_id'],MultipartUpload={'Parts':state['parts']})
    state['raw_complete']=True;save(db,identity,state,'hashing');return True


class PhysicalLines:
    """Count consumed bytes, including embedded CSV newlines, for exact range resume."""
    def __init__(self,body,start=0):self.body=body;self.offset=start;self.buffer=b'';self.eof=False
    def __iter__(self):return self
    def __next__(self):
        while b'\n' not in self.buffer and not self.eof:
            chunk=self.body.read(65536)
            if not chunk:self.eof=True
            self.buffer+=chunk
        if not self.buffer:raise StopIteration
        if b'\n' in self.buffer:line,self.buffer=self.buffer.split(b'\n',1);line+=b'\n'
        else:line,self.buffer=self.buffer,b''
        self.offset+=len(line)
        return line.decode('utf-8-sig' if self.offset==len(line) else 'utf-8')


def validate_header(meta,header):
    if not header or len(header)!=len(set(header)) or any(not h for h in header):raise ValueError('CMS CSV invalid header')
    if meta['source']=='cms_open_payments':
        if 'Record_ID' not in header or 'Program_Year' not in header:raise ValueError('Not a detailed Open Payments CSV')
    elif not any('Spndng' in h or 'Spending' in h for h in header):raise ValueError('Not a drug spending CSV')


def rows_from_reader(meta,reader,limit,first):
    rows=[]
    for _ in range(limit):
        try:values=next(reader)
        except StopIteration:return rows,True
        if len(values)!=len(reader.fieldnames) or None in values:raise ValueError('CMS malformed CSV row')
        if any(v is None for v in values.values()):raise ValueError('CMS missing CSV columns')
        n=first+len(rows)+1
        if meta['source']=='cms_open_payments':
            if not values['Record_ID'] or values['Program_Year']!=str(meta['program_year']):raise ValueError('CMS payment identity/year mismatch')
            identity=str(meta['program_year'])+':'+meta['category']+':'+values['Record_ID']
        else:identity=meta['dataset_id']+':row:'+str(n)
        rows.append({'dataset_id':meta['dataset_id'],'record_id':identity,'row_number':n,
                     'row_json':json.dumps(values,ensure_ascii=False,separators=(',',':'))})
    return rows,False


def process_csv(db,meta,state,s3,bucket,prefix,deadline,chunk_rows):
    identity=meta['edition_id']
    if not state.get('sha256'):
        h=hashlib.sha256();body=s3.get_object(Bucket=bucket,Key=state['raw_key'])['Body']
        try:
            for chunk in body.iter_chunks(1024*1024):h.update(chunk)
        finally:body.close()
        state['sha256']=h.hexdigest();save(db,identity,state,'processing')
    offset=state.get('csv_offset',0)
    if offset>=state['total_bytes']:return True
    response=s3.get_object(Bucket=bucket,Key=state['raw_key'],Range=f'bytes={offset}-')
    lines=PhysicalLines(response['Body'],offset)
    try:
        if not offset:
            header=next(csv.reader(lines,strict=True));validate_header(meta,header)
            state.update(headers=header,csv_offset=lines.offset,row_count=0,chunks=0)
        reader=csv.DictReader(lines,fieldnames=state['headers'],strict=True)
        while time.monotonic()<deadline:
            rows,finished=rows_from_reader(meta,reader,chunk_rows,state['row_count'])
            if rows:
                buf=io.BytesIO();pq.write_table(pa.Table.from_pylist(rows,schema=SCHEMA),buf,compression='snappy')
                key=prefix+'rows/'+meta['source']+'/edition_id='+identity+'/part-'+str(state['chunks']).zfill(8)+'.parquet'
                s3.put_object(Bucket=bucket,Key=key,Body=buf.getvalue(),ServerSideEncryption='AES256')
                state.update(csv_offset=lines.offset,row_count=state['row_count']+len(rows),chunks=state['chunks']+1)
                save(db,identity,state,'processing')
            if finished:
                if lines.offset!=state['total_bytes']:raise ValueError('CMS parsed byte count mismatch')
                if not state['row_count']:raise ValueError('CMS empty file')
                state['csv_offset']=lines.offset;save(db,identity,state,'publishing');return True
    finally:response['Body'].close()
    return False


def table_definition(source,bucket,prefix):
    return {'Name':TABLES[source],'TableType':'EXTERNAL_TABLE','Parameters':{'optima_owner':VERSION,'classification':'parquet'},
      'PartitionKeys':[{'Name':'edition_id','Type':'string'}], 'StorageDescriptor':{
      'Columns':[{'Name':f.name,'Type':'bigint' if pa.types.is_int64(f.type) else 'string'} for f in SCHEMA],
      'Location':f's3://{bucket}/{prefix}rows/{source}/',
      'InputFormat':'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat',
      'OutputFormat':'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat',
      'SerdeInfo':{'SerializationLibrary':'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'}}}


def publish(meta,state,s3,glue,bucket,prefix,database):
    metadata_table={'Name':'cms_financial_editions','TableType':'EXTERNAL_TABLE',
      'Parameters':{'optima_owner':VERSION},'StorageDescriptor':{
        'Columns':[{'Name':n,'Type':t} for n,t in [('edition_id','string'),('dataset_id','string'),('source','string'),('title','string'),('category','string'),('program_year','int'),('modified','string'),('published_at','string'),('row_count','bigint'),('raw_key','string'),('sha256','string'),('url','string')]],
        'Location':f's3://{bucket}/{prefix}manifests/',
        'InputFormat':'org.apache.hadoop.mapred.TextInputFormat',
        'OutputFormat':'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
        'SerdeInfo':{'SerializationLibrary':'org.openx.data.jsonserde.JsonSerDe'}}}
    try:
        existing=glue.get_table(DatabaseName=database,Name='cms_financial_editions')['Table']
        if existing.get('Parameters',{}).get('optima_owner')!=VERSION:raise ValueError('CMS metadata table ownership mismatch')
    except glue.exceptions.EntityNotFoundException:glue.create_table(DatabaseName=database,TableInput=metadata_table)
    definition=table_definition(meta['source'],bucket,prefix)
    try:
        old=glue.get_table(DatabaseName=database,Name=definition['Name'])['Table']
        if old.get('Parameters',{}).get('optima_owner')!=VERSION:raise ValueError('CMS table ownership mismatch')
    except glue.exceptions.EntityNotFoundException:glue.create_table(DatabaseName=database,TableInput=definition)
    sd=dict(definition['StorageDescriptor']);sd['Location']+='edition_id='+meta['edition_id']+'/'
    try:glue.create_partition(DatabaseName=database,TableName=definition['Name'],PartitionInput={'Values':[meta['edition_id']],'StorageDescriptor':sd})
    except glue.exceptions.AlreadyExistsException:pass
    manifest={**meta,**state,'status':'complete','published_at':now(),'version':VERSION,
              'entity_link_status':'unresolved','point_in_time_eligible':False,
              'interpretation':'Source financial records, not resolved revenue or product allocations; original strings and suppression markers retained.'}
    key=prefix+'manifests/'+meta['edition_id']+'.json'
    s3.put_object(Bucket=bucket,Key=key,Body=json.dumps(manifest).encode(),ServerSideEncryption='AES256',ContentType='application/json')
    state['manifest_key']=key


def verify_and_email(db,config,s3,bucket,prefix):
    prior=db.execute("SELECT value FROM control WHERE key='email_id'").fetchone()
    if prior:return prior[0]
    rows=db.execute('SELECT meta,state,status FROM editions WHERE initial=1').fetchall()
    if not rows or any(r[2]!='done' for r in rows):return None
    from committed_data_athena import query
    athena=boto3.client('athena',region_name=config['region'])
    expected={json.loads(m)['edition_id']:json.loads(s)['row_count'] for m,s,_ in rows}
    actual={}
    for source,table in TABLES.items():
        ids=[json.loads(m)['edition_id'] for m,_,_ in rows if json.loads(m)['source']==source]
        clause=','.join("'"+i+"'" for i in ids)
        result=query(athena,f'SELECT edition_id,count(*),count(DISTINCT record_id) FROM {config["athena_database"]}.{table} WHERE edition_id IN ({clause}) GROUP BY edition_id')
        if any(r[1]!=r[2] for r in result['rows']):raise ValueError('CMS duplicate record identifiers within edition')
        actual.update({r[0]:int(r[1]) for r in result['rows']})
    if actual!=expected:raise ValueError('CMS Athena edition counts do not match parsed source file counts')
    for _,s,_ in rows:
        state=json.loads(s)
        if s3.head_object(Bucket=bucket,Key=state['raw_key'])['ContentLength']!=state['total_bytes']:raise ValueError('CMS archived file size mismatch')
    sns=boto3.client('sns',region_name=config['region'])
    subscriptions=[s for p in sns.get_paginator('list_subscriptions_by_topic').paginate(TopicArn=config['email_topic_arn']) for s in p['Subscriptions']]
    if not subscriptions or any(s['Protocol']!='email' or s['Endpoint']!=config['email_recipient'] or not s['SubscriptionArn'].startswith('arn:') for s in subscriptions):raise ValueError('CMS notification recipient mismatch')
    receipt={'job_id':config['job_id'],'verified_at':now(),'edition_counts':actual,'scope':config['scope_note']}
    s3.put_object(Bucket=bucket,Key=prefix+'completion.json',Body=json.dumps(receipt).encode(),ServerSideEncryption='AES256')
    message=sns.publish(TopicArn=config['email_topic_arn'],Subject='CMS payments and drug-spending backfills complete - verified',
       Message='Both pinned CMS backfills are complete: original CSVs archived, full source rows converted to Parquet, and exact per-edition counts verified in Athena.\n\n'+json.dumps(receipt,indent=2)+'\n\nTables: optima_collected_data.cms_open_payments_rows and cms_drug_spending_rows. See CMS_FINANCIAL_COLLECTION.md and ENTITY_DISCOVERY_ROLLOUT_PLAN.md#sql-checks. Source payment/product mentions remain unresolved. Do not sum payments across linked products, ownership values with payments, annual with quarterly spending, overall with manufacturer subtotals, or revised editions. Spending is not net company revenue.')
    with db:db.execute("INSERT INTO control VALUES ('email_id',?)",(message['MessageId'],))
    return message['MessageId']


def execute(config):
    settings=StorageSettings.load(ROOT/config['storage_config']);bucket=settings.s3_bucket
    prefix=settings.s3_prefix.strip('/')+'/cms-financial/'
    s3=boto3.client('s3',region_name=config['region']);glue=boto3.client('glue',region_name=config['region'])
    deadline=time.monotonic()+config['max_seconds']
    with registry(ROOT/config.get('state_file',config['job_id']+'.sqlite3')) as db:
        discover(db,config,s3,bucket,prefix)
        # Fair scheduling: rotate incomplete editions, preserving all checkpoints.
        candidates=db.execute("SELECT id,meta,state FROM editions WHERE status!='done' ORDER BY CASE WHEN json_extract(meta,'$.source')='cms_drug_spending' THEN 0 ELSE 1 END,CASE WHEN json_extract(meta,'$.category')='ownership' THEN 0 ELSE 1 END,COALESCE(json_extract(state,'$.last_attempt'),''),id").fetchall()
        for identity,meta_raw,state_raw in candidates:
            if time.monotonic()>=deadline:break
            meta,state=json.loads(meta_raw),json.loads(state_raw);state['last_attempt']=now()
            save(db,identity,state)
            per_file_deadline=min(deadline,time.monotonic()+config['seconds_per_edition'])
            try:
                if not raw_download(db,meta,state,s3,bucket,prefix,per_file_deadline):continue
                if not process_csv(db,meta,state,s3,bucket,prefix,per_file_deadline,config['chunk_rows']):continue
                publish(meta,state,s3,glue,bucket,prefix,config['athena_database'])
                save(db,identity,state,'done')
                print(json.dumps({'edition_complete':identity,'title':meta['title'],'rows':state['row_count']}),flush=True)
            except Exception as exc:
                with db:db.execute('UPDATE editions SET error=? WHERE id=?',(type(exc).__name__+': '+str(exc)[:1000],identity))
                print(json.dumps({'edition_error':identity,'error':str(exc)[:300]}),flush=True)
        email=verify_and_email(db,config,s3,bucket,prefix) if config.get('notify_on_completion',True) else None
        status={'job_id':config['job_id'],'updated_at':now(),'email_id':email,'scope':config['scope_note'],
          'editions':[{'edition_id':i,'title':json.loads(m)['title'],'initial':bool(initial),'status':st,'error':err,
             'downloaded_bytes':json.loads(s).get('offset_download',0),'total_bytes':json.loads(s).get('total_bytes'),
             'row_count':json.loads(s).get('row_count',0),'raw_key':json.loads(s).get('raw_key')} for i,m,initial,s,st,err in db.execute('SELECT * FROM editions')]}
        raw=json.dumps(status,indent=2).encode()
        s3.put_object(Bucket=bucket,Key=prefix+'status.json',Body=raw,ServerSideEncryption='AES256')
        (ROOT/config.get('status_file','reports/cms-financial-backfill-latest.json')).write_bytes(raw)
        return status


def main():
    csv.field_size_limit(16*1024*1024)
    parser=argparse.ArgumentParser();parser.add_argument('--config',default='config/cms-financial-collection.json');args=parser.parse_args()
    with (ROOT/'.cms-financial.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        execute(json.loads((ROOT/args.config).read_text()))

if __name__=='__main__':main()
