"""Confirm live capture checkpoints and fresh Athena publication for repaired sources."""
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from ops import B, BASE, P, session
from deploy_on_wake import ROOT, s3_json
from metadata_engine.runtime_db import Database
from constellation.control import Control

S3=session.client('s3')


def load(key):
    from botocore.exceptions import ClientError
    try:
        with S3.get_object(Bucket=B,Key=key)['Body'] as content:
            return json.load(content)
    except ClientError as error:
        if error.response['Error']['Code'] not in ('404','NoSuchKey'):
            raise
        return None


def query(ids):
    athena=session.client('athena')
    sql=("SELECT source_key,job_id,count(*) observations,"
         "count_if(raw_completeness_status='complete') complete_rows,"
         "min(json_extract_scalar(labelled_json,'$.raw_artifacts[1].s3_uri')) provider_original "
         "FROM optima_metadata_engine.source_observations "
         "WHERE contract_version='2.0.3' AND job_id IN ("+','.join(repr(i) for i in ids)+") "
         "GROUP BY source_key,job_id")
    execution=athena.start_query_execution(QueryString=sql,WorkGroup='optima-collected-data',
        ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId']
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        status=athena.get_query_execution(QueryExecutionId=execution)['QueryExecution']['Status']
        if status['State']=='SUCCEEDED':
            values=athena.get_query_results(QueryExecutionId=execution)['ResultSet']['Rows']
            columns=[c['VarCharValue'] for c in values[0]['Data']]
            return execution,[dict(zip(columns,[c.get('VarCharValue') for c in r['Data']])) for r in values[1:]]
        if status['State'] in ('FAILED','CANCELLED'):
            raise RuntimeError('review_athena_'+status['State']+':'+status.get('StateChangeReason','')[:350])
        time.sleep(1)
    athena.stop_query_execution(QueryExecutionId=execution)
    raise TimeoutError('review_athena_partition_verification_timeout')


def verify():
    activation=s3_json('activation.json')
    raw=s3_json('worker-raw-proof.json')['sources']
    targets=activation['targets']
    updates=s3_json('capture-updates.json')
    settings=json.loads((ROOT/'config/metadata-engine.json').read_text())
    database=Database(settings,session=session)
    collection=Control(session=session)
    census='us_census_international_trade_api'
    active={}
    expected={}
    with database.tx() as cursor:
        for source,items in targets.items():
            cursor.execute('SELECT state,contract_version,last_reason FROM engine_sources WHERE source_key=%s',(source,))
            active[source]=cursor.fetchone()
            for item in items:
                identity=item['job_id']
                cursor.execute("""SELECT j.state,j.output_rows,r.status publication_status
                    FROM engine_jobs j LEFT JOIN publication_releases r ON r.release_id=UNHEX(SUBSTRING(j.job_id,1,32))
                    WHERE j.job_id=%s""",(identity,))
                row=cursor.fetchone()
                if row and row['state']=='accepted' and row['publication_status']=='published' and row['output_rows']:
                    expected[identity]=row['output_rows']
    execution,rows=query(list(expected)) if expected else (None,[])
    result={'checked_at':datetime.now(timezone.utc).isoformat(),'athena_query_id':execution,'sources':{}}
    observed={r['job_id']:r for r in rows}
    historical_jobs={r['unit']:r for r in activation['historical']}
    for source,items in targets.items():
        mode_results={}
        if source==census:
            for mode in ('daily','historical'):
                mode_results[mode]={'verified':bool(raw[source][mode]),'committed_raw_batches':raw[source][mode]}
        else:
            revision=updates[source]['raw_content_revision']
            for mode in ('daily','historical'):
                state=load(f'research-data/constellation-backfill/public-capture/states/{mode}/{source}/{revision}.json')
                done=[url for url,entry in (state or {}).get('done',{}).items() if entry['kind']=='public_document']
                mode_results[mode]={'verified':bool(done),'native_url_count':len(done),
                                    'remaining_urls':len((state or {}).get('frontier',[])),'failures':(state or {}).get('failures',{})}
        matches=[]
        complete_modes=set()
        for item in items:
            identity=item['job_id']
            row=observed.get(identity)
            if row and int(row['observations'])==expected[identity]==int(row['complete_rows']) and row['provider_original']:
                complete_modes.add(item['mode'])
                matches.append({**row,'mode':item['mode']})
        entry={'capture':mode_results,'metadata_control':active[source],'athena_samples':matches,
               'verified':active[source]['state']=='enabled' and active[source]['contract_version']=='2.0.3'
               and complete_modes=={'daily','historical'} and all(v['verified'] for v in mode_results.values())}
        history=next((r for unit,r in historical_jobs.items() if source in unit),None)
        if history:
            queue=collection.get('job#'+history['job_id'])
            entry['historical_queue']={'job_id':history['job_id'],'status':queue['status']}
        result['sources'][source]=entry
    result['raw_proof_failures']={k:v for k,v in raw.items() if not v['validated_both_modes']}
    old=P/'live-verification.json'
    old.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    overall='complete' if all(e['verified'] for e in result['sources'].values()) and not result['raw_proof_failures'] else 'partial'
    return overall,result
