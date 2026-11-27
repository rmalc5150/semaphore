"""Bounded recovery of rejected OpenDART filing originals."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time

import requests

from metadata_engine.dart_originals import REPAIR_REASONS, recover
from metadata_engine.evidence import RawFailure, Uncommitted
from metadata_engine.regional_filings import evidence
from metadata_engine.runtime_db import Database, STREAMING_RETRY
from metadata_engine.streaming import register_source, session as streaming_session
from metadata_engine.worker import load_input


SOURCE = 'south_korea_fss_opendart'
CURSOR = 'dart-original-viewer-repair-v1'
PAUSED = Path('/opt/constellation/batch-paused')
FIELDS = 'job_id,source_key,input_key,input_format,input_etag,contract_version,state,finished_at,reason'


def candidates(db, identities, *, cursor_name=CURSOR):
    with db.tx() as c:
        c.execute('SELECT state FROM engine_sources WHERE source_key=%s',(SOURCE,))
        source=c.fetchone()
        if not source or source['state']!='enabled':
            return []
    if not identities:
        state=db.cursor(cursor_name)
        condition=''
        args=[SOURCE]
        if state.get('finished_at'):
            condition='AND (finished_at>%s OR (finished_at=%s AND job_id>%s))'
            args.extend([state['finished_at'],state['finished_at'],state['job_id']])
        with db.tx() as c:
            c.execute(f"""SELECT job_id FROM engine_jobs FORCE INDEX(source_publication_order)
                          WHERE source_key=%s AND state='raw_failed' {condition}
                          ORDER BY finished_at,job_id LIMIT 96""",args)
            identities=[row['job_id'] for row in c.fetchall()]
    if not identities:
        return []
    values=','.join('%s' for _ in identities)
    with db.tx() as c:
        c.execute(f"SELECT {FIELDS} FROM engine_jobs WHERE job_id IN ({values}) AND source_key=%s AND state='raw_failed'",
                  (*identities,SOURCE))
        by_id={row['job_id']:row for row in c.fetchall()}
    return [by_id[identity] for identity in identities if identity in by_id]


def repair_job(db, s3, bucket, client, job, *, xml_only=False, request_budget=None):
    rows, _, _=load_input(s3,bucket,job,db)
    offset=int(job['input_format'].split('@')[1]) if '@' in job['input_format'] else 0
    rows=rows[offset:offset+32]
    if not rows:
        raise RawFailure('dart_repair_empty_input')
    recovered=[]
    for row in rows:
        if row.get('source')!=SOURCE:
            raise RawFailure('dart_repair_source_mismatch')
        try:
            evidence(row,s3,bucket,xml_only=xml_only)
        except RawFailure as failure:
            if str(failure) not in REPAIR_REASONS:
                raise
            details=row['payload']['data']
            identity=row['source_record_id']
            document=details.get('primary_document')
            if not details.get('filing') or not details.get('index_evidence'):
                raise
            if xml_only:
                from metadata_engine.dart_xml_repair import recover as recover_xml
                anchor,checksum=('old_archive',document['sha256']) if document else ('archived_index',details['index_evidence']['sha256'])
                recover_xml(s3,bucket,client,identity,checksum,anchor,request_budget)
            elif document:
                recover(s3,bucket,client,identity,details['filing'],document['sha256'])
            else:
                recover(s3,bucket,client,identity,details['filing'],details['index_evidence']['sha256'],
                        anchor='archived_index')
            artifacts=evidence(row,s3,bucket,xml_only=xml_only)
            originals=[item for item in artifacts if item['artifact_kind']=='primary_document']
            recovered.append({'receipt':identity,'documents':len(originals),
                              'pages':sum(item.get('validation',{}).get('pages',0) for item in originals)})
    register_source(db,SOURCE)
    with db.tx() as c:
        c.execute("""UPDATE engine_jobs SET state='retry',reason=%s,available_after=UTC_TIMESTAMP(6)
                     WHERE job_id=%s AND source_key=%s AND state='raw_failed' AND reason=%s AND finished_at=%s""",
                  (STREAMING_RETRY,job['job_id'],SOURCE,job['reason'],job['finished_at']))
        return recovered, bool(c.rowcount)


def main(argv=None, aws_session=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-receipts',type=int,default=16,choices=range(1,33))
    parser.add_argument('--max-seconds',type=int,default=200,choices=range(30,601))
    parser.add_argument('--job-id',action='append',default=[])
    parser.add_argument('--xml-only',action='store_true')
    parser.add_argument('--max-provider-requests',type=int,default=12,choices=range(1,33))
    args=parser.parse_args(argv)
    if args.job_id and (len(args.job_id)>32 or any(not re.fullmatch('[a-f0-9]{64}',value) for value in args.job_id)):
        parser.error('--job-id requires up to 32 exact identities')
    path=Path(__file__).resolve().parents[1]/'config/metadata-engine.json'
    db=Database(json.loads(path.read_text()),session=aws_session)
    cursor_name='dart-original-xml-repair-v1' if args.xml_only else CURSOR
    jobs=candidates(db,args.job_id,cursor_name=cursor_name)
    request_budget={'remaining':args.max_provider_requests}
    bucket=db.config['bucket'];s3=db.session.client('s3')
    counts=Counter();requeues=[];deadline=time.monotonic()+args.max_seconds
    with requests.Session() as client,streaming_session():
        client.headers['User-Agent']='ConstellationResearch/1.0 (support@optima-holdings.com)'
        for job in jobs:
            if PAUSED.exists() or time.monotonic()>=deadline or counts['attempted']>=args.max_receipts:
                break
            if job['reason'] in REPAIR_REASONS:
                counts['attempted']+=1
                try:
                    recovered, changed=repair_job(db,s3,bucket,client,job,xml_only=args.xml_only,request_budget=request_budget)
                    if changed:
                        requeues.append({'job_id':job['job_id'],'verified_originals':recovered})
                except (RawFailure,Uncommitted,UnicodeError) as failure:
                    detail=str(failure) if isinstance(failure,(RawFailure,Uncommitted)) else 'dart_repair_invalid_viewer_encoding'
                    counts[detail]+=1
                    db.save_cursor(cursor_name+':'+job['job_id'],{'status':'repair_required','reason':detail,
                                     'checked_at':datetime.now(timezone.utc).isoformat()})
                    if detail.startswith(('dart_repair_transport_', 'dart_repair_http_429', 'dart_repair_http_5',
                            'dart_xml_repair_transport_', 'dart_xml_repair_http_429', 'dart_xml_repair_http_5',
                            'dart_xml_repair_provider_cooldown', 'dart_xml_repair_budget_exhausted')):
                        break  # The next run retries this source outage from the same position.
            if not args.job_id:
                db.save_cursor(cursor_name,{'finished_at':str(job['finished_at']),'job_id':job['job_id']})
    print(json.dumps({'source':SOURCE,'results':counts,'requeued':requeues}),flush=True)


if __name__=='__main__':
    main()
