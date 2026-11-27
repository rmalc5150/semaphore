"""Checkpointed queue-wide audit using covering indexes and bounded failure reads."""
import json
import time
import pymysql
from pathlib import Path
from metadata_engine.runtime_db import Database

FAILURES={'metadata':('raw_failed','retry','uncommitted'),'historical':('blocked','retryable_failed')}
STATES={'metadata':'state','historical':'status'}
TABLES={'metadata':'engine_jobs','historical':'backfill_jobs'}
INDEXES={'metadata':'source_jobs','historical':'source_status_updated'}
TRANSIENT={1205,1213,2006,2013,3024}
ALL_STATES={'metadata':('queued','running','accepted','raw_failed','retry','uncommitted','superseded'),
            'historical':('pending','running','succeeded','retryable_failed','blocked','permanently_unavailable')}

def query(db,sql,params,checkpoint):
    started=time.monotonic()
    with db()as cursor:
        cursor.execute(sql,params)
        rows=cursor.fetchall()
    metrics=checkpoint['query_metrics'];metrics['queries']+=1
    metrics['max_query_seconds']=max(metrics['max_query_seconds'],round(time.monotonic()-started,4))
    return rows

def failure_reason(lane,row):
    if lane=='metadata':return row.get('reason')or 'unspecified'
    raw=row.get('result_json')
    try:result=json.loads(raw)if isinstance(raw,str)else(raw or{})
    except (ValueError,TypeError):return 'invalid_failure_json'
    return str(result.get('reason')or result.get('error_type')or 'unspecified')[:512]

def run(control,job,save,stamp,deadline_seconds=480,metadata=None):
    if metadata is None:
        cfg=json.loads((Path(__file__).resolve().parents[1]/'config/metadata-engine.json').read_text())
        metadata=Database(cfg)
    checkpoint=job.get('checkpoint')or{}
    if checkpoint.get('algorithm_version')!=2:
        checkpoint={'algorithm_version':2,'phase':'inventory','started_at':stamp(),'counts':{},'failure_counts':{},'failure_samples':{},'tables':{},'source_controls':[],
                    'sources':{},'position':0,'failure_position':0,'failure_tasks':[],
                    'after':'','after_updated_at':0,'batch_size':25,'query_metrics':{'queries':0,'max_query_seconds':0,'retries':0}}
    databases={'metadata':metadata.tx,'historical':control.db}
    deadline=time.monotonic()+deadline_seconds
    while time.monotonic()<deadline:
        phase=checkpoint['phase']
        if phase=='inventory':
            for lane,db in databases.items():
                checkpoint['tables'][lane]=query(db,"SELECT /*+ MAX_EXECUTION_TIME(5000) */ TABLE_NAME AS table_name,ENGINE AS engine,TABLE_ROWS AS estimated_rows,DATA_LENGTH AS data_bytes,INDEX_LENGTH AS index_bytes FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME",(),checkpoint)
            checkpoint['source_controls']=query(metadata.tx,"SELECT /*+ MAX_EXECUTION_TIME(5000) */ source_key,state,last_reason FROM engine_sources ORDER BY source_key",(),checkpoint)
            checkpoint['sources']['metadata']=[r['source_key']for r in checkpoint['source_controls']]
            checkpoint['sources']['historical']=[r['source_key']for r in query(control.db,"SELECT /*+ MAX_EXECUTION_TIME(5000) */ DISTINCT source_key FROM backfill_jobs FORCE INDEX(source_status_updated)",(),checkpoint)if r['source_key']!='__lease_check__']
            checkpoint.update(phase='metadata_counts',position=0)
        elif phase.endswith('_counts'):
            lane=phase.removesuffix('_counts');sources=checkpoint['sources'][lane];position=checkpoint['position']
            if position>=len(sources):
                checkpoint.update(phase='historical_counts'if lane=='metadata'else'metadata_failures',position=0)
                if lane=='historical':
                    checkpoint['failure_tasks']={kind:[{'source':source,'state':state}for source in checkpoint['sources'][kind]for state in FAILURES[kind]if checkpoint['counts'].get(kind+'|'+source+'|'+state,0)]for kind in databases}
                continue
            source=sources[position];state=STATES[lane]
            fallback=checkpoint.get('count_fallback')
            if fallback:
                ordinal=fallback['state_position'];states=ALL_STATES[lane]
                if ordinal>=len(states):
                    checkpoint.pop('count_fallback');checkpoint['position']+=1
                    save(control,job['id'],checkpoint=checkpoint);continue
                current_state=states[ordinal];limit=fallback['limit']
                if lane=='metadata':
                    sql="SELECT /*+ MAX_EXECUTION_TIME(5000) */ job_id FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s AND state=%s AND job_id>%s ORDER BY job_id LIMIT %s"
                    params=(source,current_state,fallback['after'],limit)
                else:
                    sql="SELECT /*+ MAX_EXECUTION_TIME(5000) */ job_id,updated_at FROM backfill_jobs FORCE INDEX(source_status_updated) WHERE source_key=%s AND status=%s AND (updated_at>%s OR (updated_at=%s AND job_id>%s)) ORDER BY updated_at,job_id LIMIT %s"
                    params=(source,current_state,fallback['updated_at'],fallback['updated_at'],fallback['after'],limit)
                try:rows=query(databases[lane],sql,params,checkpoint)
                except pymysql.MySQLError as exc:
                    if exc.args[0]not in TRANSIENT or limit<=5:raise
                    fallback['limit']=max(5,limit//2);checkpoint['query_metrics']['retries']+=1
                    save(control,job['id'],checkpoint=checkpoint);time.sleep(.25);continue
                key=lane+'|'+source+'|'+current_state
                checkpoint['counts'][key]=checkpoint['counts'].get(key,0)+len(rows)
                if rows:
                    fallback['after']=rows[-1]['job_id']
                    if lane=='historical':fallback['updated_at']=rows[-1]['updated_at']
                if len(rows)<limit:fallback.update(state_position=ordinal+1,after='',updated_at=0)
                save(control,job['id'],checkpoint=checkpoint);continue
            # Equality on source and grouping by the next indexed column is covering.
            try:rows=query(databases[lane],f"SELECT /*+ MAX_EXECUTION_TIME(5000) */ {state} AS job_state,COUNT(*) AS jobs FROM {TABLES[lane]} FORCE INDEX({INDEXES[lane]}) WHERE source_key=%s GROUP BY {state}",(source,),checkpoint)
            except pymysql.MySQLError as exc:
                if exc.args[0]not in TRANSIENT:raise
                checkpoint['count_fallback']={'state_position':0,'after':'','updated_at':0,'limit':100}
                checkpoint['query_metrics']['retries']+=1
                save(control,job['id'],checkpoint=checkpoint);continue
            for row in rows:checkpoint['counts'][lane+'|'+source+'|'+row['job_state']]=row['jobs']
            checkpoint['position']+=1
        elif phase.endswith('_failures'):
            lane=phase.removesuffix('_failures');tasks=checkpoint['failure_tasks'][lane];position=checkpoint['failure_position']
            if position>=len(tasks):
                checkpoint.update(phase='historical_failures'if lane=='metadata'else'complete',failure_position=0,after='',after_updated_at=0)
                continue
            task=tasks[position];limit=checkpoint['batch_size']
            if lane=='metadata':
                sql="SELECT /*+ MAX_EXECUTION_TIME(5000) */ job_id,reason FROM engine_jobs FORCE INDEX(source_jobs) WHERE source_key=%s AND state=%s AND job_id>%s ORDER BY job_id LIMIT %s"
                params=(task['source'],task['state'],checkpoint['after'],limit)
            else:
                sql="SELECT /*+ MAX_EXECUTION_TIME(5000) */ job_id,updated_at,result_json FROM backfill_jobs FORCE INDEX(source_status_updated) WHERE source_key=%s AND status=%s AND (updated_at>%s OR (updated_at=%s AND job_id>%s)) ORDER BY updated_at,job_id LIMIT %s"
                params=(task['source'],task['state'],checkpoint['after_updated_at'],checkpoint['after_updated_at'],checkpoint['after'],limit)
            try:rows=query(databases[lane],sql,params,checkpoint)
            except pymysql.MySQLError as exc:
                if exc.args[0]not in TRANSIENT or limit<=5:raise
                checkpoint['batch_size']=max(5,limit//2);checkpoint['query_metrics']['retries']+=1
                save(control,job['id'],checkpoint=checkpoint);time.sleep(.25);continue
            for row in rows:
                if lane=='historical' and task['state']=='blocked' and task['source'].startswith('legacy:'):
                    result=json.loads(row['result_json'] or '{}') or {}
                    resolution=result.get('resolution') or {}
                    if resolution.get('status')=='superseded' and resolution.get('checkpoint_manifest_uri') and resolution.get('prior_failure_archive'):
                        checkpoint['resolved_historical_invocations']=checkpoint.get('resolved_historical_invocations',0)+1
                        continue
                reason=failure_reason(lane,row);key=lane+'|'+task['source']+'|'+task['state']+'|'+reason
                checkpoint['failure_counts'][key]=checkpoint['failure_counts'].get(key,0)+1
                samples=checkpoint['failure_samples'].setdefault(key,[])
                if len(samples)<3:samples.append(row['job_id'])
            if rows:
                checkpoint['after']=rows[-1]['job_id']
                if lane=='historical':checkpoint['after_updated_at']=rows[-1]['updated_at']
            if len(rows)<limit:checkpoint.update(failure_position=position+1,after='',after_updated_at=0)
        elif phase=='complete':
            return {'schema_version':2,'algorithm':'covering_index_source_counts_and_bounded_failure_pages','started_at':checkpoint['started_at'],'finished_at':stamp(),
                    'counts':checkpoint['counts'],'failure_counts':checkpoint['failure_counts'],'failure_samples':checkpoint['failure_samples'],
                    'resolved_historical_invocations':checkpoint.get('resolved_historical_invocations',0),
                    'source_controls':checkpoint['source_controls'],'tables':checkpoint['tables'],'query_metrics':checkpoint['query_metrics'],
                    'job_rows_counted':sum(checkpoint['counts'].values()),'sources_audited':{k:len(v)for k,v in checkpoint['sources'].items()},
                    'consistency':'Live per-source counts and keyset failure reads, not a point-in-time snapshot; concurrent changes can affect totals. Table inventory row estimates are labelled separately from counted job rows.'}
        else:raise ValueError('Unknown database diagnostic phase: '+phase)
        save(control,job['id'],checkpoint=checkpoint)
    save(control,job['id'],checkpoint=checkpoint,state='pending')
    return None
