"""Action-oriented reporting; raw incidents remain in the audit history."""
from datetime import datetime
from zoneinfo import ZoneInfo
from monitoring_runbooks import steps

RETRY = {'authenticated_source_request_failed', 'source_http_429', 'scrape_gateway_http_429',
         'source_http_500', 'source_http_502', 'source_http_503', 'source_http_504',
         'source_changed_refresh_required', 'news_source_changed_refresh_required', 'source_retries_exhausted'}
COVERAGE = {'historical_designation_date_unavailable', 'market_empty_price_window_unverified', 'unresolved_market_coverage'}
ACTIONS = {
 'historical_designation_date_unavailable': 'Find dated original designation evidence; otherwise record the historical date as unavailable with its scope and reason. Do not invent dates.',
 'market_empty_price_window_unverified': 'Reconcile empty symbol/date windows against listing and trading calendars; add only evidence-backed exclusions.',
 'unresolved_market_coverage': 'Resolve missing symbol mappings/provider coverage and verify affected date windows in Athena.',
 'record_limit': 'Split the capped query into smaller date/entity scopes, resume capture, then reconcile counts.',
 'nih_result_cap_split_scope_required': 'Split NIH searches below the result cap and verify all child scopes.',
 'prerequisite_incomplete': 'Complete the upstream inventory/index first, then rerun the dependent scope.',
 'index_coverage_incomplete': 'Finish and reconcile index pages before dependent detail capture.',
 'source_http_400': 'Inspect the failed source and request parameters; correct the rejected request and run a bounded replay.',
 'scrape_gateway_http_400': 'Inspect the saved gateway response and request schema; correct it and verify one resumed page.',
 'source_http_403': 'Check the affected endpoint/account access and permitted route; verify a bounded request before resuming.',
 'service_failed': 'Inspect the failed invocation, repair its cause, and verify committed output plus Athena publication.',
 'oom_kill': 'Reduce publication batch size or memory use, rerun the failed window, and verify its Athena receipt.',
 'progress_stalled': 'Check the last committed checkpoint and quota/lock state; restore progress and verify publication.',
}

def overview(active, now, period_start, snapshot=None):
    groups = {}
    retry_groups = {}
    for key, item in sorted(active.items()):
        code = item['code']; unit = item['unit']
        first = datetime.fromisoformat(item.get('first_seen', item.get('evidence_at')).replace('Z','+00:00')).timestamp()
        if item['severity'] != 'high' and code in RETRY and now-first < 6*3600:
            retry_groups.setdefault(unit, []).append(code)
            continue
        groups.setdefault(unit, []).append(item)
    subject = f'Optima 24-hour overview: {len(groups)} services need attention' if groups else 'Optima 24-hour overview: no action items'
    local = datetime.fromtimestamp(now,ZoneInfo('Europe/Madrid')).strftime('%Y-%m-%d %H:%M %Z')
    lines=[subject, 'As of: '+local, '', 'ACTION ITEMS' if groups else 'No unresolved action items in the monitored scope.']
    for unit, items in groups.items():
        codes = {i['code'] for i in items}
        category = 'URGENT REPAIR' if any(i['severity']=='high' for i in items) else ('COVERAGE REVIEW' if codes <= COVERAGE else 'REPAIR / VERIFY')
        lines += ['', f'{unit} — {category}']
        if '-sms-' in unit or any('-sms-' in c for c in codes):
            lines += ['Owner: You + implementation', 'Action: Check sender registration and delivery failure logs. Correct any registration rejection; confirm a later successful delivery. An idle alarm is not delivery proof.']
        else:
            lines += ['Owner: Implementation (no credential purchase requested)']
            for code in sorted(codes):
                action=ACTIONS.get(code, 'Inspect the named source/checkpoint, repair the persistent failure, and verify the affected output in Athena.')
                if code in RETRY:action='Retries have not cleared this issue within six hours. Inspect provider quota/access and the exact failed scope; verify new committed output.'
                lines.append('Action: '+action+' ['+code+']')
                lines += [f'  {n}. {step.replace("<service>",unit)}' for n,step in enumerate(steps(code),1)]
        details=list(dict.fromkeys(str(i.get('detail','')) for i in items if str(i.get('detail','')) not in codes))
        lines += ['Evidence: '+d[:500] for d in details]
        job=(snapshot or {}).get('jobs',{}).get(unit,{})
        if job.get('progress',{}).get('last_verified_at'):
            lines.append('Latest service-level progress: '+job['progress']['last_verified_at']+' (not proof every failed scope is fixed).')
    lines += ['', 'AUTOMATIC RETRIES', f'{len(retry_groups)} services have recent retryable issues; no manual action yet. Persistent issues become action items after six hours.']
    for unit,codes in sorted(retry_groups.items()):lines.append(unit+': '+', '.join(sorted(set(codes))))
    if snapshot:
        jobs=snapshot.get('jobs',{})
        lines += ['', 'COLLECTION STATUS', f'{len(jobs)} services monitored; {sum(j.get("activity")=="running" for j in jobs.values())} running; {sum(j.get("activity")=="queued" for j in jobs.values())} queued.',
                  f'{sum(bool(j.get("progress",{}).get("pending")) for j in jobs.values())} services still have outstanding collection/publication work. Backfill is not itself a failure.']
        lines += ['Host inspection: '+str(snapshot.get('checked_at','missing'))]
        audit=snapshot.get('daily_audit')
        lines += ['', 'LIVE S3 / ATHENA CHECKS']
        if not audit:
            lines.append('Daily live audit not yet available; current service checks are not a replacement for Athena readbacks.')
        else:
            age=now-datetime.fromisoformat(audit['checked_at'].replace('Z','+00:00')).timestamp()
            lines.append('Audit checked: '+audit['checked_at']+(' — STALE: older than 26 hours' if age>26*3600 else ''))
            lines.append(f"Shared publisher: {audit.get('observations',0):,} committed observations across {audit.get('partitions',0)} partitions; cutoff {audit.get('publisher_finished_at')}. Includes partial windows and prior versions.")
            lines.append(f"Fresh shared readbacks: {audit.get('shared_readbacks_passed',0)}/{audit.get('partitions',0)} passed. S3: {audit.get('s3_manifests',0)} manifests and {audit.get('s3_objects',0)} referenced objects inspected; {len(audit.get('s3_failures',[]))} failures.")
            lines.append(f"Publisher receipt queries: {audit.get('receipt_queries',0)} checked; {len(audit.get('receipt_query_failures',[]))} failed/unavailable.")
            for name,r in audit.get('routes',{}).items():
                state='awaiting first complete-window publication' if name in audit.get('expected_unpublished_routes',[]) and r.get('state')!='SUCCEEDED' else r.get('state',r.get('error','unknown'))
                if name=='specialist-observations' and r.get('state')=='SUCCEEDED':
                    description=f"{sum(int(x[2]) for x in r['rows']):,} observations across {len(r['rows'])} source/dataset partitions"
                elif name=='specialist-coverage' and r.get('state')=='SUCCEEDED':
                    description=f"{sum(int(x[2]) for x in r['rows']):,} published coverage windows"
                else:description=str(r.get('rows',[]))[:1800]
                lines.append(f'{name}: {state}; {description}; query {r.get("query_id","not created")}')
            failures=[r for r in audit.get('query_failures',[]) if r['name'] not in audit.get('expected_unpublished_routes',[])]
            lines += ['Readback issue: '+r['name']+': '+str(r.get('reason') or r.get('error')) for r in failures]
            lines.append('Audit evidence: s3://'+str(snapshot.get('bucket',''))+'/'+audit.get('evidence_prefix',''))
        lines += ['', 'PUBLICATION QUEUES']
        backlog=False
        for unit,j in sorted(jobs.items()):
            for owner,count in sorted(j.get('publication_backlog',{}).items()):
                lines.append(f'{owner}: {count} outstanding queue entries ({unit})')
                backlog |= count>0
        if backlog:
            lines += [f'{n}. {step}' for n,step in enumerate(steps('publication_backlog'),1)]
        lines += ['', 'PER-JOB STATUS']
        for unit,j in sorted(jobs.items()):
            lines.append(f"{unit}: {j.get('activity','unknown')}; last verified {j.get('progress',{}).get('last_verified_at') or 'no evidence'}; pending {j.get('progress',{}).get('pending','unknown')}; issues "+(', '.join(i['code'] for i in j.get('issues',[])) or str(j.get('inspection_error') or 'none detected')))
        lines += ['', 'PIPELINE / MODEL COVERAGE']
        for stage in snapshot.get('pipeline_stages',{}).values():
            lines.append(stage['label']+': '+stage['status'])
            for unit,j in stage['jobs'].items():lines.append(f"  {unit}: {j.get('activity','unknown')}; {j.get('inspection_error') or ', '.join(i['code'] for i in j.get('issues',[])) or 'no job issues detected'}")
            for receipt in stage['receipts']:lines.append('  Output receipt: '+str(receipt))
        lines.append('New stage workers are discovered by registered unit patterns. Training/testing output checks require registered S3 receipts; unavailable stages are not marked healthy. Model quality requires the explicit metrics and validation evidence in those receipts.')
    lines += ['', 'Resolved incidents are omitted. Full incident evidence remains in S3.', 'This is operational status, not certification of complete history or specialist-ready fields.']
    return subject, '\n'.join(lines)


def sms_delivery_confirmed(alarm):
    import json
    try:
        data=json.loads(alarm.get('StateReasonData','{}'))
        points=data.get('evaluatedDatapoints',[])
        return alarm.get('StateValue')=='OK' and bool(points) and all(p.get('value',0)>=1 and p.get('sampleCount',0)>0 for p in points)
    except (ValueError,TypeError):return False
