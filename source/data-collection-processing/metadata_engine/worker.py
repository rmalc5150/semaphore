"""Resource-bounded historical/daily labelling worker on m7i."""
import argparse
import hashlib
import io
import json
import re
import time
from datetime import datetime,timezone
from pathlib import Path

import boto3

from metadata_engine.runtime_db import Database,encoded,fingerprint,collection_tx
from metadata_engine.evidence import RawFailure,Uncommitted,object_bytes,evidence_for,job_evidence_cache
from metadata_engine.labelling import label_observation
from metadata_engine.graph import register
from metadata_engine.s3_metrics import MeteredS3


def now():return datetime.now(timezone.utc).isoformat()


def load_input(s3,bucket,job,db=None):
    key=job['input_key']
    input_form=job['input_format'].split('@')[0]
    native_page=int(input_form.split(':')[1]) if input_form.startswith('native_manifest:') else 0
    job={**job,'input_format':input_form.split(':')[0]}
    if job['input_format'] == 'research_feed':
        from metadata_engine.research_feeds import load_batch
        return load_batch(s3, bucket, job)
    if job['input_format']=='legacy_batch':
        match=re.fullmatch(r'research-data/raw/source=([^/]+)/dataset=([^/]+)/ingestion_date=[^/]+/run_id=([^/]+)/[^/]+\.jsonl',key)
        if not match:raise Uncommitted('legacy_input_layout_not_supported')
        source,dataset,run=match.groups()
        manifest_key=f'research-data/manifests/collection_runs/source={source}/dataset={dataset}/{run}/final.json'
        from botocore.exceptions import ClientError
        try:manifest=json.loads(object_bytes(s3,bucket,manifest_key))
        except ClientError as error:
            if error.response['Error']['Code'] in ('NoSuchKey','404','NotFound'):raise Uncommitted('collection_manifest_not_yet_present') from None
            raise
        try:head=json.loads(object_bytes(s3,bucket,'research-data/checkpoints/'+manifest['task_id']+'/head.json'))
        except ClientError as error:
            if error.response['Error']['Code'] in ('NoSuchKey','404','NotFound'):raise Uncommitted('collection_checkpoint_head_missing') from None
            raise
        if manifest_key.removeprefix('research-data/') not in head.get('terminal_history',[]):raise Uncommitted('manifest_not_in_committed_history')
        candidates=[batch for page in manifest.get('pages',[]) for batch in page['batches'] if 'research-data/'+batch['key']==key]
        if len(candidates)!=1:raise Uncommitted('batch_not_in_manifest')
        batch=candidates[0];raw=object_bytes(s3,bucket,key,expected=batch['sha256'])
        rows=[json.loads(line) for line in raw.splitlines() if line]
        if len(rows)!=batch['records'] or len(raw)!=batch['bytes']:raise RawFailure('committed_batch_count_or_bytes_mismatch')
        return rows,raw,manifest
    if job['input_format']=='public_receipt':
        raw=object_bytes(s3,bucket,key)
        rows=[json.loads(line) for line in raw.splitlines() if line]
        output=[]
        for r in rows:
            if r.get('market_archive_original'):
                from metadata_engine.market_archive import from_receipt
                output.append(from_receipt(r, key))
                continue
            if r.get('market_original'):
                from metadata_engine.market_sources import from_receipt
                output.append(from_receipt(r))
                continue
            from metadata_engine.trade_mining import NATIVE_DATASETS
            if r.get('source') in NATIVE_DATASETS and job.get('contract_version') == '2.0.3':
                from metadata_engine.trade_mining import from_public_receipt
                output.extend(from_public_receipt(r,s3,bucket));continue
            if r.get('source')in ('taiwan_twse_mops_issuer_and_revenue_archives','taiwan_customs_trade_statistics'):
                from metadata_engine.regional_public import twse_rows,customs_rows
                output.extend((twse_rows if r['source']=='taiwan_twse_mops_issuer_and_revenue_archives'else customs_rows)(r,s3,bucket));continue
            if r.get('source')=='nist_robotics_methods':
                from metadata_engine.nist_methods import from_public_receipt
                output.extend(from_public_receipt(r,s3,bucket));continue
            if r.get('artifact_kind')=='discovery_page':raise RawFailure('public_capture_is_discovery_page_only')
            if r.get('source')=='doe_storage_program':
                from metadata_engine.doe_storage import from_public_receipt
                output.extend(from_public_receipt(r,s3,bucket));continue
            if r.get('source')=='crossref_proceedings':
                from metadata_engine.crossref import from_public_receipt
                output.extend(from_public_receipt(r,s3,bucket));continue
            output.append({'source':r['source'],'dataset':'public_documents','source_record_id':r['sha256'],
                'ingested_at':r['retrieved_at'],'source_url':r['source_url'],'payload':{'source_evidence':[{'s3_uri':r['artifact_uri'],'sha256':r['sha256'],'source_url':r['source_url'],'retrieved_at':r['retrieved_at']},*r.get('embedded_artifacts',[])]},'available_at':None})
        return output,raw,{'task':{'mode':rows[0].get('mode','historical')},'status':'complete'}
    if job['input_format']=='native_manifest':
        raw=object_bytes(s3,bucket,key);m=json.loads(raw);rows=[]
        if db is None:raise Uncommitted('native_commit_database_required')
        with collection_tx(db.session,db.config) as c:
            c.execute('SELECT status,result_json FROM backfill_jobs WHERE job_id=%s',(m['job_id'],));committed=c.fetchone()
        result=json.loads(committed['result_json']) if committed and committed.get('result_json') else {}
        if not committed or committed['status']!='succeeded' or result.get('manifest_uri')!='s3://'+bucket+'/'+key or result.get('manifest_sha256')!=hashlib.sha256(raw).hexdigest():
            raise Uncommitted('native_manifest_not_committed_in_collection_queue')
        if not m.get('pagination_exhausted'):raise Uncommitted('native_query_not_exhausted')
        pages=m.get('pages',[])
        if native_page>=len(pages) and pages:raise Uncommitted('native_page_outside_manifest')
        for page in pages[native_page:native_page+1]:
            p=page['records'];u=p['uri'].split(bucket+'/',1)[1];body=object_bytes(s3,bucket,u,expected=p['sha256'])
            # Canonical record links can name a different provider hostname
            # (e.g. www.nsf.gov versus api.nsf.gov). Verify raw origin against
            # the collector's actual request receipt rather than that link.
            request_key=key.rsplit('/manifest.json',1)[0]+'/requests/'+str(page['request_page'])+'.json'
            request_meta=json.loads(object_bytes(s3,bucket,request_key))
            if request_meta['raw']['sha256']!=page['raw']['sha256']:raise RawFailure('native_request_raw_reference_mismatch')
            projection=request_meta.get('request_parameters',{})
            if any(projection.get(field) for field in ('printFields','fields','$select','select')):
                raise RawFailure('provider_request_projects_subset_of_raw_fields')
            for line in body.splitlines():
                r=json.loads(line)
                r.update(source=r['source_key'],dataset=r['record_kind'],ingested_at=r['retrieved_at'],source_url=r.get('original_url'))
                r['payload']={**r['payload'],'source_evidence':[{'s3_uri':page['raw']['uri'],'sha256':page['raw']['sha256'],'source_url':request_meta['request_url'],'retrieved_at':r['retrieved_at']}]}
                rows.append(r)
        return rows,raw,{'status':'complete','task':{'mode':'historical'},'native_page':native_page,'native_pages':len(pages)}
    if job['input_format']=='daily_raw':
        raw=object_bytes(s3,bucket,key);rows=[]
        endpoints={'usgs_earthquakes':'https://earthquake.usgs.gov/fdsnws/event/1/query','nsf_awards':'https://api.nsf.gov/services/v1/awards.json','arxiv':'https://export.arxiv.org/api/query'}
        for line in raw.splitlines():
            r=json.loads(line);source=r['source'];day=r['retrieved_at'][:10]
            state_key=f"research-data/constellation-backfill/daily-raw/states/{day}/{source}/{r['partition_start']}.json"
            state=json.loads(object_bytes(s3,bucket,state_key))
            if state.get('status')!='complete':raise Uncommitted('daily_raw_collection_not_complete')
            data=json.loads(r['payload_json']);u=r['raw_uri'];sha=u.rsplit('/',1)[1]
            rows.append({'source':source,'dataset':'research_records','source_record_id':r['source_record_id'],'source_url':endpoints.get(source,''),
                'ingested_at':r['retrieved_at'],'available_at':None,'payload':{'data':data,'source_evidence':[{'s3_uri':u,'sha256':sha,'source_url':endpoints.get(source,''),'retrieved_at':r['retrieved_at']}]}})
        return rows,raw,{'status':'complete','task':{'mode':'daily'}}
    raise Uncommitted('unknown_input_format')


def put(s3,bucket,key,body,media='application/json'):
    from botocore.exceptions import ClientError
    import base64
    sha=hashlib.sha256(body).hexdigest()
    checksum=base64.b64encode(bytes.fromhex(sha)).decode()
    # A successful S3 checksum-validated immutable write needs no read-after-write.
    try:s3.put_object(Bucket=bucket,Key=key,Body=body,ContentType=media,ServerSideEncryption='AES256',IfNoneMatch='*',ChecksumSHA256=checksum)
    except ClientError as e:
        if e.response['Error']['Code'] not in ('412','PreconditionFailed'):raise
        # A competing/retried write is only accepted after proving identical bytes.
        object_bytes(s3,bucket,key,expected=sha)
    return 's3://'+bucket+'/'+key


def process(db,s3,config,job):
    bucket=config['bucket'];base=config['prefix']+'/jobs/'+job['job_id'];report={'job_id':job['job_id'],'source':job['source_key'],'input_key':job['input_key'],'started_at':now(),'build_sha256':config.get('build_sha256')}

    def reject_raw(reason):
        report.update(status='raw_failed',reason=reason,checked_at=now())
        uri=put(s3,bucket,base+'/attempts/'+job['lease_token']+'.json',encoded(report).encode())
        db.finish(job,'raw_failed',reason,report=uri)

    try:
        with db.tx() as c:
            c.execute('SELECT contract_json FROM source_contracts WHERE source_key=%s AND contract_version=%s',(job['source_key'],job['contract_version']))
            row=c.fetchone()
            if not row:raise RawFailure('source_contract_missing')
            contract=json.loads(row['contract_json'])
        rows,raw,manifest=load_input(s3,bucket,job,db)
        offset=int(job['input_format'].split('@')[1]) if '@' in job['input_format'] else 0
        batch_size = 128 if job['input_format'].split('@')[0] == 'research_feed' else 32
        total=len(rows);rows=rows[offset:offset+batch_size]
        input_sha256 = hashlib.sha256(raw).hexdigest()
        deadline=time.monotonic()+150
        accepted=[]
        hkex_client = None
        notices = []
        document_exclusions = []
        article_gaps = []
        resolved_article_failures = []
        if job['source_key'] == 'hkex_news':
            from metadata_engine.hkex_documents import Client
            hkex_client = Client(s3, bucket)
        seen_originals = set()
        with job_evidence_cache(rows) as evidence_cache_stats:
            for original in rows:
                if time.monotonic()>deadline:raise TimeoutError('metadata_batch_time_budget')
                if (original.get('source') or original.get('source_key'))!=job['source_key']:raise RawFailure('source_identity_mismatch')
                expanded = [(original, None)]
                if hkex_client is not None:
                    from metadata_engine.hkex_documents import expand
                    from hkex_originals import OriginalError
                    try: expanded, notice = expand(original, hkex_client, s3, bucket)
                    except OriginalError as error: raise RawFailure(str(error)) from error
                    if notice: notices.append(notice)
                for current, provider_envelope in expanded:
                    if job['source_key']=='uspto_odp':
                        from metadata_engine.patent_sources import reviewed_exclusion
                        exclusion=reviewed_exclusion(current,s3,bucket)
                        if exclusion:
                            document_exclusions.append(exclusion);continue
                    try:
                        artifacts=evidence_for(current,contract,s3,bucket)
                    except RawFailure as error:
                        if job['source_key'] not in ('people_rss','personnel_archive'):raise
                        article_gaps.append({'source_record_id':current['source_record_id'],'source_url':current['source_url'],'reason':str(error)})
                        continue
                    if job['source_key'] in ('people_rss','personnel_archive'):
                        from metadata_engine.runtime_db import fingerprint
                        resolved_article_failures.append(fingerprint([job['source_key'],current['source_record_id'],'rss_article_content' if job['source_key']=='people_rss' else 'personnel_archive_content']))
                    identity=(current['source_record_id'], tuple(a['sha256'] for a in artifacts))
                    if hkex_client is not None:
                        if identity in seen_originals: continue
                        seen_originals.add(identity)
                    # Chinese originals retain their own provider IDs and native
                    # listing provenance; an English availability notice is not a filing.
                    envelope=provider_envelope or {'artifact_kind':'provider_record','s3_uri':'s3://'+bucket+'/'+job['input_key'],
                              'sha256':input_sha256,'origin':'first_party_source',
                              'representation':'collected source envelope; substantive raw artifacts listed separately'}
                    if contract['adapter'] in ('market_archive_original', 'sedi_issuer_events'):
                        envelope = artifacts[0]
                        raw_artifacts = artifacts
                    else:
                        raw_artifacts = [envelope, *artifacts]
                    candidate={**current,'raw_s3_uri':envelope['s3_uri'],'raw_sha256':envelope['sha256'],
                               'raw_completeness_status':'complete','raw_artifacts':raw_artifacts}
                    try:accepted.append(label_observation(candidate,contract))
                    except ValueError as error:raise RawFailure(str(error)) from None
        report['evidence_cache'] = dict(evidence_cache_stats)
        if document_exclusions:
            report['reviewed_document_exclusions']=document_exclusions
        if article_gaps:
            report['article_fulltext_gaps'] = article_gaps
            report['gap_handling'] = 'Not published as raw-complete; full-text capture/backfill retries independently.'
        if notices:
            report['language_availability_notices'] = notices
            report['notice_handling'] = 'Original Chinese IDs retained; English notices excluded from substantive-filing counts.'
        report.update(status='accepted',records=len(accepted),collection_status=manifest.get('status'),checked_at=now())
        output=None
        phases = {}
        graph_stats = None
        if accepted:
            encode_started = time.monotonic()
            import pyarrow as pa
            import pyarrow.parquet as pq
            records=[]
            for row in accepted:
                records.append({key:row.get(key) for key in ('record_id','observation_id','source_observation_id','source_key','dataset','record_kind','source_record_id','contract_version','raw_s3_uri','raw_sha256','raw_completeness_status','entity_match_status','ingested_at','labelled_at')}|{'labelled_json':encoded(row),'job_id':job['job_id']})
            table=pa.Table.from_pylist(records);buffer=io.BytesIO();pq.write_table(table,buffer,compression='zstd',row_group_size=64)
            body=buffer.getvalue();key=base+'/data/'+hashlib.sha256(body).hexdigest()+'/part.parquet'
            upload_started = time.monotonic()
            output=put(s3,bucket,key,body,'application/vnd.apache.parquet')
            graph_started = time.monotonic()
            # Graph writes are idempotent. Only the final job commit exposes its
            # output to the controller's Athena publisher.
            if job['source_key'] in ('openalex_scholarly_graph','japan_kaken_funded_research'):
                graph_stats = {}
            graph_batches = register(db,accepted,write_stats=graph_stats)
            phases = {
                'parquet_encode': round(upload_started - encode_started, 4),
                'parquet_upload': round(graph_started - upload_started, 4),
                'graph_write': round(time.monotonic() - graph_started, 4),
            }
            report['graph_insert_batches'] = graph_batches
        report['output_uri']=output
        report_uri=put(s3,bucket,base+'/attempts/'+job['lease_token']+'.json',encoded(report).encode())
        if offset+len(rows)<total:
            form=job['input_format'].split('@')[0]+'@'+str(offset+len(rows))
            db.enqueue(job['source_key'],job['input_key'],job['input_etag'],form,job['priority'])
        elif manifest.get('native_page',0)+1<manifest.get('native_pages',0):
            form='native_manifest:'+str(manifest['native_page']+1)
            db.enqueue(job['source_key'],job['input_key'],job['input_etag'],form,job['priority'])
        commit_started = time.monotonic()
        db.finish(job,'accepted',report=report_uri,output=output,rows=len(accepted))
        phases['final_commit'] = round(time.monotonic() - commit_started, 4)
        report['phase_seconds'] = phases
        if graph_stats is not None:
            report['graph_table_stats'] = graph_stats
        if job['source_key'] in ('people_rss','personnel_archive'):
            from metadata_engine.runtime_db import fingerprint
            with db.tx() as c:
                for failure_id in resolved_article_failures:
                    c.execute("UPDATE pipeline_failures SET status='resolved' WHERE failure_id=%s",(failure_id,))
                for gap in article_gaps:
                    failure_id=fingerprint([job['source_key'],gap['source_record_id'],'rss_article_content' if job['source_key']=='people_rss' else 'personnel_archive_content'])
                    c.execute("""INSERT INTO pipeline_failures
                        (failure_id,source_key,job_id,stage,error_reason,report_uri,first_seen_at,last_seen_at,occurrence_count,status)
                        VALUES(%s,%s,%s,%s,%s,%s,UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),1,'open')
                        ON DUPLICATE KEY UPDATE job_id=VALUES(job_id),error_reason=VALUES(error_reason),report_uri=VALUES(report_uri),last_seen_at=UTC_TIMESTAMP(6),occurrence_count=occurrence_count+1,status='open'""",
                        (failure_id,job['source_key'],job['job_id'],'rss_article_content' if job['source_key']=='people_rss' else 'personnel_archive_content',(gap['reason']+': '+gap['source_url'])[:1000],report_uri))
    except RawFailure as e:
        reject_raw(str(e))
    except Uncommitted as e:db.finish(job,'uncommitted',str(e))
    except Exception as e:
        from metadata_engine.runtime_db import STREAMING_RETRY
        from metadata_engine.streaming import StreamingRequired,active as streaming_active,register_source
        from metadata_engine.evidence import OversizedArtifact
        streaming = streaming_active()
        if isinstance(e,(StreamingRequired,OversizedArtifact)) and not streaming:
            # Ensure the streaming worker can discover the source before
            # removing the job from the ordinary worker's eligible retries.
            register_source(db,job['source_key'])
            db.finish(job,'retry',STREAMING_RETRY)
            report.update(status='retry',reason=STREAMING_RETRY)
        elif streaming and isinstance(e,OversizedArtifact):
            reject_raw('streaming_adapter_required_for_oversized_input')
        else:
            # Keep temporary streaming failures in their assigned lane.
            reason=type(e).__name__+':'+str(e)[:350]
            if streaming:
                reason=STREAMING_RETRY+':'+reason
            db.finish(job,'retry',reason)
            report.update(status='retry',reason=reason)
    if hasattr(s3,'counts'):report['s3_requests']=s3.counts()
    print(encoded(report),flush=True)


def main():
    from pymysql.err import OperationalError

    p=argparse.ArgumentParser();p.add_argument('--config',default=str(Path(__file__).resolve().parents[1]/'config/metadata-engine.json'));p.add_argument('--max-jobs',type=int,default=8);p.add_argument('--max-seconds',type=int,default=240)
    p.add_argument('--source', help='Claim work for one source only')
    args=p.parse_args()
    config=json.loads(Path(args.config).read_text());db=Database(config);s3=MeteredS3(db.session.client('s3'));started=time.monotonic();done=0
    claim_errors = 0
    while done < args.max_jobs:
        if time.monotonic()-started>args.max_seconds:break
        try:
            job=db.claim(source_key=args.source) if args.source else db.claim()
        except OperationalError as error:
            if not error.args or error.args[0] not in (1205, 1213, 3024):
                raise
            claim_errors += 1
            print(encoded({'stage': 'metadata_claim', 'status': 'deferred',
                           'error_code': error.args[0], 'attempt': claim_errors}),flush=True)
            remaining = args.max_seconds - (time.monotonic() - started)
            if claim_errors >= 3 or remaining <= 0:
                break
            time.sleep(min(2 ** claim_errors, remaining))
            continue
        claim_errors = 0
        if not job:
            # A transient source lock is not an empty queue. Stay available
            # inside the existing time budget instead of waiting for a timer.
            remaining=args.max_seconds-(time.monotonic()-started)
            if remaining<=0:break
            time.sleep(min(2,remaining))
            continue
        process(db,s3,config,job);done+=1
    print(encoded({'jobs_processed':done,'elapsed_seconds':round(time.monotonic()-started,2),'s3_requests':s3.counts()}))


if __name__=='__main__':main()
