"""Read-only operational audit; Athena SELECTs save their normal result objects."""
import concurrent.futures as cf
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from daily_athena_routes import verified_publisher, plan_routes, inspect_changes, sample_query
from collection_health_exporter import properties, json_reports

OUT = Path(os.environ.get('OPTIMA_DAILY_HEALTH_ROOT',str(ROOT/'reports/daily-health')))/datetime.now(timezone.utc).strftime('%Y-%m-%d')
OUT.mkdir(parents=True, exist_ok=True)
cfg = json.loads((ROOT/'config/collection-monitoring.json').read_text())
BUCKET = cfg['bucket']
session = boto3.Session(region_name='us-east-1')
s3 = session.client('s3', config=Config(retries={'max_attempts': 3}))
athena = session.client('athena')
glue = session.client('glue')
def save(name, value):
    (OUT/(name+'.json')).write_text(json.dumps(value, indent=2, default=str)+'\n')
def read(key):
    with s3.get_object(Bucket=cfg['bucket'], Key=key)['Body'] as body:
        return json.load(body)
health = read(cfg['prefix'].rstrip('/')+'/health/latest.json')
save('health', health)
try:
    previous = read(cfg['prefix'].rstrip('/')+'/daily-health/latest.json')
except ClientError as exc:
    if exc.response['Error']['Code'] not in ('NoSuchKey','404'):raise
    previous = {}
print('Health snapshot saved', flush=True)
units = subprocess.check_output(['systemctl','list-unit-files','optima-*','--no-legend','--no-pager'], text=True)
(OUT/'unit-files.txt').write_text(units)
(OUT/'timers.txt').write_text(subprocess.check_output(['systemctl','list-timers','--all','--no-pager'], text=True))
services = {}
for line in units.splitlines():
    unit = line.split()[0]
    if unit.endswith('.service'):
        try:
            services[unit] = {'properties': properties(unit), 'journal': json_reports(unit)}
        except Exception as exc:
            services[unit] = {'error': str(exc)}
save('services', services)
print(f'{len(services)} services inspected', flush=True)
publisher = verified_publisher(s3, BUCKET, read('research-data/athena-committed/latest-report.json'))
save('publisher', publisher)
route_proofs, changed_routes, live_routes, pending_live, route_failures = plan_routes(publisher,previous,OUT.name)
statuses, changed_failures = inspect_changes(glue,athena,BUCKET,publisher,route_proofs,changed_routes)
route_failures.extend(changed_failures)
live_routes = [name for name in live_routes if route_proofs[name]['status']=='verified']
save('publisher-query-statuses',statuses)
def query(item):
    name, wg, sql = item
    result = {'name':name, 'sql':sql, 'workgroup':wg}
    try:
        q = athena.start_query_execution(QueryString=sql, WorkGroup=wg,
            ResultReuseConfiguration={'ResultReuseByAgeConfiguration':{'Enabled':False}})['QueryExecutionId']
        result['query_id'] = q
        deadline = time.monotonic()+300
        while True:
            row = athena.get_query_execution(QueryExecutionId=q)['QueryExecution']
            state = row['Status']['State']
            if state in ('SUCCEEDED','FAILED','CANCELLED'):
                result.update(state=state, reason=row['Status'].get('StateChangeReason'), bytes_scanned=row['Statistics'].get('DataScannedInBytes',0))
                break
            if time.monotonic()>deadline:
                athena.stop_query_execution(QueryExecutionId=q)
                raise TimeoutError('audit query exceeded five minutes')
            time.sleep(1)
        if state=='SUCCEEDED':
            data=athena.get_query_results(QueryExecutionId=q, MaxResults=1000)['ResultSet']
            result['columns']=[c['Name'] for c in data['ResultSetMetadata']['ColumnInfo']]
            result['rows']=[[c.get('VarCharValue') for c in r['Data']] for r in data['Rows'][1:]]
            if name in live_routes and not any(row and row[0] for row in result['rows']):
                result.update(state='FAILED',reason='verified nonempty route returned no observation ID')
    except Exception as exc:
        result['error']=str(exc)
    save(name, result)
    return result
checks=[sample_query(route_proofs[name]) for name in live_routes]
checks += [('reddit-freshness','optima-social-research',f'SELECT count(*) AS records,max(verified_utc) AS latest_verified,count_if(verified_utc < {time.time()-86400}) AS overdue_24h FROM optima_social_research.reddit_records'),
 ('specialist-observations','optima-collected-data','SELECT source,dataset,count(*) AS records,max(ingested_at) AS latest_capture FROM optima_specialist_inputs.source_observations_windows GROUP BY source,dataset'),
 ('specialist-coverage','optima-collected-data','SELECT source,dataset,count(*) AS windows FROM optima_specialist_inputs.source_coverage_windows GROUP BY source,dataset'),
 ('reddit','optima-social-research','SELECT count(*) AS records,count(DISTINCT record_id) AS distinct_ids FROM optima_social_research.reddit_records'),
 ('search','optima-eodhd-research','SELECT source_id,count(*) AS records,max(observed_at) AS latest_capture FROM optima_source_readiness.source_samples_windows GROUP BY source_id'),
 ('petitions','optima-patent-petitions',"SELECT count(*) AS records,count(DISTINCT provider_id) AS documents,max(ingested_at) AS latest_capture,count_if(document_retrieval_status IS DISTINCT FROM 'downloaded') AS missing_downloads FROM optima_patent_petitions.source_observations_windows"),
 ('office-actions','optima-patent-office-actions','SELECT * FROM optima_patent_office_actions.source_observations_windows LIMIT 1')]
with cf.ThreadPoolExecutor(max_workers=4) as pool:
    results=list(pool.map(query, checks))
for result in results:
    if result['name'] in live_routes:
        pending_live.pop(result['name'],None)
        if result.get('state')!='SUCCEEDED':
            pending_live[result['name']]=result
save('athena-checks', results)
save('summary', {'checked_at':datetime.now(timezone.utc).isoformat(),'services':len(services),'monitored_jobs':len(health['jobs']), 'partitions':len(publisher['sources']), 'observations':sum(p['records'] for p in publisher['sources']), 'publisher_finished_at':publisher['finished_at'], 'queries':len(results),'query_failures':[r for r in results if r['name'] not in live_routes and r.get('state')!='SUCCEEDED']+list(pending_live.values()), 'bytes_scanned':sum(r.get('bytes_scanned',0) for r in results)})
print('Audit complete', flush=True)

def refs(value):
    if isinstance(value,dict):
        for k,v in value.items():
            if k in ('manifest','last_manifest') and isinstance(v,str):yield v
            elif isinstance(v,(dict,list)):yield from refs(v)
    elif isinstance(value,list):
        for v in value:yield from refs(v)
def keys(value):
    if isinstance(value,dict):
        for k,v in value.items():
            if k=='key' and isinstance(v,str) and v.startswith(('raw/','source_documents/')):yield v
            elif isinstance(v,(dict,list)):yield from keys(v)
    elif isinstance(value,list):
        for v in value:yield from keys(v)
def check(item):
    unit,key=item
    result={'unit':unit,'manifest':key}
    try:
        doc=json.loads(s3.get_object(Bucket=BUCKET,Key='research-data/'+key)['Body'].read())
        result['manifest_status']=doc.get('status')
        result['manifest_records']=doc.get('record_count',doc.get('records'))
        objects=[]
        for ref in sorted(set(keys(doc))):
            row=s3.head_object(Bucket=BUCKET,Key='research-data/'+ref)
            objects.append({'key':ref,'bytes':row['ContentLength'],'modified_at':str(row['LastModified'])})
        result['objects']=objects
        result['status']='verified_exists'
    except Exception as exc:result.update(status='failed',error=str(exc))
    return result
checks=[]
for unit,job in services.items():
    journal=job.get('journal',[[]])[0]
    for report in reversed(journal):
        manifests=list(refs(report['value']))
        if manifests:
            checks.append((unit,manifests[-1]));break
with cf.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(check,checks))
(OUT/'s3-checks.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({'manifests':len(results),'objects':sum(len(r.get('objects',[])) for r in results),'failures':[r for r in results if r['status']=='failed']}))

summary=json.loads((OUT/'summary.json').read_text())
summary.update(published_route_proofs=route_proofs, route_live_failures=list(pending_live.values()),
    shared_receipts_reused=sum(p['basis']=='receipt_reused' for p in route_proofs.values() if p['status']=='verified'),
    shared_changed_receipts=sum(route_proofs[n]['status']=='verified' for n in changed_routes),
    shared_live_queries=len(live_routes),
    shared_readbacks_passed=sum(r.get('state')=='SUCCEEDED' for r in json.loads((OUT/'athena-checks.json').read_text()) if r['name'] in live_routes),
    s3_manifests=len(results),s3_objects=sum(len(r.get('objects',[])) for r in results),s3_failures=[r for r in results if r['status']=='failed'],
    receipt_queries=len(statuses),receipt_query_failures=route_failures)
summary['routes']={name:json.loads((OUT/(name+'.json')).read_text()) for name in ('reddit','reddit-freshness','search','petitions','office-actions','specialist-observations','specialist-coverage')}
# A missing typed Office Action route is pending only while no completed window exists.
try:
    glue.get_database(Name='optima_patent_office_actions')
    summary['expected_unpublished_routes']=[]
except glue.exceptions.EntityNotFoundException:
    summary['expected_unpublished_routes']=['office-actions']
summary['evidence_prefix']=cfg['prefix'].rstrip('/')+'/daily-health/'+OUT.name+'/'
save('summary',summary)
for artifact in OUT.glob('*.json'):
    s3.put_object(Bucket=cfg['bucket'],Key=summary['evidence_prefix']+artifact.name,Body=artifact.read_bytes(),ContentType='application/json',ServerSideEncryption='AES256')
s3.put_object(Bucket=cfg['bucket'],Key=cfg['prefix'].rstrip('/')+'/daily-health/latest.json',Body=json.dumps(summary).encode(),ContentType='application/json',ServerSideEncryption='AES256')
print(json.dumps({'daily_health_saved':summary['checked_at'],'shared_readbacks_passed':summary['shared_readbacks_passed']}),flush=True)
