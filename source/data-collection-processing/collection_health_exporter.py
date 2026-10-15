#!/usr/bin/env python3
"""Read systemd, bounded journals and S3 metadata without touching collectors."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

from collection_alerts import EXPECTED, Watchdog, epoch, fingerprint, outcome_issues, stamp
from market_coverage_exclusions import Exclusions, reconcile_state, unresolved
from research_contract import digest

ROOT = Path(__file__).resolve().parent


def command(args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=30).stdout


def properties(unit):
    fields = ['ActiveState', 'SubState', 'UnitFileState', 'Result', 'MainPID',
              'ExecMainStatus', 'ExecMainStartTimestampMonotonic', 'ExecMainExitTimestampMonotonic', 'ControlGroup']
    return dict(line.split('=', 1) for line in command(
        ['systemctl', 'show', unit, '--no-pager', '--property='+','.join(fields)]).splitlines() if '=' in line)


def activity(props, serialized):
    if props.get('ActiveState') not in ('activating', 'active', 'deactivating'):
        return 'idle', 0
    started = int(props.get('ExecMainStartTimestampMonotonic') or 0) / 1e6
    elapsed = max(0, time.clock_gettime(time.CLOCK_BOOTTIME) - started)
    if not serialized:
        return 'running', elapsed
    cg = Path('/sys/fs/cgroup') / props['ControlGroup'].lstrip('/')
    pids = (cg/'cgroup.procs').read_text().splitlines()
    ticks = __import__('os').sysconf('SC_CLK_TCK')
    payload_starts = []
    for pid in pids:
        try:
            name = Path('/proc', pid, 'comm').read_text().strip()
            if name not in {'flock', 'timeout'}:
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
    def __init__(self, s3, bucket, data_prefix):
        self.s3, self.bucket = s3, bucket
        self.prefix = data_prefix.rstrip('/')+'/'
        self.cache = {}

    def read(self, key):
        if key in self.cache:
            return self.cache[key]
        try:
            r = self.s3.get_object(Bucket=self.bucket, Key=self.prefix+key)
            if r['ContentLength'] > 8*1024*1024:
                raise ValueError('Monitoring metadata exceeds 8 MiB: '+key)
            body = r['Body'].read()
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
            for name in ('results', 'sources', 'windows', 'last_result', 'last_attempt', 'last_complete', 'last_verified', 'universe_epochs'):
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
                        count = 0
                        for batch in page['batches']:
                            response = self.s3.get_object(Bucket=self.bucket, Key=self.prefix+batch['key'])
                            if response['ContentLength'] > 8*1024*1024:
                                raise ValueError('Checkpoint batch exceeds monitoring size bound')
                            raw = response['Body'].read()
                            if (hashlib.sha256(raw).hexdigest() != batch['sha256'] or
                                    len(raw.splitlines()) != batch['records']):
                                raise ValueError('Checkpoint batch verification failed: '+batch['key'])
                            count += batch['records']
                        if count != page['record_count']:
                            raise ValueError('Checkpoint page count mismatch: '+receipt)
                        commits.append((receipt, committed_at))
            for name in ('results', 'sources', 'windows'):
                item = value.get(name)
                if name == 'sources' and isinstance(item, dict):
                    item = list(item.values())
                if item is not None:
                    observed, outstanding = self.checkpoint_commits(item)
                    commits.extend(observed)
                    pending |= outstanding
        return commits, pending


def inspect_job(unit, policy, evidence, since, now):
    service = properties(unit)
    timer = properties(policy.get('timer', unit.replace('.service', '.timer')))
    state, elapsed = activity(service, policy.get('serialized'))
    started = int(service.get('ExecMainStartTimestampMonotonic') or 0)/1e6
    reports, events, latest_commit = json_reports(unit)
    result = {'timer_enabled': timer.get('UnitFileState'), 'timer_state': timer.get('ActiveState'),
              'activity': state, 'activity_seconds': elapsed, 'result': service.get('Result'),
              'exit_status': int(service.get('ExecMainStatus') or 0),
              'last_start_age_seconds': max(0, time.clock_gettime(time.CLOCK_BOOTTIME)-started) if started else now,
              'failure_events': [e for e in events if epoch(e['at']) > since], 'issues': [], 'evidence_keys': []}
    commits, pending, tokens = evidence.confirmed(latest_commit), False, []
    values = [(r['value'], r['at']) for r in reports]
    search_verified = False
    if unit == 'optima-search-capture.service':
        paths = sorted((ROOT / 'reports').glob('search-capture-*/publication.json'))
        if paths:
            pointer = json.loads(paths[-1].read_text())
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
        doc, _, modified = evidence.read(key)
        result['evidence_keys'].append(key)
        if doc is None:
            pending = True
            continue
        if key in market_keys:
            prefix, lane = key.rsplit('/', 1)
            if prefix not in market_registries:
                registry_doc, _, _ = evidence.read(prefix + '/coverage-exclusions.json')
                market_registries[prefix] = Exclusions(None, prefix, document=registry_doc)
            doc = reconcile_state(doc, lane.removesuffix('.json'), market_registries[prefix])
            market_states[key] = doc
        values.append((doc, modified))
        cursor = doc.get('next_date')
        end = policy.get('end_exclusive') or stamp(now)[:10]
        if cursor:
            pending |= cursor < end
            tokens.append((key, cursor))
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
    for value, at in values:
        for code, severity in outcome_issues(value):
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
            commits.extend(evidence.confirmed(doc))
            tokens.append((owner, newest, receipts[newest]['ETag']))
    # Historical patent publication tracks collected vs verified months.
    if policy.get('upstream_progress_key'):
        upstream, _, _ = evidence.read(policy['upstream_progress_key'])
        own, _, _ = evidence.read(policy['progress_keys'][0])
        pending = bool(upstream and upstream.get('next_date', '') > (own or {}).get('next_date', ''))
    # A completed process with verified output can recover a process failure
    # even when its already-complete data predates this invocation. This does
    # not close source failures or establish new collection progress.
    ended = int(service.get('ExecMainExitTimestampMonotonic') or 0)/1e6
    if (state == 'idle' and service.get('Result') == 'success' and
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


def export(config, s3):
    now = time.time()
    watchdog = Watchdog(s3, None, config)
    previous = watchdog.get('health/latest.json') or {}
    since = max(epoch(previous.get('checked_at')), now-3600)
    evidence = Evidence(s3, config['bucket'], config['data_prefix'])
    result = {'schema_version': 1, 'checked_at': stamp(now), 'bucket':config['bucket'], 'jobs': {}, 'errors': []}
    for unit, policy in config['jobs'].items():
        try:
            result['jobs'][unit] = inspect_job(unit, policy, evidence, since, now)
        except Exception as exc:
            result['jobs'][unit] = {'inspection_error': str(exc)[:500]}
    result['daily_audit'] = watchdog.get('daily-health/latest.json')
    from pipeline_health import inspect_stages
    def inspect_future(unit):
        try:
            return inspect_job(unit, {'serialized':False, 'queue_timeout_seconds':0,
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
    watchdog.put('health/latest.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record-alerts', action='store_true', help='Local recording while independent AWS deployment is blocked; sends no notifications.')
    args = parser.parse_args()
    import boto3
    config = json.loads((ROOT/'config/collection-monitoring.json').read_text())
    s3 = boto3.client('s3', region_name=config['region'])
    result = export(config, s3)
    print(json.dumps({'checked_at': result['checked_at'], 'jobs': len(result['jobs']),
                      'inspection_errors': {u: j['inspection_error'] for u,j in result['jobs'].items() if 'inspection_error' in j}}))
    if args.record_alerts:
        print(json.dumps(Watchdog(s3, None, config).run(notifications=False)))


if __name__ == '__main__':
    main()
