"""t3 discovery, verified partition publication and failure email delivery."""
import argparse
from contextlib import nullcontext
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from functools import lru_cache
import json
from pathlib import Path
import re
import time

from botocore.exceptions import ClientError
from metadata_engine.runtime_db import Database,encoded,fingerprint,collection_tx,host_excluded_sources
from metadata_engine.worker import put
from metadata_engine.evidence import object_bytes
from metadata_engine.s3_metrics import MeteredS3


def enqueue_objects(db,objects,form,priority,cursor=None):
    count=0
    for item in objects:
        key=item['Key'];source=None
        if form=='legacy_batch':
            m=re.match(r'research-data/raw/source=([^/]+)/',key)
            if m and key.endswith('.jsonl'):source=m[1]
        elif form in ('public_receipt','daily_raw'):
            body=object_bytes(db.session.client('s3'),db.config['bucket'],key,2*1024*1024)
            if body.strip():source=json.loads(body.splitlines()[0]).get('source')
        elif form=='native_manifest':
            if not key.endswith('/manifest.json'):continue
            m=json.loads(object_bytes(db.session.client('s3'),db.config['bucket'],key,4*1024*1024))
            source=m.get('spec',{}).get('source_key')
        if not source:continue
        adapter = db.config['contracts'].get(source, {}).get('adapter')
        if adapter == 'research_feed':continue
        if adapter == 'market_archive_original':
            from metadata_engine.market_archive import RECEIPTS
            if form != 'public_receipt' or not key.startswith(f'{RECEIPTS}{source}/'):
                continue
        if adapter == 'sedi_issuer_events':
            from metadata_engine.sedi import DATASET
            if form != 'legacy_batch' or not key.startswith(f'research-data/raw/source={source}/dataset={DATASET}/'):
                continue
        if source.startswith('market_source_') and source not in db.config['contracts']:
            continue
        from metadata_engine.source_policies import PAUSED
        if source in PAUSED:continue
        if source not in db.config['contracts']:
            # Unmapped operational datasets remain explicit; no guessed content
            # fields or host allowlists can let them bypass raw validation.
            base={'source_key':source,'catalog_entries':[],'datasets':[],'state':'enabled','contract_version':'2.0.0',
                'adapter':'api_records','adapter_version':'2.0.0','record_kind':'source_record','license_policy_id':'source-rights-review-required','allowed_hosts':[],
                'raw_requirements':{'version':'2.0.0','minimum_completeness':'complete','required_artifact_kinds':['provider_record'],'forbidden_shortcuts':['metadata_only']}}
            register_contract(db,base);db.config['contracts'][source]=base
        if form=='legacy_batch'and source in ('cninfo_mainland_china_company_disclosures','south_korea_fss_opendart')and db.config['contracts'][source]['contract_version']=='2.0.3':
            sample=object_bytes(db.session.client('s3'),db.config['bucket'],key,2*1024*1024)
            original=json.loads(sample.splitlines()[0])if sample.strip()else{}
            if not isinstance(original.get('payload',{}).get('data',{}).get('filing'),dict):
                with(nullcontext(cursor)if cursor is not None else db.tx())as c:
                    db.enqueue(source,key,item.get('ETag',''),form,priority,c)
                    identity=fingerprint([source,key,item.get('ETag',''),form,'2.0.3'])
                    c.execute("UPDATE engine_jobs SET state='superseded',reason='legacy_index_only_replaced_by_original_filing_capture',finished_at=UTC_TIMESTAMP(6) WHERE job_id=%s AND state IN ('queued','retry','raw_failed')",(identity,))
                continue
        if form=='public_receipt' and db.config['contracts'][source]['contract_version']=='2.0.3':
            from public_source_scope import REVIEWED,in_scope
            if source in REVIEWED or source=='england_nhsbsa_prescribing_data':
                receipts=[json.loads(line)for line in body.splitlines()if line.strip()]
                substantive_receipt=(source!='england_nhsbsa_prescribing_data' and receipts and all(r.get('source')==source and r.get('artifact_kind')=='public_document'and in_scope(r.get('source_url',''),source)for r in receipts))
                if not substantive_receipt:
                    with (nullcontext(cursor)if cursor is not None else db.tx())as c:
                        db.enqueue(source,key,item.get('ETag',''),form,priority,c)
                        identity=fingerprint([source,key,item.get('ETag',''),form,db.config['contracts'][source]['contract_version']])
                        c.execute("UPDATE engine_jobs SET state='superseded',reason='index_or_out_of_scope_input; native_source_route_active',finished_at=UTC_TIMESTAMP(6) WHERE job_id=%s AND state IN ('queued','retry','raw_failed')",(identity,))
                    continue
        if source in ('europe_pmc_fulltext','chictr','cms_coverage_documents','cms_payments_catalog','doe_storage_program','imf_portwatch_shipping_activity','unido_iip_and_indstat') and form=='public_receipt':
            receipts=[json.loads(line)for line in body.splitlines()if line.strip()]
            catalogue_only=(source=='unido_iip_and_indstat' and receipts and all(
                r.get('source')==source and r.get('source_url','').startswith('https://stat.unido.org/portal/dataset/getDataset/')
                for r in receipts))
            if catalogue_only or (receipts and all(r.get('source')==source and r.get('artifact_kind')=='discovery_page'for r in receipts)):
                # Website discovery receipts are not article inputs. Keep their
                # job/audit identity but never publish them as full text or let
                # this duplicate route stop verified JATS processing.
                with (nullcontext(cursor) if cursor is not None else db.tx())as c:
                    db.enqueue(source,key,item.get('ETag',''),form,priority,c)
                    identity=fingerprint([source,key,item.get('ETag',''),form,db.config['contracts'][source]['contract_version']])
                    reason=('catalogue_not_measurements; native_statistics_route_active' if catalogue_only else
                            'discovery_page_not_fulltext_input; verified_document_route_active')
                    c.execute("UPDATE engine_jobs SET state='superseded',reason=%s,finished_at=UTC_TIMESTAMP(6) WHERE job_id=%s AND state IN ('queued','retry','raw_failed')",(reason,identity))
                    c.execute("UPDATE source_date_failures SET status='resolved' WHERE source_key=%s AND latest_job_id=%s AND reason_code='public_capture_is_discovery_page_only' AND status='open'",(source,identity))
                continue
        count+=int(db.enqueue(source,key,item.get('ETag',''),form,priority,cursor))
    return count


def register_contract(db,policy,cursor=None):
    with (nullcontext(cursor) if cursor is not None else db.tx()) as c:
        body=encoded(policy)
        c.execute('SELECT contract_sha256 FROM source_contracts WHERE source_key=%s AND contract_version=%s',(policy['source_key'],policy['contract_version']))
        existing=c.fetchone()
        if existing and existing['contract_sha256']!=fingerprint(policy):raise ValueError('immutable_contract_version_conflict:'+policy['source_key'])
        c.execute('INSERT IGNORE INTO source_contracts VALUES(%s,%s,%s,%s,%s,UTC_TIMESTAMP(6))',(policy['source_key'],policy['contract_version'],policy['adapter'],body,fingerprint(policy)))
        raw=policy['raw_requirements']
        c.execute('INSERT IGNORE INTO source_raw_requirements VALUES(%s,%s,%s,%s,%s,%s)',(policy['source_key'],policy['contract_version'],raw['version'],'complete',encoded(raw['required_artifact_kinds']),encoded(raw['forbidden_shortcuts'])))
        c.execute('INSERT IGNORE INTO engine_sources(source_key,catalog_entries,contract_version,state,updated_at) VALUES(%s,%s,%s,%s,UTC_TIMESTAMP(6))',
                  (policy['source_key'],encoded(policy['catalog_entries']),policy['contract_version'],policy['state']))
        c.execute('UPDATE engine_sources SET contract_version=%s WHERE source_key=%s',(policy['contract_version'],policy['source_key']))


def daily(db,s3):
    today=datetime.now(timezone.utc).date();prefixes=[]
    for policy in db.config['contracts'].values():
        if policy['state'] in ('owner_paused','access_layer') or policy.get('adapter') in ('research_feed','market_archive_original'):continue
        for dataset in policy.get('datasets',[]):
            if '.' in dataset:continue
            for day in (today,today-timedelta(days=1)):
                prefixes.append(f"research-data/raw/source={policy['source_key']}/dataset={dataset}/ingestion_date={day}/")
    state=db.cursor('daily-prefix-rotation');offset=int(state.get('offset',0))
    selected=prefixes[offset:offset+12]
    if not selected:selected=prefixes[:12];offset=0
    def listing(prefix):
        # Bounded prefix pagination resumes independently. A finished pass starts
        # over so randomly ordered run IDs added earlier are not missed.
        state=db.cursor('daily:'+prefix)
        options={'Bucket':db.config['bucket'],'Prefix':prefix,'MaxKeys':100}
        if state.get('after'):options['StartAfter']=state['after']
        page=s3.list_objects_v2(**options);rows=page.get('Contents',[])
        return prefix,page,rows
    added=0
    with ThreadPoolExecutor(max_workers=4) as pool:
        for prefix,page,rows in pool.map(listing,selected):
            with db.tx() as c:added+=enqueue_objects(db,rows,'legacy_batch',10,c)
            db.save_cursor('daily:'+prefix,{'after':rows[-1]['Key'] if page.get('IsTruncated') and rows else None})
    db.save_cursor('daily-prefix-rotation',{'offset':offset+len(selected) if offset+len(selected)<len(prefixes) else 0,'total_prefixes':len(prefixes)})
    return added


def historical(db,s3):
    from metadata_engine.market_archive import ADAPTER, RECEIPTS
    rotation=db.cursor('historical-source-rotation');offset=int(rotation.get('offset',0))
    with db.tx() as c:
        c.execute("SELECT source_key FROM engine_sources WHERE state='enabled' ORDER BY source_key");sources=[r['source_key'] for r in c.fetchall()]
    selected=sources[offset:offset+8]
    if not selected:selected=sources[:8];offset=0
    scans=[('historical-source:'+source,'research-data/raw/source='+source+'/','legacy_batch') for source in selected]
    scans += [('historical-market-archive:'+source,f'{RECEIPTS}{source}/','public_receipt')
              for source, contract in db.config['contracts'].items() if contract.get('adapter') == ADAPTER
              and contract.get('state') == 'enabled']
    scans += [('historical-public','research-data/constellation-backfill/public-capture/athena/','public_receipt'),
           ('daily-native','research-data/constellation-backfill/daily-raw/records/','daily_raw')]
    count=0
    for name,prefix,form in scans:
        state=db.cursor(name);options={'Bucket':db.config['bucket'],'Prefix':prefix,'MaxKeys':db.config.get('scan_page_size',100)}
        if state.get('after'):options['StartAfter']=state['after']
        result=s3.list_objects_v2(**options);rows=result.get('Contents',[])
        with db.tx() as c:count+=enqueue_objects(db,rows,form,0 if name.startswith('historical') else 10,c)
        db.save_cursor(name,{'after':rows[-1]['Key'] if rows and result.get('IsTruncated') else None,'completed_passes':state.get('completed_passes',0)+int(not result.get('IsTruncated'))})
    db.save_cursor('historical-source-rotation',{'offset':offset+len(selected) if offset+len(selected)<len(sources) else 0})
    return count


def native_commits(db):
    state=db.cursor('native-queue');after=state.get('after','')
    with collection_tx(db.session,db.config,'controller') as c:
        c.execute("SELECT job_id,source_key,result_json FROM backfill_jobs WHERE status='succeeded' AND source_key NOT LIKE 'legacy:%%' AND job_id>%s ORDER BY job_id LIMIT 25",(after,));rows=c.fetchall()
    added=0
    with db.tx() as c:
        for row in rows:
            if db.config['contracts'].get(row['source_key'], {}).get('adapter') == 'research_feed':continue
            result=json.loads(row['result_json']) if row['result_json'] else {}
            uri=result.get('manifest_uri')
            if uri and uri.startswith('s3://'+db.config['bucket']+'/'):
                key=uri.split(db.config['bucket']+'/',1)[1]
                added+=int(db.enqueue(row['source_key'],key,result.get('manifest_sha256',''),'native_manifest',cursor=c))
    db.save_cursor('native-queue',{'after':rows[-1]['job_id'] if len(rows)==25 else ''})
    return added


def committed_daily_intake(db,s3):
    count=0;today=datetime.now(timezone.utc).date()
    etags_used = head_fallbacks = 0
    for day in (today,today-timedelta(days=1)):
        prefix=db.config['prefix']+'/intake/'+str(day)+'/'
        state=db.cursor('intake:'+str(day));args={'Bucket':db.config['bucket'],'Prefix':prefix,'MaxKeys':200}
        if state.get('after'):args['StartAfter']=state['after']
        page=s3.list_objects_v2(**args);rows=page.get('Contents',[])
        for item in rows:
            marker='intake-processed:'+item['Key'].rsplit('/',1)[1]
            if db.cursor(marker).get('done'):continue
            notice=json.loads(object_bytes(s3,db.config['bucket'],item['Key'],1024*1024))
            etags = notice.get('batch_etags')
            if not isinstance(etags, dict):
                etags = {}
            for key in notice.get('batches',[]):
                etag = etags.get(key)
                if not isinstance(etag, str) or not re.fullmatch(r'"[^"\x00-\x1f\x7f]+"', etag):
                    head_fallbacks += 1
                    etag=s3.head_object(Bucket=db.config['bucket'],Key=key)['ETag']
                else:
                    etags_used += 1
                count+=enqueue_objects(db,[{'Key':key,'ETag':etag}],'legacy_batch',20)
            db.save_cursor(marker,{'done':True})
        db.save_cursor('intake:'+str(day),{'after':rows[-1]['Key'] if rows and page.get('IsTruncated') else None})
    if etags_used or head_fallbacks:
        print(encoded({'stage':'daily_intake_etags','notice_etags_used':etags_used,
                       'head_fallbacks':head_fallbacks}),flush=True)
    return count


COLUMNS=[(name,'string') for name in ('record_id','observation_id','source_observation_id','source_key','dataset','record_kind','source_record_id','contract_version','raw_s3_uri','raw_sha256','raw_completeness_status','entity_match_status','ingested_at','labelled_at','labelled_json')]


def catalog(config,session):
    return _ready_catalog(session, config['athena_database'], config['bucket'], config['prefix'])


@lru_cache(maxsize=8)
def _ready_catalog(session, database, bucket, prefix):
    """Validate existing tables once per publisher session, creating them if needed."""
    glue=session.client('glue')
    descriptor={'Columns':[{'Name':name,'Type':kind} for name,kind in COLUMNS],
        'Location':'s3://'+bucket+'/'+prefix+'/jobs/',
        'InputFormat':'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat',
        'OutputFormat':'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat',
        'SerdeInfo':{'SerializationLibrary':'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'}}
    definition={'TableType':'EXTERNAL_TABLE','Parameters':{'classification':'parquet','metadata_engine_owner':'v2'},'PartitionKeys':[{'Name':'job_id','Type':'string'}],'StorageDescriptor':descriptor}
    ensured_database=False
    for table in ('source_observations', 'source_observations_staging'):
        try:
            old=glue.get_table(DatabaseName=database,Name=table)['Table']
        except glue.exceptions.EntityNotFoundException:
            if not ensured_database:
                try:glue.create_database(DatabaseInput={'Name':database,'Description':'Metadata engine validated original-evidence releases'})
                except glue.exceptions.AlreadyExistsException:pass
                ensured_database=True
            try:glue.create_table(DatabaseName=database,TableInput={'Name':table,**definition})
            except glue.exceptions.AlreadyExistsException:
                old=glue.get_table(DatabaseName=database,Name=table)['Table']
            else:
                continue
        if old['StorageDescriptor']['Columns']!=descriptor['Columns'] or old['PartitionKeys']!=definition['PartitionKeys']:
            raise ValueError('metadata_athena_schema_conflict:'+table)
    return descriptor


def verify_publication_batch(athena, config, jobs):
    """Verify a bounded set of staged partitions with one Athena execution.

    A grouped readback preserves the exact count for every job while
    emitting one Athena result object for the batch.
    """
    job_ids=[job['job_id'] for job in jobs]
    if not job_ids or any(not re.fullmatch('[0-9a-f]{64}', identity) for identity in job_ids):
        raise ValueError('metadata_publication_invalid_job_id')
    # Keep each partition filter small so Athena can plan exact lookups within
    # one execution. A single large IN filter slows Glue partition discovery.
    partition_filter_size = 5
    selects = []
    for index in range(0, len(job_ids), partition_filter_size):
        job_group = job_ids[index:index + partition_filter_size]
        values = ','.join("'" + identity + "'" for identity in job_group)
        selects.append(
            f"SELECT job_id, count(*) AS rows FROM {config['athena_database']}"
            f".source_observations_staging WHERE job_id IN ({values}) GROUP BY job_id"
        )
    query = ' UNION ALL '.join(selects)
    execution=athena.start_query_execution(
        QueryString=query, WorkGroup=config['athena_workgroup'],
        ResultConfiguration={'OutputLocation':'s3://'+config['bucket']+'/'+config['prefix']+'/athena-results/'},
    )['QueryExecutionId']
    started=time.monotonic()
    while True:
        status=athena.get_query_execution(QueryExecutionId=execution)['QueryExecution']['Status']
        state=status['State']
        if state=='SUCCEEDED':break
        if state in ('FAILED','CANCELLED') or time.monotonic()-started>45:
            raise RuntimeError('metadata_athena_verification_'+state+': '+str(status.get('StateChangeReason',''))[:400])
        time.sleep(1)
    rows=athena.get_query_results(QueryExecutionId=execution)['ResultSet']['Rows'][1:]
    counts={row['Data'][0]['VarCharValue']:int(row['Data'][1]['VarCharValue']) for row in rows}
    expected={job['job_id']:job['output_rows'] for job in jobs}
    if counts!=expected:raise ValueError('metadata_athena_count_mismatch')
    return execution


def verify_publication_jobs(athena, config, jobs):
    chunk_size=config.get('publication_verify_chunk_size', len(jobs))
    if type(chunk_size) is not int or not 1<=chunk_size<=100:
        raise ValueError('Invalid metadata publication verification size')
    chunks=[jobs[index:index+chunk_size] for index in range(0,len(jobs),chunk_size)]
    if len(chunks)==1:
        executions=[verify_publication_batch(athena, config, jobs)]
    else:
        # Keep separate Athena executions bounded if smaller groups are configured.
        with ThreadPoolExecutor(max_workers=2) as pool:
            executions=list(pool.map(lambda group: verify_publication_batch(athena,config,group), chunks))
    return {job['job_id']:execution for chunk,execution in zip(chunks,executions) for job in chunk}


def register_partitions(glue, config, table, partitions):
    parameters = {'DatabaseName': config['athena_database'], 'TableName': table}

    def verify_existing(partition):
        old = glue.get_partition(**parameters, PartitionValues=partition['Values'])['Partition']
        if old['StorageDescriptor']['Location'] != partition['StorageDescriptor']['Location']:
            raise ValueError('metadata_partition_conflict:'+table)

    if config.get('publication_glue_batch', False):
        try:
            response = glue.batch_create_partition(**parameters, PartitionInputList=partitions)
        except ClientError as error:
            if error.response['Error']['Code'] not in {'AccessDenied', 'AccessDeniedException'}:
                raise
            config['publication_glue_batch'] = False
            print(encoded({'stage':'metadata_glue_batch', 'status':'access_denied', 'table':table}),flush=True)
        else:
            inputs = {tuple(partition['Values']): partition for partition in partitions}
            for issue in response.get('Errors', []):
                code = issue['ErrorDetail']['ErrorCode']
                if code != 'AlreadyExistsException':
                    raise ValueError('metadata_glue_batch_partition:'+table+':'+code)
                verify_existing(inputs[tuple(issue['PartitionValues'])])
            return

    def register_one(partition):
        try:
            glue.create_partition(**parameters, PartitionInput=partition)
        except glue.exceptions.AlreadyExistsException:
            verify_existing(partition)

    # Existing CreatePartition permission still supports bounded overlapping
    # requests. Each result must succeed or match an identical prior write.
    with ThreadPoolExecutor(max_workers=min(4,len(partitions))) as pool:
        list(pool.map(register_one,partitions))


def publish(db, source_key=None, job_ids=None, *, daily=False):
    if daily and (source_key is None or job_ids is not None):
        raise ValueError('Daily publication requires one scheduled source')
    if job_ids is not None and (not source_key or not 0<len(job_ids)<=5 or any(not re.fullmatch('[0-9a-f]{64}',j)for j in job_ids)):
        raise ValueError('Publication repair requires one source and at most five exact job IDs')
    excluded=host_excluded_sources()
    if source_key in excluded:
        return 0
    if source_key is None:
        # Rotate bounded source queues rather than scan/join every historic job.
        state=db.cursor('publication_source_rotation');after=state.get('after','')
        with db.tx() as c:
            c.execute("SELECT source_key FROM engine_sources WHERE state='enabled' ORDER BY source_key");sources=[r['source_key']for r in c.fetchall()]
        sources=[s for s in sources if s not in excluded]
        sources=[s for s in sources if s>after]+[s for s in sources if s<=after]
        for source in sources[:8]:
            db.save_cursor('publication_source_rotation',{'after':source})
            count=publish(db,source_key=source)
            if count:return count
        return 0
    lock='metadata-publish:'+fingerprint(source_key)[:44]
    with db.tx() as c:
        slot = None
        if db.config.get('publication_parallel_sources') == 2:
            for index in range(2):
                candidate=f'metadata-publish-slot:{index}'
                c.execute('SELECT GET_LOCK(%s,0) acquired',(candidate,))
                if c.fetchone()['acquired']==1:
                    slot=candidate
                    break
            if slot is None:
                return 0
        try:
            c.execute('SELECT GET_LOCK(%s,0) acquired',(lock,))
            if c.fetchone()['acquired']!=1:
                return 0
            try:
                return publish_source(db,source_key,job_ids,daily=daily)
            finally:
                c.execute('SELECT RELEASE_LOCK(%s)',(lock,))
        finally:
            if slot:
                c.execute('SELECT RELEASE_LOCK(%s)',(slot,))


def daily_publication_candidate(job):
    kind = job['input_format'].split('@', 1)[0]
    return (kind == 'daily_raw' or kind == 'research_feed' and '/daily/' in job['input_key']
            or kind == 'legacy_batch' and 10 <= job['priority'] <= 20)


def daily_publication_input(db, job, cache):
    if not daily_publication_candidate(job):
        return False
    if not job['input_format'].startswith('legacy_batch'):
        return True
    pattern = r'research-data/raw/source=([^/]+)/dataset=([^/]+)/ingestion_date=[^/]+/run_id=([^/]+)/[^/]+\.jsonl'
    match = re.fullmatch(pattern, job['input_key'])
    if not match:
        return False
    source, dataset, run = match.groups()
    key = f'research-data/manifests/collection_runs/source={source}/dataset={dataset}/{run}/final.json'
    if key not in cache:
        s3 = db.session.client('s3')
        cache[key] = json.loads(object_bytes(s3, db.config['bucket'], key)).get('task', {}).get('mode')
    return cache[key] == 'daily'


def publication_candidates(db, source_key, target, job_ids=None, *, daily=False):
    """Read a bounded section of a source's indexed accepted-job stream."""
    config=db.config
    scan_key=('publication_daily_scan_' if daily else 'publication_scan_')+fingerprint(source_key)
    if source_key in host_excluded_sources():
        return scan_key, [], {}
    scan=db.cursor(scan_key) if job_ids is None else {}
    with db.tx() as c:
        query="SELECT job_id,finished_at FROM engine_jobs FORCE INDEX (source_publication_order) WHERE source_key=%s AND state='accepted'"
        params=[source_key]
        if job_ids is not None:
            query="SELECT job_id,finished_at FROM engine_jobs WHERE source_key=%s AND state='accepted' AND job_id IN ("+','.join('%s'for _ in job_ids)+')'
            params.extend(job_ids)
        from public_source_scope import TRADE_MINING_SOURCES
        from regional_source_review import PUBLIC_KEYS
        if source_key in PUBLIC_KEYS|TRADE_MINING_SOURCES|{'south_korea_fss_opendart','us_census_international_trade_api'} and config['contracts'].get(source_key,{}).get('contract_version')=='2.0.3':
            # The reviewed contract requires native originals. Older accepted
            # inputs retain their audit state while awaiting separate review.
            query+=' AND contract_version=%s';params.append('2.0.3')
        if scan.get('finished_at'):
            query+=' AND (finished_at>%s OR (finished_at=%s AND job_id>%s))'
            params.extend([scan['finished_at'],scan['finished_at'],scan['job_id']])
        if daily:
            query+=' AND finished_at>=UTC_TIMESTAMP(6)-INTERVAL 2 DAY'
        scan_limit=max(32, target*4)
        c.execute(query+f' ORDER BY finished_at,job_id LIMIT {scan_limit}',tuple(params));candidates=c.fetchall()
        if candidates:
            values=','.join('%s' for _ in candidates)
            daily_fields = ',j.input_key,j.input_format,j.priority' if daily else ''
            c.execute(f"""SELECT j.job_id,j.output_rows,j.output_uri{daily_fields}
              FROM engine_jobs j
              LEFT JOIN publication_releases r ON r.release_id=UNHEX(SUBSTRING(j.job_id,1,32))
              WHERE j.job_id IN ({values}) AND j.state='accepted' AND j.output_rows>0
                AND (r.release_id IS NULL OR r.status<>'published')""",
                tuple(row['job_id'] for row in candidates))
            matches={job['job_id']:job for job in c.fetchall()}
        else:
            matches={}
    return scan_key, candidates, matches


def publish_source(db, source_key, job_ids, *, daily=False):
    session=db.session;config=db.config
    target=config.get('publication_batch_size',5) if job_ids is None else 5
    if type(target) is not int or not 1<=target<=100:
        raise ValueError('Invalid metadata publication batch size')
    scan_key,candidates,matches=publication_candidates(db,source_key,target,job_ids,daily=daily)
    jobs=[];last=None;manifest_modes={}
    for row in candidates:
        last=row
        job=matches.get(row['job_id'])
        if job and (not daily or daily_publication_input(db,job,manifest_modes)):
            jobs.append(job)
        if len(jobs)>=target:break
    if not jobs:
        if job_ids is None and (last or not daily):
            db.save_cursor(scan_key,{'finished_at':str(last['finished_at']),'job_id':last['job_id']}if last else {})
        return 0
    glue=session.client('glue');athena=session.client('athena');s3=session.client('s3')
    descriptor=catalog(config,session)
    partitions=[{'Values':[job['job_id']],'StorageDescriptor':{
        **descriptor,'Location':job['output_uri'].rsplit('/',1)[0]+'/'}} for job in jobs]
    register_partitions(glue,config,'source_observations_staging',partitions)
    executions=verify_publication_jobs(athena,config,jobs)
    register_partitions(glue,config,'source_observations',partitions)

    def persist_receipt(job):
        job_id = job['job_id']
        execution = executions[job_id]
        receipt = {
            'job_id': job_id, 'query_execution_id': execution, 'rows': job['output_rows'],
            'output_uri': job['output_uri'], 'status': 'verified',
        }
        key = f"{config['prefix']}/publication/{job_id}/{execution}.json"
        uri = put(s3, config['bucket'], key, encoded(receipt).encode())
        return job_id, uri, fingerprint(receipt)

    with ThreadPoolExecutor(max_workers=min(4, len(jobs))) as pool:
        releases = list(pool.map(persist_receipt, jobs))
    with db.tx() as c:
        placeholders=','.join(
            ["(UNHEX(SUBSTRING(%s,1,32)),'labelled',%s,%s,'published',UTC_TIMESTAMP(6),UTC_TIMESTAMP(6))"]*len(releases))
        c.execute(f"""INSERT INTO publication_releases(release_id,release_kind,s3_uri,manifest_sha256,status,created_at,verified_at)
          VALUES {placeholders}
          ON DUPLICATE KEY UPDATE status='published',verified_at=UTC_TIMESTAMP(6)""",
            tuple(value for release in releases for value in release))
    if job_ids is None:db.save_cursor(scan_key,{'finished_at':str(last['finished_at']),'job_id':last['job_id']})
    return len(jobs)


def notify(db):
    with db.tx() as c:
        c.execute("SELECT GET_LOCK('metadata_engine:notifications',0) acquired")
        if c.fetchone()['acquired']!=1:return 0
    try:return _notify(db)
    finally:
        with db.tx() as c:c.execute("SELECT RELEASE_LOCK('metadata_engine:notifications')")


def _notify(db):
    sns=db.session.client('sns');config=db.config
    with db.tx() as c:
        c.execute('SELECT * FROM engine_notifications WHERE sent_at IS NULL ORDER BY created_at LIMIT 40');rows=c.fetchall()
    if not rows:return 0
    subscribers=[r for page in sns.get_paginator('list_subscriptions_by_topic').paginate(TopicArn=config['email_topic_arn']) for r in page['Subscriptions']]
    if not subscribers or any(s['Protocol']!='email' or s['Endpoint']!=config['email_recipient'] or not s['SubscriptionArn'].startswith('arn:') for s in subscribers):
        raise RuntimeError('metadata_notification_recipient_verification_failed')
    payloads=[json.loads(row['payload']) for row in rows]
    message='Metadata processing stopped for these sources after four consecutive raw-data validation failures on separate input batches. Raw collection is unchanged.\n\n'+json.dumps(payloads,indent=2)+'\n\nInspect the evidence reports, repair capture or the source contract, then resume the named source through metadata_engine.control. Existing backlog is retained.'
    reply=sns.publish(TopicArn=config['email_topic_arn'],Subject='Metadata engine: '+str(len(rows))+' sources stopped - raw data incomplete',Message=message)
    with db.tx() as c:
        for row in rows:c.execute('UPDATE engine_notifications SET sent_at=UTC_TIMESTAMP(6),sns_message_id=%s,attempts=attempts+1 WHERE notification_id=%s AND sent_at IS NULL',(reply['MessageId'],row['notification_id']))
    return len(rows)


def main():
    from metadata_engine.research_feeds import discover as research_feed_discovery
    p=argparse.ArgumentParser();p.add_argument('--config',default=str(Path(__file__).resolve().parents[1]/'config/metadata-engine.json'));p.add_argument('--no-daily',action='store_true');p.add_argument('--no-publication',action='store_true');args=p.parse_args()
    config=json.loads(Path(args.config).read_text());db=Database(config);s3=MeteredS3(db.session.client('s3'));result={}
    # Independent stages continue when another stage has an operational error.
    for name,fn in [('notifications',lambda:notify(db)),('publication',lambda:0 if args.no_publication else publish(db)),('research_feed_discovery',lambda:research_feed_discovery(db,s3,include_daily=not args.no_daily)),('daily_intake',lambda:committed_daily_intake(db,s3)),('native_commits',lambda:native_commits(db)),('daily_discovery',lambda:0 if args.no_daily else daily(db,s3)),('historical_discovery',lambda:historical(db,s3))]:
        print(encoded({'stage':name,'state':'started'}),flush=True)
        try:result[name]=fn()
        except Exception as e:result[name]={'error':type(e).__name__,'reason':str(e)[:350]}
        print(encoded({'stage':name,'result':result[name]}),flush=True)
    result['status']=db.stats(include_jobs=False);result['s3_requests']=s3.counts();print(encoded(result),flush=True)


if __name__=='__main__':main()
