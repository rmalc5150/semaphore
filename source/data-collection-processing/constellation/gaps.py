"""Measure attempted coverage gaps, never infer gaps from an unprocessed backlog."""
from datetime import datetime,timezone
import json
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from constellation.coverage_scope import specialist_scope

POLICY=Path(__file__).resolve().parents[1]/'config/collection-gap-policy.json'

def digest(value):
    """Use the collection task identity without importing collector dependencies."""
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()

def current_core_window(window, outcome, manifest, head):
    """Clear a retained core failure only for its exact committed replacement."""
    import re
    parts=window.get('scope','').split('|')
    providers={'fda':'fda_openfda','ema':'ema_ctis','clinicaltrials':'clinicaltrials_gov',
               'uk':'uk_mhra','japan':'japan_pmda','chictr':'chictr'}
    if (len(parts)!=3 or parts[0] not in providers or not re.fullmatch(r'[a-f0-9]{64}',parts[1])
        or parts[2]!='configured_legacy_scope' or not outcome or not manifest or not head):return window
    task=manifest.get('task',{}); bounds=task.get('window',{})
    start=window['start'][:10];end=window['end'][:10]
    if (outcome.get('status')!='complete' or outcome.get('source')!=parts[0]
        or outcome.get('mode')!='historical' or outcome.get('start')!=start or outcome.get('end')!=end
        or manifest.get('status')!='complete' or not manifest.get('exhausted')
        or task.get('source')!=providers[parts[0]] or task.get('dataset')!='research_records'
        or task.get('mode')!='historical' or bounds.get('start')!=start+'T00:00:00Z'
        or bounds.get('end')!=end+'T00:00:00Z'
        or manifest.get('task_id')!='task_'+digest(task) or head.get('task')!=task
        or outcome.get('manifest') not in head.get('terminal_history',[])):return window
    return {**window,'status':'complete','reason':None,
            'replacement_manifest':outcome['manifest']}

def current_specialist_outcome(original, current):
    """A newer exact checkpoint supersedes an old execution, never another scope."""
    if (not current or not original.get('job') or not original.get('job_id') or current.get('job_id') != original['job_id']
        or (current.get('job') != original.get('job')
            and current.get('job_hash') != job_hash(original.get('job')))
        or current.get('last_attempt', '') <= original.get('last_attempt', '')):
        return original
    return {**current,'job':original.get('job')} if 'job' not in current else current

def job_hash(job):
    import hashlib
    return hashlib.sha256(json.dumps(job,sort_keys=True).encode()).hexdigest()

def expected_census_release(window, today=None):
    if (not window.get('scope','').startswith('us_census_international_trade_api|')
        or window.get('status')!='partial' or window.get('reason')!='census_period_not_yet_published'):
        return False
    today=today or datetime.now(timezone.utc).date()
    start=datetime.fromisoformat(window['start']).date()
    return (today.year-start.year)*12+today.month-start.month in (0,1)

def capacity_wait(window):
    # This is admission control before submission, not a provider failure or
    # evidence of missing data. Keep the attempt, but report it as backlog.
    return (window.get('scope','').startswith('copernicus_era5_era5_land|')
            and window.get('reason')=='copernicus_queue_wait'
            and window.get('status') in {'failed','partial'})

def merged_gaps(windows,threshold_days=5):
    latest={}
    for w in windows:
        # A scope includes provider, dataset, geography and collection identity.
        key=(w['scope'],w['start'],w['end'])
        if key not in latest or w.get('updated_at',0)>=latest[key].get('updated_at',0):latest[key]=w
    groups={}
    for w in latest.values():
        if w['status'] in ('complete','verified_complete','succeeded','deferred_not_a_gap','in_progress'):continue
        start=datetime.fromisoformat(w['start'].replace('Z','+00:00'))
        end=datetime.fromisoformat(w['end'].replace('Z','+00:00'))
        if end<=start:raise ValueError('Invalid gap interval')
        groups.setdefault(w['scope'],[]).append((start,end,w))
    gaps=[]
    for scope,items in groups.items():
        current=None
        for start,end,w in sorted(items,key=lambda item:(item[0],item[1])):
            if current is None or start>current['end']:
                if current:gaps.append(current)
                current={'scope':scope,'start':start,'end':end,'reasons':set(),'evidence':set()}
            else:current['end']=max(current['end'],end)
            current['reasons'].add(w.get('reason') or 'incomplete')
            if w.get('evidence_uri'):current['evidence'].add(w['evidence_uri'])
        if current:gaps.append(current)
    for gap in gaps:
        seconds=(gap['end']-gap['start']).total_seconds()
        gap.update(duration_days=seconds/86400,flag_for_checkup=seconds>threshold_days*86400)
        gap['start']=gap['start'].isoformat();gap['end']=gap['end'].isoformat()
        gap['reasons']=sorted(gap['reasons']);gap['evidence']=sorted(gap['evidence'])
    return gaps

def build(control):
    windows=[]
    accepted_unavailable=[]
    from reviewed_source_gaps import reviewed_gap
    report_prefix='s3://'+control.config['bucket']+'/'+control.config['prefix']+'/legacy-operation-receipts/'
    # A few adjacent jobs share a receipt, but keeping dozens of historical
    # reports can exceed this timer's 512 MiB cgroup budget.
    @lru_cache(maxsize=4)
    def load(uri):
        key=uri.removeprefix('s3://'+control.config['bucket']+'/')
        response=control.s3.get_object(Bucket=control.config['bucket'],Key=key)
        try:return uri,json.loads(response['Body'].read())
        finally:response['Body'].close()

    @lru_cache(maxsize=32)
    def scheduler(source):
        # Keep only the outcome projection, not each large scheduler's job plan.
        # Read-only reconciliation avoids repeated alerts from immutable old runs.
        import re
        if not re.fullmatch(r'[a-z0-9_]+', source):return {}
        uri='s3://'+control.config['bucket']+'/research-data/constellation-backfill/specialist-schedulers/constellation-specialist-'+source+'.service/historical.json'
        try:
            response=control.s3.get_object(Bucket=control.config['bucket'],Key=uri.removeprefix('s3://'+control.config['bucket']+'/'))
            try:state=json.loads(response['Body'].read())
            finally:response['Body'].close()
            fields=('job_id','source','source_id','start','end_exclusive','status','reason','manifest','last_attempt','gap_receipt')
            return {identity:{**{k:r[k] for k in fields if k in r},'job_hash':job_hash(r.get('job'))}
                    for identity,r in state.get('jobs',{}).items()}
        except Exception:
            # An unavailable current checkpoint cannot erase an existing gap.
            return {}

    def reconcile(outcome):
        current=scheduler(outcome.get('source','')).get(outcome.get('job_id'))
        candidate=current_specialist_outcome(outcome,current)
        if candidate is outcome:return outcome
        if candidate.get('status')=='complete':
            key=candidate.get('manifest','')
            if not key.startswith('manifests/collection_runs/'):return outcome
            try:_,manifest=load('s3://'+control.config['bucket']+'/research-data/'+key)
            except Exception:return outcome
            task=manifest.get('task',{})
            if (manifest.get('status')!='complete' or not manifest.get('exhausted')
                or task.get('source')!=candidate['source']
                or task.get('window',{}).get('start')!=candidate['start']+'T00:00:00Z'
                or task.get('window',{}).get('end')!=candidate['end_exclusive']+'T00:00:00Z'):
                return outcome
        return candidate

    expiry_cache={}
    @lru_cache(maxsize=256)
    def core_replacement(scope,start,end):
        import re
        parts=scope.split('|')
        if (len(parts)!=3 or parts[0] not in {'fda','ema','clinicaltrials','uk','japan','chictr'}
            or not re.fullmatch(r'[a-f0-9]{64}',parts[1]) or parts[2]!='configured_legacy_scope'):return None
        try:
            prefix='s3://'+control.config['bucket']+'/research-data/'
            _,outcome=load(prefix+'operations/streams/'+parts[1]+'/historical/'+parts[0]+'/'+start[:10]+'_'+end[:10]+'.json')
            if outcome.get('status')!='complete':return None
            key=outcome.get('manifest','')
            if not key.startswith('manifests/collection_runs/'):return None
            _,manifest=load(prefix+key)
            _,head=load(prefix+'checkpoints/task_'+digest(manifest.get('task',{}))+'/head.json')
            return outcome,manifest,head
        except Exception:return None

    def expired_listing(outcome):
        if outcome.get('status')!='accepted_unavailable' or outcome.get('reason')!='edinet_listing_expired':return None
        key=outcome.get('gap_receipt','')
        if not key.startswith('operations/specialists/reviewed-gaps/'):return None
        cache_key=(key,job_hash(outcome.get('job')))
        if cache_key in expiry_cache:return expiry_cache[cache_key]
        if len(expiry_cache)<512:expiry_cache[cache_key]=None
        try:
            from reviewed_source_gaps import reviewed_edinet_expiry
            _,receipt=load('s3://'+control.config['bucket']+'/research-data/'+key)
            if receipt.get('job')!=outcome.get('job'):return None
            decision=receipt.get('decision',{})
            if not reviewed_edinet_expiry(receipt['job'],decision.get('provider_status'),decision.get('reviewed_at')):return None
            import hashlib
            for ref in receipt.get('source_evidence',[]):
                raw=control.s3.get_object(Bucket=control.config['bucket'],Key='research-data/'+ref['key'])['Body']
                try:body=raw.read()
                finally:raw.close()
                if hashlib.sha256(body).hexdigest()!=ref['sha256']:return None
                if str(json.loads(body).get('metadata',{}).get('status'))=='404':
                    if len(expiry_cache)<512:expiry_cache[cache_key]=decision
                    return decision
        except Exception:return None
        return None

    def process(job):
        """Project one job while retaining only a small LRU of S3 receipts."""
        spec=json.loads(job['spec_json']);result=json.loads(job['result_json']) if job['result_json'] else {}
        if job['source_key'].startswith('legacy:'):
            projected=[]
            for uri in {w.get('evidence_uri') for w in result.get('coverage_windows',[]) if '|specialist_historical' in w.get('scope','')}:
                if not uri or not uri.startswith(report_prefix):continue
                _,report=load(uri)
                for outcome in report.get('outcomes',[]):
                    outcome=reconcile(outcome)
                    if (outcome.get('job') or {}).get('adapter')=='additional_epo':continue
                    decision=reviewed_gap(outcome.get('job') or {}) or expired_listing(outcome)
                    if decision:
                        accepted_unavailable.append({'scope':specialist_scope(outcome),'start':outcome['start'],'end':outcome['end_exclusive'],'status':'accepted_unavailable','decision':decision,'evidence_uri':uri})
                        continue
                    manifest={}
                    key=outcome.get('manifest','')
                    if outcome.get('status')=='partial' and not outcome.get('reason') and key.startswith('manifests/collection_runs/'):
                        _,manifest=load('s3://'+control.config['bucket']+'/research-data/'+key)
                    projected.append({'scope':specialist_scope(outcome),'start':outcome['start'],'end':outcome['end_exclusive'],'status':outcome['status'],'reason':outcome.get('reason') or manifest.get('reason_code'),'evidence_uri':uri,'updated_at':job['updated_at']})
            original=[w for w in result.get('coverage_windows',[]) if '|specialist_historical' not in w.get('scope','')]
            for window in original+projected:
                if window.get('status') not in {'complete','succeeded'}:
                    replacement=core_replacement(window.get('scope',''),window['start'],window['end'])
                    if replacement:window=current_core_window(window,*replacement)
                if window.get('scope','').startswith('epo_ops_patent_legal_events|'):continue
                if expected_census_release(window):
                    window={**window,'status':'deferred_not_a_gap'}
                if capacity_wait(window):
                    window={**window,'status':'in_progress'}
                if window.get('status')=='partial' and window.get('reason') in {'record_limit','page_limit','page_budget','max_pages','max_records','decodo_web_data_daily_budget','pdf_proxy_daily_budget','pdf_proxy_url_cooldown','pdf_proxy_client_budget'}:
                    window={**window,'status':'in_progress'}
                windows.append(window)
            return
        if job['status'] in ('pending','running') and not result:return
        if result.get('coverage_status')=='deferred_not_a_gap':return
        scope='|'.join((job['source_key'],spec['dataset'],spec['geography']))
        windows.append({'scope':scope,'start':spec['start'],'end':spec['end'],'status':job['status'],'reason':result.get('reason'),'updated_at':job['updated_at'],'evidence_uri':result.get('manifest_uri') or result.get('gap_evidence_uri') or 'rds:backfill_jobs/'+job['job_id']})

    after=''
    while True:
        with control.db() as cursor:
            cursor.execute("SELECT job_id,source_key,status,spec_json,result_json,updated_at FROM backfill_jobs WHERE attempts>0 AND source_key<>'__lease_check__' AND (source_key LIKE %s OR status<>'succeeded') AND job_id>%s ORDER BY job_id LIMIT 500", ('legacy:%',after))
            jobs=cursor.fetchall()
        if not jobs:break
        for job in jobs:process(job)
        if len(jobs)<500:break
        after=jobs[-1]['job_id']
    threshold=json.loads(POLICY.read_text())['checkup_reporting']['flag_when_gap_days_greater_than']
    gaps=merged_gaps(windows,threshold)
    return {'checked_at':datetime.now(timezone.utc).isoformat(),'interval_semantics':'[start,end)',
        'backlog_summary':{'copernicus_capacity_wait_scopes':len({(w['scope'],w['start'],w['end'])
            for w in windows if w.get('status')=='in_progress' and w.get('reason')=='copernicus_queue_wait'})},
        'accepted_unavailable': list({(w['scope'],w['start'],w['end']):w for w in accepted_unavailable}.values()),
        'threshold_days':threshold,'exactly_five_days':'record_only','gaps':gaps,
        'flagged_gaps':sum(g['flag_for_checkup'] for g in gaps),'record_only_gaps':sum(not g['flag_for_checkup'] for g in gaps),
        'note':'Only attempted scopes. Pending backlog and unaudited coverage are not inferred missing data.'}

def main():
    from constellation.control import Control,canonical
    c=Control();report=build(c)
    key='research-data/monitoring/health/constellation-gaps.json'
    history=c.config['prefix']+'/monitoring/gap-history/'+report['checked_at'].replace(':','-')+'.json'
    report['evidence_uri']='s3://'+c.config['bucket']+'/'+history
    for target in (history,key):
        c.s3.put_object(Bucket=c.config['bucket'],Key=target,Body=canonical(report),ContentType='application/json',ServerSideEncryption='AES256')
    print(json.dumps({k:v for k,v in report.items() if k!='gaps'}))

if __name__=='__main__':main()
