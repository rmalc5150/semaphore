"""Estimate eligible historical execution time for the dedicated C7 worker."""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_CACHE = ROOT / 'constellation/autostop/m7-historical-openalex-parts.json'
HISTORICAL_DISPATCH_UNITS = frozenset({'optima-m7-capture-assignments-reviewed-historical.service'})
NON_BACKFILL_ROUTE_KINDS = frozenset({'independent_public_daily', 'migration_probe'})


def seed_openalex_manifest(public):
    from constellation.research_feeds import snapshot_manifest
    document, raw, _ = snapshot_manifest(public)
    index = {'sha256': hashlib.sha256(raw).hexdigest(),
             'parts': [[row['meta']['content_length'], row['meta']['record_count']] for row in document['files']]}
    temp = MANIFEST_CACHE.with_suffix('.new')
    temp.write_text(json.dumps(index, separators=(',', ':')) + '\n')
    temp.replace(MANIFEST_CACHE)
    return index


def snapshot_estimate(progress, index, settings):
    position = int((progress or {}).get('next_part', 0))
    parts = index['parts']
    if progress and progress.get('snapshot_sha256') != index['sha256']:
        raise ValueError('OpenAlex checkpoint manifest differs from the validated size index')
    if not 0 <= position <= len(parts):
        raise ValueError('OpenAlex checkpoint position is outside its manifest')
    remaining = parts[position:]
    storage = sum(row[0] for row in remaining)
    records = sum(row[1] for row in remaining)
    # Use optimistic observed throughput, and the shorter estimate, to avoid
    # waking a 12-hour worker for marginal work. One shared checkpoint is counted
    # once even when the trial host also works on it.
    seconds = int(3600 * min(storage / (1024**3 * settings['openalex_fast_gib_per_hour']),
                             records / settings['openalex_fast_records_per_hour']))
    return {'parts': len(remaining), 'bytes': storage, 'provider_rows': records, 'estimated_seconds': seconds}


def pool_estimate(ready, settings):
    """Do not add wall-clock estimates for work that can run in parallel."""
    occupied = {'raw': 0, 'legacy': 0}
    longest_source = 0
    for source, total in ready.items():
        lane = 'legacy' if source.startswith('legacy:') else 'raw'
        seconds = settings.get('seconds_per_job_by_source', {}).get(source, settings[lane + '_seconds_per_job'])
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError('Invalid historical duration profile for ' + source)
        demand = total * seconds
        occupied[lane] += demand
        source_slots = 1 if lane == 'legacy' or source == 'arxiv' else 2
        longest_source = max(longest_source, demand / source_slots)
    return int(max(longest_source, occupied['raw'] / settings['raw_slots'],
                   occupied['legacy'] / settings['legacy_slots']))


def eligible_work(now, settings):
    from constellation.control import Control
    from constellation.legacy_routes import manifest
    from constellation.research_feeds import Evidence, OPENALEX, KAKEN, FLOOR, JAPAN, fiscal_year
    from datetime import datetime
    from source_pauses import is_paused, unit_pause

    control = Control()
    gate = control.get('control') or {}
    remaining_authorization = max(0, int(gate.get('stop_after_epoch', 0) - now))
    active = bool(gate.get('enabled') and remaining_authorization > 0)
    result = {'authorization_seconds': remaining_authorization, 'capture_enabled': active,
              'ready': 0, 'leased': 0, 'estimated_seconds': 0, 'has_work': False}
    if not active:
        return result
    routes = {r['unit']: r for r in manifest()['routes']}
    ready = {}
    with control.db() as cursor:
        cursor.execute("""SELECT source_key,
            SUM(lease_until < %s AND next_attempt_at <= %s AND attempts < 3) ready,
            SUM(status='running' AND lease_until >= %s) leased
          FROM backfill_jobs FORCE INDEX (claimable)
          WHERE status IN ('pending','running','retryable_failed') AND source_key <> '__lease_check__'
          GROUP BY source_key""", (now, now, now))
        for row in cursor.fetchall():
            source = row['source_key']
            if source.startswith('legacy:'):
                unit = source.removeprefix('legacy:')
                route = routes.get(unit)
                if (not route or not route['execution_enabled'] or route['route_kind'] in NON_BACKFILL_ROUTE_KINDS
                        or unit_pause(route.get('original_unit', unit))
                        or route.get('specialist_source') and is_paused(route['specialist_source'])):
                    continue
            elif is_paused(source):
                continue
            if row['ready']:
                ready[source] = int(row['ready'])
            result['leased'] += int(row['leased'] or 0)
    result['ready'] = sum(ready.values())
    result['queue_estimated_seconds'] = pool_estimate(ready, settings)
    result['estimated_seconds'] = result['queue_estimated_seconds']
    evidence = Evidence(control)
    feeds, _ = evidence.state('control.json')
    if feeds and feeds.get('historical_enabled'):
        if not is_paused(OPENALEX):
            progress, _ = evidence.state(f'progress/{OPENALEX}/snapshot.json')
            index = json.loads(MANIFEST_CACHE.read_text())
            result['openalex'] = snapshot_estimate(progress, index, settings)
            result['estimated_seconds'] = max(result['estimated_seconds'], result['openalex']['estimated_seconds'])
        if not is_paused(KAKEN):
            kaken, _ = evidence.state(f'progress/{KAKEN}/historical.json')
            year = int((kaken or {}).get('next', FLOOR.year))
            if year < fiscal_year(datetime.fromtimestamp(now, JAPAN).date()):
                cp, _ = evidence.state(f'checkpoints/{KAKEN}/historical/fy-{year}.json')
                result['kaken_pending'] = not (cp and cp.get('exhausted') and cp.get('coverage_status') == 'partial')
    result['has_work'] = bool(result['ready'] or result['leased'] or result.get('openalex', {}).get('parts')
                             or result.get('kaken_pending'))
    return result


def meets_wake_threshold(work, threshold_seconds):
    return (work['capture_enabled'] and work['authorization_seconds'] >= threshold_seconds
            and work['estimated_seconds'] >= threshold_seconds)
