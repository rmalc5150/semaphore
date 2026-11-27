#!/usr/bin/env python3
"""Read systemd, bounded journals and S3 metadata without touching collectors."""
from datetime import date, datetime, timedelta, timezone
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import tempfile

from collection_alerts import EXPECTED, Watchdog, epoch, fingerprint, outcome_issues, stamp
from market_coverage_exclusions import Exclusions, reconcile_state, unresolved
from research_contract import digest

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / 'config'


# This is the stream pinned by the controller's patent-gap-catchup deployment.
PATENT_GAP_STREAM = ('operations/patents/global-backfill/streams/'
                     'd5548c10ab24a442ae7b6c5f05ed3e283f32a1e1e29b0662b74abdd80f903b96')
RESEARCH_FEED_HISTORY = 'constellation-backfill/research-feeds/v1'


def historical_capture_blockers(paused_sources, evidence):
    """Check the actual capture routes and their durable evidence.

    Older catalog flags and staged migrations do not describe these routes.
    A positive checkpoint clears a setup blocker, not outstanding coverage.
    """
    start = json.loads((CONFIG / 'collection-gap-policy.json').read_text())['historical_start_target']
    target = date.fromisoformat(start)
    blockers = []

    def read(key):
        return evidence.read(key)[0] or {}

    def block(source, label, issue, fix):
        blockers.append(dict(source=source, label=label, issue=issue, fix=fix))

    feeds = {'openalex_scholarly_graph': 'OpenAlex scholarly graph',
             'japan_kaken_funded_research': 'Japan KAKEN funded research'}
    if set(feeds) - paused_sources:
        active = read(RESEARCH_FEED_HISTORY + '/control.json').get('historical_enabled') is True
        for source, label in feeds.items():
            if source in paused_sources:
                continue
            if not active:
                block(source, label, 'The research-feed historical route is not enabled in its current control.',
                      'Check the historical route control and any intentional pause before resuming.')
                continue
            if source == 'openalex_scholarly_graph':
                from constellation.research_feeds import FLOOR, SNAPSHOT_PARTS
                row = read(f'{RESEARCH_FEED_HISTORY}/progress/{source}/snapshot.json')
                proven = (FLOOR <= target and row.get('snapshot_sha256')
                          and 0 < row.get('next_part', 0) <= SNAPSHOT_PARTS
                          and row.get('retained', 0) > 0)
            else:
                # KAKEN scopes are project-start fiscal years, not calendar periods.
                year = target.year
                row = read(f'{RESEARCH_FEED_HISTORY}/checkpoints/{source}/historical/fy-{year}.json')
                scope = row.get('scope', {})
                proven = (scope.get('fiscal_year') == year and scope.get('active') is False
                          and row.get('unique_records', 0) > 0 and row.get('published_batches', 0) > 0)
            if not proven:
                block(source, label, 'No committed evidence was found for the configured historical route.',
                      'Check the research-feed worker and validate a bounded historical batch.')

    source = 'google_patents_bigquery'
    if source not in paused_sources:
        collection = read(PATENT_GAP_STREAM + '/progress.json')
        publication = read(PATENT_GAP_STREAM + '/athena-publication/progress.json')
        timer = properties('optima-patent-gap-catchup.timer')
        config = json.loads((CONFIG / 'patent-backfill.json').read_text())
        # The dedicated catch-up timer disables itself when its 2016–2020 gap is filled.
        route_available = (timer.get('ActiveState') == 'active'
                           or (publication.get('next_date') or '') >= '2021-01-01')
        if not (route_available and config['start_date'] <= start
                and (collection.get('next_date') or '') > start
                and collection.get('completed_windows', 0) > 0):
            block(source, 'Google Patents BigQuery',
                  'The controller historical catch-up is not scheduled or lacks a committed checkpoint.',
                  'Check the controller catch-up timer and its BigQuery checkpoint before changing federation.')

    if 'finlight' not in paused_sources:
        control = json.loads((CONFIG / 'finlight-backfill.json').read_text())
        news = json.loads((ROOT / control['collection_config']).read_text())
        primary = news['providers']['finlight']
        primary_floor = primary.get('history_start')
        split_archive = bool(primary_floor and primary_floor > start)
        archive = (control.get('earlier_archive') or {}) if split_archive else primary
        floor = archive.get('start') or archive.get('history_start')
        key = archive.get('history_evidence')
        probe = read(key) if floor and key and floor <= start else {}
        proven = (probe.get('provider') == 'finlight' and any(
            isinstance(row.get('start'), str) and row['start'] <= start
            and isinstance(row.get('earliest'), str) and row['earliest'][:10] >= start
            and row['earliest'][:10] < (row.get('end_exclusive') or '')
            and (not split_archive or row['earliest'][:10] < primary_floor)
            and row.get('count', 0) > 0 and (row.get('raw') or {}).get('key', '').startswith('source_documents/finlight/')
            for row in probe.get('results', [])))
        if not control.get('enabled') or not proven:
            block('finlight', 'Finlight news',
                  f'The enabled archive route or its access evidence for {start} is missing.',
                  'Check the configured earlier archive and validate a bounded historical response.')
    return blockers


def daily_reconciliation_gap(key, doc, evidence):
    directory, _, name = key.rpartition('/')
    source = directory.rsplit('/', 1)[-1]
    if key.startswith('operations/streams/') and '/daily/' in key and name.startswith('progress-'):
        pending, _, _ = evidence.read(directory + '/reconciliation.json')
        dates = sorted((pending or {}).get('pending_dates', []))
        if dates:
            # The queue can span multiple failure causes. Name the cause only
            # for a single retained date whose exact outcome can be checked.
            reason = None
            if len(dates) == 1:
                start = date.fromisoformat(dates[0])
                outcome, _, _ = evidence.read(f'{directory}/{start}_{start + timedelta(days=1)}.json')
                reason = (outcome or {}).get('reason')
            return {'source': source, 'dates': dates, 'reason': reason}
    if key.startswith('operations/news/automation/') and name == 'reconcile.json':
        attempted = doc.get('attempted_date')
        outcome = doc.get('last_result') or {}
        if attempted in doc.get('pending', []) and outcome.get('status') in {'partial', 'failed', 'blocked'}:
            return {'source': source, 'dates': [attempted], 'reason': outcome.get('reason')}
    return None


def command(args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=30).stdout


def properties(unit):
    fields = ['ActiveState', 'SubState', 'UnitFileState', 'Result', 'MainPID',
              'ActiveEnterTimestampMonotonic', 'ExecMainStatus', 'ExecMainStartTimestampMonotonic', 'ExecMainExitTimestampMonotonic', 'ControlGroup']
    return dict(line.split('=', 1) for line in command(
        ['systemctl', 'show', unit, '--no-pager', '--property='+','.join(fields)]).splitlines() if '=' in line)


def activity(props, serialized):
    if props.get('ActiveState') not in ('activating', 'active', 'deactivating'):
        return 'idle', 0
    started = int(props.get('ExecMainStartTimestampMonotonic') or 0) / 1e6
    elapsed = max(0, time.clock_gettime(time.CLOCK_BOOTTIME) - started)
    cg = Path('/sys/fs/cgroup') / props['ControlGroup'].lstrip('/')
    pids = (cg/'cgroup.procs').read_text().splitlines()
    ticks = __import__('os').sysconf('SC_CLK_TCK')
    payload_starts = []
    for pid in pids:
        try:
            name = Path('/proc', pid, 'comm').read_text().strip()
            if name not in {'flock', 'timeout'}:
                if name.startswith('python') and b'm7_capture_worker.py' in Path('/proc',pid,'cmdline').read_bytes():
                    continue  # Admission/queue wrapper; the payload is a child.
                # Parenthesized comm can contain spaces: parse after its last ')'.
                fields = Path('/proc', pid, 'stat').read_text().rsplit(')', 1)[1].split()
                payload_starts.append(float(fields[19])/ticks)
        except FileNotFoundError:
            continue
    if payload_starts:
        return 'running', max(0, time.clock_gettime(time.CLOCK_BOOTTIME)-min(payload_starts))
    return 'queued', elapsed


def json_reports(unit):
    # journalctl streams the bounded result; never capture an unbounded journal.
    # On this systemd version --since makes -n select the first N matching
    # entries. Tail first, then enforce the age bound locally.
    process = subprocess.Popen(['journalctl', '-u', unit, '-n', '500',
                                '--no-pager', '--all', '-o', 'json'], stdout=subprocess.PIPE, text=True)
    reports, events = [], []
    try:
        for line in process.stdout:
            row = json.loads(line)
            message = row.get('MESSAGE')
            if not isinstance(message, str):
                continue
            at = int(row['__REALTIME_TIMESTAMP'])/1e6
            if at < time.time()-3*86400:
                continue
            invocation = row.get('_SYSTEMD_INVOCATION_ID')
            if 'oom-kill' in message.lower() or 'out of memory' in message.lower():
                events.append({'code': 'oom_kill', 'severity': 'high', 'detail': message[:300], 'at': stamp(at)})
            elif 'Failed with result' in message:
                events.append({'code': 'service_failed', 'severity': 'low', 'detail': message[:300], 'at': stamp(at)})
            if message.lstrip().startswith(('{', '[')):
                try:
                    value = json.loads(message)
                except (ValueError, TypeError):
                    continue
                if isinstance(value, dict) and 'stage' in value:
                    continue  # Page activity is not a terminal collection outcome.
                reports.append({'at': stamp(at), 'invocation': invocation, 'value': value})
        if process.wait(timeout=10):
            raise RuntimeError('journalctl failed for '+unit)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    # Preserve the most recent commit-bearing invocation, even if subsequent
    # invocations only report quota deferrals or already-complete work.
    def has_commit(value):
        if isinstance(value, list):
            return any(has_commit(v) for v in value)
        if isinstance(value, dict):
            return bool((value.get('status') == 'complete' and value.get('manifest')) or
                        value.get('last_manifest') or value.get('verification_key') or
                        any(has_commit(v) for v in value.values() if isinstance(v, (dict, list))))
        return False
    latest_commit = next((r['value'] for r in reversed(reports) if has_commit(r['value'])), None)
    if reports:
        latest = reports[-1]
        reports = [r for r in reports if r['invocation'] == latest['invocation']] if latest['invocation'] else [latest]
    return reports, events, latest_commit


class Evidence:
    def __init__(self, s3, bucket, data_prefix, batch_cache=None):
        self.s3, self.bucket = s3, bucket
        self.prefix = data_prefix.rstrip('/')+'/'
        self.cache = {}
        # A successful batch is immutable (key + SHA-256 + record count).  The
        # optional durable cache avoids re-downloading it on every health pass.
        self.batch_cache = batch_cache
        self.batch_checks = {'downloads': 0, 'cache_hits': 0, 'list_requests': 0}

    def cached_batch(self, batch):
        entry = (self.batch_cache or {}).get(batch['key'])
        try:
            if (isinstance(entry, dict) and entry.get('etag') and entry.get('sha256') == batch['sha256']
                    and entry.get('records') == batch['records']
                    and epoch(entry.get('verified_at')) >= time.time()-86400):
                return entry
        except (ValueError, TypeError, AttributeError):
            pass
        return None

    def verify_batch(self, batch, current_etag=None):
        key = batch['key']
        cached = self.cached_batch(batch)
        if current_etag and cached and cached['etag'] == current_etag:
            self.batch_checks['cache_hits'] += 1
            return
        self.batch_checks['downloads'] += 1
        response = self.s3.get_object(Bucket=self.bucket, Key=self.prefix+key)
        if response['ContentLength'] > 8*1024*1024:
            response['Body'].close()
            raise ValueError('Checkpoint batch exceeds monitoring size bound')
        try:
            raw = response['Body'].read(8*1024*1024+1)
        finally:
            response['Body'].close()
        if len(raw) > 8*1024*1024 or hashlib.sha256(raw).hexdigest() != batch['sha256'] or len(raw.splitlines()) != batch['records']:
            raise ValueError('Checkpoint batch verification failed: '+key)
        if self.batch_cache is not None:
            self.batch_cache[key] = {'sha256': batch['sha256'], 'records': batch['records'],
                                     'etag': response.get('ETag'),
                                     'verified_at': stamp()}

    def verify_batches(self, batches):
        groups = {}
        for batch in batches:
            key = batch['key']
            if '/' in key:
                groups.setdefault(key.rsplit('/', 1)[0]+'/', []).append(batch)
        etags = {}
        for prefix, group in groups.items():
            cached = [batch for batch in group if self.cached_batch(batch)]
            # LIST is usually dearer than GET. Require enough likely cache hits
            # and bound this to one listing before falling back to direct GETs.
            if len(cached) < 16:
                continue
            keys = sorted(self.prefix+batch['key'] for batch in cached)
            try:
                self.batch_checks['list_requests'] += 1
                page = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=self.prefix+prefix,
                                               StartAfter=keys[0][:-1], MaxKeys=1000)
            except Exception:
                continue
            for row in page.get('Contents', []):
                etags[row['Key'][len(self.prefix):]] = row.get('ETag')
        for batch in batches:
            self.verify_batch(batch, etags.get(batch['key']))

    def read(self, key):
        if key in self.cache:
            return self.cache[key]
        try:
            r = self.s3.get_object(Bucket=self.bucket, Key=self.prefix+key)
            # The shared runtime index grows with retained paths; ordinary
            # metadata keeps its smaller limit. Bound the actual read as well.
            limit = (32 if key == 'operations/s3-runtime/current.json' else 8)*1024*1024
            try:
                if r['ContentLength'] > limit:
                    raise ValueError('Monitoring metadata exceeds '+str(limit//(1024*1024))+' MiB: '+key)
                body = r['Body'].read(limit+1)
                if len(body) > limit:
                    raise ValueError('Monitoring metadata exceeds actual read bound: '+key)
            finally:
                r['Body'].close()
            value = json.loads(body)
            result = (value, hashlib.sha256(body).hexdigest(), stamp(r['LastModified'].timestamp()))
        except Exception as exc:
            if getattr(exc, 'response', {}).get('Error', {}).get('Code') not in ('NoSuchKey', '404'):
                raise
            result = (None, None, None)
        self.cache[key] = result
        return result

    def inventory(self, prefix):
        result = {}
        for n, page in enumerate(self.s3.get_paginator('list_objects_v2').paginate(Bucket=self.bucket, Prefix=self.prefix+prefix)):
            if n >= 100:
                raise ValueError('Monitoring metadata inventory exceeded 100,000 objects: '+prefix)
            for item in page.get('Contents', []):
                result[item['Key'][len(self.prefix):]] = item
        return result

    def confirmed(self, value):
        """Read committed manifest/verification evidence; never infer from stdout alone."""
        commits = []
        if isinstance(value, list):
            for item in value:
                commits.extend(self.confirmed(item))
        elif isinstance(value, dict):
            verification = value.get('verification_key')
            checksum = value.get('verification_sha256')
            manifest = value.get('last_manifest') or (value.get('manifest') if value.get('status') == 'complete' else None)
            if verification and checksum:
                document, actual, modified = self.read(verification)
                if not document or actual != checksum:
                    raise ValueError('Publication verification checksum mismatch: '+verification)
                commits.append((verification, document.get('checked_at') or modified))
            if manifest:
                document, _, modified = self.read(manifest)
                if document and document.get('status') == 'complete' and document.get('exhausted'):
                    commits.append((manifest, document.get('finished_at') or modified))
            # Only traverse outcome/evidence subtrees, not account data or raw records.
            for name in ('results', 'outcomes', 'sources', 'windows', 'last_result', 'last_attempt', 'last_complete', 'last_verified', 'universe_epochs'):
                item = value.get(name)
                if name == 'sources' and isinstance(item, dict):
                    item = list(item.values())
                if item is not None:
                    commits.extend(self.confirmed(item))
        return commits

    def checkpoint_commits(self, value):
        """Verify the latest reachable page, including in an unfinished run.

        Attempt starts and refreshed head timestamps are not progress. The
        immutable page receipt and every batch must match the current head.
        """
        commits, pending = [], False
        if isinstance(value, list):
            for item in value:
                observed, outstanding = self.checkpoint_commits(item)
                commits.extend(observed)
                pending |= outstanding
        elif isinstance(value, dict):
            key = value.get('manifest')
            if key:
                manifest, _, _ = self.read(key)
                if manifest and manifest.get('task_id') and manifest.get('task'):
                    head, _, _ = self.read('checkpoints/'+manifest['task_id']+'/head.json')
                    if head and head.get('task') == manifest['task']:
                        pending |= not head.get('exhausted', False)
                    if head and head.get('task') == manifest['task'] and head.get('pages'):
                        page = head['pages'][-1]
                        prefix = head['manifest_prefix'].rsplit('/', 1)[0]+'/'+page['run_id']
                        receipt = prefix+f"/pages/{page['sequence']:08d}-{digest(page)}.json"
                        saved, _, committed_at = self.read(receipt)
                        if saved != page:
                            raise ValueError('Checkpoint page receipt mismatch: '+receipt)
                        if len(page['batches']) > 100:
                            raise ValueError('Checkpoint page exceeds monitoring batch bound')
                        self.verify_batches(page['batches'])
                        count = sum(batch['records'] for batch in page['batches'])
                        if count != page['record_count']:
                            raise ValueError('Checkpoint page count mismatch: '+receipt)
                        commits.append((receipt, committed_at))
                # Hourly patent parents commit an hour only after its entire
                # scan completes. A bounded child can still have real pages.
                child_key = value.get('partition_manifest')
                if child_key and manifest and manifest.get('task', {}).get('scope', {}).get('partition_strategy') == 'hourly-v1':
                    child, _, _ = self.read(child_key)
                    parent_task = manifest['task']
                    child_task = (child or {}).get('task', {})
                    same = all(child_task.get(k) == parent_task.get(k) for k in
                               ('source','dataset','mode','collector_version','universe_hash','taxonomy_hash','window'))
                    bounds = child_task.get('scope', {}).get('query_bounds', [])
                    window = parent_task['window']
                    if (not same or len(bounds) != 2 or not
                            epoch(window['start']) <= epoch(bounds[0]) < epoch(bounds[1]) <= epoch(window['end'])):
                        raise ValueError('Patent partition task/window mismatch: '+child_key)
                    observed, outstanding = self.checkpoint_commits({'manifest': child_key})
                    commits.extend(observed)
                    pending |= outstanding
            for name in ('results', 'outcomes', 'sources', 'windows'):
                item = value.get(name)
                if name == 'sources' and isinstance(item, dict):
                    item = list(item.values())
                if item is not None:
                    observed, outstanding = self.checkpoint_commits(item)
                    commits.extend(observed)
                    pending |= outstanding
        return commits, pending


def apply_document_exceptions(value, decisions):
    """Remove only explicitly excepted document-denial alerts; retain raw audit evidence."""
    if isinstance(value, list):
        return [apply_document_exceptions(v, decisions) for v in value]
    if not isinstance(value, dict):
        return value
    result = {k: apply_document_exceptions(v, decisions) for k, v in value.items()}
    diagnostics = value.get('diagnostics', {})
    if (value.get('reason') == 'source_http_403' and diagnostics.get('host') == 'api.uspto.gov'
            and diagnostics.get('http_status') == 403
            and any(d.get('status') == 'active' and d.get('dataset') == 'patent_office_actions'
                    and d.get('application_number') == '16545140'
                    and diagnostics.get('path') == '/api/v1/patent/applications/16545140/documents'
                    for d in decisions)):
        result.update(status='excluded', reason='owner_accepted_document_access_gap')
    return result


def reconcile_repaired_outcomes(value, evidence):
    """Replace stale failures only with a newer, page-verified same-task outcome."""
    commits = []
    if isinstance(value, list):
        updated = []
        for item in value:
            item, observed = reconcile_repaired_outcomes(item, evidence)
            updated.append(item); commits.extend(observed)
        return updated, commits
    if not isinstance(value, dict): return value, commits
    result = dict(value)
    reason = value.get('reason') or value.get('reason_code')
    key = value.get('manifest')
    repairable = {'disclosure_unsupported_zip', 'hkex_non_pdf_response', 'hkex_original_empty_or_oversize', 'news_source_changed_refresh_required', 'news_duplicate_page_refresh_required', 'source_http_400',
                  'scrape_gateway_http_429', 'nih_split_count_changed',
                  'sam_count_mismatch', 'sam_source_changed_refresh_required'}
    if reason in repairable and isinstance(key, str) and key.startswith('manifests/collection_runs/'):
        old, _, _ = evidence.read(key)
        if old and old.get('task_id') and old.get('task'):
            head, _, _ = evidence.read('checkpoints/'+old['task_id']+'/head.json')
            replacement = (head or {}).get('terminal_manifest')
            if (head and head.get('task') == old['task'] and replacement and replacement != key
                    and replacement in head.get('terminal_history', [])):
                current, _, _ = evidence.read(replacement)
                if (current and current.get('task') == old['task']
                        and current.get('status') in {'complete', 'partial'}
                        and epoch(current.get('finished_at')) > epoch(old.get('finished_at'))):
                    observed, _ = evidence.checkpoint_commits({'manifest': replacement})
                    if observed and max(epoch(at) for _, at in observed) > epoch(old.get('finished_at')):
                        for name in ('reason', 'reason_code', 'error', 'error_type', 'capture_error'):
                            result.pop(name, None)
                        result.update(status=current['status'], reason=current.get('reason_code'),
                                      manifest=replacement, superseded_manifest=key)
                        commits.extend(observed)
    for name in ('results', 'outcomes', 'sources', 'windows', 'last_result', 'universe_epochs'):
        child = result.get(name)
        if isinstance(child, dict) and name == 'sources':
            revised = {}
            for k, v in child.items():
                revised[k], observed = reconcile_repaired_outcomes(v, evidence); commits.extend(observed)
            result[name] = revised
        elif isinstance(child, (dict, list)):
            result[name], observed = reconcile_repaired_outcomes(child, evidence); commits.extend(observed)
    return result, commits


def inspect_job(unit, policy, evidence, since, now):
    from source_pauses import unit_pause
    pause = unit_pause(unit)
    if not pause and policy.get('maintenance_pause_reason'):
        pause={'reason':policy['maintenance_pause_reason']}
    if pause:
        return {'operator_paused': pause, 'issues': [], 'progress': {'pending': False}}
    from constellation.m7_health import UNITS, view
    if (policy.get('execution_worker_unit') and unit in UNITS
            and getattr(evidence, 'worker_workload_mode', None) == 'historical_only'):
        from constellation.m7_historical_policy import HISTORICAL_DISPATCH_UNITS
        if UNITS[unit] not in HISTORICAL_DISPATCH_UNITS:
            return {'operator_paused': {'reason': 'Worker reserved for historical backfill'},
                    'issues': [], 'progress': {'pending': False}}
    worker = view(unit,evidence,now) if policy.get('execution_worker_unit') and unit in UNITS else None
    service = worker['service'] if worker else properties(unit)
    timer = properties(policy.get('timer', unit.replace('.service', '.timer')))
    state, elapsed = (worker['activity'],worker['elapsed']) if worker else activity(service, policy.get('serialized'))
    started = int(service.get('ExecMainStartTimestampMonotonic') or 0)/1e6
    # A newly enabled weekly timer may not have invoked its service this boot.
    # Its activation starts schedule grace; it does not establish data progress.
    schedule_started = started or int(timer.get('ActiveEnterTimestampMonotonic') or 0)/1e6
    reports, events, latest_commit = (worker['reports'],worker['events'],worker['latest_commit']) if worker else json_reports(unit)
    start_age = max(0, time.clock_gettime(time.CLOCK_BOOTTIME)-schedule_started) if schedule_started else now
    if worker and reports:
        # An unloaded remote oneshot can retain a start from a prior boot.
        # A recent journal outcome from the same worker proves an invocation.
        report_age = now - max(epoch(report.get('at')) for report in reports)
        if 0 <= report_age < start_age:
            start_age = report_age
    result = {'timer_enabled': timer.get('UnitFileState'), 'timer_state': timer.get('ActiveState'),
              'activity': state, 'activity_seconds': elapsed, 'result': service.get('Result'),
              'exit_status': int(service.get('ExecMainStatus') or 0),
              'last_start_age_seconds': start_age,
              'failure_events': [e for e in events if epoch(e['at']) > since], 'issues': [], 'evidence_keys': []}
    if worker:result['execution_host']={'instance_id':'i-06241bd1c4e91c2fc','unit':worker['worker_unit']}
    if worker and worker.get('scheduled_batch_wait'):
        result['scheduled_batch_wait'] = worker['scheduled_batch_wait']
        result['last_execution_result'] = result['result']
        result['result'] = None  # No current invocation while the worker sleeps.
    commits, pending, tokens = evidence.confirmed(latest_commit), False, []
    values = [(r['value'], r['at']) for r in reports]
    search_verified = False
    if unit == 'optima-search-capture.service':
        # Durable S3 state, independent of the collector's evictable RAM workspace.
        runtime, _, _ = evidence.read('operations/s3-runtime/current.json')
        pointers = sorted(k for k in (runtime or {}).get('paths', {})
                          if k.startswith('reports/search-capture-') and k.endswith('/publication.json'))
        pointer = None
        if pointers:
            entry = runtime['paths'][pointers[-1]]
            key = entry['key']
            if not key.startswith(evidence.prefix):
                raise ValueError('Search runtime pointer outside collection prefix')
            pointer, checksum, _ = evidence.read(key[len(evidence.prefix):])
            if checksum != entry['sha256']:
                raise ValueError('Search runtime pointer checksum mismatch')
        if pointer is None and not (ROOT / 'reports').is_symlink():
            paths = sorted((ROOT / 'reports').glob('search-capture-*/publication.json'))
            pointer = json.loads(paths[-1].read_text()) if paths else None
        if pointer:
            key = pointer.get('verification_s3_key', '')
            if key.startswith(evidence.prefix + 'search-capture/'):
                doc, _, _ = evidence.read(key[len(evidence.prefix):])
                if doc and doc.get('release_id') == pointer.get('release_id'):
                    query = doc.get('query', {})
                    count = sum(int(r[2]) for r in query.get('rows', [])[1:])
                    if query.get('status', {}).get('State') == 'SUCCEEDED' and count == doc.get('rows'):
                        raw = evidence.s3.get_object(Bucket=evidence.bucket, Key=doc['parquet_key'])['Body'].read()
                        if hashlib.sha256(raw).hexdigest() != doc['parquet_sha256']:
                            raise ValueError('Search publication checksum mismatch')
                        commits.append((key, doc['verified_at']))
                        search_verified = True
    market_states, market_registries = {}, {}
    market_keys = [key for key in policy.get('progress_keys', [])
                   if key.startswith('operations/market/automation/') and key.endswith(('/daily.json', '/historical.json'))]
    for key in policy.get('progress_keys', []):
        from source_pauses import is_paused
        if '/marketaux/' in key and is_paused('marketaux'):
            continue
        doc, _, modified = evidence.read(key)
        result['evidence_keys'].append(key)
        if doc is None:
            pending = True
            continue
        if gap := daily_reconciliation_gap(key, doc, evidence):
            result.setdefault('daily_reconciliation_gaps', []).append(gap)
        if key in market_keys:
            prefix, lane = key.rsplit('/', 1)
            if prefix not in market_registries:
                registry_doc, _, _ = evidence.read(prefix + '/coverage-exclusions.json')
                market_registries[prefix] = Exclusions(None, prefix, document=registry_doc)
            doc = reconcile_state(doc, lane.removesuffix('.json'), market_registries[prefix])
            market_states[key] = doc
        values.append((doc, modified))
        cursor = doc.get('next_date')
        end = policy.get('progress_end_exclusive', {}).get(key) or policy.get('end_exclusive') or stamp(now)[:10]
        if cursor:
            pending |= cursor < end
            tokens.append((key, cursor))
            if (unit == 'optima-conference-collection.service' and cursor >= end
                    and len(policy.get('progress_keys', [])) == 1 and evidence.confirmed(doc)):
                result['progress_scope_complete'] = {'checked_at': stamp(now), 'checkpoint': key,
                                                     'manifest': doc.get('last_manifest')}
        if 'symbols' in doc:
            unresolved_count = sum(unresolved(v) for v in doc['symbols'].values())
            if unresolved_count:
                result['issues'].append({'code': 'unresolved_market_coverage', 'severity': 'low',
                                         'detail': f'{unresolved_count} symbols have unverified coverage in {key}', 'at': modified})
            # Historical market work ends at the configured daily origin;
            # excluded historical gaps must not create a permanent stall flag.
            market_end = None
            if key in market_keys and key.endswith('/historical.json'):
                market_end = json.loads((ROOT/'config/market-operations.json').read_text())['daily_origin']
            pending |= any(v.get('next_date', '') < (market_end or end) for v in doc['symbols'].values())
            tokens.extend((key, name, item.get('next_date'), item.get('scan_next_date')) for name, item in doc['symbols'].items())
            # Confirm a bounded recent success sample; aggregate cursor tokens cover all symbols.
            recent = sorted((v for v in doc['symbols'].values()
                             if v.get('last_result', {}).get('status') == 'complete' or v.get('last_complete')),
                            key=lambda v: v.get('last_attempt', ''), reverse=True)[:3]
            for item in recent:
                commits.extend(evidence.confirmed(item))
        if key.endswith('latest-observation.json'):
            commits.append((str(doc.get('checked_at')), doc.get('checked_at') or modified))
    # Persisted operations reports contain nested failures omitted from terse stdout.
    for value, at in list(values):
        if isinstance(value, dict) and value.get('report_key'):
            doc, _, modified = evidence.read(value['report_key'])
            if doc:
                values.append((doc, modified))
    page_commits = []
    decisions = []
    if unit == 'optima-patents-prosecution.service':
        decisions = json.loads((ROOT/'config/patent-document-exceptions.json').read_text())['exceptions']
        result['document_exceptions'] = [d for d in decisions if d.get('status') == 'active']
        for decision in result['document_exceptions']:
            manifest = decision.get('recovery_manifest')
            if manifest and manifest.startswith('manifests/collection_runs/source=uspto_odp/dataset=patent_office_actions/'):
                recovered, _ = evidence.checkpoint_commits({'manifest': manifest})
                commits.extend(recovered)
                page_commits.extend(recovered)
    for value, at in values:
        if isinstance(value, dict) and value.get('reason') == 'worker_pool_memory_busy':
            result['resource_wait'] = 'worker_pool_memory_busy'
            pending = True
        value, repaired_commits = reconcile_repaired_outcomes(value, evidence)
        commits.extend(repaired_commits)
        for code, severity in outcome_issues(apply_document_exceptions(value, decisions)):
            result['issues'].append({'code': code, 'severity': severity, 'detail': code, 'at': at})
        commits.extend(evidence.confirmed(value))
        if policy.get('checkpoint_progress') or unit in {'optima-patents-daily.service', 'optima-nmpa-inventory.service'}:
            observed, outstanding = evidence.checkpoint_commits(value)
            commits.extend(observed)
            page_commits.extend(observed)
            pending |= outstanding
        def quota(value):
            if isinstance(value, dict):
                reason = value.get('reason', '')
                return (reason in EXPECTED and ('quota' in reason or 'daily' in reason)) or any(quota(v) for v in value.values() if isinstance(v, (dict, list)))
            return isinstance(value, list) and any(quota(v) for v in value)
        if quota(value):
            result['quota_wait'] = True
            pending = True
    # A later verified page proves that these earlier blocking source failures
    # were passed. Keep failures observed after the latest committed page.
    if page_commits:
        latest_page = max(epoch(at) for _, at in page_commits)
        recoverable = {'source_changed_refresh_required', 'source_http_413',
                       'rendered_source_unavailable', 'scrape_target_http_202', 'nmpa_page_out_of_range'}
        result['issues'] = [issue for issue in result['issues']
                            if issue['code'] not in recoverable or epoch(issue.get('at')) >= latest_page]
    if market_keys and len(market_states) == len(market_keys):
        items = [v for state in market_states.values() for v in state.get('symbols', {}).values()]
        excluded = sum(len(v.get('excluded_windows', {})) for v in items)
        outstanding = sum(unresolved(v) for v in items)
        empty = any(v.get('last_result', {}).get('reason') == 'market_empty_price_window_unverified' or
                    any(g.get('reason') == 'market_empty_price_window_unverified' for g in v.get('gaps', {}).values())
                    for v in items)
        by_lane = {}
        for key, state in market_states.items():
            lane = key.rsplit('/', 1)[-1].removesuffix('.json')
            by_lane[lane] = by_lane.get(lane, 0) + sum(unresolved(v) for v in state.get('symbols', {}).values())
        result['coverage_review'] = {'excluded_windows': excluded, 'unresolved_symbols_across_lanes': outstanding,
                                     'unresolved_symbols_by_lane': by_lane,
                                     'registry_keys': [r.key for r in market_registries.values()]}
        clear = set()
        if not empty:
            clear.add('market_empty_price_window_unverified')
        if not outstanding:
            clear.add('unresolved_market_coverage')
        # Current scoped checkpoints supersede older aggregate journal counts.
        result['issues'] = [issue for issue in result['issues'] if issue['code'] not in clear]
        for issue in result['issues']:
            if issue['code'] == 'unresolved_market_coverage':
                issue['detail'] = ('Unresolved coverage: ' + '; '.join(f'{lane}: {count} symbols' for lane, count in sorted(by_lane.items())) +
                                   f'. {excluded} windows excluded with reviewed evidence.')
            elif issue['code'] == 'market_empty_price_window_unverified':
                issue['detail'] = f'Empty price windows remain unverified outside the {excluded} reviewed window exclusions.'
        if excluded:
            result['coverage_resolutions'] = {code: {'at': stamp(now), 'basis': 'reviewed_scoped_exclusions',
                'registry_keys': result['coverage_review']['registry_keys']} for code in clear}
    verified_publication_receipts = []
    for scope in policy.get('publication_scopes', []):
        owner, prefix = scope['owner'], scope['queue_prefix']
        queue = evidence.inventory(prefix)
        if len(queue) > 256:
            raise ValueError('Scoped publication check exceeds 256 windows: '+prefix)
        outstanding = 0
        for key in queue:
            entry, _, _ = evidence.read(key)
            wid = (entry or {}).get('window_id', '')
            if len(wid) != 64 or any(c not in '0123456789abcdef' for c in wid):
                raise ValueError('Invalid scoped publication window: '+key)
            receipt_key = 'operations/'+owner+'/publication-receipts/'+wid+'.json'
            receipt, _, _ = evidence.read(receipt_key)
            verified = []
            if (receipt and receipt.get('status') == 'verified'
                    and receipt.get('window_id') == wid
                    and receipt.get('manifests') == entry.get('manifests')):
                verified = evidence.confirmed(receipt)
            if verified:
                document, _, _ = evidence.read(receipt['verification_key'])
                if document.get('window_id') != wid or document.get('status') != 'verified':
                    raise ValueError('Scoped publication verification identity mismatch: '+key)
                commits.extend(verified)
                tokens.append((prefix, wid, receipt['verification_sha256']))
            else:
                outstanding += 1
        pending |= bool(outstanding)
        result.setdefault('publication_backlog', {})[prefix] = outstanding
        result.setdefault('scoped_publication_checks', []).append({
            'queue_prefix': prefix, 'windows': len(queue), 'verified': len(queue)-outstanding,
            'checked_at': stamp(now)})
    for owner in policy.get('publication_owners', []):
        queue = evidence.inventory('operations/'+owner+'/publication-queue/')
        receipts = evidence.inventory('operations/'+owner+'/publication-receipts/')
        outstanding = [item for key, item in queue.items()
                       if key.replace('/publication-queue/', '/publication-receipts/') not in receipts or
                       receipts[key.replace('/publication-queue/', '/publication-receipts/')]['LastModified'] < item['LastModified']]
        pending |= bool(outstanding)
        result.setdefault('publication_backlog', {})[owner] = len(outstanding)
        # Receipt creation is progress; verify the most recent receipt's actual evidence.
        if receipts:
            newest = max(receipts, key=lambda k: receipts[k]['LastModified'])
            doc, _, _ = evidence.read(newest)
            verified = evidence.confirmed(doc)
            commits.extend(verified)
            if verified:
                verified_publication_receipts.append(newest)
            tokens.append((owner, newest, receipts[newest]['ETag']))
    if (policy.get('publication_owners') and not pending
            and len(verified_publication_receipts) == len(policy['publication_owners'])):
        result['publication_queue_drained'] = {'checked_at': stamp(now),
            'owners': list(policy['publication_owners']),
            'verified_receipts': verified_publication_receipts}
    # Historical patent publication tracks collected vs verified months.
    if policy.get('upstream_progress_key'):
        upstream, _, _ = evidence.read(policy['upstream_progress_key'])
        own, _, _ = evidence.read(policy['progress_keys'][0])
        pending = bool(upstream and upstream.get('next_date', '') > (own or {}).get('next_date', ''))
    # A completed process with verified output can recover a process failure
    # even when its already-complete data predates this invocation. This does
    # not close source failures or establish new collection progress.
    ended = int(service.get('ExecMainExitTimestampMonotonic') or 0)/1e6
    if (state in ('idle', 'scheduled_wait') and service.get('Result') == 'success' and
            result['exit_status'] == 0 and ended >= started > 0 and
            (search_verified or any(evidence.confirmed(r['value']) for r in reports) or
             (commits and result.get('publication_backlog') and
              not any(result['publication_backlog'].values()) and
              any(isinstance(r['value'], dict) and r['value'].get('status') == 'complete' for r in reports))) and
            reports and not any(outcome_issues(r['value']) for r in reports)):
        completed_at = now - max(0, time.clock_gettime(time.CLOCK_BOOTTIME)-ended)
        if any(epoch(r['at']) >= now-result['last_start_age_seconds'] for r in reports):
            result['successful_execution_at'] = stamp(completed_at)
    tokens.extend(key for key, _ in commits)
    result['progress'] = {'token': fingerprint(sorted(set(map(str, tokens)))) if tokens else None,
                          'pending': pending, 'last_verified_at': max((at for _, at in commits), key=epoch, default=None)}
    result['issues'] = list({i['code']: i for i in result['issues']}.values())
    return result


def export(config, s3, *, full_audit=False):
    now = time.time()
    watchdog = Watchdog(s3, None, config)
    previous = watchdog.get('health/latest.json') or {}
    since = max(epoch(previous.get('checked_at')), now-3600)
    cache_path = ROOT/'state'/'collection-health'/'health-verified-batches.json'
    try:
        batch_cache = json.loads(cache_path.read_text())
        if not isinstance(batch_cache, dict):
            raise ValueError('cache must be an object')
    except (OSError, ValueError):
        batch_cache = {}
    evidence = Evidence(s3, config['bucket'], config['data_prefix'], None if full_audit else batch_cache)
    from constellation.m7_health import UNITS
    from constellation.m7_batch import policy as worker_policy
    evidence.worker_workload_mode = worker_policy().get('mode')
    for unit,worker in UNITS.items():
        if unit in config['jobs']:config['jobs'][unit]['execution_worker_unit']=worker
    result = {'schema_version': 1, 'checked_at': stamp(now), 'bucket':config['bucket'], 'jobs': {}, 'errors': []}
    try:
        from constellation.m7_health import refresh
        evidence.worker_instance_state = refresh(config['bucket'])
    except Exception as exc:
        result['errors'].append('Worker execution inspection: '+str(exc)[:500])
    now=time.time()
    result['checked_at']=stamp(now)
    for unit, policy in config['jobs'].items():
        try:
            result['jobs'][unit] = inspect_job(unit, policy, evidence, since, now)
        except Exception as exc:
            result['jobs'][unit] = {'inspection_error': str(exc)[:500]}
    result['daily_audit'] = watchdog.get('daily-health/latest.json')
    try:
        pauses = json.loads((CONFIG / 'source-pauses.json').read_text())['sources']
        contracts = json.loads((CONFIG / 'metadata-engine.json').read_text())['contracts']
        paused_sources = set(pauses) | {source for source, contract in contracts.items()
                                        if contract.get('state') == 'owner_paused'}
        result['paused_sources'] = sorted(paused_sources)
        result['historical_capture_blockers'] = historical_capture_blockers(paused_sources, evidence)
    except (OSError, ValueError, KeyError) as exc:
        result['errors'].append('Historical coverage prerequisite inspection: '+str(exc)[:300])
    from pipeline_health import inspect_stages
    def inspect_future(unit):
        try:
            return inspect_job(unit, {'execution_worker_unit':UNITS.get(unit), 'serialized':False, 'queue_timeout_seconds':0,
                'execution_timeout_seconds':7200, 'max_start_gap_seconds':129600,
                'stale_progress_seconds':129600}, evidence, since, now)
        except Exception as exc:
            return {'inspection_error':str(exc)[:500]}
    def verify_artifact(artifact):
        key=artifact['key']
        if not key.startswith(('curated/','models/','training/','testing/','events/')):
            raise ValueError('Artifact must use a registered research-data output prefix')
        response=s3.get_object(Bucket=config['bucket'], Key=config['data_prefix'].rstrip('/')+'/'+key)
        if response['ContentLength'] > 1024**3:
            response['Body'].close()
            raise ValueError('Artifact exceeds 1 GiB monitoring checksum bound; supply a bounded validation artifact')
        checksum=hashlib.sha256(); size=0
        try:
            for chunk in response['Body'].iter_chunks(chunk_size=1024**2):
                checksum.update(chunk); size+=len(chunk)
        finally:response['Body'].close()
        if checksum.hexdigest()!=artifact['sha256'] or size!=artifact['bytes']:
            raise ValueError('Artifact checksum/size mismatch: '+key)
    try:
        registry=json.loads((ROOT/'config/pipeline-health-registry.json').read_text())
        units=[line.split()[0] for line in command(['systemctl','list-unit-files','optima-*','--no-legend','--no-pager']).splitlines() if line.split()]
        result['pipeline_stages']=inspect_stages(registry,units,inspect_future,
            lambda key:evidence.read(key)[0],verify_artifact)
    except Exception as exc:
        result['errors'].append('Pipeline stage inspection: '+str(exc)[:500])
    # Retain only a bounded recent cache.  It is an optimization, never an
    # authority: key/checksum/count must still match the current manifest.
    if len(batch_cache) > 100000:
        batch_cache = dict(sorted(batch_cache.items(), key=lambda item: (
            item[1].get('verified_at','') if isinstance(item[1], dict) else ''), reverse=True)[:100000])
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile('w', dir=cache_path.parent, delete=False) as handle:
            json.dump(batch_cache, handle, sort_keys=True)
            handle.write('\n')
            temporary = Path(handle.name)
        temporary.replace(cache_path)
    except OSError as exc:
        result['errors'].append('Batch verification cache not persisted: '+str(exc)[:200])
    result['s3_batch_checks'] = evidence.batch_checks
    watchdog.put('health/latest.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record-alerts', action='store_true', help='Local recording while independent AWS deployment is blocked; sends no notifications.')
    parser.add_argument('--full-audit', action='store_true', help='Download and reverify every referenced checkpoint batch.')
    args = parser.parse_args()
    import boto3
    config = json.loads((ROOT/'config/collection-monitoring.json').read_text())
    s3 = boto3.client('s3', region_name=config['region'])
    result = export(config, s3, full_audit=args.full_audit)
    print(json.dumps({'checked_at': result['checked_at'], 'jobs': len(result['jobs']),
                      's3_batch_checks': result['s3_batch_checks'],
                      'inspection_errors': {u: j['inspection_error'] for u,j in result['jobs'].items() if 'inspection_error' in j}}))
    if args.record_alerts:
        print(json.dumps(Watchdog(s3, None, config).run(notifications=False)))


if __name__ == '__main__':
    main()
