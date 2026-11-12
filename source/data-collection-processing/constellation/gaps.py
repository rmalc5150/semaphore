"""Measure attempted coverage gaps, never infer gaps from an unprocessed backlog."""
from datetime import datetime,timezone
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from constellation.coverage_scope import specialist_scope

POLICY=Path(__file__).resolve().parents[1]/'config/collection-gap-policy.json'

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

    def process(job):
        """Project one job while retaining only a small LRU of S3 receipts."""
        spec=json.loads(job['spec_json']);result=json.loads(job['result_json']) if job['result_json'] else {}
        if job['source_key'].startswith('legacy:'):
            projected=[]
            for uri in {w.get('evidence_uri') for w in result.get('coverage_windows',[]) if '|specialist_historical' in w.get('scope','')}:
                if not uri or not uri.startswith(report_prefix):continue
                _,report=load(uri)
                for outcome in report.get('outcomes',[]):
                    if (outcome.get('job') or {}).get('adapter')=='additional_epo':continue
                    decision=reviewed_gap(outcome.get('job') or {})
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
                if window.get('scope','').startswith('epo_ops_patent_legal_events|'):continue
                if window.get('status')=='partial' and window.get('reason') in {'record_limit','page_limit','page_budget','max_pages','max_records'}:
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
