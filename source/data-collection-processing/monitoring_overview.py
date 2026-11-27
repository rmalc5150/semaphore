"""Action-oriented 24-hour digest of unresolved incidents and coverage gaps."""
from collections import defaultdict
from datetime import datetime, timezone

RETRY = {'authenticated_source_request_failed', 'source_http_429', 'scrape_gateway_http_429',
         'source_http_500', 'source_http_502', 'source_http_503', 'source_http_504',
         'source_changed_refresh_required', 'news_source_changed_refresh_required', 'source_retries_exhausted'}
COVERAGE = {'historical_designation_date_unavailable', 'market_empty_price_window_unverified',
            'unresolved_market_coverage', 'github_release_archive_cap'}
ACTIONS = {
    'github_release_archive_cap': 'Use a verified archive route for older releases beyond the provider result cap.',
    'historical_designation_date_unavailable': 'Find a dated original designation record or document the exact unavailable period.',
    'market_empty_price_window_unverified': 'Check the affected tickers, listings and trading dates against EODHD coverage.',
    'unresolved_market_coverage': 'Correct ticker and listing mappings, and replay the affected EODHD windows.',
    'record_limit': 'Split the capped search into smaller date or entity scopes.',
    'nih_result_cap_split_scope_required': 'Split the affected NIH searches below the result cap.',
    'prerequisite_incomplete': 'Complete the upstream inventory or document window and replay the dependent dates.',
    'index_coverage_incomplete': 'Repair missing index pages and resume dependent capture.',
    'source_http_400': 'Correct the provider request for the affected scope and replay it.',
    'scrape_gateway_http_400': 'Correct the request rejected by the scraping gateway and replay the affected scope.',
    'source_http_401': 'Restore the source credential and replay the affected windows.',
    'source_http_403': 'Verify permission for the affected endpoint and use an authorized route.',
    'source_http_404': 'Verify the original provider URL or find its current archive location.',
    'source_http_204': 'Verify whether the exact provider window is empty or needs a narrower query.',
    'public_http_403': 'Verify source access and use an authorized archive endpoint.',
    'public_http_404': 'Find the provider’s replacement archive URL for the affected records.',
    'source_changed_refresh_required': 'Replay the affected window from a fresh stable provider snapshot.',
    'source_changed_during_pagination': 'Refresh the affected search window from a stable provider snapshot.',
    'additional_duplicate_provider_ids': 'Use stable pagination and reconcile provider identifiers in the affected windows.',
    'duplicate_provider_record': 'Use stable pagination and reconcile provider identifiers in the affected windows.',
    'portwatch_invalid_features': 'Validate the PortWatch response schema and replay the affected ArcGIS windows.',
    'portwatch_missing_count': 'Repair the PortWatch count query and reconcile the affected ArcGIS windows.',
    'nhsbsa_release_not_yet_published': 'Confirm the provider release date and collect the period when its original file is available.',
    'database_connection_failed': 'Restore worker connectivity to the database and replay the affected windows.',
    'capture_interrupted': 'Resume the interrupted historical scope from its retained checkpoint.',
    'pdf_proxy_http_429': 'Resume the affected document windows after the proxy cooldown.',
    'run_request_budget_reached': 'Resume the affected dates using the saved checkpoint and existing request cap.',
    'missing_verified_raw_artifacts': 'Recover the missing original artifact and rerun validation for the affected records.',
    'eia_html_instead_of_xlsx': 'Update the EIA workbook URL or adapter and verify a valid XLSX download.',
    'timer_disabled': 'Restore the scheduled timer for this active service.',
    'queue_timeout': 'Resolve lock contention and retry the affected job.',
    'execution_timeout': 'Resume the last committed checkpoint with a smaller work window.',
    'service_failed': 'Repair the failed service invocation and verify new committed output.',
    'oom_kill': 'Reduce memory per batch or move the payload to a worker with sufficient capacity.',
    'progress_stalled': 'Clear the blocked checkpoint, lock or quota condition and verify committed progress.',
    'daily_audit_missing_or_stale': 'Restore the scheduled S3 and Athena verification run.',
    'daily_audit_verification_failed': 'Repair the failed S3 objects, publication receipts or Athena readbacks listed in the audit.',
    'inspection_failed': 'Restore access to the worker or monitoring evidence and refresh the health check.',
}
RETRY_FIX = 'Resolve the provider throttling, outage or changed response and replay the affected scope.'
DAILY_FIX = 'Reconcile the listed dates from the retained checkpoint and verify the resulting output.'
HISTORICAL_FIX = 'Repair and replay the affected historical windows and verify the resulting coverage.'


def method(code, fallback):
    return ACTIONS.get(code.split(':', 1)[0], RETRY_FIX if code in RETRY else fallback)


def distinct(values):
    return list(dict.fromkeys(values))


def incident_lines(items):
    by_unit = defaultdict(list)
    for item in items:
        by_unit[item['unit']].append(item)
    lines = []
    for unit, entries in sorted(by_unit.items(), key=lambda row: (
            not any(i['severity'] == 'high' for i in row[1]), row[0])):
        for item in sorted(entries, key=lambda i: (i['severity'] != 'high', i['code'])):
            code = item['code']
            detail = ' '.join(str(item.get('detail') or '').split())
            urgent = 'URGENT ' if item['severity'] == 'high' else ''
            fix = ('Correct the sender registration or delivery failure and verify a later SMS delivery.'
                   if '-sms-' in unit or '-sms-' in code else
                   method(code, 'Repair the affected service or source checkpoint and verify fresh output.'))
            lines.append(f'- {urgent}{unit} [{code}]'
                         + (f' — {detail[:220]}' if detail and detail != code else '')
                         + f' Fix — {fix}')
    return lines


def historical_gap_lines(report, paused):
    grouped = defaultdict(list)
    for gap in report.get('gaps', []):
        source = gap['scope'].split('|', 1)[0]
        if gap.get('flag_for_checkup') and source not in paused:
            grouped[source].append(gap)
    lines = []
    for source, gaps in sorted(grouped.items()):
        longest = max(gaps, key=lambda gap: gap['duration_days'])
        reasons = sorted({
            'database_connection_failed' if reason.startswith('(2003,') else
            'capture_interrupted' if reason == "(0, '')" else reason
            for gap in gaps for reason in gap['reasons']
        })
        fixes = distinct(method(reason, HISTORICAL_FIX) for reason in reasons) or [HISTORICAL_FIX]
        fix = ' '.join(fixes[:2])
        intervals = '1 flagged interval' if len(gaps) == 1 else f'{len(gaps)} flagged intervals'
        lines.append(f'- {source} — {intervals}. Longest '
                     f'{longest["start"][:10]} to {longest["end"][:10]} (end exclusive, '
                     f'{longest["duration_days"]:g} days). '
                     f'{", ".join(reasons[:3])[:200] or "Incomplete coverage"}. Fix — {fix}')
    return lines


def daily_gap_lines(jobs, paused):
    grouped = defaultdict(set)
    for job in jobs.values():
        if job.get('operator_paused'):
            continue
        for gap in job.get('daily_reconciliation_gaps', []):
            if gap['source'] not in paused:
                grouped[(gap['source'], gap.get('reason'))].update(gap['dates'])
    matching = defaultdict(list)
    for (source, reason), dates in sorted(grouped.items(), key=lambda row: (row[0][0], row[0][1] or '')):
        matching[(tuple(sorted(dates)), reason)].append(source)
    lines = []
    for (dates, reason), sources in matching.items():
        if not dates:
            continue
        date_text = ', '.join(dates[:4])
        if len(dates) > 4:
            date_text += f' and {len(dates)-4} more'
        cause = f' ({reason})' if reason else ''
        lines.append(f'- {", ".join(sources)} — Reconciliation pending for {date_text}{cause}. '
                     f'Fix — {method(reason, DAILY_FIX) if reason else DAILY_FIX}')
    return lines


def legacy_failure_lines(shutdown, paused, jobs, now):
    checked_at = shutdown.get('checked_at')
    if not checked_at or now - datetime.fromisoformat(checked_at.replace('Z', '+00:00')).timestamp() > 26*3600:
        return []
    grouped = defaultdict(set)
    for failure in shutdown.get('failures', []):
        source = failure.get('source') or failure.get('unit') or failure.get('scope', 'unknown')
        if source in paused or jobs.get(failure.get('unit'), {}).get('operator_paused'):
            continue
        grouped[(source, failure.get('reason') or 'unknown')].add(
            (failure.get('start'), failure.get('end'), failure.get('job_id') or failure.get('evidence_uri')))
    lines = []
    for (source, reason), failures in sorted(grouped.items()):
        lines.append(f'- {source} — {len(failures)} unresolved capture failure(s) at the last historical worker check '
                     f'({reason}). Fix — {method(reason, HISTORICAL_FIX)}')
    return lines


def publication_context(report, now):
    """Keep the digest action-oriented, with the shared count snapshot as context."""
    if not isinstance(report, dict) or report.get('schema_version') != 1:
        return []
    def time_of(snapshot):
        return datetime.fromisoformat(snapshot['as_of'].replace('Z', '+00:00')).astimezone(timezone.utc)
    try:
        receipts = report['receipts']
        totals = receipts['totals']
        as_of = time_of(receipts)
        freshness = ' (stale)' if now - as_of.timestamp() > 26 * 3600 else ''
        lines = [f"Labelled metadata — {totals['rows']:,} rows in {totals['releases']:,} verified releases "
                 f"as of {as_of:%Y-%m-%d %H:%M UTC}{freshness}."]
        if checked := report.get('athena'):
            when = time_of(checked)
            if now - when.timestamp() <= 26 * 3600:
                result = checked['totals']
                lines.append(f"Grouped Athena check — {result['rows']:,} rows in {result['releases']:,} job partitions "
                             f"as of {when:%Y-%m-%d %H:%M UTC}.")
        if report.get('report_uri'):
            lines.append('Saved source counts — ' + report['report_uri'])
        return lines
    except (KeyError, TypeError, ValueError, AttributeError):
        return []


def overview(active, now, period_start, snapshot=None):
    snapshot = snapshot or {}
    jobs = snapshot.get('jobs', {})
    paused = set(snapshot.get('paused_sources', ()))
    repairs, coverage = [], []
    for item in active.values():
        if jobs.get(item['unit'], {}).get('operator_paused'):
            continue
        first_seen = item.get('first_seen') or item.get('evidence_at')
        recent = first_seen and now - datetime.fromisoformat(first_seen.replace('Z', '+00:00')).timestamp() < 6*3600
        if item['severity'] != 'high' and item['code'] in RETRY and recent:
            continue
        target = coverage if item['code'] in COVERAGE and item['severity'] != 'high' else repairs
        target.append(item)
    blockers = [f'- {gap["label"]} — {gap["issue"]} Fix — {gap["fix"]}'
                for gap in snapshot.get('historical_capture_blockers', [])
                if gap['source'] not in paused]
    report = snapshot.get('historical_gaps') or {}
    historical = historical_gap_lines(report, paused)
    daily = daily_gap_lines(jobs, paused)
    shutdown = snapshot.get('historical_autostop') or {}
    failures = legacy_failure_lines(shutdown, paused, jobs, now)
    sections = [
        ('NEEDS REPAIR', incident_lines(repairs)),
        ('HISTORICAL CAPTURE BLOCKERS', blockers),
        ('HISTORICAL DATA GAPS', historical),
        ('HISTORICAL CAPTURE FAILURES', failures),
        ('DAILY DATA GAPS', daily),
        ('OTHER COVERAGE GAPS', incident_lines(coverage)),
    ]
    services = len({item['unit'] for item in repairs})
    gaps = len(blockers) + len(historical) + len(failures) + len(daily) + len(coverage)
    counts = []
    if services:
        counts.append('1 service' if services == 1 else f'{services} services')
    if gaps:
        counts.append('1 data gap group' if gaps == 1 else f'{gaps} data gap groups')
    summary = ' and '.join(counts) + (' needs attention' if services+gaps == 1 else ' need attention') if counts else 'no action items'
    subject = 'Optima 24-hour overview: ' + summary
    date = datetime.fromtimestamp(now, timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    lines = [subject, date]
    for title, entries in sections:
        if entries:
            lines.extend(['', title, *entries])
            if title == 'HISTORICAL DATA GAPS' and report.get('evidence_uri'):
                lines.append('Affected dates and evidence — ' + report['evidence_uri'])
            if title == 'HISTORICAL CAPTURE FAILURES' and shutdown.get('repair_list_uri'):
                lines.append('Failure evidence — ' + shutdown['repair_list_uri'])
    if not services and not gaps:
        lines.extend(['', 'No unresolved action items in the monitored scope.'])
    counts = publication_context(snapshot.get('metadata_publication_counts'), now)
    if counts:
        lines.extend(['', *counts])
    return subject, '\n'.join(lines)


def sms_delivery_confirmed(alarm):
    import json
    try:
        data = json.loads(alarm.get('StateReasonData', '{}'))
        points = data.get('evaluatedDatapoints', [])
        return alarm.get('StateValue') == 'OK' and bool(points) and all(
            p.get('value', 0) >= 1 and p.get('sampleCount', 0) > 0 for p in points)
    except (ValueError, TypeError):
        return False
