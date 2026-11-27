"""Separate unfinished capture work from failures handed to the daily repair list."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from research_contract import digest
from specialist_inputs import VERSION
from specialist_plan import jobs
from constellation.legacy_routes import route_hash
from research_contract import ROOT

QUOTA_REASONS={'historical_daily_budget_exhausted','epo_daily_request_budget','epo_weekly_byte_budget','epo_concurrency_deferred','github_public_hour_budget','sam_daily_request_budget','sam_hourly_request_budget','source_http_429'}
QUOTA_REASONS.add('comtrade_daily_request_budget')

def get_json(control,key):
    try:r=control.s3.get_object(Bucket=control.config['bucket'],Key=key)
    except control.s3.exceptions.NoSuchKey:return None
    try:return json.loads(r['Body'].read())
    finally:r['Body'].close()


def inspect_routes(control,rows,routes,plan):
    prefix=control.config['prefix'];keys={}
    public={r['source']:r for r in json.loads((ROOT/'config/constellation-public-sources.json').read_text())['sources']}
    for route in routes:
        if route.get('public_capture_source'):
            source=route['public_capture_source'];revision=public.get(source,{}).get('raw_content_revision');keys[route['unit']]=prefix+'/public-capture/states/historical/'+source+('/'+revision if revision else '')+'.json'
        elif route.get('specialist_source'):keys[route['unit']]=prefix+'/specialist-schedulers/'+route['unit']+'/historical.json'
    with ThreadPoolExecutor(max_workers=6) as pool:states=dict(pool.map(lambda pair:(pair[0],get_json(control,pair[1])),keys.items()))
    universe=None;universe_hash=None;proofs={}
    for route in routes:
        unit=route['unit'];source='legacy:'+unit;state=states.get(unit)
        receipts=[r for r in rows if r['source_key']==source and r.get('result_json')]
        receipt=max(receipts,key=lambda r:(r['updated_at'],r['job_id']),default=None)
        result=json.loads(receipt['result_json']) if receipt else {};spec=json.loads(receipt['spec_json']) if receipt else {}
        matching=(spec.get('start')==route['start_target'] and spec.get('end')==route['end_exclusive'] and spec.get('parameters',{}).get('route_sha256')==route_hash(route))
        proof={'state':'unfinished','reason':'no_current_completion_evidence','failure_count':0,'failures':[]}
        if route.get('public_capture_source') and state is not None:
            failures=state.get('failures',{});healthy=[r for r in state.get('frontier',[]) if r['url'] not in failures]
            known=set(state.get('done',{}))|set(failures)|{r['url'] for r in state.get('frontier',[])}
            missing_seeds=[u for u in public[route['public_capture_source']]['seeds'] if u not in known]
            proof.update(state='unfinished' if healthy or missing_seeds else 'failed_only' if failures else 'complete',reason='public_frontier',healthy_pending=len(healthy)+len(missing_seeds),failure_count=len(failures),failures=[{'source':route['public_capture_source'],'url':url,'reason':r.get('reason'),'evidence_uri':'s3://'+control.config['bucket']+'/'+keys[unit]} for url,r in failures.items()])
        elif route.get('specialist_source') and state is not None:
            source_name=route['specialist_source'];selected=[r for r in plan['sources'] if r['source']==source_name]
            if not selected:proof['reason']='source_plan_missing';proofs[unit]=proof;continue
            if universe is None:
                seed=get_json(control,control.config['legacy_seed_key']);universe=get_json(control,seed['paths']['config/company-universe.v0.5.json']['key']);universe_hash=digest(universe)
            expected=list(jobs({**plan,'sources':selected},universe,'historical',datetime.now(timezone.utc).date()))
            # Include discovered/retained unfinished scopes, as the native scheduler does.
            stored=state.get('jobs',{});ids={digest({'job':j,'universe_hash':universe_hash,'version':VERSION}) for j in expected}
            ids.update(k for k,r in stored.items() if r.get('status')!='complete')
            missing=sum(identity not in stored for identity in ids);unfinished=[stored[i] for i in ids if i in stored and stored[i].get('status') not in ('complete','failed')]
            failed=[stored[i] for i in ids if i in stored and stored[i].get('status')=='failed']
            latest=max(failed,key=lambda r:r.get('last_attempt',''),default={});reason=latest.get('reason','')
            retry_at=state.get('source_retries',{}).get(source_name,'')
            held=bool(retry_at) and datetime.fromisoformat(retry_at.replace('Z','+00:00'))>datetime.now(timezone.utc) and reason not in QUOTA_REASONS and bool(latest)
            if held and any(r.get('last_attempt','')>latest.get('last_attempt','') and r.get('status') in ('complete','partial') for r in stored.values()):held=False
            failure_items=[{'source':source_name,'start':r.get('start'),'end':r.get('end_exclusive'),'reason':r.get('reason'),'manifest':r.get('manifest'),'job_id':r.get('job_id')} for r in failed]
            if held:
                proof.update(state='failed_only',reason='provider_failure_holds_remaining_source_scopes',failure_count=len(failed),skipped_unattempted_or_partial_scopes=missing+len(unfinished),failures=failure_items)
            elif missing or unfinished or any(r.get('reason') in QUOTA_REASONS for r in failed):
                proof.update(state='unfinished',reason='healthy_backlog_or_quota_wait',unattempted=missing,partial_or_deferred=len(unfinished),failure_count=len(failed),failures=failure_items)
            else:
                # A current execution receipt also accounts for discovered jobs
                # that have not yet appeared in the scheduler's mutable state.
                accounted=matching and result.get('route_drained') is True and result.get('checkpoint_verified') is True
                if not accounted and matching:
                    report_keys=[w.get('evidence_uri','') for w in result.get('coverage_windows',[])]
                    if not report_keys and result.get('report_uri','').startswith('s3://'+control.config['bucket']+'/'+prefix+'/legacy-reports/'):
                        response=control.s3.get_object(Bucket=control.config['bucket'],Key=result['report_uri'].split('/',3)[3])
                        try:lines=response['Body'].read().decode(errors='replace').splitlines()
                        finally:response['Body'].close()
                        for line in lines:
                            try:event=json.loads(line)
                            except ValueError:continue
                            if isinstance(event,dict) and event.get('report_key','').startswith('constellation-backfill/legacy-operation-receipts/'):
                                report_keys.append('s3://'+control.config['bucket']+'/research-data/'+event['report_key'])
                    for uri in set(report_keys):
                        if uri.startswith('s3://'+control.config['bucket']+'/'+prefix+'/legacy-operation-receipts/'):
                            report=get_json(control,uri.split('/',3)[3]) or {}
                            if 'remaining_jobs' in report:accounted=report['remaining_jobs']<=len(failed)
                proof.update(state=('failed_only' if failed else 'complete') if accounted else 'unfinished',reason='native_planned_scopes_accounted' if accounted else 'discovered_or_unverified_jobs_remain',planned_jobs=len(ids),failure_count=len(failed),failures=failure_items)
        elif matching and result.get('route_drained') is True and result.get('checkpoint_verified') is True:
            failures=[w for w in result.get('coverage_windows',[]) if w.get('status') in ('failed','blocked')]
            proof.update(state='failed_only' if failures else 'complete',reason='checkpointed_route_drained',failure_count=len(failures),failures=failures)
        elif matching and (receipt['status'] in ('blocked','retryable_failed') or result.get('reason')):
            proof.update(state='failed_only',reason='executor_failure',failure_count=1,failures=[{'source':source,'reason':result.get('reason') or result.get('error') or 'executor_failed','evidence_uri':result.get('report_uri'),'job_id':receipt['job_id']}])
        elif matching:
            windows=result.get('coverage_windows',[]);failed=[w for w in windows if w.get('status') in ('failed','blocked')]
            healthy_partial=[w for w in windows if w.get('status')=='partial' and w.get('reason') in ('page_budget','page_limit','record_limit')]
            if failed and not healthy_partial and not any(w.get('reason') in QUOTA_REASONS for w in failed):proof.update(state='failed_only',reason='source_failure_remaining_for_repair',failure_count=len(failed),failures=failed)
        proofs[unit]=proof
    return proofs
